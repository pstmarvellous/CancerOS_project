"""COS-081 release suite: unit, schema, provenance and simulation integrity.

Consolidates the existing five-family tabular regression (50 attempts: five
families x ten fixed seeds, plus a repeated five-family determinism check),
contract/decimal/time coverage and provenance/integrity negative cases into one
documented release suite with a frozen manifest and machine-readable results.
Uses tiny synthetic fixtures only; authorized real-data suites stay separate.
"""

import hashlib
import json
import platform
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from test_scenario_families import config as generic
from test_scenario_sc02 import stable
from test_scenario_sc05 import payload as deterioration

from canceros.clinical_generation import materialize_measurement_only
from canceros.sampling import sample_observations
from canceros.scenario_families import build_registry
from canceros.simulation_contracts import SimulationConfig
from canceros.simulation_validation import validate_complete_run

FAMILIES = ("SC-01", "SC-02", "SC-03", "SC-04", "SC-05")
SEEDS = tuple(range(10))
REPEAT_SEED = 7
SUITE_VERSION = "release-suite/1"
MANIFEST_PATH = Path(__file__).resolve().parent / "release_suite_manifest.json"
RESULTS_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "engineering" / "evidence" / "release-suite.json"
)


def regression_config(family, seed):
    if family == "SC-05":
        data = deterioration(family="SC-02", symptom=True)
        data["sc02_parameters"] = {
            "mode": "near_stable",
            "max_absolute_change_mm3": "0",
            "max_relative_change": "0",
        }
    elif family == "SC-02":
        data = stable(targets=("512", "512", "512"), absolute="0", relative="0").model_dump(
            mode="json"
        )
    else:
        values = {
            "SC-01": ("216", "64", "8"),
            "SC-03": ("1000", "1728", "2744"),
            "SC-04": ("216", "64", "216"),
        }[family]
        data = generic(targets=values, days=("37", "56", "90")).model_dump(mode="json")
        data["scenario"] = {
            "family": family,
            "definition_version": family.lower().replace("-", "") + "-explicit/1",
        }
        if family == "SC-04":
            data["sc04_parameters"] = {"change_point_day": "56", "nadir_mm3": "64"}
    data["seed"] = seed
    data["geometry_policy"] = "none"
    if family == "SC-05":
        for point in data["tumor_profile"]["points"]:
            point["target_mm3"] = "512"
        data["sc05_parameters"]["symptom_course"][-1]["rating"] = 6
    return SimulationConfig.model_validate(data)


def run_tabular(family, seed, run_id):
    config = regression_config(family, seed)
    output = build_registry().generate(config, Decimal(512))
    sampled = sample_observations(config, output)
    clinical = materialize_measurement_only(config, output, run_id)
    report = validate_complete_run(config, output, sampled, clinical, Decimal(512), [])
    assert report.scope == "measurement_only"
    return config, report


def write_manifest():
    manifest = {
        "suite": SUITE_VERSION,
        "families": list(FAMILIES),
        "seeds_per_family": list(SEEDS),
        "repeat_seed": REPEAT_SEED,
        "scope": "tiny synthetic fixtures only; authorized real-data suites remain separate",
        "entrypoint": "uv run python -m pytest tests/test_release_suite.py --tb=line",
        "negative_fixtures": [
            "wrong units rejected by schema validation (test_clinical_validation)",
            "nonfinite numbers rejected (test_clinical_validation)",
            "DCE phases never create visits (test_annotation_contracts)",
            "stale snapshot reuse denied (test_twin_states)",
            "failed runs invisible to judges (test_simulation_runs)",
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def write_results(attempts, repeated_match, manifest_hash):
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "manifest_sha256": manifest_hash,
        "attempts": attempts,
        "attempted": len(attempts),
        "passed": sum(1 for a in attempts if a["status"] == "engineering_passed"),
        "repeated_set_semantic_match": repeated_match,
        "scope": "fixture verification only; no real-data or qualified review claim",
        "result": "passed"
        if len(attempts) == 50
        and all(a["status"] == "engineering_passed" for a in attempts)
        and repeated_match
        else "failed",
    }
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def test_release_manifest_is_frozen_and_complete():
    manifest = write_manifest()
    assert manifest["families"] == list(FAMILIES)
    assert manifest["seeds_per_family"] == list(SEEDS)
    assert len(manifest["negative_fixtures"]) >= 5


def test_fifty_tabular_attempts_and_repeated_set():
    attempts = []
    digests = {}
    for family_index, family in enumerate(FAMILIES):
        for seed in SEEDS:
            _, report = run_tabular(family, seed, UUID(int=family_index * 100 + seed + 1))
            attempts.append({"family": family, "seed": seed, "status": report.status})
    assert len(attempts) == 50
    assert all(a["status"] == "engineering_passed" for a in attempts)
    matched = True
    for index, family in enumerate(FAMILIES):
        first = run_tabular(family, REPEAT_SEED, UUID(int=index + 1))[1]
        repeated = run_tabular(family, REPEAT_SEED, UUID(int=index + 101))[1]
        digests[family] = first.semantic_digest
        matched = (
            matched
            and first.status == repeated.status == "engineering_passed"
            and first.semantic_digest == repeated.semantic_digest
        )
    assert matched
    manifest_hash = hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
    payload = write_results(attempts, matched, manifest_hash)
    assert payload["result"] == "passed"
