"""Actual child process termination and one isolated private imaging worker cycle."""

import importlib.util
import os
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from test_imaging_ingestion import imaging_db
from test_segmentation_reviews import qc_input
from test_source_registry import registry_db

from canceros import imaging_jobs
from canceros.imaging_jobs import ImagingJobInput, enqueue_imaging
from canceros.jobs import queue_for
from canceros.settings import Settings

__all__ = ["registry_db", "imaging_db"]
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("imaging_supervisor", ROOT / "workers/imaging.py")
supervisor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(supervisor)


def test_supervisor_terminates_only_its_owned_child_on_wall_and_rss_limits():
    sleeping = [sys.executable, "-c", "import time; time.sleep(5)"]
    timed = supervisor.supervise(sleeping, max_wall_seconds=0.2)
    assert timed["outcome"] == "wall_limit" and timed["exit_code"] != 0
    limited = supervisor.supervise(sleeping, max_rss_bytes=1024 * 1024)
    assert limited["outcome"] == "rss_limit" and limited["exit_code"] != 0
    normal = supervisor.supervise([sys.executable, "-c", "raise SystemExit(0)"])
    assert normal["outcome"] == "completed" and normal["exit_code"] == 0


def test_supervised_actual_private_cpu_job_and_measured_resource_use(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    command = qc_input(imaging_db)
    c.execute(
        text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:u,'admin')"),
        {"p": p, "u": i.user_id},
    )
    value = ImagingJobInput(
        expected_revision=1,
        command={"operation": "segmentation_qc", "input": command.model_dump(mode="json")},
    )
    job = enqueue_imaging(c, i, p, patient.patient_id, value, "cli-cycle", storage)
    c.commit()
    queue = queue_for(Settings())
    suffix = str(uuid4())
    ready, processing = (
        "canceros:tests:imaging-cli:" + suffix + ":ready",
        "canceros:tests:imaging-cli:" + suffix + ":processing",
    )
    env = {
        **os.environ,
        "MODE": "test",
        "DATABASE_URL": c.engine.url.render_as_string(hide_password=False),
        "CANCEROS_IMAGING_READY": ready,
        "CANCEROS_IMAGING_PROCESSING": processing,
    }
    try:
        result = supervisor.supervise(
            [
                sys.executable,
                str(ROOT / "workers/imaging.py"),
                "--child-once",
                "--project-id",
                str(p),
            ],
            env=env,
        )
        assert result["outcome"] == "completed"
        assert 0 < result["sampled_peak_rss_bytes"] <= imaging_jobs.MAX_RSS_BYTES
        assert 0 < result["elapsed_seconds"] <= imaging_jobs.MAX_WALL_SECONDS
        record = c.execute(
            text("SELECT status,publication_status FROM ops.jobs WHERE id=:id"), {"id": job.id}
        ).one()
        assert record.status == "succeeded" and record.publication_status == "draft"
        attempt = c.execute(
            text(
                "SELECT outcome,rss_peak_bytes FROM imaging.job_attempt_evidence WHERE job_id=:id"
            ),
            {"id": job.id},
        ).one()
        assert attempt.outcome == "completed" and attempt.rss_peak_bytes > 0
    finally:
        queue.delete(ready, processing)
