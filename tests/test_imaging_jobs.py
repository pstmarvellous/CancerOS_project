"""Real disposable SQL, Redis and private S3; artificial imaging only."""

from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from redis import Redis
from sqlalchemy import text
from test_imaging_ingestion import imaging_db
from test_imaging_volumes import confirmed
from test_segmentation_reviews import qc_input
from test_source_registry import registry_db

from canceros import imaging_jobs, jobs
from canceros.imaging_jobs import (
    GeometryCommand,
    ImagingJobInput,
    PreprocessingCommand,
    SegmentationQCCommand,
    cancel_imaging_job,
    dispatch_imaging,
    enqueue_imaging,
    process_imaging_one,
    read_imaging_job,
    recover_imaging,
)
from canceros.imaging_preprocessing import PreprocessingConfig
from canceros.imaging_volumes import GeometryValidationInput, validate_volume
from canceros.lineage import WithdrawalInput, require_resource_action, withdraw_resource
from canceros.preprocessing_runs import PreprocessInput
from canceros.settings import Settings
from canceros.source_registry import SourceAction

__all__ = ["imaging_db", "registry_db"]


@pytest.fixture
def runtime(imaging_db, monkeypatch):
    c, identity, project, patient, _, storage, config = imaging_db
    c.execute(
        text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:a,'admin')"),
        {"p": project, "a": identity.user_id},
    )
    settings = Settings(mode="test")
    queue = jobs.queue_for(settings)
    suffix = str(uuid4())
    monkeypatch.setattr(imaging_jobs, "READY", "canceros:tests:imaging:ready:" + suffix)
    monkeypatch.setattr(imaging_jobs, "PROCESSING", "canceros:tests:imaging:processing:" + suffix)
    yield imaging_db, queue, settings
    queue.delete(imaging_jobs.READY, imaging_jobs.PROCESSING)


def enqueue_geometry(runtime, key="geometry-first"):
    data, queue, settings = runtime
    c, identity, project, patient, _, storage, _ = data
    imported_id = c.execute(
        text(
            "SELECT id FROM imaging.imports WHERE project_id=:p AND patient_id=:u ORDER BY id LIMIT 1"
        ),
        {"p": project, "u": patient.patient_id},
    ).scalar_one_or_none()
    if imported_id is None:
        imported_id = confirmed(data).id
    request = ImagingJobInput(
        expected_revision=1,
        command=GeometryCommand(
            operation="geometry", input=GeometryValidationInput(import_id=imported_id)
        ),
    )
    job = enqueue_imaging(c, identity, project, patient.patient_id, request, key, storage)
    assert enqueue_imaging(c, identity, project, patient.patient_id, request, key, storage) == job
    c.commit()
    return job, request


def get_job(runtime, job):
    data, _, _ = runtime
    c, identity, project, patient, *_ = data
    with c.engine.connect() as connection:
        return read_imaging_job(connection, identity, project, patient.patient_id, job.id)


def test_actual_geometry_worker_duplicate_delivery_private_result_and_metrics(runtime):
    data, queue, settings = runtime
    c, identity, project, patient, _, storage, _ = data
    job, request = enqueue_geometry(runtime)
    assert dispatch_imaging(c.engine, queue, project) == 1
    assert process_imaging_one(c.engine, queue, storage, settings) == job.id
    queue.lpush(imaging_jobs.READY, str(job.id))
    assert process_imaging_one(c.engine, queue, storage, settings) == job.id
    result = get_job(runtime, job)
    assert result.status == "succeeded" and result.attempt_count == 1
    assert result.publication == "draft" and not result.publication_allowed
    assert result.result_artifact_id and result.result_report_id
    with c.engine.connect() as connection:
        evidence = connection.execute(
            text("SELECT * FROM imaging.job_attempt_evidence WHERE job_id=:id"), {"id": job.id}
        ).one()
        assert 0 <= evidence.wall_seconds < 120 and 0 < evidence.rss_peak_bytes <= 512 * 1024 * 1024
        assert (
            connection.execute(
                text("SELECT publication_status FROM ops.jobs WHERE id=:id"), {"id": job.id}
            ).scalar_one()
            == "draft"
        )
        assert (
            enqueue_imaging(
                connection,
                identity,
                project,
                patient.patient_id,
                request,
                "geometry-first",
                storage,
            ).id
            == job.id
        )
    with pytest.raises(HTTPException):
        read_imaging_job(c, identity, project, uuid4(), job.id)


