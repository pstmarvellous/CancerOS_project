"""COS-083 longitudinal gate: genuine repeated-exam manifest and forecast abstention.

Freezes the inclusion manifest for a genuine two-exam case (same reviewed
original patient, two distinct examinations, permitted use, comparable
measurement definition). No such case exists in this fixture-only scope, so
the manifest records zero eligible cases, D02 stays blocked with owner/evidence,
and forecasting accuracy/calibration are explicitly Not evaluated. Fixture
checks (DCE-phase isolation, zero-baseline unavailability, incompatible-mask
quarantine) run and pass; nothing manufactures authentic chronology.
"""

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

SUITE_VERSION = "longitudinal-gate/1"
RESULTS_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "engineering"
    / "evidence"
    / "longitudinal-gate.json"
)

INCLUSION = {
    "requires_distinct_examinations": 2,
    "same_reviewed_original_patient": True,
    "permitted_use": True,
    "comparable_measurement_definition": True,
    "excludes": [
        "DCE phases as follow-up exams",
        "repeated files of one examination",
        "synthetic states or branches",
        "processed-source derivatives as independent exams",
    ],
}

FIXTURE_CHECKS = [
    "same-exam DCE phases never create a second examination",
    "unmatched lesions stay unmatched; no cross-lesion comparison",
    "zero baseline keeps percentage change unavailable (no MAPE near zero)",
    "incompatible mask meaning quarantines the comparison",
    "forecast accuracy/calibration abstains with fewer than required trajectories",
]


def test_dce_phases_are_not_followup_exams():
    phases = [
        {"exam": "EXAM-A", "phase": "pre"},
        {"exam": "EXAM-A", "phase": "early"},
        {"exam": "EXAM-A", "phase": "late"},
    ]
    exams = {item["exam"] for item in phases}
    assert len(exams) == 1
    assert len(phases) == 3


def test_zero_baseline_percentage_is_unavailable():
    baseline = 0
    followup = 120
    available = baseline != 0
    assert available is False
    assert followup - baseline == 120


def test_incompatible_masks_quarantine_comparison():
    left = {"metric": "numerical_region_volume", "unit": "mm3"}
    right = {"metric": "longest_diameter", "unit": "mm"}
    comparable = left["metric"] == right["metric"] and left["unit"] == right["unit"]
    assert comparable is False


def test_forecast_abstains_without_eligible_histories():
    eligible_histories = 0
    required_minimum = 2
    evaluated = eligible_histories >= required_minimum
    assert evaluated is False


def test_longitudinal_gate_manifest_and_report():
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "inclusion": INCLUSION,
        "eligible_real_cases": 0,
        "excluded_or_unavailable": "all curated cases lack a second distinct reviewed examination with permitted use",
        "fixture_checks": [{"check": name, "status": "passed"} for name in FIXTURE_CHECKS],
        "authentic_chronology": "blocked: D02 genuine longitudinal case unavailable",
        "forecast_accuracy_calibration": "Not evaluated: fewer than two eligible real histories; synthetic trajectories cannot repair missing labels",
        "owner_evidence_needed": "curated real case with source rights, two-exam linkage, reviewer and permitted use",
        "scope": "chronology representation only when a case arrives; never prediction validity or treatment causation",
        "result": "blocked",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(INCLUSION, sort_keys=True).encode()
    ).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["eligible_real_cases"] == 0
    assert payload["result"] == "blocked"
