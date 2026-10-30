"""Private revision-pinned observation pages; future generator targets are never read."""

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID, uuid5

from fastapi import HTTPException
from pydantic import Field
from sqlalchemy import text

from canceros.clinical_contracts import ClinicalTime, ExactResult
from canceros.clinical_generation_runs import read_clinical_batch
from canceros.clinical_ingestion import read_record
from canceros.contracts import Availability, Context, Contract, Quantity, RelativeTime
from canceros.identity import authorize_project
from canceros.lesion_tracking import read_association
from canceros.lineage import get_resource, lock_lineage
from canceros.measurement_runs import read_measurement
from canceros.patient_linkage import authorize_patient
from canceros.persistence import science_hash
from canceros.simulation_execution import read_completion
from canceros.simulation_runs import _usable, read_run
from canceros.synthetic_geometry import read_geometry_result
from canceros.temporal_timeline import (
    TemporalFeatures,
    TimelinePoint,
    TimelineWindow,
    extract_features,
    from_generated_event,
    select_window,
)
from canceros.timeline_source import load_source_points
from canceros.twin_states import Publication, _latest, read_branch, read_state


class TimelineQuery(Contract):
    window: TimelineWindow
    completion_id: UUID | None = None
    limit: Annotated[int, Field(strict=True, ge=1, le=100)] = 25
    cursor: Annotated[str, Field(max_length=128)] | None = None


class TimelinePage(Contract):
    version: Literal["timeline-page/1"] = "timeline-page/1"
    window: TimelineWindow
    completion_id: UUID | None
    items: list[TimelinePoint]
    features: TemporalFeatures
    total_points: int
    next_cursor: str | None
    current_patient_revision: int
    historical_revision: bool
    restrictions: list[str]
    next_action: str


def _hash(c, i, p, u, identifier):
    _usable(c, i, p, u, identifier)
    return get_resource(c, i, p, u, identifier)["content_hash"]


def read_window_points(c, i, p, u, value: TimelineQuery):
    """One complete authorized input window for deterministic derivatives, never one page."""
    authorize_project(i, p, "admin")
    authorize_patient(c, i, p, u, edit=True)
    lock_lineage(c, p, u)
    if value.cursor is not None:
        raise HTTPException(422, detail="derivative_requires_complete_window_not_pagination_cursor")
    if (value.window.scope.mode == "simulation") != (value.completion_id is not None):
        raise HTTPException(422, detail="completion_id_only_for_simulation_timeline")
    points, restrictions = (
        _simulation_points(c, i, p, u, value)
        if value.window.scope.mode == "simulation"
        else load_source_points(c, i, p, u, value.window)
    )
    try:
        selected = select_window(points, value.window)
    except ValueError:
        raise HTTPException(409, detail="timeline_window_or_membership_invalid") from None
    _assert_snapshot_rights(c, i, p, u, selected)
    return selected, restrictions


def _assert_snapshot_rights(c, i, p, u, points):
    resources = set()
    for point in points:
        if point.branch_id is None and point.measurement_basis == "source_record":
            # Source locators are evidence references, not registry resource IDs.
            # The clinical record's lineage recursively enforces artifact/source rights.
            record = read_record(c, i, p, u, point.id)
            if point.source_ids != [record.id, record.item.source_locator_id]:
                raise HTTPException(409, detail="timeline_source_reference_integrity_failed")
            resources.add(record.id)
        else:
            resources.update(point.source_ids)
    for resource in resources:
        try:
            _usable(c, i, p, u, resource)
        except HTTPException:
            raise HTTPException(
                409, detail="timeline_snapshot_access_changed_start_new_query"
            ) from None


