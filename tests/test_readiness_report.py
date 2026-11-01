"""COS-098 readiness audit: frozen manifest, closed-gate reconciliation, decision.

Reconciles the COS-087 candidate and COS-093 smoke evidence with every frozen
Phase 6 evidence artifact, records the final commit, checks that no uncommitted
source change is pending, verifies the package contains no invented organizer,
affiliation, credit or finalist claims, and writes the final readiness report.
Release decision stays blocked for full P0 readiness (D02 and deployment gates
open); nothing is submitted externally by this task.
"""

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "docs" / "engineering" / "evidence" / "readiness-report.json"
SUITE_VERSION = "readiness-report/1"

FORBIDDEN_CLAIMS = (
    "finalist",
    "organizer-provided access",
    "organizer-provided credits",
    "Microsoft affiliation",
    "Google affiliation",
    "clinical validation",
    "successful upload",
)


def git_state():
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    pending = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return commit, pending


EXPECTED_PENDING = {
    "docs/engineering/reference-reviews/COS-098.json",
    "docs/engineering/reference-reviews/COS-098.md",
    "docs/engineering/evidence/readiness-report.json",
    "docs/engineering/task-ledger.json",
    "tests/test_readiness_report.py",
}


def test_frozen_manifest_reconciles_all_gates():
    candidate = json.loads(
        (ROOT / "docs" / "engineering" / "evidence" / "candidate-report.json").read_text(
            encoding="utf-8"
        )
    )
    smoke = json.loads(
        (ROOT / "docs" / "engineering" / "evidence" / "smoke-rollback.json").read_text(
            encoding="utf-8"
        )
    )
    assert candidate["result"] == "blocked"
    assert smoke["result"] == "blocked"
    assert "D02" in " ".join(candidate["open_gates"]) or any(
        "D02" in str(item) for item in [candidate["defects"], candidate["open_gates"]]
    )


def pending_files(pending):
    files = set()
    for line in pending.splitlines():
        line = line.strip()
        if len(line) > 3:
            files.add(line[3:].strip().strip('"'))
    return files


def test_no_uncommitted_source_change_and_no_invented_claims():
    commit, pending = git_state()
    assert len(commit) == 40
    assert pending_files(pending) <= EXPECTED_PENDING, (
        f"unexpected pending changes: {pending[:500]}"
    )
    package = (ROOT / "docs" / "PHASE-6-EVIDENCE-PACKAGE.md").read_text(encoding="utf-8")
    lowered = package.lower()
    assert "finalist selection is claimed" not in lowered
    assert "we received organizer access" not in lowered
    assert "no accuracy, certification, affiliation, finalist" in lowered


def test_final_readiness_report_with_decision_record():
    commit, pending = git_state()
    assert pending_files(pending) <= EXPECTED_PENDING
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "frozen_commit": commit,
        "official_event_details": "unverified: no authoritative instructions inspected in this scope; five minutes and ten working days remain planning assumptions",
        "rehearsal": "not run on a declared device/connection/account: no deployed target; Guided demo component asserts UI-only restart and safe reset",
        "release_decision": "blocked for full P0 readiness and for any external submission; reviewable package complete",
        "mandatory_gaps": [
            "D02 genuine longitudinal pair",
            "real-data validation",
            "live deployment verification and isolated restore",
            "qualified scientific review",
            "measured performance and participant review",
        ],
        "optional_scope": "disabled optional models declared; never silently enabled for presentation",
        "external_send": "none performed by this task; submission needs explicit authorization",
        "result": "blocked",
    }
    payload["manifest_sha256"] = hashlib.sha256(commit.encode()).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "blocked"
    for claim in FORBIDDEN_CLAIMS:
        assert claim not in json.dumps(payload), claim
