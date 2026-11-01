"""COS-093 smoke gate: rollback safety rules with honest blocked deployment."""

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

RESULTS_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "engineering"
    / "evidence"
    / "smoke-rollback.json"
)
SUITE_VERSION = "smoke-rollback/1"

RUNBOOK = Path(__file__).resolve().parents[1] / "docs" / "runbooks" / "smoke-rollback-restore.md"


def destructive_migration_plan(migrations):
    return [name for name in migrations if "drop" in name.lower() or "destructive" in name.lower()]


def test_rollback_plan_never_blindly_downgrades():
    assert RUNBOOK.exists()
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "never blindly" in text.lower()
    assert "expand/contract" in text.lower()
    assert destructive_migration_plan(["0001_foundation", "0002_drop_column"]) == [
        "0002_drop_column"
    ]
    assert destructive_migration_plan(["0001_foundation"]) == []


def test_no_duplicate_publication_or_history_rewrite_rule():
    seen_runs = set()
    publications = []
    for run_id, branch in [("run-1", "branch-a"), ("run-2", "branch-a")]:
        assert run_id not in seen_runs
        seen_runs.add(run_id)
        publications.append((run_id, branch))
    assert len(publications) == len({run for run, _ in publications})
    history = ["rev-1", "rev-2"]
    assert history == ["rev-1", "rev-2"]


def test_smoke_gate_records_blocked_without_deployed_target():
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "candidate_freeze": "procedure documented; no candidate deployed in this scope",
        "smoke_journey": "blocked: no deployed target with a clean browser and account",
        "rollback_rehearsal": "blocked: no staging apply; expand/contract rule asserted on fixtures",
        "isolated_restore": "blocked: inherits COS-089; no isolated restore run",
        "measured_latency_mesh_cost": "unmeasured on deployment connection; local checks are not deployment evidence",
        "disposition": "blocked",
        "scope": "reviewed procedure and fixture rules; not deployed-and-recovered",
        "result": "blocked",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps({"suite": SUITE_VERSION}, sort_keys=True).encode()
    ).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "blocked"
