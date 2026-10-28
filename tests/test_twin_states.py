"""Exact revision/time semantics against disposable PostgreSQL and private fixture S3."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_clinical_ingestion import row, stage
from test_imaging_ingestion import imaging_db
from test_lesion_tracking import event, lesion, source
from test_source_registry import registry_db

from canceros.clinical_ingestion import BatchCommand, accept_batch
from canceros.contracts import Context, RelativeTime
from canceros.identity import Identity
from canceros.lineage import WithdrawalInput, derive_resource, processing_spec, withdraw_resource
from canceros.mesh_quality_runs import MeshQCInput, create_mesh_qc
from canceros.mesh_runs import MeshInput, create_mesh
from canceros.persistence import canonical_bytes, science_hash
from canceros.quality import record_technical_validation
from canceros.twin_states import (
    BranchInput,
    ClinicalMember,
    GeneratedGeometryMember,
    ImagingMember,
    PublishInput,
    ReviewInput,
    StateBuildInput,
    build_state,
    create_branch,
    freeze_state_inputs,
    list_states,
    publish_state,
    read_branch,
    read_state,
    review_state,
)

__all__ = ["imaging_db", "registry_db"]


def setup(data):
    c, i, p, patient, _, storage, _ = data
    annotations, measures, origin, _ = source(data)
    identity = lesion(data, annotations[0][0])
    association = event(data, identity, annotations[0][0], measures[0], origin, 0, "state-event")
    branch = create_branch(
        c,
        i,
        p,
        patient.patient_id,
        BranchInput(
            baseline_measurement_id=measures[0].id, timeline_origin_id=origin, run_id=uuid4()
        ),
        storage,
        "state-branch",
    )
    return branch, association, measures, origin


def time(origin, day="0"):
    return RelativeTime(
        basis="relative_day", value=day, time_domain="simulation", timeline_origin_id=origin
    )


def clinical(data, origin, rows, revision=1, corrects=None, key="clinical-state"):
    c, i, p, patient, component, storage, _ = data
    receipt = stage((c, i, p, patient, origin, component, storage), rows)
    return accept_batch(
        c,
        i,
        p,
        patient.patient_id,
        BatchCommand(
            source_artifact_id=receipt.artifact_id,
            expected_revision=revision,
            corrects_record_id=corrects,
        ),
        key,
        storage,
    )


def test_exact_revision_rebuild_explicit_review_publication_and_retained_history(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, association, measures, origin = setup(imaging_db)
    imported = clinical(imaging_db, origin, [row(origin)])
    value = StateBuildInput(
        target_revision=2,
        association_head=association.sequence,
        branch_id=branch.id,
        time=time(origin),
        clinical_members=[ClinicalMember(record_id=imported.record_ids[0])],
        imaging_members=[
            ImagingMember(measurement_id=measures[0].id, association_event_id=association.id)
        ],
    )
    pins = freeze_state_inputs(c, i, p, u, value, storage)
    assert {branch.id, association.id, measures[0].id, imported.record_ids[0]} <= set(pins)
    snapshot = build_state(c, i, p, u, value, storage, "state")
    assert build_state(c, i, p, u, value, storage, "state") == snapshot
    before = read_state(c, i, p, u, snapshot.id)
    assert before.publication is None and before.review is None
    assert snapshot.context == "SYNTHETIC" and snapshot.time.value == "0"
    assert snapshot.scientific_review == "pending" and snapshot.status == "ready_partial"
    review = review_state(
        c,
        i,
        p,
        u,
        snapshot.id,
        ReviewInput(
            snapshot_hash=before.snapshot_hash,
            decision="accepted_engineering",
            evidence_sha256="a" * 64,
        ),
        "review",
    )
    publication_input = PublishInput(
        snapshot_hash=before.snapshot_hash,
        expected_patient_revision=2,
        expected_association_head=association.sequence,
        expected_review_id=review.id,
    )
    published = publish_state(c, i, p, u, snapshot.id, publication_input, "publish")
    assert publish_state(c, i, p, u, snapshot.id, publication_input, "publish") == published
    assert (
        publish_state(c, i, p, u, snapshot.id, publication_input, "publish-concurrent") == published
    )
    changed = row(
        origin,
        original_value="10",
        result={"form": "exact", "quantity": {"value": "10", "unit": "g/dL"}},
    )
    corrected = clinical(
        imaging_db, origin, [changed], revision=2, corrects=imported.record_ids[0], key="correct"
    )
    assert corrected.result_revision == 3
    rebuilt = build_state(c, i, p, u, value, storage, "rebuild-old")
    assert rebuilt.clinical_members == snapshot.clinical_members
    assert rebuilt.revision_manifest_hash == snapshot.revision_manifest_hash
    assert rebuilt.baseline_hash == branch.baseline_hash
    retained = read_state(c, i, p, u, snapshot.id)
    assert retained.snapshot == snapshot and retained.snapshot_hash == before.snapshot_hash
    assert retained.publication == published and retained.stale
    assert read_branch(c, i, p, u, branch.id) == branch
    with pytest.raises(HTTPException):
        build_state(
            c,
            i,
            p,
            u,
            value.model_copy(
                update={"clinical_members": [ClinicalMember(record_id=corrected.record_ids[0])]}
            ),
            storage,
            "wrong-revision",
        )
    with pytest.raises(DBAPIError), c.begin_nested():
        c.execute(
            text("UPDATE imaging.twin_branches SET baseline_hash=:h WHERE id=:id"),
            {"h": "b" * 64, "id": branch.id},
        )
    with pytest.raises(DBAPIError), c.begin_nested():
        c.execute(text("DELETE FROM imaging.twin_publications WHERE id=:id"), {"id": published.id})
    withdraw_resource(c, i, p, u, measures[0].id, WithdrawalInput(reason_code="rights_withdrawn"))
    after = read_state(c, i, p, u, snapshot.id)
    assert "ancestor_withdrawn" in after.restrictions and after.snapshot == snapshot
    with pytest.raises(HTTPException):
        build_state(c, i, p, u, value, storage, "state")
    with pytest.raises(HTTPException):
        create_branch(c, i, p, u, branch.input, storage, "state-branch")


def test_same_time_conflicts_no_carry_and_historical_mesh_reuse_lab_state(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, association, measures, origin = setup(imaging_db)
    imported = clinical(imaging_db, origin, [row(origin), row(origin, client_record_key="other")])
    value = StateBuildInput(
        target_revision=2,
        association_head=association.sequence,
        branch_id=branch.id,
        time=time(origin),
        clinical_members=[ClinicalMember(record_id=r) for r in imported.record_ids],
    )
    snapshot = build_state(c, i, p, u, value, storage, "conflict")
    assert snapshot.conflicts == ["same_time_conflict:laboratory:hemoglobin"]
    assert snapshot.status == "blocked" and len(snapshot.clinical_members) == 2
    assert "imaging_not_available_at_this_visit" in snapshot.missing
    view = read_state(c, i, p, u, snapshot.id)
    with pytest.raises(HTTPException):
        review_state(
            c,
            i,
            p,
            u,
            snapshot.id,
            ReviewInput(
                snapshot_hash=view.snapshot_hash,
                decision="accepted_engineering",
                evidence_sha256="a" * 64,
            ),
            "conflict-review",
        )
    with pytest.raises(HTTPException) as no_carry:
        build_state(
            c, i, p, u, value.model_copy(update={"time": time(origin, "1")}), storage, "no-carry"
        )
    assert no_carry.value.detail == "current_member_requires_exact_state_time"
    later = row(origin, client_record_key="later")
    later["time"]["reference"]["value"] = "1"
    imported_later = clinical(imaging_db, origin, [later], revision=2, key="later")
    mesh = create_mesh(c, i, p, u, MeshInput(measurement_id=measures[0].id), storage, "old-mesh")
    qc = create_mesh_qc(c, i, p, u, MeshQCInput(mesh_run_id=mesh.id), storage, "old-mesh-qc")
    assert qc.status == "validated"
    mesh_count = c.execute(
        text("SELECT count(*) FROM imaging.mesh_runs WHERE project_id=:p"), {"p": p}
    ).scalar_one()
    lab = StateBuildInput(
        target_revision=3,
        association_head=association.sequence,
        branch_id=branch.id,
        time=time(origin, "1"),
        clinical_members=[ClinicalMember(record_id=imported_later.record_ids[0])],
        imaging_members=[
            ImagingMember(
                measurement_id=measures[0].id,
                mesh_qc_report_id=qc.id,
                association_event_id=association.id,
                role="historical_context",
                reason="Original image retained for context; no imaging at this visit",
            )
        ],
    )
    result = build_state(c, i, p, u, lab, storage, "lab-only")
    assert result.status == "ready_partial" and result.imaging_members[0].time.value == "0"
    assert result.imaging_members[0].membership.role == "historical_context"
    assert result.clinical_members[0].record.item.time.reference.value == "1"
    assert not result.conflicts and "imaging_not_available_at_this_visit" in result.missing
    assert result.imaging_members[0].mesh_qc.id == qc.id
    assert (
        c.execute(
            text("SELECT count(*) FROM imaging.mesh_runs WHERE project_id=:p"), {"p": p}
        ).scalar_one()
        == mesh_count
    )


def test_stable_scoped_cursor_and_permissions_and_unknown_image_time(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, association, measures, origin = setup(imaging_db)
    value = StateBuildInput(
        target_revision=1,
        association_head=association.sequence,
        branch_id=branch.id,
        time=time(origin),
        imaging_members=[
            ImagingMember(measurement_id=measures[0].id, association_event_id=association.id)
        ],
    )
    competing = [
        GeneratedGeometryMember(geometry_id=uuid4()),
        GeneratedGeometryMember(geometry_id=uuid4()),
    ]
    # Distinct resource IDs still compete for the branch's sole baseline/time.
    with pytest.raises(ValidationError):
        StateBuildInput.model_validate(
            {
                **value.model_dump(mode="json"),
                "generated_geometry_members": [
                    member.model_dump(mode="json") for member in competing
                ],
            }
        )
    bypassed = value.model_copy(update={"generated_geometry_members": competing})
    with pytest.raises(HTTPException) as conflict:
        freeze_state_inputs(c, i, p, u, bypassed, storage)
    assert conflict.value.detail == "one_generated_geometry_per_branch_state_required"
    before_count = c.execute(
        text("SELECT count(*) FROM imaging.twin_snapshots WHERE project_id=:p"), {"p": p}
    ).scalar_one()
    with pytest.raises(HTTPException):
        build_state(c, i, p, u, bypassed, storage, "competing-geometry")
    assert (
        c.execute(
            text("SELECT count(*) FROM imaging.twin_snapshots WHERE project_id=:p"), {"p": p}
        ).scalar_one()
        == before_count
    )
    first = build_state(c, i, p, u, value, storage, "first")
    second = build_state(c, i, p, u, value, storage, "second")
    page = list_states(c, i, p, u, branch_id=branch.id, limit=1)
    assert page.next_cursor and page.snapshot_revision == 1
    build_state(c, i, p, u, value, storage, "third")
    next_page = list_states(c, i, p, u, branch_id=branch.id, limit=1, cursor=page.next_cursor)
    assert next_page.next_cursor is None
    assert {page.items[0].snapshot.id, next_page.items[0].snapshot.id} == {first.id, second.id}
    with pytest.raises(HTTPException):
        list_states(c, i, p, u, branch_id=branch.id, limit=2, cursor=page.next_cursor)
    with pytest.raises(HTTPException):
        list_states(c, i, p, u, limit=1, cursor=page.next_cursor)
    c.execute(text("UPDATE imaging.twin_cursors SET expires_at=now()-interval '1 second'"))
    with pytest.raises(HTTPException):
        list_states(c, i, p, u, branch_id=branch.id, limit=1, cursor=page.next_cursor)
    unknown = value.model_copy(
        update={"imaging_members": [ImagingMember(measurement_id=measures[0].id)]}
    )
    with pytest.raises(HTTPException) as missing:
        build_state(c, i, p, u, unknown, storage, "unknown-current")
    assert missing.value.detail == "current_member_requires_exact_state_time"
    historical = unknown.model_copy(
        update={
            "imaging_members": [
                ImagingMember(
                    measurement_id=measures[0].id,
                    role="historical_context",
                    reason="Unknown original image time",
                )
            ]
        }
    )
    assert (
        build_state(c, i, p, u, historical, storage, "unknown-historical")
        .imaging_members[0]
        .time.basis
        == "unknown"
    )
    with pytest.raises(HTTPException):
        build_state(
            c,
            i,
            p,
            u,
            value.model_copy(update={"context": Context.OBSERVED, "branch_id": None}),
            storage,
            "observed",
        )
    outsider = Identity(uuid4(), {})
    with pytest.raises(HTTPException):
        build_state(c, outsider, p, u, value, storage, "outsider")
    with pytest.raises(HTTPException):
        build_state(c, i, p, uuid4(), value, storage, "wrong-patient")
    view = read_state(c, i, p, u, first.id)
    assert science_hash(first.model_dump(mode="json")) == view.snapshot_hash


def test_event_head_is_frozen_and_qc_changes_restrict_current_use(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, association, measures, origin = setup(imaging_db)
    value = StateBuildInput(
        target_revision=1,
        association_head=association.sequence,
        branch_id=branch.id,
        time=time(origin),
        imaging_members=[
            ImagingMember(measurement_id=measures[0].id, association_event_id=association.id)
        ],
    )
    snapshot = build_state(c, i, p, u, value, storage, "before-correction")
    initial = read_state(c, i, p, u, snapshot.id)
    review = review_state(
        c,
        i,
        p,
        u,
        snapshot.id,
        ReviewInput(
            snapshot_hash=initial.snapshot_hash,
            decision="accepted_engineering",
            evidence_sha256="a" * 64,
        ),
        "review-before-correction",
    )
    from canceros.lesion_tracking import append_association

    correction = append_association(
        c,
        i,
        p,
        u,
        association.input.model_copy(
            update={"status": "rejected", "supersedes_event_id": association.id}
        ),
        storage,
        "event-correction",
    )
    rebuilt = build_state(c, i, p, u, value, storage, "after-correction-old-head")
    assert rebuilt.patient_event_head == association.sequence
    assert rebuilt.imaging_members == snapshot.imaging_members
    assert read_state(c, i, p, u, rebuilt.id).stale
    with pytest.raises(HTTPException) as obsolete:
        build_state(
            c,
            i,
            p,
            u,
            value.model_copy(update={"association_head": correction.sequence}),
            storage,
            "old-event-new-head",
        )
    assert obsolete.value.detail == "association_not_current_at_captured_head"
    with pytest.raises(HTTPException):
        publish_state(
            c,
            i,
            p,
            u,
            snapshot.id,
            PublishInput(
                snapshot_hash=initial.snapshot_hash,
                expected_patient_revision=1,
                expected_association_head=association.sequence,
                expected_review_id=review.id,
            ),
            "stale-publish",
        )
    record_technical_validation(
        c,
        i,
        p,
        u,
        measures[0].selections[0].segmentation_id,
        "fail",
        "segmentation-qc/1",
        {"fixture": "explicit QC failure; no real review"},
    )
    view = read_state(c, i, p, u, snapshot.id)
    assert (
        not view.current_use_allowed
        and "current_annotation_measurement_or_qc_unavailable" in view.restrictions
    )
    assert view.snapshot == snapshot and view.snapshot_hash == initial.snapshot_hash


def test_previous_state_schema_hash_and_command_replay_remain_stable(imaging_db):
    """Load an actual persisted COS-039 shape lacking the new optional category."""
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, association, measures, origin = setup(imaging_db)
    value = StateBuildInput(
        target_revision=1,
        association_head=association.sequence,
        branch_id=branch.id,
        time=time(origin),
        imaging_members=[
            ImagingMember(measurement_id=measures[0].id, association_event_id=association.id)
        ],
    )
    source_snapshot = build_state(c, i, p, u, value, storage, "modern-shape")
    old_input = value.model_dump(mode="json")
    old_input.pop("generated_geometry_members")
    legacy_id = uuid4()
    legacy_report = source_snapshot.model_dump(mode="json")
    legacy_report.pop("generated_geometry_members")
    legacy_report.update(id=str(legacy_id), request_manifest_hash=science_hash(old_input))
    persisted_hash = science_hash(legacy_report)
    c.execute(
        text(
            "INSERT INTO imaging.twin_snapshots(id,project_id,patient_id,actor_id,command_key,input_hash,report,report_hash,branch_id,input_revision) VALUES(:id,:p,:u,:actor,'legacy-shape',:input,CAST(:report AS jsonb),:hash,:branch,1)"
        ),
        {
            "id": legacy_id,
            "p": p,
            "u": u,
            "actor": i.user_id,
            "input": science_hash(old_input),
            "report": canonical_bytes(legacy_report).decode(),
            "hash": persisted_hash,
            "branch": branch.id,
        },
    )
    derive_resource(
        c,
        i,
        p,
        u,
        legacy_id,
        "twin_snapshot",
        persisted_hash,
        [branch.id, measures[0].id, association.id],
        processing_spec(
            __file__,
            "legacy-schema-compatibility-test/1",
            "exact-membership/1",
            {"fixture": "COS039 persisted schema"},
        ),
    )
    view = read_state(c, i, p, u, legacy_id)
    assert view.snapshot_hash == persisted_hash
    assert view.snapshot.generated_geometry_members == []
    replay = build_state(c, i, p, u, value, storage, "legacy-shape")
    assert replay.id == legacy_id and replay.request_manifest_hash == science_hash(old_input)
