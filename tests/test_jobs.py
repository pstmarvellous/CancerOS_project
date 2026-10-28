import os
from uuid import uuid4

import pytest
from dotenv import dotenv_values
from redis import Redis
from sqlalchemy import create_engine, text

from canceros import jobs
from canceros.settings import Settings
from canceros.storage import PrivateStorage

pytestmark = pytest.mark.integration


@pytest.fixture
def runtime(monkeypatch):
    settings = Settings()
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(".env").get("TEST_DATABASE_URL")
    assert url and "disposable" in url
    engine = create_engine(url, hide_parameters=True)
    queue = jobs.queue_for(settings)
    suffix = str(uuid4())
    monkeypatch.setattr(jobs, "READY", "canceros:tests:ready:" + suffix)
    monkeypatch.setattr(jobs, "PROCESSING", "canceros:tests:processing:" + suffix)
    project, patient = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO access.projects(id,name) VALUES(:id,'Engineering-only job test')"),
            {"id": project},
        )
        connection.execute(
            text(
                "INSERT INTO source.research_patients(id,project_id,display_code) VALUES(:u,:p,:code)"
            ),
            {"u": patient, "p": project, "code": str(patient)},
        )
    storage = PrivateStorage(settings)
    yield engine, queue, storage, settings, project, patient
    # Only this test's transport keys; never FLUSHDB or delete user records.
    queue.delete(jobs.READY, jobs.PROCESSING)
    engine.dispose()


def test_persisted_digest_and_duplicate_delivery(runtime):
    engine, queue, storage, settings, project, patient = runtime
    identity = jobs.enqueue(engine, project, patient)
    assert jobs.dispatch(engine, queue, project) >= 1
    assert jobs.process_one(engine, queue, storage, settings) == identity
    queue.lpush(jobs.READY, str(identity))
    jobs.process_one(engine, queue, storage, settings)
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT status,result_hash,publication_status,attempt_count FROM ops.jobs WHERE id=:id"
            ),
            {"id": identity},
        ).one()
        assert row.status == "succeeded" and len(row.result_hash) == 64
        assert row.publication_status == "ready" and row.attempt_count == 1


def test_outbox_survives_transport_outage_and_abandoned_delivery(runtime):
    engine, queue, storage, settings, project, patient = runtime
    identity = jobs.enqueue(engine, project, patient)
    unavailable = Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.1, socket_timeout=0.1)
    with pytest.raises(Exception):
        jobs.dispatch(engine, unavailable, project)
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT delivered_at FROM ops.outbox WHERE job_id=:id"), {"id": identity}
            ).scalar_one()
            is None
        )
    jobs.dispatch(engine, queue, project)
    assert queue.rpoplpush(jobs.READY, jobs.PROCESSING) == str(identity)
    assert jobs.recover(engine, queue) >= 1
    jobs.process_one(engine, queue, storage, settings)
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT status FROM ops.jobs WHERE id=:id"), {"id": identity}
            ).scalar_one()
            == "succeeded"
        )


def test_queued_cancellation_has_no_ready_result(runtime):
    engine, queue, storage, settings, project, patient = runtime
    identity = jobs.enqueue(engine, project, patient)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE ops.jobs SET cancel_requested=true WHERE id=:id"), {"id": identity}
        )
    jobs.dispatch(engine, queue, project)
    jobs.process_one(engine, queue, storage, settings)
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT status,result_artifact_id FROM ops.jobs WHERE id=:id"), {"id": identity}
        ).one()
        assert row.status == "cancelled" and row.result_artifact_id is None
