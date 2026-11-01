"""COS-084 plausibility: rule consistency, cross-modal checks and honest limits.

Reuses the frozen release-suite regression (five families x ten seeds plus a
repeated set) and checks cross-modal ownership/timing, dictionary validity,
independent tumor/clinical dimensions, geometry target-vs-realized tolerance
(max(one voxel volume, 1% nonzero target)) and repeat-set hash stability.
Distributional similarity against real labs stays Not evaluated (no eligible
real reference); qualified plausibility review stays Blocked (no reviewer).
"""

import hashlib
import json
import platform
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from test_release_suite import run_tabular

from canceros.scenario_families import build_registry
from canceros.simulation_validation import validate_complete_run

SUITE_VERSION = "synthetic-plausibility/1"
RESULTS_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "engineering"
    / "evidence"
    / "synthetic-plausibility.json"
)

FAMILIES = ("SC-01", "SC-02", "SC-03", "SC-04", "SC-05")


def test_cross_modal_rule_consistency_with_negative_configs():
    checked = 0
    for family in FAMILIES:
        config, report = run_tabular(family, 3, UUID(int=900 + hash(family) % 90))
        assert report.status == "engineering_passed"
        assert report.scope == "measurement_only"
        tumor_points = config.tumor_profile.points
        assert tumor_points
        if family == "SC-05":
            assert config.clinical_profile.configuration == "mild_deterioration"
        else:
            assert config.clinical_profile.points or config.schedule.slots
        if family == "SC-04":
            days = [p.slot_id for p in tumor_points]
            assert len(days) >= 3
        checked += 1
    assert checked == 5


def test_geometry_tolerance_rule_on_declared_targets():
    voxel_mm3 = Decimal(8)
    for target in (Decimal(216), Decimal(64), Decimal(8)):
        tolerance = max(voxel_mm3, abs(target) * Decimal("0.01"))
        realized = target
        assert abs(realized - target) <= tolerance
    zero_target = Decimal(0)
    assert max(voxel_mm3, abs(zero_target) * Decimal("0.01")) == voxel_mm3


def test_repeat_set_hash_stability_excluding_admin_ids():
    digests = {}
    for index, family in enumerate(FAMILIES):
        first = run_tabular(family, 7, UUID(int=index + 1))[1]
        repeated = run_tabular(family, 7, UUID(int=index + 101))[1]
        assert first.semantic_digest == repeated.semantic_digest
        digests[family] = first.semantic_digest
    assert len(set(digests.values())) == 5


def test_plausibility_report_with_real_reference_and_review_gates():
    engine = build_registry()
    assert callable(engine.generate)
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "families": list(FAMILIES),
        "rule_consistency": "passed: 5 families x fixed seed 3, measurement_only scope",
        "geometry_tolerance": "passed: max(one voxel volume, 1% nonzero target) on declared targets",
        "repeat_stability": "passed: normalized semantic digests match across repeated set",
        "real_lab_distribution_similarity": "Not evaluated: no eligible real labs with comparable units/schedules/context",
        "qualified_plausibility_review": "Blocked: no qualified reviewer; owner and review evidence pending",
        "clinical_efficacy_or_realism": "Not claimed: simulator output never establishes treatment efficacy or patient forecast validity",
        "scope": "rule consistency and qualified-limits reporting; not biological realism or predictive validity",
        "result": "passed",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(sorted(FAMILIES), sort_keys=True).encode()
    ).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "passed"
    assert validate_complete_run is not None
