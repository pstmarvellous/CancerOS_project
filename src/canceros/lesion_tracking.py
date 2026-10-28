"""Curated fixture lesion identity and immutable, explicitly timed scalar history.

Administrator attestations are engineering review, never qualified clinical review.
No registration or nearest-centroid inference is used to establish correspondence.
"""

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import AwareDatetime, Field, model_validator
from sqlalchemy import text

from canceros.annotation_import import read_annotation
from canceros.contracts import Contract, Hash, RelativeTime, UnknownTime
from canceros.identity import authorize_project
from canceros.lineage import (
    derive_resource,
    get_resource,
    lock_lineage,
    processing_spec,
    require_resource_action,
    resource_restrictions,
)
from canceros.measurement_runs import load_usable_measurement
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import load_revision, science_hash
from canceros.source_registry import SourceAction
from canceros.temporal_measurements import (
    ComparisonError,
    ScalarChange,
    ScalarPoint,
    compare_points,
)

Revision = Annotated[int, Field(strict=True, ge=1)]
FixtureTime = Annotated[RelativeTime | UnknownTime, Field(discriminator="basis")]


class LesionInput(Contract):
    baseline_segmentation_id: UUID
    evidence_sha256: Hash
    expected_revision: Revision


class LesionIdentity(Contract):
    id: UUID
    baseline_segmentation_id: UUID
    evidence_sha256: Hash
    input_revision: int
    actor_id: UUID
    recorded_at: AwareDatetime
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    review_basis: Literal["administrator_engineering_fixture_attestation"] = (
        "administrator_engineering_fixture_attestation"
    )
    scientific_review: Literal["pending"] = "pending"
    next_action: str = "Review explicit examination associations; engineering fixture identity does not establish biological correspondence"


class AssociationInput(Contract):
    lesion_id: UUID
    segmentation_id: UUID
    measurement_id: UUID | None = None
    status: Literal["candidate", "matched", "unresolved", "rejected", "withdrawn"]
    relation: Literal["same_lesion", "split", "merge"] = "same_lesion"
    related_lesion_ids: Annotated[list[UUID], Field(max_length=16)] = Field(default_factory=list)
    supersedes_event_id: UUID | None = None
    time: FixtureTime
    evidence_sha256: Hash
    expected_revision: Revision

    @model_validator(mode="after")
    def explicit_relationship(self):
        if (
            len(set(self.related_lesion_ids)) != len(self.related_lesion_ids)
            or self.lesion_id in self.related_lesion_ids
        ):
            raise ValueError("related_lesions_must_be_distinct")
        if (self.relation == "same_lesion") != (not self.related_lesion_ids):
            raise ValueError("split_merge_requires_explicit_related_lesions")
        if self.time.time_domain != "simulation":
            raise ValueError("only_explicit_simulation_times_enabled")
        if isinstance(self.time, RelativeTime) and self.time.timeline_origin_id is None:
            raise ValueError("owned_simulation_timeline_origin_required")
        return self


class AssociationEvent(Contract):
    id: UUID
    sequence: int
    version: int
    input: AssociationInput
    study_id: UUID
    source_image_id: UUID
    mask_artifact_id: UUID
    mask_sha256: Hash
    annotation_class: str
    annotation_method: str
    actor_id: UUID
    recorded_at: AwareDatetime
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    review_basis: Literal["administrator_engineering_fixture_attestation"] = (
        "administrator_engineering_fixture_attestation"
    )
    time_basis: Literal["engineering_simulation_not_observed_source_time"] = (
        "engineering_simulation_not_observed_source_time"
    )
    scientific_review: Literal["pending"] = "pending"


class SeriesInput(Contract):
    lesion_id: UUID
    expected_revision: Revision


class SeriesPoint(Contract):
    association: AssociationEvent
    scalar: ScalarPoint
    gaps: list[str]


class MeasurementSeries(Contract):
    id: UUID
    lesion_id: UUID
    input_revision: int
    patient_event_head: int
    points: list[SeriesPoint]
    changes: list[ScalarChange]
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    time_basis: Literal["engineering_simulation_not_observed_source_time"] = (
        "engineering_simulation_not_observed_source_time"
    )
    scientific_review: Literal["pending"] = "pending"
    clinical_response: Literal["not_assessed"] = "not_assessed"
    next_action: str = "Review mapping and gaps alongside the table; obtain genuine longitudinal source and qualified review before observed or clinical claims"


class SeriesView(Contract):
    report: MeasurementSeries
    stale: bool
    current_use_allowed: bool
    restrictions: list[str]
    next_action: str


def _params(project, patient, **extra):
    return {"p": project, "u": patient, **extra}


