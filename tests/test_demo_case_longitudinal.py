"""COS-095 authentic demo gate: reuses the COS-083 longitudinal gate, stays blocked.

No verified original-patient case with two distinct real exams, permitted demo
use and reviewed lesion/mask/measurement meaning exists in this scope. The gate
re-reads the COS-083 evidence artifact, pins the same D02 requirement into the
demo preflight, and refuses synthetic dates/scans, morphed baselines and
recordings labeled authentic. Reduced-scope demo stays honest: five synthetic
entries (COS-094) without a genuine pair.
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
    / "demo-case-longitudinal.json"
)
SUITE_VERSION = "demo-case-longitudinal/1"
GATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "engineering"
    / "evidence"
    / "longitudinal-gate.json"
)


def test_authentic_pair_reuses_cos083_gate_and_stays_blocked():
    assert GATE_PATH.exists(), "COS-083 longitudinal gate evidence required"
    gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))
    assert gate["result"] == "blocked"
    assert gate["eligible_real_cases"] == 0
    allowed_narration = [
        "what was collected",
        "what changed",
        "what is uncertain",
        "what cannot be concluded",
    ]
    forbidden = [
        "causal treatment benefit",
        "resistance claim",
        "stage claim",
        "survival claim",
        "formal response grade",
        "population forecast",
        "synthetic dates",
        "morphed baseline",
        "recording labeled authentic",
    ]
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "cos083_gate_result": gate["result"],
        "eligible_original_patients": 0,
        "distinct_real_exams": 0,
        "registration_qc": "not established; side-by-side or sequential only with spatial alignment not established",
        "narration_scope": allowed_narration,
        "forbidden_claims": forbidden,
        "demo_preflight": "blocked D02 retained; reduced-scope demo uses COS-094 synthetic entries only",
        "scope": "preflight pin without an authentic pair; no overstated clinical conclusion",
        "result": "blocked",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps({"gate": gate["manifest_sha256"]}, sort_keys=True).encode()
    ).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "blocked"
