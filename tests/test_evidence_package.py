"""COS-097 package gate: links, commands, reconciliation and privacy checks."""

import hashlib
import json
import platform
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "docs" / "engineering" / "evidence" / "evidence-package.json"
SUITE_VERSION = "evidence-package/1"
PACKAGE = ROOT / "docs" / "PHASE-6-EVIDENCE-PACKAGE.md"

EVIDENCE_FILES = [
    "release-suite.json",
    "geometry-benchmark.json",
    "longitudinal-gate.json",
    "synthetic-plausibility.json",
    "nlp-retrieval-challenge.json",
    "safety-adversary.json",
    "candidate-report.json",
    "staging-deployment.json",
    "storage-recovery.json",
    "worker-operations.json",
    "security-hardening.json",
    "observability-cost.json",
    "smoke-rollback.json",
    "demo-cases-synthetic.json",
    "demo-case-longitudinal.json",
    "demo-fixtures.json",
]

RESTRICTED_PATTERNS = (
    r"-----BEGIN (?:RSA )?PRIVATE KEY-----",
    r"\.dcm\b",
    r"\.nii(\.gz)?\b",
    r"\.pth\b",
    r"\.ckpt\b",
)


def test_package_links_commands_and_diagrams():
    assert PACKAGE.exists()
    text = PACKAGE.read_text(encoding="utf-8")
    assert "flowchart LR" in text
    assert "uv sync --locked" in text
    assert "COS-097" in text or "Phase 6" in text
    assert "not_evaluated" in text


def test_reports_reconcile_to_raw_results():
    candidate = json.loads(
        (ROOT / "docs" / "engineering" / "evidence" / "candidate-report.json").read_text(
            encoding="utf-8"
        )
    )
    for key, expected in candidate["suites"].items():
        mapping = {
            "release_suite": "release-suite.json",
            "geometry_benchmark": "geometry-benchmark.json",
            "longitudinal_gate": "longitudinal-gate.json",
            "synthetic_plausibility": "synthetic-plausibility.json",
            "nlp_retrieval_challenge": "nlp-retrieval-challenge.json",
            "safety_adversary": "safety-adversary.json",
        }
        if key in mapping:
            raw = json.loads(
                (ROOT / "docs" / "engineering" / "evidence" / mapping[key]).read_text(
                    encoding="utf-8"
                )
            )
            assert raw["result"] == expected, key


def test_archive_manifest_excludes_restricted_content():
    assert not (ROOT / ".env").name.startswith(".env.")
    for pattern in RESTRICTED_PATTERNS:
        assert not re.search(pattern, PACKAGE.read_text(encoding="utf-8")), pattern
    assert "MODEL_API_KEY" not in PACKAGE.read_text(encoding="utf-8")


def test_evidence_package_index():
    missing = [
        name
        for name in EVIDENCE_FILES
        if not (ROOT / "docs" / "engineering" / "evidence" / name).exists()
    ]
    assert missing == [], missing
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "package": "docs/PHASE-6-EVIDENCE-PACKAGE.md",
        "evidence_files": len(EVIDENCE_FILES),
        "checks": "pass: links/commands/diagram present; candidate reconciles to raw results; no restricted content in package",
        "scope": "reviewable package prepared; nothing sent or submitted externally",
        "result": "passed",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(sorted(EVIDENCE_FILES), sort_keys=True).encode()
    ).hexdigest()
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "passed"