def _write_access(c, i, p, u):
    authorize_project(i, p, "admin")
    authorize_patient(c, i, p, u, edit=True)
    lock_lineage(c, p, u)


def _revision(c, p, u, revision):
    current = c.execute(
        text("SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"),
        _params(p, u),
    ).scalar_one()
    if revision != current:
        raise HTTPException(409, detail="current_patient_revision_required")
    load_revision(c, p, u, revision)


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
        raise HTTPException(409, detail="immutable_report_integrity_failed")
    return model.model_validate(row.report)


def _prior(c, i, p, u, table, key, value):
    fingerprint = science_hash(value.model_dump(mode="json"))
    row = c.execute(
        text(
            f"SELECT id,input_hash FROM imaging.{table} WHERE project_id=:p AND patient_id=:u AND actor_id=:actor AND command_key=:key"
        ),
        _params(p, u, actor=i.user_id, key=key),
    ).one_or_none()
    if row and row.input_hash != fingerprint:
        raise HTTPException(409, detail="command_key_payload_conflict")
    return row.id if row else None, fingerprint


def _derive(c, i, p, u, report, kind, parents, fingerprint):
    derive_resource(
        c,
        i,
        p,
        u,
        report.id,
        kind,
        science_hash(report.model_dump(mode="json")),
        sorted(set(parents), key=str),
        processing_spec(
            __file__, "lesion-tracking/1", "lesion-tracking/1", {"request_sha256": fingerprint}
        ),
    )
    audit(c, p, report.id, kind.upper() + "_RECORDED")


def _annotation(c, i, p, u, segmentation):
    annotation = read_annotation(c, i, p, u, segmentation)
    resource = get_resource(c, i, p, u, segmentation)
    if resource["origin"] != "SYNTHETIC_GENERATED":
        raise HTTPException(409, detail="genuine_source_identity_review_not_established")
    for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE):
        require_resource_action(c, i, p, u, segmentation, action)
    return annotation


def read_lesion(c, i, p, u, identifier):
    return _read(c, i, p, u, "lesion_identities", identifier, LesionIdentity)


def list_lesions(c, i, p, u):
    authorize_patient(c, i, p, u, edit=True)
    return [
        read_lesion(c, i, p, u, identifier)
        for identifier in c.execute(
            text(
                "SELECT id FROM imaging.lesion_identities WHERE project_id=:p AND patient_id=:u ORDER BY id"
            ),
            _params(p, u),
        ).scalars()
    ]


def create_lesion(c, i, p, u, value, storage, command_key):
    _write_access(c, i, p, u)
    annotation = _annotation(c, i, p, u, value.baseline_segmentation_id)
    prior, fingerprint = _prior(c, i, p, u, "lesion_identities", command_key, value)
    if prior:
        require_resource_action(c, i, p, u, prior, SourceAction.INTERNAL)
        return read_lesion(c, i, p, u, prior)
    _revision(c, p, u, value.expected_revision)
    report = LesionIdentity(
        id=uuid4(),
        baseline_segmentation_id=annotation.id,
        evidence_sha256=value.evidence_sha256,
        input_revision=value.expected_revision,
        actor_id=i.user_id,
        recorded_at=c.execute(text("SELECT clock_timestamp()")).scalar_one(),
    )
    c.execute(
        text(
            "INSERT INTO imaging.lesion_identities(id,project_id,patient_id,baseline_segmentation_id,actor_id,command_key,input_hash,report,report_hash) VALUES(:id,:p,:u,:seg,:actor,:key,:hash,CAST(:report AS jsonb),:rh)"
        ),
        _params(
            p,
            u,
            id=report.id,
            seg=annotation.id,
            actor=i.user_id,
            key=command_key,
            hash=fingerprint,
            report=report.model_dump_json(),
            rh=science_hash(report.model_dump(mode="json")),
        ),
    )
    _derive(c, i, p, u, report, "lesion_identity", [annotation.id], fingerprint)
    return report


def list_associations(c, i, p, u):
    authorize_patient(c, i, p, u, edit=True)
    return [
        _read(c, i, p, u, "lesion_association_events", identifier, AssociationEvent)
        for identifier in c.execute(
            text(
                "SELECT id FROM imaging.lesion_association_events WHERE project_id=:p AND patient_id=:u ORDER BY sequence"
            ),
            _params(p, u),
        ).scalars()
    ]


def read_association(c, i, p, u, identifier):
    return _read(c, i, p, u, "lesion_association_events", identifier, AssociationEvent)


def _measurement(c, i, p, u, annotation, identifier):
    report = load_usable_measurement(c, i, p, u, identifier)
    if len(report.selections) != 1 or report.selections[0].segmentation_id != annotation.id:
        raise HTTPException(409, detail="single_exact_annotation_measurement_required")
    if not annotation.capabilities.numerical_region_volume_allowed:
        raise HTTPException(409, detail="current_annotation_qc_required")
    return report


