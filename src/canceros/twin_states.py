"""Exact-membership twin assembly. Engineering fixtures never certify observed baselines."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import AwareDatetime, Field, model_validator
from sqlalchemy import text

from canceros.annotation_import import read_annotation
from canceros.clinical_contracts import ClinicalRecord
from canceros.clinical_ingestion import read_record
from canceros.contracts import Context, Contract, Hash, RelativeTime, TimeReference, UnknownTime
from canceros.identity import authorize_project
from canceros.lesion_tracking import AssociationEvent, read_association
from canceros.lineage import (
    derive_resource,
    lock_lineage,
    processing_spec,
    require_resource_action,
    resource_restrictions,
)
from canceros.measurement_runs import MeasurementReport, load_usable_measurement
from canceros.mesh_quality_runs import MeshQCReport, load_display_mesh
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import canonical_bytes, load_revision, science_hash
from canceros.simulation_contracts import GeneratedEvent
from canceros.source_registry import SourceAction
from canceros.synthetic_contracts import GeometrySummary

Revision = Annotated[int, Field(strict=True, ge=1)]
POLICY: Literal["exact-membership/1"] = "exact-membership/1"


class BranchInput(Contract):
    baseline_measurement_id: UUID
    baseline_mesh_qc_report_id: UUID | None = None
    timeline_origin_id: UUID
    run_id: UUID


class BranchReport(Contract):
    id: UUID
    input: BranchInput
    baseline_hash: Hash
    baseline_state_id: None = None
    observed_baseline_verified: Literal[False] = False
    mode: Literal["engineering_fixture"] = "engineering_fixture"
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    scientific_review: Literal["pending"] = "pending"


class ClinicalMember(Contract):
    record_id: UUID
    role: Literal["current", "historical_context"] = "current"
    reason: Annotated[str, Field(min_length=1, max_length=200)] | None = None


class ImagingMember(Contract):
    measurement_id: UUID
    mesh_qc_report_id: UUID | None = None
    association_event_id: UUID | None = None
    role: Literal["current", "historical_context"] = "current"
    reason: Annotated[str, Field(min_length=1, max_length=200)] | None = None


class GeneratedGeometryMember(Contract):
    geometry_id: UUID


class GeneratedClinicalMember(Contract):
    batch_id: UUID
    event_ids: Annotated[list[UUID], Field(min_length=1, max_length=256)]

    @model_validator(mode="after")
    def unique_events(self):
        if len(set(self.event_ids)) != len(self.event_ids):
            raise ValueError("duplicate_generated_clinical_event")
        return self


class StateBuildInput(Contract):
    target_revision: Revision
    association_head: Annotated[int, Field(strict=True, ge=0)]
    branch_id: UUID | None = None
    context: Context = Context.SYNTHETIC
    time: RelativeTime
    clinical_members: Annotated[list[ClinicalMember], Field(max_length=256)] = Field(
        default_factory=list
    )
    imaging_members: Annotated[list[ImagingMember], Field(max_length=32)] = Field(
        default_factory=list
    )
    # Each branch pins one baseline measurement. At one state time, multiple
    # generated outputs compete for that same baseline, even with distinct IDs.
    generated_geometry_members: Annotated[list[GeneratedGeometryMember], Field(max_length=1)] = (
        Field(default_factory=list)
    )
    generated_clinical_members: Annotated[list[GeneratedClinicalMember], Field(max_length=1)] = (
        Field(default_factory=list)
    )

    @model_validator(mode="after")
    def membership(self):
        if len({m.record_id for m in self.clinical_members}) != len(self.clinical_members) or len(
            {m.measurement_id for m in self.imaging_members}
        ) != len(self.imaging_members):
            raise ValueError("duplicate_state_member")
        if len({m.geometry_id for m in self.generated_geometry_members}) != len(
            self.generated_geometry_members
        ):
            raise ValueError("duplicate_generated_geometry_member")
        if (
            not self.clinical_members
            and not self.imaging_members
            and not self.generated_geometry_members
            and not self.generated_clinical_members
        ):
            raise ValueError("state_members_required")
        return self


class ClinicalSnapshotMember(Contract):
    membership: ClinicalMember
    record: ClinicalRecord
    source_hash: Hash


class ImagingSnapshotMember(Contract):
    membership: ImagingMember
    time: TimeReference
    measurement: MeasurementReport
    source_hash: Hash
    association: AssociationEvent | None
    mesh_qc: MeshQCReport | None


class GeneratedGeometrySnapshotMember(Contract):
    geometry: GeometrySummary


class GeneratedClinicalSnapshotMember(Contract):
    batch_id: UUID
    run_id: UUID
    events: list[GeneratedEvent]
    source_hash: Hash


class SnapshotReport(Contract):
    id: UUID
    patient_id: UUID
    branch_id: UUID
    context: Literal["SYNTHETIC"] = "SYNTHETIC"
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    time: RelativeTime
    input_revision: int
    patient_event_head: int
    assembly_policy_version: Literal["exact-membership/1"] = POLICY
    request_manifest_hash: Hash
    revision_manifest_hash: Hash
    baseline_hash: Hash
    clinical_members: list[ClinicalSnapshotMember]
    imaging_members: list[ImagingSnapshotMember]
    generated_geometry_members: list[GeneratedGeometrySnapshotMember] = Field(default_factory=list)
    generated_clinical_members: list[GeneratedClinicalSnapshotMember] = Field(default_factory=list)
    missing: list[str]
    conflicts: list[str]
    status: Literal["ready", "ready_partial", "blocked"]
    technical_readiness: Literal["ready", "blocked"]
    scientific_review: Literal["pending"] = "pending"
    publication: Literal["draft"] = "draft"
    next_action: str


class ReviewInput(Contract):
    snapshot_hash: Hash
    decision: Literal["accepted_engineering", "rejected"]
    evidence_sha256: Hash


class ReviewEvent(Contract):
    id: UUID
    snapshot_id: UUID
    input: ReviewInput
    actor_id: UUID
    recorded_at: AwareDatetime
    review_basis: Literal["administrator_engineering_fixture_attestation"] = (
        "administrator_engineering_fixture_attestation"
    )
    scientific_review: Literal["pending"] = "pending"


class PublishInput(Contract):
    snapshot_hash: Hash
    expected_patient_revision: Revision
    expected_association_head: Annotated[int, Field(strict=True, ge=0)]
    expected_review_id: UUID


class Publication(Contract):
    id: UUID
    snapshot_id: UUID
    input: PublishInput
    actor_id: UUID
    recorded_at: AwareDatetime
    scope: Literal["private_engineering_fixture"] = "private_engineering_fixture"
    scientific_review: Literal["pending"] = "pending"


class StateView(Contract):
    snapshot: SnapshotReport
    snapshot_hash: Hash
    stale: bool
    current_use_allowed: bool
    restrictions: list[str]
    review: ReviewEvent | None
    publication: Publication | None
    available_actions: list[str]
    next_action: str


class StatePage(Contract):
    items: list[StateView]
    next_cursor: str | None
    snapshot_revision: int


def _params(p, u, **extra):
    return {"p": p, "u": u, **extra}


def _write(c, i, p, u):
    authorize_project(i, p, "admin")
    authorize_patient(c, i, p, u, edit=True)
    lock_lineage(c, p, u)


def _head(c, p, u):
    return c.execute(
        text("SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"),
        _params(p, u),
    ).scalar_one()


def _events(c, p, u):
    return c.execute(
        text(
            "SELECT COALESCE(max(sequence),0) FROM imaging.lesion_association_events WHERE project_id=:p AND patient_id=:u"
        ),
        _params(p, u),
    ).scalar_one()


def _read(c, i, p, u, table, identifier, model):
    authorize_patient(c, i, p, u, edit=True)
    row = c.execute(
        text(
            f"SELECT report,report_hash FROM imaging.{table} WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        _params(p, u, id=identifier),
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.report) != row.report_hash:
        raise HTTPException(409, detail="immutable_state_integrity_failed")
    return model.model_validate(row.report)


def _prior(c, p, u, i, table, key, value, model):
    fingerprint = science_hash(value.model_dump(mode="json"))
    row = c.execute(
        text(
            f"SELECT id,input_hash FROM imaging.{table} WHERE project_id=:p AND patient_id=:u AND actor_id=:actor AND command_key=:key"
        ),
        _params(p, u, actor=i.user_id, key=key),
    ).one_or_none()
    if row:
        fingerprints = {fingerprint}
        if table == "twin_snapshots" and not value.generated_clinical_members:
            # Earlier schemas predate optional generated membership categories.
            legacy = value.model_dump(mode="json")
            legacy.pop("generated_clinical_members")
            fingerprints.add(science_hash(legacy))
            if not value.generated_geometry_members:
                legacy.pop("generated_geometry_members")
                fingerprints.add(science_hash(legacy))
        if row.input_hash not in fingerprints:
            raise HTTPException(409, detail="command_key_payload_conflict")
        return _read(c, i, p, u, table, row.id, model), fingerprint
    return None, fingerprint


def _store(c, i, p, u, table, key, fingerprint, report, extra=None):
    columns = {
        "id": report.id,
        "project_id": p,
        "patient_id": u,
        "actor_id": i.user_id,
        "command_key": key,
        "input_hash": fingerprint,
        "report": canonical_bytes(report.model_dump(mode="json")).decode(),
        "report_hash": science_hash(report.model_dump(mode="json")),
        **(extra or {}),
    }
    c.execute(
        text(
            f"INSERT INTO imaging.{table}({','.join(columns)}) VALUES({','.join('CAST(:report AS jsonb)' if k == 'report' else ':' + k for k in columns)})"
        ),
        columns,
    )
    audit(c, p, report.id, table.upper() + "_RECORDED")


def _derive(c, i, p, u, report, parents, kind, fingerprint):
    derive_resource(
        c,
        i,
        p,
        u,
        report.id,
        kind,
        science_hash(report.model_dump(mode="json")),
        sorted(set(parents), key=str),
        processing_spec(__file__, "twin-states/1", POLICY, {"request_sha256": fingerprint}),
    )


def read_branch(c, i, p, u, identifier):
    return _read(c, i, p, u, "twin_branches", identifier, BranchReport)


def _mesh(c, i, p, u, measurement, qc_id, storage):
    qc, _ = load_display_mesh(c, i, p, u, qc_id, storage)
    if qc.measurement_id != measurement.id:
        raise HTTPException(409, detail="mesh_measurement_mismatch")
    require_resource_action(c, i, p, u, qc.id, SourceAction.DERIVATIVE)
    return qc


def create_branch(c, i, p, u, value: BranchInput, storage, command_key):
    _write(c, i, p, u)
    prior, fingerprint = _prior(c, p, u, i, "twin_branches", command_key, value, BranchReport)
    if prior:
        _usable_resource(c, i, p, u, prior.id)
        return prior
    origin = c.execute(
        text(
            "SELECT time_domain FROM source.timeline_origins WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        _params(p, u, id=value.timeline_origin_id),
    ).scalar_one_or_none()
    if origin != "simulation":
        raise HTTPException(404, detail="owned_simulation_origin_required")
    measurement = _measurement(c, i, p, u, value.baseline_measurement_id)
    if measurement.origin != "SYNTHETIC_GENERATED":
        raise HTTPException(409, detail="genuine_baseline_review_not_established")
    parents = [measurement.id]
    baseline = {"measurement": measurement.model_dump(mode="json"), "mesh": None}
    if value.baseline_mesh_qc_report_id:
        qc = _mesh(c, i, p, u, measurement, value.baseline_mesh_qc_report_id, storage)
        parents.append(qc.id)
        baseline["mesh"] = qc.model_dump(mode="json")
    report = BranchReport(id=uuid4(), input=value, baseline_hash=science_hash(baseline))
    _store(
        c,
        i,
        p,
        u,
        "twin_branches",
        command_key,
        fingerprint,
        report,
        {
            "baseline_measurement_id": measurement.id,
            "baseline_hash": report.baseline_hash,
            "timeline_origin_id": value.timeline_origin_id,
        },
    )
    _derive(c, i, p, u, report, parents, "twin_branch", fingerprint)
    return report


def _usable_resource(c, i, p, u, identifier):
    for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE):
        require_resource_action(c, i, p, u, identifier, action)


def _measurement(c, i, p, u, identifier):
    report = load_usable_measurement(c, i, p, u, identifier)
    for selection in report.selections:
        annotation = read_annotation(c, i, p, u, selection.segmentation_id)
        if not annotation.capabilities.numerical_region_volume_allowed:
            raise HTTPException(409, detail="current_annotation_qc_required")
    return report


def _time_role(actual, target, role, reason):
    if role == "current":
        if actual.model_dump(mode="json") != target.model_dump(mode="json"):
            raise HTTPException(409, detail="current_member_requires_exact_state_time")
    elif not reason:
        raise HTTPException(422, detail="historical_context_reason_required")
    elif (
        isinstance(actual, RelativeTime)
        and actual.timeline_origin_id == target.timeline_origin_id
        and actual.time_domain == target.time_domain
        and Decimal(actual.value) > Decimal(target.value)
    ):
        raise HTTPException(409, detail="future_member_not_historical_context")


def _assemble(c, i, p, u, value, storage):
    authorize_patient(c, i, p, u, edit=True)
    if len(value.generated_geometry_members) > 1:
        raise HTTPException(409, detail="one_generated_geometry_per_branch_state_required")
    if len(value.generated_clinical_members) > 1 or any(
        not member.event_ids or len(set(member.event_ids)) != len(member.event_ids)
        for member in value.generated_clinical_members
    ):
        raise HTTPException(409, detail="unique_generated_clinical_members_required")
    if value.context != Context.SYNTHETIC:
        raise HTTPException(409, detail="genuine_observed_state_review_not_established")
    if value.branch_id is None:
        raise HTTPException(422, detail="synthetic_branch_required")
    branch = read_branch(c, i, p, u, value.branch_id)
    if value.association_head > _events(c, p, u):
        raise HTTPException(409, detail="association_head_unavailable")
    if (
        value.time.time_domain != "simulation"
        or value.time.timeline_origin_id != branch.input.timeline_origin_id
    ):
        raise HTTPException(409, detail="branch_simulation_origin_required")
    try:
        revision = load_revision(c, p, u, value.target_revision)
    except LookupError as exc:
        raise HTTPException(409, detail="revision_unavailable") from exc
    parents = [branch.id]
    for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE):
        require_resource_action(c, i, p, u, branch.id, action)
    clinical, imaging, conflicts, generated, generated_clinical = [], [], [], [], []
    concepts: dict[tuple[str, str], list[str]] = {}
    for member in value.clinical_members:
        if str(member.record_id) not in revision.get("members", []):
            raise HTTPException(409, detail="clinical_member_not_in_target_revision")
        record = read_record(c, i, p, u, member.record_id)
        if record.context != Context.SYNTHETIC or record.origin != "SYNTHETIC_GENERATED":
            raise HTTPException(409, detail="engineering_fixture_source_required")
        for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE):
            require_resource_action(c, i, p, u, record.id, action)
        _time_role(record.item.time.reference, value.time, member.role, member.reason)
        if member.role == "current":
            concepts.setdefault((record.item.kind, record.item.concept), []).append(str(record.id))
        clinical.append(
            {
                "membership": member.model_dump(mode="json"),
                "record": record.model_dump(mode="json"),
                "source_hash": science_hash(record.model_dump(mode="json")),
            }
        )
        parents.append(record.id)
    for (kind, concept), ids in concepts.items():
        if len(ids) > 1:
            conflicts.append("same_time_conflict:" + kind + ":" + concept)
    for member in value.imaging_members:
        measurement = _measurement(c, i, p, u, member.measurement_id)
        actual = UnknownTime(
            basis="unknown", time_domain="simulation", missing_reason="not_recorded"
        )
        association = None
        if member.association_event_id:
            association = read_association(c, i, p, u, member.association_event_id)
            latest_at_head = c.execute(
                text(
                    "SELECT id FROM imaging.lesion_association_events WHERE project_id=:p AND patient_id=:u AND segmentation_id=:seg AND sequence<=:head ORDER BY sequence DESC LIMIT 1"
                ),
                _params(p, u, seg=association.input.segmentation_id, head=value.association_head),
            ).scalar_one_or_none()
            if latest_at_head != association.id:
                raise HTTPException(409, detail="association_not_current_at_captured_head")
            if (
                association.input.measurement_id != measurement.id
                or association.input.status != "matched"
                or association.input.relation != "same_lesion"
                or association.annotation_class != "anatomical_tumor_contour"
            ):
                raise HTTPException(409, detail="matched_anatomical_association_required")
            actual = association.input.time
            parents.append(association.id)
            require_resource_action(c, i, p, u, association.id, SourceAction.INTERNAL)
            require_resource_action(c, i, p, u, association.id, SourceAction.DERIVATIVE)
        _time_role(actual, value.time, member.role, member.reason)
        qc = None
        if member.mesh_qc_report_id:
            qc = _mesh(c, i, p, u, measurement, member.mesh_qc_report_id, storage)
            parents.append(qc.id)
        imaging.append(
            {
                "membership": member.model_dump(mode="json"),
                "time": actual.model_dump(mode="json"),
                "measurement": measurement.model_dump(mode="json"),
                "source_hash": science_hash(measurement.model_dump(mode="json")),
                "association": association.model_dump(mode="json") if association else None,
                "mesh_qc": qc.model_dump(mode="json") if qc else None,
            }
        )
        parents.append(measurement.id)
    if value.generated_geometry_members:
        # The geometry service writes states through this module; import only at use.
        from canceros.synthetic_geometry import load_ready_geometry

        for member in value.generated_geometry_members:
            geometry = load_ready_geometry(c, i, p, u, member.geometry_id)
            run_matches = geometry.run_id == branch.input.run_id
            if not run_matches:
                from canceros.simulation_runs import read_run

                common = read_run(c, i, p, u, geometry.run_id)
                run_matches = (
                    common.branch_id == branch.id
                    and common.config.baseline_hash == branch.baseline_hash
                    and common.input_revision == geometry.input_revision
                    and common.association_head == geometry.association_head
                )
            if (
                geometry.branch_id != branch.id
                or not run_matches
                or geometry.baseline_hash != branch.baseline_hash
                or geometry.baseline_measurement_id != branch.input.baseline_measurement_id
                or geometry.time != value.time
                or geometry.input_revision > value.target_revision
                or geometry.association_head != value.association_head
            ):
                raise HTTPException(409, detail="generated_geometry_state_membership_mismatch")
            generated.append(GeneratedGeometrySnapshotMember(geometry=geometry))
            parents.append(geometry.id)
    if value.generated_clinical_members:
        from canceros.clinical_generation_runs import read_clinical_batch
        from canceros.simulation_runs import read_run

        for member in value.generated_clinical_members:
            batch = read_clinical_batch(c, i, p, u, member.batch_id)
            run = read_run(c, i, p, u, batch.run_id)
            if (
                batch.branch_id != branch.id
                or run.branch_id != branch.id
                or run.config.baseline_hash != branch.baseline_hash
                or batch.config_hash != run.config_hash
                or batch.input_revision != value.target_revision
                or run.input_revision != value.target_revision
                or run.association_head != value.association_head
                or any(m.geometry.run_id != run.id for m in generated)
            ):
                raise HTTPException(409, detail="generated_clinical_state_membership_mismatch")
            events = {event.event_id: event for event in batch.batch.events}
            if any(identifier not in events for identifier in member.event_ids):
                raise HTTPException(409, detail="generated_clinical_event_not_in_batch")
            selected = [events[identifier] for identifier in member.event_ids]
            if any(
                event.run_id != run.id
                or event.branch_id != branch.id
                or Decimal(event.relative_day) != Decimal(value.time.value)
                for event in selected
            ):
                raise HTTPException(409, detail="generated_clinical_requires_exact_state_time")
            generated_clinical.append(
                GeneratedClinicalSnapshotMember(
                    batch_id=batch.id,
                    run_id=run.id,
                    events=selected,
                    source_hash=science_hash(batch.model_dump(mode="json")),
                )
            )
            parents.append(batch.id)
    if len(set(parents)) > 256:
        raise HTTPException(422, detail="state_parent_resource_limit_exceeded")
    return (
        branch,
        revision,
        sorted(set(parents), key=str),
        clinical,
        imaging,
        sorted(conflicts),
        generated,
        generated_clinical,
    )


def freeze_state_inputs(c, i, p, u, value: StateBuildInput, storage):
    return _assemble(c, i, p, u, value, storage)[2]


def build_state(c, i, p, u, value: StateBuildInput, storage, command_key):
    _write(c, i, p, u)
    prior, fingerprint = _prior(c, p, u, i, "twin_snapshots", command_key, value, SnapshotReport)
    if prior:
        _usable_resource(c, i, p, u, prior.id)
        return prior
    branch, revision, parents, clinical, imaging, conflicts, generated, generated_clinical = (
        _assemble(c, i, p, u, value, storage)
    )
    missing = []
    if not any(m.role == "current" for m in value.clinical_members) and not any(
        event.value.kind != "missing" for member in generated_clinical for event in member.events
    ):
        missing.append("clinical_not_available_at_this_visit")
    if not any(m.role == "current" for m in value.imaging_members):
        missing.append("imaging_not_available_at_this_visit")
    has_generated_mesh = any(
        m.geometry.status == "ready" and m.geometry.mesh_artifact_id is not None for m in generated
    )
    has_configured_zero = any(m.geometry.status == "zero" for m in generated)
    if has_configured_zero:
        missing.append("configured_zero_no_surface_expected")
    if (
        not any(m.role == "current" and m.mesh_qc_report_id for m in value.imaging_members)
        and not has_generated_mesh
        and not has_configured_zero
    ):
        missing.append("current_display_mesh_not_available_at_this_visit")
    report = SnapshotReport(
        id=uuid4(),
        patient_id=u,
        branch_id=branch.id,
        time=value.time,
        input_revision=value.target_revision,
        patient_event_head=value.association_head,
        request_manifest_hash=fingerprint,
        revision_manifest_hash=science_hash(revision),
        baseline_hash=branch.baseline_hash,
        clinical_members=clinical,
        imaging_members=imaging,
        generated_geometry_members=generated,
        generated_clinical_members=generated_clinical,
        missing=missing,
        conflicts=conflicts,
        status="blocked" if conflicts else "ready_partial" if missing else "ready",
        technical_readiness="blocked" if conflicts else "ready",
        next_action="Resolve retained conflicts"
        if conflicts
        else "Request explicit administrator engineering review; scientific review remains pending",
    )
    _store(
        c,
        i,
        p,
        u,
        "twin_snapshots",
        command_key,
        fingerprint,
        report,
        {"branch_id": branch.id, "input_revision": value.target_revision},
    )
    _derive(c, i, p, u, report, parents, "twin_snapshot", fingerprint)
    for parent in parents:
        c.execute(
            text("INSERT INTO imaging.twin_members VALUES(:p,:u,:snapshot,:resource)"),
            _params(p, u, snapshot=report.id, resource=parent),
        )
    return report


def _latest(c, i, p, u, table, snapshot, model):
    order = "sequence DESC" if table == "twin_reviews" else "id"
    identifier = c.execute(
        text(
            f"SELECT id FROM imaging.{table} WHERE project_id=:p AND patient_id=:u AND snapshot_id=:id ORDER BY {order} LIMIT 1"
        ),
        _params(p, u, id=snapshot),
    ).scalar_one_or_none()
    return _read(c, i, p, u, table, identifier, model) if identifier else None


def read_state(c, i, p, u, identifier):
    snapshot = _read(c, i, p, u, "twin_snapshots", identifier, SnapshotReport)
    # Hash persisted bytes, preserving prior schema versions when optional fields evolve.
    snapshot_hash = c.execute(
        text(
            "SELECT report_hash FROM imaging.twin_snapshots WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        _params(p, u, id=identifier),
    ).scalar_one()
    restrictions = resource_restrictions(c, i, p, u, identifier, SourceAction.INTERNAL)
    restrictions.extend(resource_restrictions(c, i, p, u, identifier, SourceAction.DERIVATIVE))
    branch = read_branch(c, i, p, u, snapshot.branch_id)
    for measurement_id in {
        branch.input.baseline_measurement_id,
        *(member.measurement.id for member in snapshot.imaging_members),
    }:
        try:
            _measurement(c, i, p, u, measurement_id)
        except HTTPException:
            restrictions.append("current_annotation_measurement_or_qc_unavailable")
    stale = snapshot.input_revision != _head(c, p, u) or snapshot.patient_event_head != _events(
        c, p, u
    )
    if stale:
        restrictions.append("captured_revision_or_association_head_changed")
    if snapshot.conflicts:
        restrictions.append("state_conflicts_require_resolution")
    review = _latest(c, i, p, u, "twin_reviews", identifier, ReviewEvent)
    publication = _latest(c, i, p, u, "twin_publications", identifier, Publication)
    if review and review.input.decision == "rejected":
        restrictions.append("engineering_review_rejected")
    actions = ["inspect_history"]
    common_run_member = bool(snapshot.generated_clinical_members) or any(
        member.geometry.run_id != branch.input.run_id
        for member in snapshot.generated_geometry_members
    )
    if not restrictions:
        actions.append("review_engineering")
        if (
            review
            and review.input.decision == "accepted_engineering"
            and not publication
            and not common_run_member
        ):
            actions.append("publish_private_fixture")
    return StateView(
        snapshot=snapshot,
        snapshot_hash=snapshot_hash,
        stale=stale,
        current_use_allowed=not restrictions,
        restrictions=sorted(set(restrictions)),
        review=review,
        publication=publication,
        available_actions=actions,
        next_action="Inspect restrictions and rebuild from explicit corrected members"
        if restrictions
        else "Complete and validate the common run before its separate explicit publication"
        if common_run_member
        else "Review or explicitly publish this private engineering fixture; genuine scientific review remains pending",
    )


def review_state(c, i, p, u, identifier, value: ReviewInput, command_key):
    _write(c, i, p, u)
    # Include the path identity in idempotence; equal payload cannot target a second snapshot.
    key_value = {"snapshot_id": str(identifier), "input": value.model_dump(mode="json")}
    fingerprint = science_hash(key_value)
    prior = c.execute(
        text(
            "SELECT id,input_hash FROM imaging.twin_reviews WHERE project_id=:p AND patient_id=:u AND actor_id=:actor AND command_key=:key"
        ),
        _params(p, u, actor=i.user_id, key=command_key),
    ).one_or_none()
    if prior:
        if prior.input_hash != fingerprint:
            raise HTTPException(409, detail="command_key_payload_conflict")
        return _read(c, i, p, u, "twin_reviews", prior.id, ReviewEvent)
    view = read_state(c, i, p, u, identifier)
    if view.snapshot_hash != value.snapshot_hash or (
        value.decision == "accepted_engineering" and not view.current_use_allowed
    ):
        raise HTTPException(409, detail="state_not_eligible_for_review")
    report = ReviewEvent(
        id=uuid4(),
        snapshot_id=identifier,
        input=value,
        actor_id=i.user_id,
        recorded_at=datetime.now(timezone.utc),
    )
    _store(
        c, i, p, u, "twin_reviews", command_key, fingerprint, report, {"snapshot_id": identifier}
    )
    return report


def publish_state(c, i, p, u, identifier, value: PublishInput, command_key):
    return _publish_state(c, i, p, u, identifier, value, command_key)


def _publish_state(c, i, p, u, identifier, value, command_key, completion_id=None):
    _write(c, i, p, u)
    fingerprint = science_hash(
        {"snapshot_id": str(identifier), "input": value.model_dump(mode="json")}
    )
    prior = c.execute(
        text(
            "SELECT id,input_hash FROM imaging.twin_publications WHERE project_id=:p AND patient_id=:u AND actor_id=:actor AND command_key=:key"
        ),
        _params(p, u, actor=i.user_id, key=command_key),
    ).one_or_none()
    if prior:
        if prior.input_hash != fingerprint:
            raise HTTPException(409, detail="command_key_payload_conflict")
        return _read(c, i, p, u, "twin_publications", prior.id, Publication)
    view = read_state(c, i, p, u, identifier)
    if view.publication:
        if view.publication.input == value:
            return view.publication
        raise HTTPException(409, detail="snapshot_already_published")
    branch = read_branch(c, i, p, u, view.snapshot.branch_id)
    if (
        view.snapshot.generated_clinical_members
        or any(
            member.geometry.run_id != branch.input.run_id
            for member in view.snapshot.generated_geometry_members
        )
    ) and completion_id is None:
        raise HTTPException(
            409, detail="common_run_requires_complete_validation_and_separate_publication"
        )
    if (
        not view.current_use_allowed
        or view.snapshot_hash != value.snapshot_hash
        or value.expected_patient_revision != _head(c, p, u)
        or value.expected_association_head != _events(c, p, u)
        or not view.review
        or view.review.id != value.expected_review_id
        or view.review.input.decision != "accepted_engineering"
    ):
        raise HTTPException(409, detail="publication_preconditions_changed")
    for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE):
        require_resource_action(c, i, p, u, identifier, action)
    report = Publication(
        id=uuid4(),
        snapshot_id=identifier,
        input=value,
        actor_id=i.user_id,
        recorded_at=datetime.now(timezone.utc),
    )
    _store(
        c,
        i,
        p,
        u,
        "twin_publications",
        command_key,
        fingerprint,
        report,
        {"snapshot_id": identifier, "review_id": view.review.id},
    )
    return report


def publish_complete_run_states(
    c, i, p, u, state_ids, run_id, expected_revision, expected_head, command_key, *, completion_id
):
    """Internal complete-run transaction participant; never commits or advances pointers."""
    from canceros.simulation_runs import read_run

    _write(c, i, p, u)
    row = c.execute(
        text(
            "SELECT report,report_hash FROM imaging.simulation_completions "
            "WHERE project_id=:p AND patient_id=:u AND id=:id AND run_id=:run"
        ),
        _params(p, u, id=completion_id, run=run_id),
    ).one_or_none()
    if row is None or science_hash(row.report) != row.report_hash:
        raise HTTPException(409, detail="ready_completion_integrity_required")
    report = row.report
    run = read_run(c, i, p, u, run_id)
    _usable_resource(c, i, p, u, completion_id)
    if (
        report.get("status") != "ready"
        or report.get("stage") != "complete"
        or report.get("validation", {}).get("status") != "engineering_passed"
        or report.get("run_id") != str(run_id)
        or report.get("branch_id") != str(run.branch_id)
        or report.get("config_hash") != run.config_hash
        or report.get("state_ids") != [str(identifier) for identifier in state_ids]
        or not state_ids
        or len(set(state_ids)) != len(state_ids)
        or report.get("input_revision") != expected_revision
        or report.get("association_head") != expected_head
        or run.input_revision != expected_revision
        or run.association_head != expected_head
        or expected_revision != _head(c, p, u)
        or expected_head != _events(c, p, u)
    ):
        raise HTTPException(409, detail="complete_run_publication_preconditions_changed")
    branch = read_branch(c, i, p, u, run.branch_id)
    views = [read_state(c, i, p, u, identifier) for identifier in state_ids]
    for view in views:
        snapshot = view.snapshot
        run_ids = {
            *(member.geometry.run_id for member in snapshot.generated_geometry_members),
            *(member.run_id for member in snapshot.generated_clinical_members),
        }
        shared_baseline_reference = (
            not run_ids
            and Decimal(snapshot.time.value) == 0
            and snapshot.time.time_domain == "simulation"
            and snapshot.time.timeline_origin_id == branch.input.timeline_origin_id
            and len(snapshot.imaging_members) == 1
            and snapshot.imaging_members[0].measurement.id == branch.input.baseline_measurement_id
            and not snapshot.clinical_members
            and not snapshot.generated_geometry_members
            and not snapshot.generated_clinical_members
        )
        if (
            snapshot.branch_id != run.branch_id
            or snapshot.baseline_hash != run.config.baseline_hash
            or snapshot.input_revision != expected_revision
            or snapshot.patient_event_head != expected_head
            or (run_ids != {run_id} and not shared_baseline_reference)
            or not view.current_use_allowed
        ):
            raise HTTPException(409, detail="complete_run_state_membership_mismatch")
    publications = []
    for view in views:
        key = science_hash({"key": command_key, "state": str(view.snapshot.id)})
        review = review_state(
            c,
            i,
            p,
            u,
            view.snapshot.id,
            ReviewInput(
                snapshot_hash=view.snapshot_hash,
                decision="accepted_engineering",
                evidence_sha256=row.report_hash,
            ),
            "complete-review-" + key,
        )
        publications.append(
            _publish_state(
                c,
                i,
                p,
                u,
                view.snapshot.id,
                PublishInput(
                    snapshot_hash=view.snapshot_hash,
                    expected_patient_revision=expected_revision,
                    expected_association_head=expected_head,
                    expected_review_id=review.id,
                ),
                "complete-publish-" + key,
                completion_id=completion_id,
            )
        )
    return publications


def list_states(c, i, p, u, branch_id=None, published_only=False, cursor=None, limit=25):
    authorize_patient(c, i, p, u, edit=True)
    if not 1 <= limit <= 100:
        raise HTTPException(422, detail="page_limit_out_of_range")
    if branch_id:
        read_branch(c, i, p, u, branch_id)
    scope = science_hash(
        {
            "actor": str(i.user_id),
            "project": str(p),
            "patient": str(u),
            "branch": str(branch_id),
            "published_only": published_only,
            "limit": limit,
        }
    )
    now = datetime.now(timezone.utc)
    if cursor:
        row = c.execute(
            text(
                "SELECT scope_hash,manifest,manifest_hash,expires_at FROM imaging.twin_cursors WHERE token_hash=:h"
            ),
            {"h": hashlib.sha256(cursor.encode()).hexdigest()},
        ).one_or_none()
        if (
            not row
            or row.scope_hash != scope
            or row.expires_at <= now
            or science_hash(row.manifest) != row.manifest_hash
        ):
            raise HTTPException(409, detail="cursor_expired_or_scope_changed")
        manifest = row.manifest
    else:
        rows = c.execute(
            text(
                "SELECT s.id,s.report FROM imaging.twin_snapshots s WHERE s.project_id=:p AND s.patient_id=:u ORDER BY s.report->'time'->>'value',s.id"
            ),
            _params(p, u),
        ).all()
        ids = []
        for row in sorted(rows, key=lambda r: (Decimal(r.report["time"]["value"]), str(r.id))):
            if branch_id and row.report["branch_id"] != str(branch_id):
                continue
            if published_only and not _latest(c, i, p, u, "twin_publications", row.id, Publication):
                continue
            ids.append(str(row.id))
        manifest = {
            "ids": ids,
            "offset": 0,
            "revision": _head(c, p, u),
            "expires_at": (now + timedelta(minutes=15)).isoformat(),
        }
    offset = manifest["offset"]
    items = [
        read_state(c, i, p, u, UUID(identifier))
        for identifier in manifest["ids"][offset : offset + limit]
    ]
    next_cursor = None
    if offset + limit < len(manifest["ids"]):
        next_cursor = secrets.token_urlsafe(32)
        following = {**manifest, "offset": offset + limit}
        c.execute(
            text(
                "INSERT INTO imaging.twin_cursors VALUES(:token,:scope,CAST(:manifest AS jsonb),:hash,:expiry)"
            ),
            {
                "token": hashlib.sha256(next_cursor.encode()).hexdigest(),
                "scope": scope,
                "manifest": canonical_bytes(following).decode(),
                "hash": science_hash(following),
                "expiry": datetime.fromisoformat(manifest["expires_at"]),
            },
        )
    return StatePage(items=items, next_cursor=next_cursor, snapshot_revision=manifest["revision"])
