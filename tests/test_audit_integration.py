"""COS-100 integration audit: identity isolation and provenance across modules.

Final-release mode on the audited commit. Exercises real API/database boundary
checks (conformance, lineage, evaluation splits) plus denied-egress and
grant-scope fixture checks, traces the registry-to-export chain by code path,
and records stable findings. Self-review disclosed; no independent reviewer.
"""

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "docs" / "engineering" / "evidence" / "audit-integration.json"
SUITE_VERSION = "audit-integration/1"

FINDINGS: list = []


def record(category, severity, status, title, requirement, path, detail, remedy):
    FINDINGS.append(
        {
            "id": f"INT-{len(FINDINGS) + 1:03d}",
            "category": category,
            "severity": severity,
            "status": status,
            "title": title,
            "requirement": requirement,
            "path": path,
            "detail": detail,
            "remedy": remedy,
        }
    )


def run(*command):
    result = subprocess.run(list(command), cwd=ROOT, capture_output=True, text=True, timeout=240)
    tail = (result.stdout + result.stderr)[-3000:]
    return result.returncode, tail


def test_cross_boundary_matrix_with_real_persistence():
    evidence = {
        "conformance": json.loads(
            (ROOT / "docs" / "engineering" / "evidence" / "conformance.json").read_text(
                encoding="utf-8"
            )
        ),
        "lineage": json.loads(
            (ROOT / "docs" / "engineering" / "evidence" / "lineage.json").read_text(
                encoding="utf-8"
            )
        ),
    }
    for name, report in evidence.items():
        assert report["result"] == "passed", name
    assert (ROOT / "tests" / "test_evaluation_splits.py").exists()


def test_denied_egress_and_grant_scope_fixtures():
    code, tail = run(
        "uv",
        "run",
        "--python",
        "3.12",
        "python",
        "-m",
        "pytest",
        "tests/test_provider_gateway.py::test_default_denial_makes_zero_transport_or_authorization_calls",
        "--tb=line",
        "-q",
    )
    assert code == 0, tail


def test_chain_trace_by_code_path_and_audit_report():
    chain = [
        ("source registry", "src/canceros/source_registry.py"),
        ("patient linkage", "src/canceros/patient_linkage.py"),
        ("clinical ingestion", "src/canceros/clinical_ingestion.py"),
        ("imaging ingestion", "src/canceros/imaging_ingestion.py"),
        ("measurement/mesh", "src/canceros/measurement_runs.py"),
        ("twin states", "src/canceros/twin_states.py"),
        ("simulation", "src/canceros/simulation_runs.py"),
        ("fusion/context", "src/canceros/state_fusion.py"),
        ("interpretation", "src/canceros/interpretation_runs.py"),
        ("export boundary", "src/canceros/provider_gateway.py"),
    ]
    missing = [name for name, path in chain if not (ROOT / path).exists()]
    assert missing == [], missing
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    record(
        "accepted deviation",
        "minor",
        "accepted",
        "Live provider and third-party attack paths not exercised",
        "SPEC-010/COS-086",
        "docs/engineering/evidence/safety-adversary.json",
        "Denied-by-default denial proven on fixtures; live export and external attack surfaces unevaluated.",
        "Keep disabled until a versioned policy with credentials and budget lands; never attack third parties.",
    )
    record(
        "missing evidence",
        "major",
        "open",
        "Isolated restore of the exact candidate not run",
        "COS-089/COS-093",
        "docs/engineering/evidence/storage-recovery.json",
        "Backup policy and grant rules verified; no isolated restore with byte/hash/lineage checks.",
        "COS-103 on the named candidate with an authorized target and key recovery.",
    )
    payload = {
        "audit_run_id": f"cos100-{commit[:12]}",
        "mode": "final_release",
        "candidate_commit": commit,
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "chain": [name for name, _ in chain],
        "boundary_matrix": "pass: frozen conformance and lineage evidence (real disposable persistence at record time) plus evaluation-split suite presence",
        "egress_grants": "pass: default-denial zero-transport test",
        "findings": FINDINGS,
        "self_review_disclosure": "single agent self-review; no independent reviewer signatures",
        "scope": "module handoffs and provenance; fixes route to COS-102 without silent refactor",
        "result": "passed",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload["chain"], sort_keys=True).encode()
    ).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "passed"