def test_transport_outage_lost_delivery_and_lease_recovery(runtime):
    data, queue, settings = runtime
    c, _, project, _, _, storage, _ = data
    job, _ = enqueue_geometry(runtime)
    unavailable = Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.1, socket_timeout=0.1)
    with pytest.raises(Exception):
        dispatch_imaging(c.engine, unavailable, project)
    with c.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT delivered_at FROM ops.outbox WHERE job_id=:id"), {"id": job.id}
            ).scalar_one()
            is None
        )
    dispatch_imaging(c.engine, queue, project)
    assert queue.rpoplpush(imaging_jobs.READY, imaging_jobs.PROCESSING) == str(job.id)
    # Simulate an actually claimed worker dying before a stage transaction commits.
    token = uuid4()
    with c.engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE ops.jobs SET status='running',lease_token=:t,attempt_count=1,leased_until=clock_timestamp()-interval '1 second' WHERE id=:id"
            ),
            {"id": job.id, "t": token},
        )
        connection.execute(
            text(
                "INSERT INTO ops.job_attempts(job_id,attempt_number,lease_token,outcome) VALUES(:id,1,:t,'running')"
            ),
            {"id": job.id, "t": token},
        )
    assert recover_imaging(c.engine, queue, project) == 1
    with c.engine.connect() as connection:
        diagnostic = connection.execute(
            text(
                "SELECT outcome,wall_seconds,rss_peak_bytes FROM imaging.job_attempt_evidence WHERE job_id=:id AND attempt_number=1"
            ),
            {"id": job.id},
        ).one()
        assert diagnostic.outcome == "lease_expired"
        assert diagnostic.wall_seconds is None and diagnostic.rss_peak_bytes is None
    dispatch_imaging(c.engine, queue, project)
    process_imaging_one(c.engine, queue, storage, settings)
    result = get_job(runtime, job)
    assert result.status == "succeeded" and result.attempt_count == 2
    with c.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT outcome FROM ops.job_attempts WHERE job_id=:id AND attempt_number=1"),
                {"id": job.id},
            ).scalar_one()
            == "lease_expired"
        )


def test_queued_and_inflight_cancel_commit_no_partial_scientific_references(runtime, monkeypatch):
    data, queue, settings = runtime
    c, identity, project, patient, _, storage, _ = data
    first, _ = enqueue_geometry(runtime)
    with c.engine.begin() as connection:
        assert (
            cancel_imaging_job(connection, identity, project, patient.patient_id, first.id).status
            == "cancelled"
        )
    assert dispatch_imaging(c.engine, queue, project) == 0
    second, request = enqueue_geometry(runtime, "geometry-inflight")
    original = imaging_jobs._execute

    def cancel_after_stage(connection, *args):
        result = original(connection, *args)
        with c.engine.begin() as other:
            cancel_imaging_job(other, identity, project, patient.patient_id, second.id)
        return result

    monkeypatch.setattr(imaging_jobs, "_execute", cancel_after_stage)
    dispatch_imaging(c.engine, queue, project)
    process_imaging_one(c.engine, queue, storage, settings)
    result = get_job(runtime, second)
    assert result.status == "cancelled" and result.result_artifact_id is None
    with c.engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM imaging.volume_validations WHERE import_id=CAST(:id AS uuid)"
                ),
                {"id": str(request.command.input.import_id)},
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM imaging.job_results WHERE job_id=:id"), {"id": second.id}
            ).scalar_one()
            == 0
        )


def test_object_failure_retries_with_backoff_and_eventual_single_stage_commit(runtime, monkeypatch):
    data, queue, settings = runtime
    c, _, project, _, _, storage, _ = data
    job, _ = enqueue_geometry(runtime)
    original_write = storage.write_verified

    def fail_object(*args, **kwargs):
        raise OSError("PRIVATE_SOURCE_VALUE_NEVER_LOG")

    monkeypatch.setattr(storage, "write_verified", fail_object)
    dispatch_imaging(c.engine, queue, project)
    process_imaging_one(c.engine, queue, storage, settings)
    failed = get_job(runtime, job)
    assert failed.status == "queued" and failed.error_code == "DEPENDENCY_OR_TRANSACTION_FAILURE"
    with c.engine.begin() as connection:
        assert connection.execute(
            text("SELECT next_attempt_at>clock_timestamp() FROM ops.jobs WHERE id=:id"),
            {"id": job.id},
        ).scalar_one()
        connection.execute(
            text("UPDATE ops.jobs SET next_attempt_at=clock_timestamp() WHERE id=:id"),
            {"id": job.id},
        )
    monkeypatch.setattr(storage, "write_verified", original_write)
    dispatch_imaging(c.engine, queue, project)
    process_imaging_one(c.engine, queue, storage, settings)
    assert get_job(runtime, job).status == "succeeded"
    assert get_job(runtime, job).attempt_count == 2


def test_stale_completion_rolls_back_stage_and_recovery_uses_original_revision(
    runtime, monkeypatch
):
    data, queue, settings = runtime
    c, _, project, patient, _, storage, _ = data
    job, _ = enqueue_geometry(runtime)
    original = imaging_jobs._execute

    def expire_after_stage(connection, *args):
        result = original(connection, *args)
        with c.engine.begin() as other:
            other.execute(
                text(
                    "UPDATE ops.jobs SET lease_token=:t,leased_until=clock_timestamp()-interval '1 second' WHERE id=:id"
                ),
                {"t": uuid4(), "id": job.id},
            )
        return result

    monkeypatch.setattr(imaging_jobs, "_execute", expire_after_stage)
    dispatch_imaging(c.engine, queue, project)
    process_imaging_one(c.engine, queue, storage, settings)
    assert get_job(runtime, job).status == "running"
    assert get_job(runtime, job).result_artifact_id is None
    with c.engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT outcome FROM imaging.job_attempt_evidence WHERE job_id=:id AND attempt_number=1"
                ),
                {"id": job.id},
            ).scalar_one()
            == "stale_completion_rejected"
        )
    with c.engine.begin() as connection:
        # The worker must continue to use frozen revision1/resources, not a later head.
        connection.execute(
            text(
                "UPDATE source.research_patients SET data_revision=2 WHERE project_id=:p AND id=:u"
            ),
            {"p": project, "u": patient.patient_id},
        )
    recover_imaging(c.engine, queue, project)
    monkeypatch.setattr(imaging_jobs, "_execute", original)
    dispatch_imaging(c.engine, queue, project)
    process_imaging_one(c.engine, queue, storage, settings)
    assert get_job(runtime, job).status == "succeeded"
    assert get_job(runtime, job).data_revision == 1


