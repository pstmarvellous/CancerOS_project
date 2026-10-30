"""Fifty explicit tabular trajectories and a repeated five-family set; not geometry coverage."""

from decimal import Decimal
from uuid import UUID

from test_scenario_families import config as generic
from test_scenario_sc02 import stable
from test_scenario_sc05 import payload as deterioration

from canceros.clinical_generation import materialize_measurement_only
from canceros.sampling import sample_observations
from canceros.scenario_families import build_registry
from canceros.simulation_contracts import SimulationConfig
from canceros.simulation_validation import validate_complete_run


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
    data["schedule"]["slots"].append(
        {"slot_id": "optional-weight", "modality": "vital", "relative_day": "5"}
    )
    data["clinical_profile"]["points"].append(
        {"slot_id": "optional-weight", "code": "weight", "value": "65", "unit": "kg"}
    )
    data["sampling"] = {
        "noise_rules": [
            {
                "slot_id": "optional-weight",
                "channel": "weight",
                "min_offset": "-0.1",
                "max_offset": "0.1",
            }
        ]
    }
    return SimulationConfig.model_validate(data)


def run_tabular(family, seed, run_id):
    config = regression_config(family, seed)
    output = build_registry().generate(config, Decimal(512))
    sampled = sample_observations(config, output)
    clinical = materialize_measurement_only(config, output, run_id)
    report = validate_complete_run(config, output, sampled, clinical, Decimal(512), [])
    assert report.scope == "measurement_only"
    return report


def test_fifty_attempts_across_five_families_and_ten_fixed_seeds():
    attempts = []
    for family_index, family in enumerate(("SC-01", "SC-02", "SC-03", "SC-04", "SC-05")):
        for seed in range(10):
            report = run_tabular(family, seed, UUID(int=family_index * 100 + seed + 1))
            attempts.append({"family": family, "seed": seed, "status": report.status})
    assert len(attempts) == 50
    assert sum(attempt["status"] == "engineering_passed" for attempt in attempts) == 50
    assert all(
        sum(attempt["family"] == family for attempt in attempts) == 10
        for family in ("SC-01", "SC-02", "SC-03", "SC-04", "SC-05")
    )


def test_repeat_complete_five_family_set_has_matching_scientific_semantics():
    for index, family in enumerate(("SC-01", "SC-02", "SC-03", "SC-04", "SC-05")):
        first = run_tabular(family, 7, UUID(int=index + 1))
        repeated = run_tabular(family, 7, UUID(int=index + 101))
        assert first.status == repeated.status == "engineering_passed"
        assert first.semantic_digest == repeated.semantic_digest
