"""Explicit durable revision projections; immutable science and publication stay separate."""

from __future__ import annotations

from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from canceros.contracts import Contract, Hash
from canceros.identity import authorize_project
from canceros.lineage import derive_resource, get_resource, lock_lineage, processing_spec
from canceros.patient_linkage import authorize_patient
from canceros.persistence import canonical_bytes, load_revision, science_hash
from canceros.simulation_runs import _usable
from canceros.state_fusion import FusionReport, fuse_state
from canceros.temporal_timeline import TemporalFeatures, extract_features
from canceros.temporal_trends import TrendReport, analyze_trends
from canceros.timeline_runs import TimelineQuery, read_window_points
from canceros.twin_states import (
    StateBuildInput,
    _measurement,
    build_state,
    freeze_state_inputs,
    read_branch,
    read_state,
)


class DependentUpdateInput(Contract):
    event_id: UUID
    expected_revision: int
    revision_hash: Hash
    timeline: TimelineQuery
    state_input: StateBuildInput | None = None


class DependentUpdateReceipt(Contract):
    event_id: UUID
    job_id: UUID
    data_revision: int
    scope_key: str
    status: Literal["queued"] = "queued"
    next_action: str = "Dispatch and run the existing worker; refresh status explicitly"


class DependentUpdateReport(Contract):
    version: Literal["dependent-update/1"] = "dependent-update/1"
    id: UUID
    event_id: UUID
    data_revision: int
    revision_hash: Hash
    scope_key: str
    status: Literal["ready", "quarantined"]
    features: TemporalFeatures
    trends: TrendReport
    fusion: FusionReport | None
    state_id: UUID | None
    dependency_hashes: dict[str, str]
    input_dependency_hashes: dict[str, str]
    source_ids: list[UUID]
    restrictions: list[str]
    geometry_recomputed: Literal[False] = False
    scientific_review: Literal["pending"] = "pending"
    publication: Literal["draft"] = "draft"
    next_action: str


class DependentUpdateView(Contract):
    status: Literal["pending", "current", "stale", "failed", "unavailable"]
    current_patient_revision: int
    requested_revision: int | None = None
    job_id: UUID | None = None
    job_status: str | None = None
    last_ready: DependentUpdateReport | None = None
    restrictions: list[str]
    baseline_superseded: bool = False
    eligible_event: DependentEvent | None = None
    next_action: str


class DependentEvent(Contract):
    event_id: UUID
    revision: int
    revision_hash: Hash


DependentUpdateView.model_rebuild()


def _scope(value):
    return str(value.state_input.branch_id) if value.state_input else "source_fixture"


def _authorize(c, i, p, u):
    authorize_project(i, p, "admin")
    authorize_patient(c, i, p, u, edit=True)
    _revision(c, p, u)
    lock_lineage(c, p, u)


def _revision(c, p, u):
    return c.execute(
        text(
            "SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u FOR UPDATE"
        ),
        {"p": p, "u": u},
    ).scalar_one()


def freeze_update_inputs(c, i, p, u, value, storage):
    """Validate exact source revision and return real registry parents for worker pins."""
    _authorize(c, i, p, u)
    window = value.timeline.window
    if (
        window.scope.mode != "source_fixture"
        or window.scope.data_revision != value.expected_revision
        or value.timeline.cursor is not None
        or value.timeline.completion_id is not None
    ):
        raise HTTPException(422, detail="dependent_update_requires_exact_source_fixture_window")
    event = c.execute(
        text(
            "SELECT revision FROM ops.domain_outbox WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": p, "u": u, "id": value.event_id},
    ).scalar_one_or_none()
    if (
        event != value.expected_revision
        or science_hash(load_revision(c, p, u, event)) != value.revision_hash
    ):
        raise HTTPException(409, detail="event_revision_or_manifest_mismatch")
    points, restrictions = read_window_points(c, i, p, u, value.timeline)
    if restrictions:
        raise HTTPException(409, detail="source_window_restricted")
    parents = {point.id for point in points}
    if value.state_input:
        if window.event_cutoff != value.state_input.time:
            raise HTTPException(422, detail="dependent_state_window_must_end_at_selected_state")
        if (
            value.state_input.target_revision != event
            or value.state_input.generated_geometry_members
            or value.state_input.generated_clinical_members
        ):
            raise HTTPException(422, detail="update_state_requires_explicit_source_membership")
        parents.update(freeze_state_inputs(c, i, p, u, value.state_input, storage))
    if not parents:
        # A fully retracted window still depends on the withdrawn historical record;
        # retain rights checks rather than invent an unparented synthetic result.
        prior = load_revision(c, p, u, max(1, event - 1))
        parents.update(UUID(x) for x in prior.get("members", []))
    if not parents:
        raise HTTPException(409, detail="no_authorized_dependency_members")
    return sorted(parents, key=str)


