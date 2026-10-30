"""SC-03 arithmetic constraints, separate from biological and source-context claims."""

from decimal import Decimal

import pytest
from pydantic import ValidationError
from test_scenario_families import config as sc01_config

from canceros.scenario_families import build_registry, check_family_realized, check_realized_growth
from canceros.simulation_contracts import SimulationConfig


def config(targets=("110", "130", "170"), clinical="stable"):
    data = sc01_config(targets=targets, clinical=clinical).model_dump(mode="json")
    data["scenario"] = {"family": "SC-03", "definition_version": "sc03-explicit/1"}
    return SimulationConfig.model_validate(data)


@pytest.mark.parametrize("clinical", ["stable", "severe_deterioration", "recovery"])
def test_increasing_targets_irregular_days_and_independent_clinical_state(clinical):
    request = config(clinical=clinical)
    before = request.model_dump_json()
    baseline = Decimal(100)
    output = build_registry().generate(request, baseline)
    assert output == build_registry().generate(request, baseline)
    assert [point.relative_day for point in output.tumor_targets] == ["7", "35", "91"]
    assert [point.target_mm3 for point in output.tumor_targets] == ["110", "130", "170"]
    assert output.family == "SC-03" and output.mode is None
    assert output.clinical_profile == request.clinical_profile
    assert request.model_dump_json() == before and baseline == 100


@pytest.mark.parametrize(
    "targets",
    [
        ("100", "130", "170"),
        ("110", "110", "170"),
        ("110", "109", "170"),
        ("0", "110", "170"),
        ("110", "130", "129"),
    ],
)
def test_invalid_growth_or_zero_target_is_rejected(targets):
    with pytest.raises(ValueError):
        build_registry().generate(config(targets), Decimal(100))


@pytest.mark.parametrize("baseline", ["0", "-1", "NaN", "Infinity", "1000000000000000"])
def test_invalid_baselines_are_not_given_growth_narratives(baseline):
    with pytest.raises(ValueError):
        build_registry().generate(config(), Decimal(baseline))


def test_very_high_bounded_finite_targets_do_not_overflow():
    request = config(("999999999999997", "999999999999998", "999999999999999.999999999"))
    output = build_registry().generate(request, Decimal("999999999999996"))
    assert output.tumor_targets[-1].target_mm3 == "999999999999999.999999999"
    for value in ("1000000000000000", "1000000000000001", "NaN", "Infinity", "-1"):
        with pytest.raises(ValidationError):
            config(("110", "130", value))


def test_generic_hypothetical_exposure_does_not_change_explicit_growth():
    data = config().model_dump(mode="json")
    data["treatment"] = {
        "exposure": "hypothetical",
        "events": [
            {"event_id": "start", "relative_day": "0", "category": "hypothetical_exposure_start"}
        ],
    }
    request = SimulationConfig.model_validate(data)
    assert build_registry().generate(request, Decimal(100)).tumor_targets[0].target_mm3 == "110"
    data["treatment"]["category"] = "chemotherapy"
    with pytest.raises(ValueError, match="unreviewed"):
        build_registry().generate(SimulationConfig.model_validate(data), Decimal(100))


def test_wrong_metric_unit_is_not_accepted_as_volume():
    data = config().model_dump(mode="json")
    data["tumor_profile"]["unit"] = "cm3"
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(data)


@pytest.mark.parametrize(
    "actual,reason",
    [
        (["110", "130", "170"], None),
        (["100", "130", "170"], "realized_growth_plateau"),
        (["110", "110", "170"], "realized_growth_plateau"),
        (["110", "109", "170"], "realized_growth_reversed"),
        (["110", "130", "0"], "invalid_realized_measurement"),
        (["110", "130", "NaN"], "invalid_realized_measurement"),
        (["110", None, "170"], "missing_realized_measurement"),
    ],
)
def test_actual_growth_is_required_and_original_values_are_retained(actual, reason):
    request = config()
    output = build_registry().generate(request, Decimal(100))
    realized = [Decimal(value) if value is not None else None for value in actual]
    before = realized.copy()
    result = check_family_realized(request, output.tumor_targets, realized, Decimal(100))
    assert result.ordering_valid == (reason is None)
    assert result.status == ("ready" if reason is None else "blocked")
    if reason:
        assert any(item.startswith(reason) for item in result.reasons)
    assert all(a is b for a, b in zip(realized, before, strict=True))


def test_measured_count_mismatch_and_invalid_frozen_targets_block():
    request = config()
    output = build_registry().generate(request, Decimal(100))
    assert check_realized_growth(output.tumor_targets, [], Decimal(100)).status == "blocked"
    altered = output.tumor_targets.copy()
    altered[0] = altered[0].model_copy(update={"target_mm3": "120"})
    result = check_family_realized(
        request, altered, [Decimal(110), Decimal(130), Decimal(170)], Decimal(100)
    )
    assert result.status == "blocked"


def test_noise_and_missingness_do_not_fake_latent_growth_or_source_context():
    data = config().model_dump(mode="json")
    data["noise"] = {
        "mode": "explicit",
        "points": [
            {"slot_id": "scan-0", "channel": "numerical_region_volume", "additive_offset": "-100"}
        ],
    }
    data["missingness"] = {
        "mode": "explicit",
        "points": [
            {"slot_id": "scan-1", "channel": "numerical_region_volume", "reason": "not_collected"}
        ],
    }
    output = build_registry().generate(SimulationConfig.model_validate(data), Decimal(100))
    assert [point.target_mm3 for point in output.tumor_targets] == ["110", "130", "170"]
    assert output.assumptions == "unreviewed_demonstration_not_patient_prediction"
