"""Actual durable SQL/Redis updates using synthetic clinical source artifacts."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_clinical_ingestion import clinical_db
from test_imaging_ingestion import imaging_db
from test_imaging_jobs import runtime as imaging_runtime
from test_source_registry import registry_db
from test_timeline_source import accept, clock, window

from canceros import imaging_jobs, jobs
from canceros.dependent_updates import DependentUpdateInput, dispatch_update, read_update_view
from canceros.imaging_jobs import dispatch_imaging, process_imaging_one, recover_imaging
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.persistence import load_revision, science_hash
from canceros.settings import Settings
from canceros.timeline_runs import TimelineQuery

__all__ = ["clinical_db", "registry_db", "imaging_db", "imaging_runtime"]


@pytest.fixture
def runtime(clinical_db, monkeypatch):
    c, i, p, patient, *_ = clinical_db
    c.execute(
        text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:a,'admin')"),
        {"p": p, "a": i.user_id},
    )
    suffix = str(uuid4())
    monkeypatch.setattr(imaging_jobs, "READY", "canceros:test:update:ready:" + suffix)
    monkeypatch.setattr(imaging_jobs, "PROCESSING", "canceros:test:update:processing:" + suffix)
    config = Settings(mode="test")
    queue = jobs.queue_for(config)
    yield clinical_db, queue, config
    queue.delete(imaging_jobs.READY, imaging_jobs.PROCESSING)


def request(data, revision):
    c, _, p, patient, *_ = data
    event = c.execute(
        text(
            "SELECT id FROM ops.domain_outbox WHERE project_id=:p AND patient_id=:u AND revision=:r"
        ),
        {"p": p, "u": patient.patient_id, "r": revision},
    ).scalar_one()
    return DependentUpdateInput(
        event_id=event,
        expected_revision=revision,
        revision_hash=science_hash(load_revision(c, p, patient.patient_id, revision)),
        timeline=TimelineQuery(window=window(revision, clock(c))),
    )


def dispatch(data, value, key="update-first"):
    c, i, p, patient, _, _, storage = data
    return dispatch_update(c, i, p, patient.patient_id, value, key, storage)


def view(data):
    c, i, p, patient, *_ = data
    return read_update_view(c, i, p, patient.patient_id)


def work(runtime, receipt):
    data, queue, config = runtime
    c, _, p, _, _, _, storage = data
    c.commit()
    assert dispatch_imaging(c.engine, queue, p) >= 1
    assert process_imaging_one(c.engine, queue, storage, config) == receipt.job_id


def test_durable_duplicate_delivery_and_coherent_report(runtime):
    data, queue, config = runtime
    c, _, _, _, _, _, storage = data
    accept(data)
    value = request(data, 2)
    assert view(data).eligible_event.event_id == value.event_id
    receipt = dispatch(data, value)
    assert dispatch(data, value, "duplicate-event-other-key") == receipt
    assert view(data).status == "pending"
    work(runtime, receipt)
    result = view(data)
    assert result.status == "current" and result.last_ready.data_revision == 2
    assert result.last_ready.fusion is None and result.last_ready.state_id is None
    assert not result.last_ready.geometry_recomputed
    assert len(result.last_ready.dependency_hashes) == 4
    assert result.last_ready.features.selected_point_ids
    assert result.last_ready.publication == "draft"
    queue.lpush(imaging_jobs.READY, str(receipt.job_id))
    assert process_imaging_one(c.engine, queue, storage, config) == receipt.job_id
    project = data[2]
    for table, expected in (
        ("ops.dependent_update_reports", 1),
        ("imaging.twin_publications", 0),
        ("imaging.mesh_runs", 0),
    ):
        assert (
            c.execute(
                text(f"SELECT count(*) FROM {table} WHERE project_id=:p"), {"p": project}
            ).scalar_one()
            == expected
        )


def test_old_job_retained_without_advancing_new_revision_head(runtime):
    data, _, _ = runtime
    first = accept(data)
    old = dispatch(data, request(data, 2))
    accept(data, revision=2, previous=first, value="13.5", key="correction")
    work(runtime, old)
    result = view(data)
    assert result.current_patient_revision == 3 and result.last_ready is None
    assert result.eligible_event.revision == 3
    fresh = dispatch(data, request(data, 3), "update-fresh")
    work(runtime, fresh)
    assert view(data).status == "current" and view(data).last_ready.data_revision == 3


def test_older_undispatched_event_stays_unconsumed(runtime):
    data, _, _ = runtime
    c, *_ = data
    first = accept(data)
    old = request(data, 2)
    accept(data, revision=2, previous=first, value="13.5", key="correction")
    with pytest.raises(HTTPException) as caught:
        dispatch(data, old)
    assert caught.value.status_code == 409
    assert (
        c.execute(
            text("SELECT delivered_at FROM ops.domain_outbox WHERE id=:id"), {"id": old.event_id}
        ).scalar_one()
        is None
    )


def test_atomic_dispatch_rollback_and_safe_recovery(runtime):
    data, queue, config = runtime
    c, _, p, _, _, _, storage = data
    accept(data)
    value = request(data, 2)
    c.commit()
    receipt = dispatch(data, value)
    c.rollback()
    assert view(data).job_id is None and view(data).eligible_event
    receipt = dispatch(data, value)
    c.commit()
    dispatch_imaging(c.engine, queue, p)
    # Transport disappearance after dispatch: durable SQL outbox recovers it.
    queue.delete(imaging_jobs.READY)
    recover_imaging(c.engine, queue, p)
    dispatch_imaging(c.engine, queue, p)
    assert process_imaging_one(c.engine, queue, storage, config) == receipt.job_id
    assert view(data).status == "current"


def test_withdrawal_hides_retained_values(runtime):
    data, _, _ = runtime
    c, i, p, patient, *_ = data
    record = accept(data)
    receipt = dispatch(data, request(data, 2))
    work(runtime, receipt)
    withdraw_resource(
        c, i, p, patient.patient_id, record, WithdrawalInput(reason_code="rights_withdrawn")
    )
    result = view(data)
    assert result.last_ready is None and "retained_result_access_restricted" in result.restrictions


def test_event_hash_scope_and_ownership_are_checked(runtime):
    data, _, _ = runtime
    c, i, p, patient, _, _, storage = data
    accept(data)
    value = request(data, 2)
    for changed in (
        value.model_copy(update={"revision_hash": "a" * 64}),
        value.model_copy(update={"event_id": uuid4()}),
    ):
        with pytest.raises(HTTPException):
            dispatch(data, changed)
    with pytest.raises(HTTPException):
        dispatch_update(c, i, p, uuid4(), value, "other-patient", storage)


def test_newer_completion_then_older_delivery_cannot_replace_head(runtime):
    data, queue, config = runtime
    c, _, p, _, _, _, storage = data
    first = accept(data)
    old = dispatch(data, request(data, 2))
    accept(data, revision=2, previous=first, value="13.5", key="newer")
    fresh = dispatch(data, request(data, 3), "fresh-job")
    c.commit()
    dispatch_imaging(c.engine, queue, p)
    queue.delete(imaging_jobs.READY)
    queue.lpush(imaging_jobs.READY, str(fresh.job_id), str(old.job_id))
    assert process_imaging_one(c.engine, queue, storage, config) == fresh.job_id
    fresh_hash = science_hash(view(data).last_ready.model_dump(mode="json"))
    c.commit()
    assert process_imaging_one(c.engine, queue, storage, config) == old.job_id
    assert view(data).last_ready.data_revision == 3
    assert science_hash(view(data).last_ready.model_dump(mode="json")) == fresh_hash


def test_worker_death_lease_recovery_executes_one_report(runtime):
    data, queue, config = runtime
    c, _, p, _, _, _, storage = data
    accept(data)
    receipt = dispatch(data, request(data, 2))
    token = uuid4()
    c.execute(
        text(
            "UPDATE ops.jobs SET status='running',attempt_count=1,lease_token=:t,leased_until=clock_timestamp()-interval '1 second' WHERE id=:id"
        ),
        {"t": token, "id": receipt.job_id},
    )
    c.execute(
        text(
            "INSERT INTO ops.job_attempts(job_id,attempt_number,lease_token,outcome) VALUES(:id,1,:t,'running')"
        ),
        {"id": receipt.job_id, "t": token},
    )
    c.commit()
    recover_imaging(c.engine, queue, p)
    dispatch_imaging(c.engine, queue, p)
    assert process_imaging_one(c.engine, queue, storage, config) == receipt.job_id
    assert view(data).status == "current"
    assert (
        c.execute(
            text("SELECT attempt_count FROM ops.jobs WHERE id=:id"), {"id": receipt.job_id}
        ).scalar_one()
        == 2
    )


def test_concurrent_event_dispatch_is_deduplicated(runtime):
    data, _, _ = runtime
    c, i, p, patient, _, _, storage = data
    accept(data)
    value = request(data, 2)
    c.commit()

    def run(key):
        with c.engine.begin() as other:
            return dispatch_update(other, i, p, patient.patient_id, value, key, storage)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(run, ("concurrent-a", "concurrent-b")))
    assert first.job_id == second.job_id
    assert (
        c.execute(
            text("SELECT count(*) FROM ops.dependent_update_requests WHERE project_id=:p"), {"p": p}
        ).scalar_one()
        == 1
    )


def test_database_rejects_mixed_report_scope_and_revision(runtime):
    data, _, _ = runtime
    c, _, p, *_ = data
    accept(data)
    receipt = dispatch(data, request(data, 2))
    work(runtime, receipt)
    for column, replacement in (("scope_key", "'wrong-scope'"), ("revision", "1")):
        selection = {
            name: name
            for name in (
                "id",
                "project_id",
                "patient_id",
                "revision",
                "scope_key",
                "event_id",
                "job_id",
                "report",
                "report_hash",
            )
        }
        selection["id"] = ":new_id"
        selection[column] = replacement
        columns = ",".join(selection)
        values = ",".join(selection.values())
        with pytest.raises(DBAPIError), c.begin_nested():
            c.execute(
                text(
                    f"INSERT INTO ops.dependent_update_reports({columns}) SELECT {values} FROM ops.dependent_update_reports WHERE project_id=:p LIMIT 1"
                ),
                {"new_id": uuid4(), "p": p},
            )


def test_exact_new_draft_fusion_reuses_mesh_and_preserves_published_history(imaging_runtime):
    from test_clinical_ingestion import row
    from test_twin_states import clinical, setup, time

    from canceros.mesh_quality_runs import MeshQCInput, create_mesh_qc
    from canceros.mesh_runs import MeshInput, create_mesh
    from canceros.twin_states import (
        ClinicalMember,
        ImagingMember,
        PublishInput,
        ReviewInput,
        StateBuildInput,
        build_state,
        publish_state,
        read_state,
        review_state,
    )

    imaging_data, queue, config = imaging_runtime
    c, i, p, patient, component, storage, _ = imaging_data
    u = patient.patient_id
    branch, association, measures, origin = setup(imaging_data)
    data = (c, i, p, patient, origin, component, storage)
    imported = clinical(imaging_data, origin, [row(origin)])
    mesh = create_mesh(
        c, i, p, u, MeshInput(measurement_id=measures[0].id), storage, "retained-mesh"
    )
    qc = create_mesh_qc(c, i, p, u, MeshQCInput(mesh_run_id=mesh.id), storage, "retained-mesh-qc")
    state_input = StateBuildInput(
        target_revision=2,
        association_head=association.sequence,
        branch_id=branch.id,
        time=time(origin),
        clinical_members=[ClinicalMember(record_id=imported.record_ids[0])],
        imaging_members=[
            ImagingMember(
                measurement_id=measures[0].id,
                mesh_qc_report_id=qc.id,
                association_event_id=association.id,
            )
        ],
    )
    old = build_state(c, i, p, u, state_input, storage, "old-published")
    old_view = read_state(c, i, p, u, old.id)
    review = review_state(
        c,
        i,
        p,
        u,
        old.id,
        ReviewInput(
            snapshot_hash=old_view.snapshot_hash,
            decision="accepted_engineering",
            evidence_sha256="a" * 64,
        ),
        "old-review",
    )
    published = publish_state(
        c,
        i,
        p,
        u,
        old.id,
        PublishInput(
            snapshot_hash=old_view.snapshot_hash,
            expected_patient_revision=2,
            expected_association_head=association.sequence,
            expected_review_id=review.id,
        ),
        "old-publication",
    )
    later = row(origin, client_record_key="later-lab")
    later["time"]["reference"]["value"] = "1"
    imported_later = clinical(imaging_data, origin, [later], revision=2, key="later-lab")
    new_input = state_input.model_copy(
        update={
            "target_revision": 3,
            "time": time(origin, "1"),
            "clinical_members": [ClinicalMember(record_id=imported_later.record_ids[0])],
            "imaging_members": [
                state_input.imaging_members[0].model_copy(
                    update={
                        "role": "historical_context",
                        "reason": "Earlier image is explicit historical context",
                    }
                )
            ],
        }
    )
    value = request(data, 3).model_copy(update={"state_input": new_input})
    with pytest.raises(HTTPException) as mismatch:
        dispatch(data, value)
    assert mismatch.value.status_code == 422
    value = value.model_copy(
        update={
            "timeline": value.timeline.model_copy(
                update={
                    "window": value.timeline.window.model_copy(
                        update={"event_cutoff": new_input.time}
                    )
                }
            )
        }
    )
    source_receipt = dispatch(data, value.model_copy(update={"state_input": None}), "source-scope")
    work((data, queue, config), source_receipt)
    assert read_update_view(c, i, p, u, branch.id).eligible_event.event_id == value.event_id
    receipt = dispatch(data, value)
    c.commit()
    dispatch_imaging(c.engine, queue, p)
    assert process_imaging_one(c.engine, queue, storage, config) == receipt.job_id
    result = read_update_view(c, i, p, u, branch.id)
    assert result.status == "current" and result.last_ready.fusion
    draft = read_state(c, i, p, u, result.last_ready.state_id)
    assert draft.publication is None and draft.review is None
    assert draft.snapshot.imaging_members[0].membership.role == "historical_context"
    assert draft.snapshot.imaging_members[0].mesh_qc.id == qc.id
    assert (
        c.execute(
            text("SELECT count(*) FROM imaging.mesh_runs WHERE project_id=:p"), {"p": p}
        ).scalar_one()
        == 1
    )
    retained = read_state(c, i, p, u, old.id)
    assert retained.snapshot_hash == old_view.snapshot_hash and retained.publication == published
    assert read_update_view(c, i, p, u).last_ready.state_id is None
    assert receipt.job_id != source_receipt.job_id
    assert str(measures[0].id) in result.last_ready.input_dependency_hashes
    conflicting = [row(origin, client_record_key=key) for key in ("conflict-a", "conflict-b")]
    for item in conflicting:
        item["time"]["reference"]["value"] = "2"
    conflict_batch = clinical(imaging_data, origin, conflicting, revision=3, key="conflicting-labs")
    conflicted_input = new_input.model_copy(
        update={
            "target_revision": 4,
            "time": time(origin, "2"),
            "clinical_members": [
                ClinicalMember(record_id=identifier) for identifier in conflict_batch.record_ids
            ],
        }
    )
    conflict_request = request(data, 4)
    conflict_request = conflict_request.model_copy(
        update={
            "timeline": conflict_request.timeline.model_copy(
                update={
                    "window": conflict_request.timeline.window.model_copy(
                        update={"event_cutoff": conflicted_input.time}
                    )
                }
            ),
            "state_input": conflicted_input,
        }
    )
    blocked = dispatch(
        data,
        conflict_request,
        "quarantined-labs",
    )
    work((data, queue, config), blocked)
    quarantined = read_update_view(c, i, p, u, branch.id)
    assert quarantined.status == "failed" and quarantined.last_ready.data_revision == 3
    assert read_state(c, i, p, u, old.id).snapshot_hash == old_view.snapshot_hash
    withdraw_resource(c, i, p, u, measures[0].id, WithdrawalInput(reason_code="source_corrected"))
    assert read_update_view(c, i, p, u, branch.id).baseline_superseded