def _simulation_points(c, i, p, u, query):
    if query.completion_id is None:
        raise HTTPException(422, detail="simulation_timeline_requires_exact_published_completion")
    scope = query.window.scope
    completion = read_completion(c, i, p, u, query.completion_id)
    if (
        completion.run_id != scope.run_id
        or completion.branch_id != scope.branch_id
        or completion.input_revision != scope.data_revision
    ):
        raise HTTPException(409, detail="timeline_completion_scope_mismatch")
    publication = c.execute(
        text(
            "SELECT report,report_hash FROM imaging.simulation_publications WHERE project_id=:p AND patient_id=:u AND completion_id=:id ORDER BY (report->>'recorded_at')::timestamptz,id LIMIT 1"
        ),
        {"p": p, "u": u, "id": completion.id},
    ).one_or_none()
    if publication is None or science_hash(publication.report) != publication.report_hash:
        raise HTTPException(409, detail="complete_run_not_published_or_integrity_failed")
    from canceros.simulation_execution import RunPublication

    published = RunPublication.model_validate(publication.report)
    recorded_at = published.recorded_at
    run = read_run(c, i, p, u, completion.run_id)
    branch = read_branch(c, i, p, u, run.branch_id)
    batch = read_clinical_batch(c, i, p, u, completion.clinical_batch_id)
    points: dict[UUID, TimelinePoint] = {}
    results = {
        read_geometry_result(c, i, p, u, r).geometry.id: r for r in completion.geometry_result_ids
    }
    association_id = c.execute(
        text(
            "SELECT id FROM imaging.lesion_association_events WHERE project_id=:p AND patient_id=:u AND measurement_id=:m AND sequence<=:h ORDER BY sequence DESC LIMIT 1"
        ),
        {
            "p": p,
            "u": u,
            "m": branch.input.baseline_measurement_id,
            "h": completion.association_head,
        },
    ).scalar_one_or_none()
    association = read_association(c, i, p, u, association_id) if association_id else None
    lesion = (
        association.input.lesion_id
        if association
        and association.input.status == "matched"
        and association.input.relation == "same_lesion"
        else None
    )
    for state_id in completion.state_ids:
        state = read_state(c, i, p, u, state_id)
        if not _latest(c, i, p, u, "twin_publications", state_id, Publication):
            raise HTTPException(409, detail="complete_run_state_not_published")
        for member in state.snapshot.generated_clinical_members:
            if member.batch_id != batch.id or member.run_id != run.id:
                raise HTTPException(409, detail="timeline_state_batch_mismatch")
            for event in member.events:
                point = from_generated_event(
                    event,
                    u,
                    recorded_at,
                    completion.input_revision,
                    member.source_hash,
                    timeline_origin_id=branch.input.timeline_origin_id,
                    state_ids=[state_id],
                    lesion_id=lesion if event.modality == "imaging" else None,
                    measurement_basis="simulated_target_no_mask_realization"
                    if event.modality == "imaging"
                    else "source_record",
                )
                points[point.id] = point.model_copy(update={"source_ids": [batch.id, run.id]})
        for member in state.snapshot.generated_geometry_members:
            geometry = member.geometry
            result_id = results.get(geometry.id)
            measured = geometry.shape.realized_values
            if result_id is None or measured is None or measured.volume_mm3 is None:
                raise HTTPException(409, detail="timeline_realized_geometry_unavailable")
            point = TimelinePoint(
                id=geometry.id,
                patient_id=u,
                time=ClinicalTime(reference=geometry.time, precision="relative_day"),
                recorded_at=recorded_at,
                revision=completion.input_revision,
                origin=geometry.origin,
                context=Context.SYNTHETIC,
                modality="imaging",
                concept="numerical_region_volume",
                numeric_result=ExactResult(
                    form="exact", quantity=Quantity(value=measured.volume_mm3, unit="mm3")
                ),
                exact_value=measured.exact_volume_mm3,
                metric_definition=geometry.target_metric,
                availability=Availability.AVAILABLE,
                source_ids=[geometry.id, result_id] + ([association.id] if association else []),
                source_hash=_hash(c, i, p, u, geometry.id),
                state_ids=[state_id],
                geometry_result_id=result_id,
                lesion_id=lesion,
                measurement_basis="mask_realized",
                method_version=measured.version,
                branch_id=run.branch_id,
                run_id=run.id,
            )
            points[point.id] = point
        if state.snapshot.time.value == "0":
            measurement = read_measurement(c, i, p, u, branch.input.baseline_measurement_id)
            if measurement.values.volume_mm3 is None:
                raise HTTPException(409, detail="baseline_reference_quantity_unavailable")
            identifier = uuid5(run.id, "timeline-shared-baseline-reference/1")
            points[identifier] = TimelinePoint(
                id=identifier,
                patient_id=u,
                time=ClinicalTime(
                    reference=RelativeTime(
                        basis="relative_day",
                        value="0",
                        time_domain="simulation",
                        timeline_origin_id=branch.input.timeline_origin_id,
                    ),
                    precision="relative_day",
                ),
                recorded_at=recorded_at,
                revision=completion.input_revision,
                origin=measurement.origin,
                context=Context.SYNTHETIC,
                modality="imaging",
                concept=measurement.definition,
                numeric_result=ExactResult(
                    form="exact", quantity=Quantity(value=measurement.values.volume_mm3, unit="mm3")
                ),
                exact_value=measurement.values.exact_volume_mm3,
                metric_definition=measurement.definition,
                availability=Availability.AVAILABLE,
                source_ids=[measurement.id, run.id] + ([association.id] if association else []),
                source_hash=_hash(c, i, p, u, measurement.id),
                state_ids=[state_id],
                lesion_id=lesion,
                measurement_basis="baseline_reference",
                method_version=measurement.values.version,
                historical_context=True,
                summary="Shared engineering baseline reference; no authentic observed baseline approval",
                branch_id=run.branch_id,
                run_id=run.id,
            )
    return list(points.values()), []


