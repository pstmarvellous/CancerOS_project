"""SC-01 explicit-parameter software tests; no clinical response categories are inferred."""

from decimal import Decimal, localcontext
from uuid import UUID

import pytest

from canceros.scenario_families import build_registry, check_realized_order, volume_at
from canceros.simulation_contracts import SimulationConfig


def config(targets=("90", "70", "40"), clinical="stable", days=("7", "35", "91")):
    return SimulationConfig.model_validate(
        {
            "baseline_state_id": None,
            "baseline_hash": "a" * 64,
            "branch_id": UUID(int=1),
            "input_revision": 1,
            "scenario": {"family": "SC-01", "definition_version": "sc01-explicit/1"},
            "treatment": {"exposure": "none"},
            "schedule": {
                "slots": [
                    {"slot_id": f"scan-{i}", "modality": "imaging", "relative_day": day}
                    for i, day in enumerate(days)
                ]
            },
            "tumor_profile": {
                "points": [
                    {"slot_id": f"scan-{i}", "target_mm3": target}
                    for i, target in enumerate(targets)
                ]
            },
            "clinical_profile": {"configuration": clinical},
            "noise": {"mode": "none"},
            "missingness": {"mode": "none"},
            "geometry_policy": "none",
            "seed": 42,
        }
    )


@pytest.mark.parametrize("clinical", ["stable", "moderate_deterioration", "recovery"])
def test_irregular_explicit_knots_deterministic_and_clinical_independent(clinical):
    value = config(clinical=clinical)
    before = value.model_dump_json()
    baseline = Decimal(100)
    output = build_registry().generate(value, baseline)
    assert output == build_registry().generate(value, baseline)
    assert output.clinical_profile == value.clinical_profile
    assert [point.relative_day for point in output.tumor_targets] == ["7", "35", "91"]
    assert [point.target_mm3 for point in output.tumor_targets] == ["90", "70", "40"]
    assert baseline == 100 and value.model_dump_json() == before
    assert output.origin == "SYNTHETIC_GENERATED"


def test_piecewise_volume_exact_knots_intermediate_and_no_extrapolation():
    output = build_registry().generate(config(), Decimal(100))
    assert volume_at(output, Decimal(100), Decimal(0)) == 100
    assert volume_at(output, Decimal(100), Decimal(7)) == 90
    assert volume_at(output, Decimal(100), Decimal(21)) == 80
    assert volume_at(output, Decimal(100), Decimal(91)) == 40
    with localcontext() as context:
        context.prec = 5
        assert volume_at(output, Decimal(100), Decimal(21)) == 80
    for time in (Decimal(-1), Decimal(92), Decimal("NaN")):
        with pytest.raises(ValueError, match="outside"):
            volume_at(output, Decimal(100), time)


@pytest.mark.parametrize("baseline", ["0", "-1", "NaN", "Infinity", "1000000000000000"])
def test_invalid_baselines(baseline):
    with pytest.raises(ValueError):
        build_registry().generate(config(), Decimal(baseline))


@pytest.mark.parametrize(
    "targets", [("90", "90", "40"), ("90", "95", "40"), ("90", "70", "0"), ("101", "70", "40")]
)
def test_invalid_decline_and_disappearance(targets):
    with pytest.raises(ValueError):
        build_registry().generate(config(targets), Decimal(100))


def test_specific_unreviewed_exposure_is_rejected():
    data = config().model_dump(mode="json")
    data["treatment"] = {
        "exposure": "hypothetical",
        "category": "endocrine",
        "events": [
            {"event_id": "start", "relative_day": "0", "category": "hypothetical_exposure_start"}
        ],
    }
    with pytest.raises(ValueError, match="unreviewed"):
        build_registry().generate(SimulationConfig.model_validate(data), Decimal(100))


def test_noise_and_missingness_do_not_rewrite_latent_points():
    data = config().model_dump(mode="json")
    data["noise"] = {
        "mode": "explicit",
        "points": [
            {"slot_id": "scan-0", "channel": "numerical_region_volume", "additive_offset": "5"}
        ],
    }
    data["missingness"] = {
        "mode": "explicit",
        "points": [
            {"slot_id": "scan-1", "channel": "numerical_region_volume", "reason": "not_collected"}
        ],
    }
    output = build_registry().generate(SimulationConfig.model_validate(data), Decimal(100))
    assert [target.target_mm3 for target in output.tumor_targets] == ["90", "70", "40"]


@pytest.mark.parametrize(
    "realized,reason",
    [
        (["90", "90", "40"], "realized_decline_plateau"),
        (["90", "91", "40"], "realized_decline_reversed"),
        (["100", "70", "40"], "realized_decline_plateau"),
        (["90", None, "40"], "missing_realized_measurement"),
        (["90", "70", "0"], "invalid_realized_measurement"),
    ],
)
def test_quantization_order_failures_block_without_rewriting(realized, reason):
    output = build_registry().generate(config(), Decimal(100))
    values = [Decimal(value) if value is not None else None for value in realized]
    before = values.copy()
    result = check_realized_order(output.tumor_targets, values, Decimal(100))
    assert result.status == "blocked" and not result.ordering_valid
    assert any(item.startswith(reason) for item in result.reasons)
    assert values == before


def test_successful_measured_decline_only_closes_ordering_check():
    output = build_registry().generate(config(), Decimal(100))
    result = check_realized_order(
        output.tumor_targets, [Decimal(89), Decimal(71), Decimal(41)], Decimal(100)
    )
    assert result.ordering_valid and result.status == "ready"
    assert result.publication_gate == "separate_review_and_complete_run_required"
    assert check_realized_order(output.tumor_targets, [], Decimal(100)).status == "blocked"


def test_other_families_not_registered_before_their_implementation():
    with pytest.raises(ValueError, match="not registered"):
        build_registry().resolve("SC-01", "unknown-version")