def dispatch_update(c, i, p, u, value, key, storage):
    from canceros.imaging_jobs import DependentUpdateCommand, ImagingJobInput, enqueue_imaging

    _authorize(c, i, p, u)
    # Serialize duplicate delivery and correction against the accepted revision.
    current = _revision(c, p, u)
    event = (
        c.execute(
            text(
                "SELECT * FROM ops.domain_outbox WHERE project_id=:p AND patient_id=:u AND id=:id FOR UPDATE"
            ),
            {"p": p, "u": u, "id": value.event_id},
        )
        .mappings()
        .one_or_none()
    )
    if event is None:
        raise HTTPException(404)
    fingerprint = science_hash(value.model_dump(mode="json"))
    prior = c.execute(
        text(
            "SELECT request_hash,receipt FROM ops.dependent_update_requests WHERE event_id=:id AND scope_key=:s"
        ),
        {"id": value.event_id, "s": _scope(value)},
    ).one_or_none()
    if prior:
        if prior.request_hash != fingerprint:
            raise HTTPException(409, detail="event_already_dispatched_with_different_inputs")
        freeze_update_inputs(c, i, p, u, value, storage)
        return DependentUpdateReceipt.model_validate(prior.receipt)
    if current != value.expected_revision:
        raise HTTPException(409, detail="event_superseded_dispatch_current_revision_explicitly")
    freeze_update_inputs(c, i, p, u, value, storage)
    job = enqueue_imaging(
        c,
        i,
        p,
        u,
        ImagingJobInput(
            expected_revision=current,
            command=DependentUpdateCommand(operation="dependent_update", input=value),
        ),
        key,
        storage,
        allow_dependent=True,
    )
    receipt = DependentUpdateReceipt(
        event_id=value.event_id, job_id=job.id, data_revision=current, scope_key=_scope(value)
    )
    c.execute(
        text(
            "INSERT INTO ops.dependent_update_requests(event_id,project_id,patient_id,revision,scope_key,job_id,request_hash,receipt) VALUES(:id,:p,:u,:r,:s,:j,:h,CAST(:v AS jsonb))"
        ),
        {
            "id": value.event_id,
            "p": p,
            "u": u,
            "r": current,
            "s": _scope(value),
            "j": job.id,
            "h": fingerprint,
            "v": canonical_bytes(receipt.model_dump(mode="json")).decode(),
        },
    )
    c.execute(
        text("UPDATE ops.domain_outbox SET delivered_at=clock_timestamp() WHERE id=:id"),
        {"id": value.event_id},
    )
    return receipt


def execute_update(c, i, p, u, value, storage, job_id):
    parents = freeze_update_inputs(c, i, p, u, value, storage)
    points, restrictions = read_window_points(c, i, p, u, value.timeline)
    features = extract_features(points, value.timeline.window)
    trends = analyze_trends(points, value.timeline.window)
    state, fusion = None, None
    assets = {}
    if value.state_input:
        state = build_state(c, i, p, u, value.state_input, storage, "dependent-" + str(job_id))
        view = read_state(c, i, p, u, state.id)
        fusion = fuse_state(view)
        parents.append(state.id)
        for member in state.imaging_members:
            assets[str(member.measurement.id)] = member.source_hash
            if member.mesh_qc:
                assets[str(member.mesh_qc.id)] = science_hash(
                    member.mesh_qc.model_dump(mode="json")
                )
        restrictions.extend(state.conflicts)
    report = DependentUpdateReport(
        id=uuid4(),
        event_id=value.event_id,
        data_revision=value.expected_revision,
        revision_hash=value.revision_hash,
        scope_key=_scope(value),
        status="quarantined" if restrictions else "ready",
        features=features,
        trends=trends,
        fusion=fusion,
        state_id=state.id if state else None,
        dependency_hashes={
            "features": science_hash(features.model_dump(mode="json")),
            "comparisons": science_hash(trends.model_dump(mode="json")),
            "fusion": science_hash(fusion.model_dump(mode="json"))
            if fusion
            else science_hash({"unavailable": "explicit_state_membership_required"}),
            "measurements_and_assets": science_hash(assets),
        },
        input_dependency_hashes={
            "window": science_hash(value.timeline.window.model_dump(mode="json")),
            "revision": value.revision_hash,
            "state_membership": science_hash(value.state_input.model_dump(mode="json"))
            if value.state_input
            else science_hash({"state": "unavailable"}),
            "measurement_assets": science_hash(assets),
            **{
                str(parent): get_resource(c, i, p, u, parent)["content_hash"]
                for parent in sorted(set(parents), key=str)
            },
        },
        source_ids=sorted(set(parents), key=str),
        restrictions=sorted(set(restrictions)),
        next_action="Resolve quarantined inputs and explicitly dispatch a corrected revision"
        if restrictions
        else "Build an exact draft state explicitly to enable fusion; publication remains separate"
        if fusion is None
        else "Inspect the new draft; explicit review and publication remain separate",
    )
    payload = report.model_dump(mode="json")
    c.execute(
        text(
            "INSERT INTO ops.dependent_update_reports(id,project_id,patient_id,revision,scope_key,event_id,job_id,report,report_hash) VALUES(:id,:p,:u,:r,:s,:e,:j,CAST(:v AS jsonb),:h)"
        ),
        {
            "id": report.id,
            "p": p,
            "u": u,
            "r": report.data_revision,
            "s": report.scope_key,
            "e": report.event_id,
            "j": job_id,
            "v": canonical_bytes(payload).decode(),
            "h": science_hash(payload),
        },
    )
    derive_resource(
        c,
        i,
        p,
        u,
        report.id,
        "dependent_update_report",
        science_hash(payload),
        report.source_ids,
        processing_spec(
            __file__,
            "dependent-update/1",
            "dependent-update/1",
            {"dependency_hashes": report.dependency_hashes},
        ),
    )
    # This head serves a computed preview only; it cannot publish a state or run.
    if report.status == "ready" and _revision(c, p, u) == report.data_revision:
        c.execute(
            text(
                "INSERT INTO ops.dependent_update_heads(project_id,patient_id,scope_key,revision,report_id) VALUES(:p,:u,:s,:r,:id) ON CONFLICT(project_id,patient_id,scope_key) DO UPDATE SET revision=excluded.revision,report_id=excluded.report_id WHERE ops.dependent_update_heads.revision<=excluded.revision"
            ),
            {"p": p, "u": u, "s": report.scope_key, "r": report.data_revision, "id": report.id},
        )
    return report