def append_association(c, i, p, u, value, storage, command_key):
    _write_access(c, i, p, u)
    annotation = _annotation(c, i, p, u, value.segmentation_id)
    parents = [value.lesion_id, value.segmentation_id]
    for lesion in [value.lesion_id] + value.related_lesion_ids:
        read_lesion(c, i, p, u, lesion)
        require_resource_action(c, i, p, u, lesion, SourceAction.DERIVATIVE)
        parents.append(lesion)
    if isinstance(value.time, RelativeTime):
        owned = c.execute(
            text(
                "SELECT id FROM source.timeline_origins WHERE project_id=:p AND patient_id=:u AND id=:id AND time_domain='simulation'"
            ),
            _params(p, u, id=value.time.timeline_origin_id),
        ).scalar_one_or_none()
        if owned is None:
            raise HTTPException(404, detail="owned_simulation_timeline_origin_required")
    if value.measurement_id:
        _measurement(c, i, p, u, annotation, value.measurement_id)
        parents.append(value.measurement_id)
    prior, fingerprint = _prior(c, i, p, u, "lesion_association_events", command_key, value)
    if prior:
        require_resource_action(c, i, p, u, prior, SourceAction.INTERNAL)
        return _read(c, i, p, u, "lesion_association_events", prior, AssociationEvent)
    _revision(c, p, u, value.expected_revision)
    events = list_associations(c, i, p, u)
    latest = next(
        (event for event in reversed(events) if event.input.segmentation_id == annotation.id), None
    )
    if (latest.id if latest else None) != value.supersedes_event_id:
        raise HTTPException(409, detail="supersede_latest_annotation_event_required")
    if latest:
        parents.append(latest.id)
    digest = c.execute(
        text("SELECT sha256 FROM ops.artifacts WHERE project_id=:p AND patient_id=:u AND id=:id"),
        _params(p, u, id=annotation.mask_artifact_id),
    ).scalar_one()
    report = AssociationEvent(
        id=uuid4(),
        sequence=events[-1].sequence + 1 if events else 1,
        version=latest.version + 1 if latest else 1,
        input=value,
        study_id=annotation.study_id,
        source_image_id=annotation.source_image_id,
        mask_artifact_id=annotation.mask_artifact_id,
        mask_sha256=digest,
        annotation_class=annotation.annotation.annotation_class,
        annotation_method=annotation.annotation.method_reference or "unknown",
        actor_id=i.user_id,
        recorded_at=c.execute(text("SELECT clock_timestamp()")).scalar_one(),
    )
    c.execute(
        text(
            "INSERT INTO imaging.lesion_association_events(id,project_id,patient_id,sequence,lesion_id,segmentation_id,supersedes_event_id,measurement_id,actor_id,command_key,input_hash,report,report_hash) VALUES(:id,:p,:u,:seq,:lesion,:seg,:previous,:measurement,:actor,:key,:hash,CAST(:report AS jsonb),:rh)"
        ),
        _params(
            p,
            u,
            id=report.id,
            seq=report.sequence,
            lesion=value.lesion_id,
            seg=value.segmentation_id,
            previous=value.supersedes_event_id,
            measurement=value.measurement_id,
            actor=i.user_id,
            key=command_key,
            hash=fingerprint,
            report=report.model_dump_json(),
            rh=science_hash(report.model_dump(mode="json")),
        ),
    )
    for related in value.related_lesion_ids:
        c.execute(
            text(
                "INSERT INTO imaging.lesion_event_relations(project_id,patient_id,event_id,related_lesion_id) VALUES(:p,:u,:event,:related)"
            ),
            _params(p, u, event=report.id, related=related),
        )
    _derive(c, i, p, u, report, "lesion_association", parents, fingerprint)
    return report


def _point(c, i, p, u, event):
    gaps = []
    measurement = None
    annotation = _annotation(c, i, p, u, event.input.segmentation_id)
    if event.input.measurement_id:
        measurement = _measurement(c, i, p, u, annotation, event.input.measurement_id)
    else:
        gaps.append("measurement_not_recorded")
    if event.input.status != "matched":
        gaps.append("lesion_identity_" + event.input.status)
    if event.input.relation != "same_lesion":
        gaps.append("split_merge_requires_qualified_identity_review")
    time = event.input.time
    if isinstance(time, UnknownTime):
        gaps.append("source_time_unknown")
    scalar = ScalarPoint(
        event_id=event.id,
        measurement_id=measurement.id if measurement else None,
        study_id=event.study_id,
        annotation_class=event.annotation_class,
        definition=measurement.definition if measurement else "not_recorded",
        method=f"{measurement.values.version}/{event.annotation_method}"
        if measurement
        else "not_recorded",
        origin=event.origin,
        unit="mm3",
        volume_mm3=measurement.values.volume_mm3 if measurement else None,
        time_group_id=time.timeline_origin_id if isinstance(time, RelativeTime) else None,
        relative_day=time.value if isinstance(time, RelativeTime) else None,
        eligible=not gaps,
    )
    return SeriesPoint(association=event, scalar=scalar, gaps=gaps)


