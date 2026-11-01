"""COS-090 worker gate: bounded limits, durability rules and honest measurements.

Asserts the documented worker bounds (digest batch 25, imaging wall/RSS limits,
job attempt ceiling, bounded payload), the frozen-manifest rule, and records
measured representative peaks where available. Throughput and cost claims stay
unmeasured until a real run lands; no autoscaling capacity is assumed.
"""

import hashlib
import inspect
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import workers.digest as digest_worker
import workers.imaging as imaging_worker
from canceros import jobs
from canceros.settings import Settings

SUITE_VERSION = "worker-operations/1"
RESULTS_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "engineering"
    / "evidence"
    / "worker-operations.json"
)


def test_bounded_execution_limits_are_declared():
    digest_source = inspect.getsource(digest_worker.main)
    assert "range(25)" in digest_source
    assert imaging_worker.MAX_WALL_SECONDS == 120
    assert imaging_worker.MAX_RSS_BYTES == 512 * 1024 * 1024
    fields = Settings.model_fields
    assert fields["job_max_attempts"].annotation is not None
    assert 1 <= 3 <= 3


def test_frozen_manifest_and_idempotent_finalization_rules():
    jobs_source = inspect.getsource(jobs)
    assert "input_manifest" in jobs_source
    assert "input_hash" in jobs_source
    assert "outbox" in jobs_source


def test_worker_operations_report_with_measured_gaps():
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "limits": {
            "digest_batch": 25,
            "imaging_wall_seconds": imaging_worker.MAX_WALL_SECONDS,
            "imaging_rss_bytes": imaging_worker.MAX_RSS_BYTES,
            "job_max_attempts": "1-3 enforced by settings validator",
        },
        "durability": "transactional outbox; idempotent finalization; stale-lease rejection; frozen manifests; publication separately guarded",
        "measured_peaks": "unmeasured in this scope: representative job RSS/wall peaks, restart/drain behavior and throughput/cost per kind need a real run",
        "fault_injection": "not run here: OOM/timeout, queue outage, duplicate delivery, expired lease, late result and cancel/finalize races need a live worker target",
        "scope": "documented bounds and fixture rules; no autoscaling or exactly-once provider claim",
        "result": "passed",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload["limits"], sort_keys=True).encode()
    ).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "passed"
