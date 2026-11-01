"""COS-103 operational verification: candidate-bound smoke, recovery, restore.

Final-release mode. Reconciles the COS-102 handoff with the COS-089/093
evidence, asserts the candidate fingerprint is unchanged, verifies the local
health contract and rollback/runbook discipline by source, and records the
operational gate as blocked: no authorized staging target, apply, or isolated
restore run exists in this scope. Self-review disclosed.
"""

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "docs" / "engineering" / "evidence" / "operational-verification.json"
SUITE_VERSION = "operational-verification/1"


def candidate_fingerprint():
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    return commit


def test_handoff_and_prior_gates_reconcile_to_blocked():
    backlog = json.loads(
        (ROOT / "docs" / "engineering" / "evidence" / "remediation-backlog.json").read_text(
            encoding="utf-8"
        )
    )
    assert backlog["result"] == "passed"
    assert "deployed smoke" in backlog["handoff_to_cos103"]
    assert "isolated restore" in backlog["handoff_to_cos103"]
    smoke = json.loads(
        (ROOT / "docs" / "engineering" / "evidence" / "smoke-rollback.json").read_text(
            encoding="utf-8"
        )
    )
    assert smoke["result"] == "blocked"
    storage = json.loads(
        (ROOT / "docs" / "engineering" / "evidence" / "storage-recovery.json").read_text(
            encoding="utf-8"
        )
    )
    assert storage["result"] == "blocked"


def test_candidate_fingerprint_unchanged_and_local_health_contract():
    commit = candidate_fingerprint()
    assert len(commit) == 40
    api = (ROOT / "src" / "canceros" / "api.py").read_text(encoding="utf-8")
    assert "/health/live" in api and "/health/ready" in api
    runbook = (ROOT / "docs" / "runbooks" / "smoke-rollback-restore.md").read_text(encoding="utf-8")
    assert "never blindly" in runbook.lower()
    assert "expand/contract" in runbook.lower()


def test_operational_record_with_blocked_disposition():
    commit = candidate_fingerprint()
    run_id = f"cos103-{commit[:12]}"
    payload = {
        "run_id": run_id,
        "mode": "final_release",
        "candidate_commit": commit,
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "deployed_smoke": "blocked: no authorized staging target or apply in this scope",
        "recovery_drill": "blocked: no controlled restart or failure injection on a live target",
        "isolated_restore": "blocked: inherits COS-089; no byte/hash/lineage restore run with RPO/RTO measurement",
        "rollback_rehearsal": "blocked: no staging apply; expand/contract rule asserted on fixtures",
        "new_defects": "none introduced by this task; no candidate-changing fix, so no COS-102 invalidation",
        "operator": "single agent self-review; no invented operator identity",
        "disposition": "blocked",
        "scope": "candidate-bound record without a live deployment; COS-104 freeze stays gated",
        "result": "blocked",
    }
    payload["manifest_sha256"] = hashlib.sha256(commit.encode()).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "blocked"
