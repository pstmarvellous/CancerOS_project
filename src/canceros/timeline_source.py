"""Resolve source timelines from one immutable revision and a separate knowledge cutoff."""

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text

from canceros.clinical_ingestion import read_record
from canceros.contracts import Context, Provenance
from canceros.identity import authorize_project
from canceros.lineage import require_resource_action
from canceros.patient_linkage import authorize_patient
from canceros.persistence import load_revision, science_hash
from canceros.source_registry import SourceAction
from canceros.temporal_timeline import TimelinePoint, TimelineWindow, from_clinical_record

MAX_CANDIDATES = 2000
MAX_CHAIN_DEPTH = 128


def load_source_points(c, i, p, u, window: TimelineWindow) -> tuple[list[TimelinePoint], list[str]]:
    """Never consult live heads, merge branches or restore currently withdrawn source data."""
    authorize_project(i, p, "editor")
    authorize_patient(c, i, p, u)
    if window.scope.mode not in ("observed", "source_fixture"):
        raise HTTPException(422, detail="source_timeline_scope_required")
    if window.scope.branch_id is not None or window.scope.run_id is not None:
        raise HTTPException(422, detail="source_timeline_cannot_select_simulation_branch")
    try:
        manifest = load_revision(c, p, u, window.scope.data_revision)
    except LookupError:
        raise HTTPException(409, detail="timeline_revision_unavailable") from None
    except ValueError:
        raise HTTPException(409, detail="timeline_revision_integrity_failed") from None
    members, retractions = manifest.get("members", []), manifest.get("retractions", [])
    if len(members) + len(retractions) > MAX_CANDIDATES:
        raise HTTPException(413, detail="source_timeline_candidate_limit_exceeded")
    candidates = {UUID(value) for value in members}
    retracted = set()
    for identifier in retractions:
        row = c.execute(
            text(
                "SELECT record_id,recorded_at FROM clinical.retractions "
                "WHERE project_id=:p AND patient_id=:u AND id=:id"
            ),
            {"p": p, "u": u, "id": UUID(identifier)},
        ).one_or_none()
        if row is None:
            raise HTTPException(409, detail="timeline_retraction_reference_unavailable")
        if row.recorded_at > window.knowledge_as_of:
            candidates.add(row.record_id)
        else:
            retracted.add(row.record_id)
    selected: dict[str, Any] = {}
    cache = {}
    for candidate in sorted(candidates, key=str):
        current, seen = candidate, set()
        for _ in range(MAX_CHAIN_DEPTH):
            if current in seen:
                raise HTTPException(409, detail="source_timeline_correction_cycle")
            seen.add(current)
            if current not in cache:
                cache[current] = c.execute(
                    text(
                        "SELECT id,logical_key,supersedes_id,payload,payload_hash,recorded_at "
                        "FROM clinical.observations WHERE project_id=:p AND patient_id=:u AND id=:id"
                    ),
                    {"p": p, "u": u, "id": current},
                ).one_or_none()
            row = cache[current]
            if row is None or science_hash(row.payload) != row.payload_hash:
                raise HTTPException(409, detail="source_timeline_record_integrity_failed")
            if row.recorded_at <= window.knowledge_as_of:
                if row.id not in retracted:
                    prior = selected.get(row.logical_key)
                    if prior is None or (row.recorded_at, str(row.id)) > (
                        prior.recorded_at,
                        str(prior.id),
                    ):
                        selected[row.logical_key] = row
                break
            if row.supersedes_id is None:
                break
            current = row.supersedes_id
        else:
            raise HTTPException(413, detail="source_timeline_correction_depth_exceeded")
    points, restrictions = [], set()
    for row in sorted(selected.values(), key=lambda value: (value.recorded_at, str(value.id))):
        record = read_record(c, i, p, u, row.id)
        if window.scope.mode == "observed":
            if record.context != Context.OBSERVED or record.origin not in (
                Provenance.REAL_OBSERVED,
                Provenance.REAL_DERIVED,
            ):
                continue
        elif record.context != Context.SYNTHETIC or record.origin != Provenance.SYNTHETIC_GENERATED:
            continue
        try:
            for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE):
                require_resource_action(c, i, p, u, row.id, action)
        except HTTPException:
            restrictions.add("current_source_access_restricted")
            continue
        points.append(
            from_clinical_record(
                record,
                row.recorded_at,
                window.scope.data_revision,
                row.payload_hash,
                supersedes_id=row.supersedes_id,
            )
        )
    return points, sorted(restrictions)
