"""Explicit SC-02 engineering bounds; no clinical response threshold is assumed."""

from decimal import Decimal

import pytest
from pydantic import ValidationError
from test_scenario_families import config as sc01_config

from canceros.scenario_families import build_registry, check_family_realized
from canceros.simulation_contracts import SimulationConfig


def config(mode="near_stable", targets=("100", "99", "101"), **bounds):
    data = sc01_config(targets=targets).model_dump(mode="json")
    data["scenario"] = {"family": "SC-02", "definition_version": "sc02-explicit/1"}
    data["sc02_parameters"] = {"mode": mode, **bounds}
    return SimulationConfig.model_validate(data)


def stable(targets=("100", "99", "101"), absolute="2", relative="0.02"):
    return config(targets=targets, max_absolute_change_mm3=absolute, max_relative_change=relative)


def modest(targets=("99", "95", "90"), lower="0.05", upper="0.15"):
    return config(
        mode="modest_reduction",
        targets=targets,
        min_relative_decline=lower,
        max_relative_decline=upper,
    )


@pytest.mark.parametrize("value", [stable, modest])
def test_modes_repeat_and_preserve_independent_clinical_profile(value):
    request = value()
    data = request.model_dump(mode="json")
    data["clinical_profile"]["configuration"] = "severe_deterioration"
    request = SimulationConfig.model_validate(data)
    before = request.model_dump_json()
    output = build_registry().generate(request, Decimal(100))
    assert output == build_registry().generate(request, Decimal(100))
    assert output.family == "SC-02" and output.mode == request.sc02_parameters.mode
    assert output.clinical_profile == request.clinical_profile
    assert request.model_dump_json() == before


def test_overlapping_bands_preserve_explicit_requested_mode():
    targets = ("99", "98", "97")
    first = build_registry().generate(stable(targets, "5", "0.05"), Decimal(100))
    second = build_registry().generate(modest(targets, "0.01", "0.05"), Decimal(100))
    assert first.tumor_targets == second.tumor_targets
    assert first.mode == "near_stable" and second.mode == "modest_reduction"


@pytest.mark.parametrize(
    "absolute,relative,targets,ok",
    [
        ("2", "0.01", ("99", "100", "101"), True),
        ("2", "0.01", ("99", "100", "101.000000001"), False),
        ("1", "0.02", ("99", "100", "101.000000001"), False),
        ("0", "0", ("100", "100", "100"), True),
        ("0", "0", ("100", "100", "99.999999999"), False),
    ],
)
def test_near_stable_uses_intersection_of_declared_limits(absolute, relative, targets, ok):
    request = stable(targets, absolute, relative)
    if ok:
        build_registry().generate(request, Decimal(100))
    else:
        with pytest.raises(ValueError, match="bound"):
            build_registry().generate(request, Decimal(100))


@pytest.mark.parametrize(
    "targets,ok",
    [
        (("99", "95", "90"), True),
        (("99", "95", "85"), True),
        (("99", "95", "95"), False),
        (("99", "95", "96"), False),
        (("99", "95", "94.999999999"), True),
        (("99", "95", "95.000000001"), False),
        (("99", "95", "84.999999999"), False),
        (("99", "95", "0"), False),
    ],
)
def test_modest_horizon_bounds_and_order(targets, ok):
    request = modest(targets)
    if ok:
        build_registry().generate(request, Decimal(100))
    else:
        with pytest.raises(ValueError):
            build_registry().generate(request, Decimal(100))


@pytest.mark.parametrize(
    "params",
    [
        {"mode": "near_stable", "max_absolute_change_mm3": "-1", "max_relative_change": "0.1"},
        {"mode": "near_stable", "max_absolute_change_mm3": "1", "max_relative_change": "1.1"},
        {
            "mode": "near_stable",
            "max_absolute_change_mm3": "1",
            "max_relative_change": "0.1",
            "min_relative_decline": "0.1",
        },
        {"mode": "modest_reduction", "min_relative_decline": "0", "max_relative_decline": "1"},
        {"mode": "modest_reduction", "min_relative_decline": "0.2", "max_relative_decline": "0.1"},
        {"mode": "modest_reduction", "min_relative_decline": "0.1", "max_relative_decline": "1.1"},
    ],
)
def test_invalid_or_contradictory_declared_parameters(params):
    data = stable().model_dump(mode="json")
    data["sc02_parameters"] = params
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(data)


def test_modes_are_required_and_not_silently_ignored_by_other_families():
    data = stable().model_dump(mode="json")
    data["sc02_parameters"] = None
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(data)
    data = sc01_config().model_dump(mode="json")
    data["sc02_parameters"] = stable().sc02_parameters.model_dump(mode="json")
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(data)


@pytest.mark.parametrize(
    "configuration,realized,ready",
    [
        (stable(), ["100", "99", "101"], True),
        (stable(), ["100", "99", "102.000000001"], False),
        (modest(), ["99", "95", "90"], True),
        (modest(), ["99", "99", "90"], False),
        (modest(), ["99", None, "90"], False),
        (modest(), ["99", "95", "96"], False),
    ],
)
def test_realized_values_use_same_declared_mode_without_rewriting(configuration, realized, ready):
    output = build_registry().generate(configuration, Decimal(100))
    values = [Decimal(item) if item is not None else None for item in realized]
    before = values.copy()
    result = check_family_realized(configuration, output.tumor_targets, values, Decimal(100))
    assert result.ordering_valid == ready
    assert result.status == ("ready" if ready else "blocked")
    assert values == before


def test_explicit_wide_near_stable_band_can_include_zero_without_cure_inference():
    request = stable(("99", "90", "0"), "100", "1")
    output = build_registry().generate(request, Decimal(100))
    assert output.mode == "near_stable"
    assert check_family_realized(
        request, output.tumor_targets, [Decimal(99), Decimal(90), Decimal(0)], Decimal(100)
    ).ordering_valid


def test_sampling_noise_and_missingness_are_separate_from_latent_mode():
    data = stable().model_dump(mode="json")
    data["noise"] = {
        "mode": "explicit",
        "points": [
            {"slot_id": "scan-0", "channel": "numerical_region_volume", "additive_offset": "50"}
        ],
    }
    data["missingness"] = {
        "mode": "explicit",
        "points": [
            {"slot_id": "scan-1", "channel": "numerical_region_volume", "reason": "not_collected"}
        ],
    }
    output = build_registry().generate(SimulationConfig.model_validate(data), Decimal(100))
    assert [point.target_mm3 for point in output.tumor_targets] == ["100", "99", "101"]
    assert output.mode == "near_stable"


def test_wrong_units_and_zero_baseline_are_rejected():
    data = stable().model_dump(mode="json")
    data["tumor_profile"]["unit"] = "cm3"
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(data)
    with pytest.raises(ValueError):
        build_registry().generate(stable(), Decimal(0))


def test_nonfinite_realized_and_wrong_frozen_targets_block():
    request = stable()
    output = build_registry().generate(request, Decimal(100))
    result = check_family_realized(
        request, output.tumor_targets, [Decimal(100), Decimal("NaN"), Decimal(101)], Decimal(100)
    )
    assert result.status == "blocked"
    changed = output.tumor_targets.copy()
    changed[0] = changed[0].model_copy(update={"target_mm3": "99"})
    assert (
        check_family_realized(
            request, changed, [Decimal(100), Decimal(99), Decimal(101)], Decimal(100)
        ).status
        == "blocked"
    )