def test_actor_revocation_and_validation_failure_are_nonretryable(runtime):
    data, queue, settings = runtime
    c, identity, project, _, _, storage, _ = data
    job, _ = enqueue_geometry(runtime)
    with c.engine.begin() as connection:
        connection.execute(
            text("DELETE FROM access.memberships WHERE project_id=:p AND user_id=:a"),
            {"p": project, "a": identity.user_id},
        )
    dispatch_imaging(c.engine, queue, project)
    process_imaging_one(c.engine, queue, storage, settings)
    assert get_job(runtime, job).status == "failed"
    assert get_job(runtime, job).error_code == "INPUT_OR_ACCESS_REJECTED"
    assert get_job(runtime, job).attempt_count == 1


def test_actual_preprocessing_and_qc_commands_and_digest_dispatch_isolation(runtime):
    data, queue, settings = runtime
    c, identity, project, patient, _, storage, _ = data
    value = qc_input(data)
    qc_job = enqueue_imaging(
        c,
        identity,
        project,
        patient.patient_id,
        ImagingJobInput(
            expected_revision=1,
            command=SegmentationQCCommand(operation="segmentation_qc", input=value),
        ),
        "qc-job",
        storage,
    )
    source = validate_volume(
        c,
        identity,
        project,
        patient.patient_id,
        GeometryValidationInput(
            import_id=c.execute(
                text(
                    "SELECT import_id FROM imaging.volume_validations WHERE project_id=:p AND patient_id=:u LIMIT 1"
                ),
                {"p": project, "u": patient.patient_id},
            ).scalar_one()
        ),
        storage,
    )
    preprocess_job = enqueue_imaging(
        c,
        identity,
        project,
        patient.patient_id,
        ImagingJobInput(
            expected_revision=1,
            command=PreprocessingCommand(
                operation="preprocessing",
                input=PreprocessInput(
                    volume_artifact_id=source.volume_artifact_id,
                    config=PreprocessingConfig(expected_sequence="t2"),
                ),
            ),
        ),
        "preprocess-invalid-sequence",
        storage,
    )
    c.commit()
    # Engineering digest dispatcher must leave imaging outbox entries untouched.
    jobs.dispatch(c.engine, queue, project)
    with c.engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM ops.outbox o JOIN ops.jobs j ON j.id=o.job_id WHERE j.project_id=:p AND j.kind=:kind AND o.delivered_at IS NOT NULL"
                ),
                {"p": project, "kind": imaging_jobs.KIND},
            ).scalar_one()
            == 0
        )
    assert dispatch_imaging(c.engine, queue, project) == 2
    process_imaging_one(c.engine, queue, storage, settings)
    process_imaging_one(c.engine, queue, storage, settings)
    assert get_job(runtime, qc_job).status == "succeeded"
    assert get_job(runtime, preprocess_job).status == "failed"
    assert get_job(runtime, preprocess_job).error_code == "VALIDATION_REJECTED"


def test_cached_job_report_inherits_actual_output_withdrawal(runtime):
    data, queue, settings = runtime
    c, identity, project, patient, _, storage, _ = data
    job, request = enqueue_geometry(runtime)
    dispatch_imaging(c.engine, queue, project)
    process_imaging_one(c.engine, queue, storage, settings)
    result = get_job(runtime, job)
    with c.engine.begin() as connection:
        operation_result = connection.execute(
            text("SELECT result FROM imaging.job_results WHERE job_id=:id"), {"id": job.id}
        ).scalar_one()
        withdraw_resource(
            connection,
            identity,
            project,
            patient.patient_id,
            UUID(operation_result["volume_artifact_id"]),
            WithdrawalInput(reason_code="privacy_review"),
        )
    with c.engine.begin() as connection:
        with pytest.raises(HTTPException):
            require_resource_action(
                connection,
                identity,
                project,
                patient.patient_id,
                result.result_artifact_id,
                SourceAction.INTERNAL,
            )
        with pytest.raises(HTTPException):
            enqueue_imaging(
                connection,
                identity,
                project,
                patient.patient_id,
                request,
                "geometry-first",
                storage,
            )
        assert (
            read_imaging_job(connection, identity, project, patient.patient_id, job.id).status
            == "succeeded"
        )
