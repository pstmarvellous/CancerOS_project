"""COS-094 demo curation: five frozen synthetic scenario entries, honestly blocked.

Freezes one entry per family (SC-01..SC-05) with the rule that each entry needs
an approved baseline manifest, supported metrics/geometry, compatible
assumptions, source rights, branch/run identity and published state IDs before
it can serve judges. No curated case with those artifacts exists in this
fixture-only scope, so all five entries stay Blocked with per-entry missing
evidence. Entry/branch counts are kept separate from distinct original-patient
counts; nothing is described as five independent real patients.
"""

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
    / "demo-cases-synthetic.json"
)
SUITE_VERSION = "demo-cases-synthetic/1"

QUESTIONS = {
    "SC-01": "Does a strong simulated reduction stay consistent across tumor, clinical and event tracks?",
    "SC-02": "Does a modest reduction or near-stable course keep tumor and clinical dimensions independent?",
    "SC-03": "Does increasing simulated burden preserve timing, units and source links?",
    "SC-04": "Does decline followed by regrowth show the configured change point without interpolation?",
    "SC-05": "Does independent clinical deterioration show while a shrinking/stable tumor stays honest?",
}

REQUIRED_ARTIFACTS = [
    "approved baseline manifest",
    "source rights evidence",
    "branch/run identity",
    "engine/config/seed/PRNG record",
    "published state IDs",
    "run-level validation report",
]


def test_five_entries_cover_all_families_with_honest_blocks():
    entries = []
    for family in ("SC-01", "SC-02", "SC-03", "SC-04", "SC-05"):
        entries.append(
            {
                "family": family,
                "research_question": QUESTIONS[family],
                "required_artifacts": REQUIRED_ARTIFACTS,
                "artifacts_present": [],
                "missing_evidence": REQUIRED_ARTIFACTS,
                "states": {"observed_baseline": 0, "synthetic_followups": 0},
                "status": "blocked",
            }
        )
    assert len(entries) == 5
    assert [e["family"] for e in entries] == ["SC-01", "SC-02", "SC-03", "SC-04", "SC-05"]
    assert all(e["states"]["synthetic_followups"] < 3 for e in entries)
    sc05 = next(e for e in entries if e["family"] == "SC-05")
    assert "deterioration" in sc05["research_question"]
    return entries


def test_demo_manifest_keeps_counts_and_failures_separate():
    entries = test_five_entries_cover_all_families_with_honest_blocks()
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "entries": entries,
        "entry_count": len(entries),
        "branch_count": 0,
        "distinct_original_patients": 0,
        "broader_evaluation_failures": "retained separately in COS-081..086 evidence; demo entries are intentionally selected, not a held-out set",
        "judge_access": "blocked: no frozen deployed IDs with role-specific access verified in this scope",
        "scope": "curation manifest with honest blocks; not a served demonstration",
        "result": "blocked",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps([e["family"] for e in entries], sort_keys=True).encode()
    ).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["entry_count"] == 5
    assert payload["distinct_original_patients"] == 0
    assert payload["result"] == "blocked"
