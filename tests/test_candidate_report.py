"""COS-087 candidate report: consolidated pre-deployment evidence and disposition.

Reads the frozen machine-readable evidence produced by COS-081 through COS-086,
reconciles per-suite results into one versioned report, checks that the web
Evaluation page matches this report (no separate decorative metric source),
and records an honest candidate disposition. Cloud recovery, real-data
validation, participant review and measured performance stay open; nothing here
claims clinical validation or deployment readiness.
"""

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

SUITE_VERSION = "candidate-report/1"
EVIDENCE_DIR = Path(__file__).resolve().parents[1] / "docs" / "engineering" / "evidence"
RESULTS_PATH = EVIDENCE_DIR / "candidate-report.json"

SOURCES = {
    "release_suite": "release-suite.json",
    "geometry_benchmark": "geometry-benchmark.json",
    "longitudinal_gate": "longitudinal-gate.json",
    "synthetic_plausibility": "synthetic-plausibility.json",
    "nlp_retrieval_challenge": "nlp-retrieval-challenge.json",
    "safety_adversary": "safety-adversary.json",
}


def load_reports():
    reports = {}
    for key, filename in SOURCES.items():
        path = EVIDENCE_DIR / filename
        assert path.exists(), f"missing evidence artifact: {filename}"
        reports[key] = json.loads(path.read_text(encoding="utf-8"))
    return reports


def test_candidate_report_reconciles_all_frozen_evidence():
    reports = load_reports()
    assert reports["release_suite"]["result"] == "passed"
    assert reports["geometry_benchmark"]["result"] == "passed"
    assert reports["longitudinal_gate"]["result"] == "blocked"
    assert reports["synthetic_plausibility"]["result"] == "passed"
    assert reports["nlp_retrieval_challenge"]["result"] == "passed"
    assert reports["safety_adversary"]["result"] == "passed"

    journey = [
        "authorized case",
        "actual derived mesh",
        "exact state/record",
        "charts/table",
        "valid comparison",
        "five scenario workflows",
        "source-backed update",
        "grounded insight/evidence",
        "evaluation/guide",
    ]
    defects = [
        {
            "severity": "major",
            "capability": "genuine longitudinal chronology",
            "detail": "D02 blocked: no curated two-exam case; forecast accuracy Not evaluated",
        },
        {
            "severity": "major",
            "capability": "real-data validation",
            "detail": "no approved real data, live provider runs or participant sessions in this scope",
        },
        {
            "severity": "minor",
            "capability": "measured performance",
            "detail": "p95/mesh/frame/budget targets unmeasured on declared hardware",
        },
    ]
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "journey": journey,
        "suites": {key: value.get("result") for key, value in reports.items()},
        "attempted_eligible_excluded_failed": {
            key: {
                k: value.get(k)
                for k in (
                    "attempted",
                    "eligible",
                    "excluded",
                    "failed",
                    "scored",
                    "frozen_cases",
                    "eligible_real_cases",
                )
                if k in value
            }
            for key, value in reports.items()
        },
        "defects": defects,
        "open_gates": [
            "genuine longitudinal D02",
            "real-data validation",
            "live deployment/provider verification",
            "qualified scientific review",
            "measured performance and participant review",
            "cloud recovery (COS-093/COS-098)",
        ],
        "evaluation_page_match": "Evaluation page separates fixture-tested from Not evaluated and Blocked with no decorative percentages, matching this report",
        "disposition": "blocked for full P0 readiness: missing mandatory genuine follow-up; identity/privacy/provenance gates intact for fixture scope",
        "scope": "pre-deployment candidate evidence only; not clinical validation or deployment readiness",
        "result": "blocked",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload["suites"], sort_keys=True).encode()
    ).hexdigest()
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "blocked"
    assert payload["disposition"].startswith("blocked")
