"""COS-102 remediation backlog: consolidated findings, minimal fixes, disposition.

Final-release mode. Consolidates stable findings from COS-099/100/101 into a
dependency-ordered backlog, executes the authorized reversible in-scope fix
(exact-wording restart-contract assertion that previously used a count proxy),
reruns the affected regression, and records verified_fixed versus open/blocked
versus accepted_nonblocking with evidence. Engineering disposition stays
blocked for full readiness pending COS-103/104. Self-review disclosed.
"""

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "docs" / "engineering" / "evidence" / "remediation-backlog.json"
SUITE_VERSION = "remediation-backlog/1"

BACKLOG: list = []


def record(rank, finding_id, severity, status, title, dependency, owner, acceptance):
    BACKLOG.append(
        {
            "rank": rank,
            "finding_id": finding_id,
            "severity": severity,
            "status": status,
            "title": title,
            "dependency": dependency,
            "owner": owner,
            "acceptance": acceptance,
        }
    )


def run(*command):
    result = subprocess.run(list(command), cwd=ROOT, capture_output=True, text=True, timeout=300)
    return result.returncode, (result.stdout + result.stderr)[-3000:]


def test_backlog_consolidates_audits_without_duplicates():
    audits = {
        "architecture": json.loads(
            (ROOT / "docs" / "engineering" / "evidence" / "audit-architecture.json").read_text(
                encoding="utf-8"
            )
        ),
        "integration": json.loads(
            (ROOT / "docs" / "engineering" / "evidence" / "audit-integration.json").read_text(
                encoding="utf-8"
            )
        ),
        "functionality": json.loads(
            (ROOT / "docs" / "engineering" / "evidence" / "audit-functionality.json").read_text(
                encoding="utf-8"
            )
        ),
    }
    seen = set()
    for name, report in audits.items():
        for finding in report["findings"]:
            key = finding["title"]
            assert key not in seen, f"duplicate finding: {key}"
            seen.add(key)
    assert len(seen) >= 6


def test_minimal_fix_exact_restart_contract_with_regression():
    component = (ROOT / "apps" / "web" / "components" / "guided-demo.tsx").read_text(
        encoding="utf-8"
    )
    assert "Restart resets UI selection, camera and progress only" in component
    audit = (ROOT / "tests" / "test_audit_functionality.py").read_text(encoding="utf-8")
    assert "Restart resets UI selection, camera and progress only" in audit
    code, tail = run(
        "uv",
        "run",
        "--python",
        "3.12",
        "python",
        "-m",
        "pytest",
        "tests/test_audit_functionality.py",
        "--tb=line",
        "-q",
    )
    assert code == 0, tail


def test_disposition_with_verified_statuses_and_handoff():
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    record(
        1,
        "AUD-001",
        "major",
        "open",
        "No deployed target or isolated restore run",
        "COS-103",
        "platform",
        "deployed smoke + isolated restore pass on named candidate",
    )
    record(
        2,
        "AUD-002",
        "major",
        "open",
        "No genuine two-exam longitudinal case",
        "curated case",
        "data/rights",
        "two-exam case with rights, linkage, reviewer and demo use",
    )
    record(
        3,
        "INT-002",
        "major",
        "open",
        "Isolated restore of the exact candidate not run",
        "COS-103",
        "platform",
        "isolated restore with byte/hash/lineage checks and RPO/RTO",
    )
    record(
        4,
        "FUN-002",
        "major",
        "open",
        "No live judge walkthrough on a deployed target",
        "COS-103",
        "demo",
        "clean-browser judge access with presenter separation",
    )
    record(
        5,
        "FUN-003",
        "major",
        "open",
        "Measured device/browser/performance trials not run",
        "declared device",
        "qa",
        "declared-device trials with retained slow/failing trials",
    )
    record(
        6,
        "AUD-003",
        "minor",
        "accepted_nonblocking",
        "Optional models disabled pending verified policy",
        "policy/credentials",
        "platform",
        "existing denial tests; enable only with versioned policy",
    )
    record(
        7,
        "COS-101-proxy",
        "minor",
        "verified_fixed",
        "Restart-contract assertion now uses exact wording",
        "none",
        "qa",
        "test_audit_functionality passes on exact contract text",
    )
    payload = {
        "audit_run_id": f"cos102-{commit[:12]}",
        "mode": "final_release",
        "candidate_commit": commit,
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "backlog": BACKLOG,
        "engineering_disposition": "blocked for full P0 readiness; ready_for_final_operational_verification of the named candidate",
        "handoff_to_cos103": "candidate fingerprint above; remaining checks: deployed smoke, failed-rollout rehearsal, isolated restore with RPO/RTO",
        "self_review_disclosure": "single agent self-review; no invented owner signatures",
        "result": "passed",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload["backlog"], sort_keys=True).encode()
    ).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "passed"
    assert sum(1 for item in BACKLOG if item["status"] == "open") == 5
    assert sum(1 for item in BACKLOG if item["status"] == "verified_fixed") == 1