def read_update_view(c, i, p, u, branch_id=None):
    _authorize(c, i, p, u)
    scope = str(branch_id) if branch_id else "source_fixture"
    baseline_superseded = False
    if branch_id:
        branch = read_branch(c, i, p, u, branch_id)
        try:
            _measurement(c, i, p, u, branch.input.baseline_measurement_id)
            if branch.input.baseline_mesh_qc_report_id:
                _usable(c, i, p, u, branch.input.baseline_mesh_qc_report_id)
        except HTTPException:
            baseline_superseded = True
    current = _revision(c, p, u)
    params = {"p": p, "u": u, "s": scope}
    request = c.execute(
        text(
            "SELECT r.revision,r.job_id,j.status FROM ops.dependent_update_requests r JOIN ops.jobs j ON j.id=r.job_id WHERE r.project_id=:p AND r.patient_id=:u AND r.scope_key=:s ORDER BY r.revision DESC LIMIT 1"
        ),
        params,
    ).one_or_none()
    retained = c.execute(
        text(
            "SELECT r.report,r.report_hash FROM ops.dependent_update_heads h JOIN ops.dependent_update_reports r ON r.id=h.report_id AND r.project_id=h.project_id AND r.patient_id=h.patient_id WHERE h.project_id=:p AND h.patient_id=:u AND h.scope_key=:s"
        ),
        params,
    ).one_or_none()
    report, restrictions = None, []
    if baseline_superseded:
        restrictions.append("branch_baseline_dependency_no_longer_usable_create_new_branch")
    if retained:
        if science_hash(retained.report) != retained.report_hash:
            raise HTTPException(409, detail="derived_report_integrity_failed")
        candidate = DependentUpdateReport.model_validate(retained.report)
        try:
            _usable(c, i, p, u, candidate.id)
            report = candidate
        except HTTPException:
            restrictions.append("retained_result_access_restricted")
    status: Literal["pending", "current", "stale", "failed", "unavailable"] = "unavailable"
    if request and request.status in ("queued", "running"):
        status = "pending"
    elif request and request.status in ("failed", "cancelled"):
        status = "failed"
    elif report:
        status = "current" if report.data_revision == current else "stale"
    elif request and request.revision != current:
        status = "stale"
    if report and report.data_revision != current:
        restrictions.append("retained_view_is_historical_revision")
    event_id = c.execute(
        text(
            "SELECT e.id FROM ops.domain_outbox e WHERE e.project_id=:p AND e.patient_id=:u AND e.revision=:r AND NOT EXISTS(SELECT 1 FROM ops.dependent_update_requests d WHERE d.event_id=e.id AND d.scope_key=:s) ORDER BY e.id LIMIT 1"
        ),
        {"p": p, "u": u, "r": current, "s": scope},
    ).scalar_one_or_none()
    eligible = (
        DependentEvent(
            event_id=event_id,
            revision=current,
            revision_hash=science_hash(load_revision(c, p, u, current)),
        )
        if event_id
        else None
    )
    return DependentUpdateView(
        status=status,
        current_patient_revision=current,
        requested_revision=request.revision if request else None,
        job_id=request.job_id if request else None,
        job_status=request.status if request else None,
        last_ready=report,
        restrictions=restrictions,
        baseline_superseded=baseline_superseded,
        eligible_event=eligible,
        next_action="Dispatch or recover the existing bounded worker job; retain the exact selected state and revision"
        if status == "pending"
        else "Inspect the failed job; correct the source in a new accepted revision before a new explicit dispatch"
        if status == "failed"
        else "Explicitly dispatch the current accepted event; source changes never rebase a branch or publish a state"
        if status != "current"
        else report.next_action
        if report
        else "Inspect current revision",
    )