def query_timeline(c, i, p, u, value: TimelineQuery):
    authorize_project(i, p, "admin")
    authorize_patient(c, i, p, u, edit=True)
    lock_lineage(c, p, u)
    if (value.window.scope.mode == "simulation") != (value.completion_id is not None):
        raise HTTPException(422, detail="completion_id_only_for_simulation_timeline")
    scope_hash = science_hash(
        {
            "actor": str(i.user_id),
            "project": str(p),
            "patient": str(u),
            "query": value.model_dump(mode="json", exclude={"cursor"}),
        }
    )
    now = datetime.now(timezone.utc)
    if value.cursor:
        row = c.execute(
            text(
                "SELECT scope_hash,manifest,manifest_hash,expires_at FROM imaging.twin_cursors WHERE token_hash=:h"
            ),
            {"h": hashlib.sha256(value.cursor.encode()).hexdigest()},
        ).one_or_none()
        if (
            row is None
            or row.scope_hash != scope_hash
            or row.expires_at <= now
            or science_hash(row.manifest) != row.manifest_hash
        ):
            raise HTTPException(409, detail="timeline_cursor_expired_or_scope_changed")
        manifest = row.manifest
        points = [TimelinePoint.model_validate(point) for point in manifest["points"]]
        restrictions = manifest["restrictions"]
    else:
        points, restrictions = read_window_points(c, i, p, u, value)
        manifest = {
            "points": [point.model_dump(mode="json") for point in points],
            "restrictions": restrictions,
            "offset": 0,
        }
    # Cursor snapshots retain exact membership, but never bypass current withdrawal/access.
    _assert_snapshot_rights(c, i, p, u, points)
    features = extract_features(points, value.window)
    offset = manifest["offset"]
    cursor = None
    if offset + value.limit < len(points):
        cursor = secrets.token_urlsafe(32)
        following = {**manifest, "offset": offset + value.limit}
        c.execute(
            text(
                "INSERT INTO imaging.twin_cursors VALUES(:h,:scope,CAST(:manifest AS jsonb),:digest,:expires)"
            ),
            {
                "h": hashlib.sha256(cursor.encode()).hexdigest(),
                "scope": scope_hash,
                "manifest": json.dumps(following),
                "digest": science_hash(following),
                "expires": now + timedelta(minutes=15),
            },
        )
    current = c.execute(
        text("SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"),
        {"p": p, "u": u},
    ).scalar_one()
    return TimelinePage(
        window=value.window,
        completion_id=value.completion_id,
        items=points[offset : offset + value.limit],
        features=features,
        total_points=len(points),
        next_cursor=cursor,
        current_patient_revision=current,
        historical_revision=current != value.window.scope.data_revision,
        restrictions=restrictions,
        next_action="Select an exact observation/state; only points with geometry offer a current 3D view",
    )