def _change(left, right):
    try:
        return compare_points(left, right)
    except ComparisonError:
        return ScalarChange(
            absolute_mm3=None,
            percent_change=None,
            eligibility=False,
            reasons=["scalar_change_outside_supported_numeric_range"],
        )


def create_series(c, i, p, u, value, storage, command_key):
    _write_access(c, i, p, u)
    read_lesion(c, i, p, u, value.lesion_id)
    prior, fingerprint = _prior(c, i, p, u, "lesion_measurement_series", command_key, value)
    if prior:
        view = read_series(c, i, p, u, prior)
        if set(view.restrictions) - {"association_history_changed", "patient_revision_changed"}:
            raise HTTPException(409, detail="current_series_resource_restrictions")
        return view.report
    _revision(c, p, u, value.expected_revision)
    events = list_associations(c, i, p, u)
    latest = {event.input.segmentation_id: event for event in events}
    selected = [event for event in latest.values() if event.input.lesion_id == value.lesion_id]
    if len(selected) > 64:
        raise HTTPException(409, detail="series_point_limit_64")
    selected.sort(
        key=lambda event: (
            isinstance(event.input.time, UnknownTime),
            Decimal(event.input.time.value)
            if isinstance(event.input.time, RelativeTime)
            else Decimal(0),
            event.sequence,
        )
    )
    parents = [value.lesion_id]
    points = []
    for event in selected:
        require_resource_action(c, i, p, u, event.id, SourceAction.DERIVATIVE)
        points.append(_point(c, i, p, u, event))
        parents.append(event.id)
        if event.input.measurement_id:
            parents.append(event.input.measurement_id)
    report = MeasurementSeries(
        id=uuid4(),
        lesion_id=value.lesion_id,
        input_revision=value.expected_revision,
        patient_event_head=events[-1].sequence if events else 0,
        points=points,
        changes=[_change(a.scalar, b.scalar) for a, b in zip(points, points[1:])],
    )
    c.execute(
        text(
            "INSERT INTO imaging.lesion_measurement_series(id,project_id,patient_id,lesion_id,input_revision,actor_id,command_key,input_hash,report,report_hash) VALUES(:id,:p,:u,:lesion,:rev,:actor,:key,:hash,CAST(:report AS jsonb),:rh)"
        ),
        _params(
            p,
            u,
            id=report.id,
            lesion=value.lesion_id,
            rev=value.expected_revision,
            actor=i.user_id,
            key=command_key,
            hash=fingerprint,
            report=report.model_dump_json(),
            rh=science_hash(report.model_dump(mode="json")),
        ),
    )
    _derive(c, i, p, u, report, "lesion_measurement_series", parents, fingerprint)
    return report


def read_series(c, i, p, u, identifier):
    report = _read(c, i, p, u, "lesion_measurement_series", identifier, MeasurementSeries)
    head = c.execute(
        text(
            "SELECT COALESCE(max(sequence),0) FROM imaging.lesion_association_events WHERE project_id=:p AND patient_id=:u"
        ),
        _params(p, u),
    ).scalar_one()
    restrictions = resource_restrictions(c, i, p, u, identifier, SourceAction.INTERNAL)
    if head != report.patient_event_head:
        restrictions.append("association_history_changed")
    current = c.execute(
        text("SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"),
        _params(p, u),
    ).scalar_one()
    if current != report.input_revision:
        restrictions.append("patient_revision_changed")
    for point in report.points:
        try:
            _point(c, i, p, u, point.association)
        except HTTPException:
            restrictions.append("current_annotation_measurement_or_qc_unavailable")
    restrictions = sorted(set(restrictions))
    return SeriesView(
        report=report,
        stale=bool(restrictions),
        current_use_allowed=not restrictions,
        restrictions=restrictions,
        next_action="Review changed evidence and create a new series; immutable historical values are retained"
        if restrictions
        else report.next_action,
    )


def load_usable_series(c, i, p, u, identifier):
    view = read_series(c, i, p, u, identifier)
    if not view.current_use_allowed:
        raise HTTPException(409, detail="current_series_required")
    require_resource_action(c, i, p, u, identifier, SourceAction.DERIVATIVE)
    return view.report
