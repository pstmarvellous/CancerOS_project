"""Configured model turning point and sampled minimum remain distinct, without biology inference."""

from decimal import Decimal

import pytest
from pydantic import ValidationError
from test_scenario_families import config as sc01_config

from canceros.scenario_families import build_registry, check_family_realized, sc04_volume_at
from canceros.simulation_contracts import SimulationConfig
from canceros.simulation_plugins import PluginRegistry


def config(days=("10", "30", "40"), targets=("80", "75", "90"), change="20", nadir="60"):
    data = sc01_config(days=days, targets=targets).model_dump(mode="json")
    data["scenario"] = {"family": "SC-04", "definition_version": "sc04-explicit/1"}
    data["sc04_parameters"] = {"change_point_day": change, "nadir_mm3": nadir}
    return SimulationConfig.model_validate(data)


@pytest.mark.parametrize(
    "days,targets,sampled_day,sampled_minimum",
    [
        (("10", "30", "40"), ("80", "75", "90"), "30", "75"),
        (("10", "20", "40"), ("80", "60", "90"), "20", "60"),
    ],
)
def test_change_point_on_or_between_samples_retains_both_kinds_of_minimum(
    days, targets, sampled_day, sampled_minimum
):
    request = config(days, targets)
    before = request.model_dump_json()
    output = build_registry().generate(request, Decimal(100))
    assert output == build_registry().generate(request, Decimal(100))
    control = output.turning_point
    assert control is not None
    assert control.configured_day == "20" and control.configured_nadir_mm3 == "60"
    assert control.latent_sampled_minimum_day == sampled_day
    assert control.latent_sampled_minimum_mm3 == sampled_minimum
    assert control.kind == "model_control_not_detected_biology"
    assert len(output.tumor_targets) == 3
    assert request.model_dump_json() == before
    assert output.tumor_targets[-1].target_mm3 == "90"  # Regrowth need not exceed baseline.


def test_continuity_on_each_side_of_explicit_control_and_closed_horizon():
    request = config()
    baseline = Decimal(100)
    assert sc04_volume_at(request, baseline, Decimal(0)) == 100
    assert sc04_volume_at(request, baseline, Decimal(20)) == 60
    assert sc04_volume_at(request, baseline, Decimal(40)) == 90
    assert sc04_volume_at(request, baseline, Decimal("19.999999999")) == Decimal("60.000000002")
    assert sc04_volume_at(request, baseline, Decimal("20.000000001")) == Decimal("60.0000000015")
    for day in (Decimal(-1), Decimal(41), Decimal("NaN")):
        with pytest.raises(ValueError, match="outside"):
            sc04_volume_at(request, baseline, day)


@pytest.mark.parametrize("profile", ["stable", "moderate_deterioration", "recovery"])
def test_clinical_profile_independent_of_control_path(profile):
    data = config().model_dump(mode="json")
    data["clinical_profile"]["configuration"] = profile
    request = SimulationConfig.model_validate(data)
    output = build_registry().generate(request, Decimal(100))
    assert output.clinical_profile == request.clinical_profile


@pytest.mark.parametrize(
    "change,nadir",
    [
        ("0", "60"),
        ("-1", "60"),
        ("20", "0"),
        ("20", "-1"),
        ("NaN", "60"),
        ("20", "Infinity"),
    ],
)
def test_invalid_nonpositive_nonfinite_control_fields_rejected(change, nadir):
    with pytest.raises(ValidationError):
        config(change=change, nadir=nadir)


@pytest.mark.parametrize("change,nadir", [("40", "60"), ("41", "60"), ("20", "100"), ("20", "101")])
def test_change_point_must_be_interior_and_nadir_below_positive_baseline(change, nadir):
    with pytest.raises(ValueError):
        build_registry().generate(config(change=change, nadir=nadir), Decimal(100))


@pytest.mark.parametrize("targets", [("80", "74", "90"), ("80", "75", "60"), ("80", "75", "0")])
def test_conflicting_knots_or_no_regrowth_rejected(targets):
    with pytest.raises(ValueError):
        build_registry().generate(config(targets=targets), Decimal(100))


def test_schedule_must_reveal_turning_and_have_three_followups():
    # The continuous nadir exists, but these samples only decline (100,95,90,85).
    with pytest.raises(ValueError):
        build_registry().generate(
            config(days=("1", "2", "40"), targets=("95", "90", "85"), change="8", nadir="60"),
            Decimal(100),
        )
    data = config().model_dump(mode="json")
    data["schedule"]["slots"].pop()
    data["tumor_profile"]["points"].pop()
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(data)


def test_first_followup_can_be_sampled_nadir_with_baseline_showing_decline():
    request = config(days=("10", "20", "40"), targets=("60", "70", "90"), change="10")
    output = build_registry().generate(request, Decimal(100))
    assert output.turning_point.latent_sampled_minimum_slot_id == "scan-0"


@pytest.mark.parametrize(
    "actual,ready",
    [
        (["80", "75", "90"], True),
        (["79", "74", "91"], True),
        (["80", "80", "90"], False),
        (["80", "79", "75"], False),
        (["70", "80", "90"], False),
        (["110", "115", "120"], False),
        (["80", None, "90"], False),
        (["80", "0", "90"], False),
        (["80", "NaN", "90"], False),
    ],
)
def test_realized_turn_erasure_shift_plateau_and_missing_block_without_rewrite(actual, ready):
    request = config()
    output = build_registry().generate(request, Decimal(100))
    values = [Decimal(value) if value is not None else None for value in actual]
    before = values.copy()
    result = check_family_realized(request, output.tumor_targets, values, Decimal(100))
    assert result.ordering_valid == ready
    assert result.status == ("ready" if ready else "blocked")
    assert all(a is b for a, b in zip(values, before, strict=True))


def test_sc04_parameters_required_only_for_sc04_and_exposure_remains_unreviewed():
    data = config().model_dump(mode="json")
    data["sc04_parameters"] = None
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(data)
    data = config().model_dump(mode="json")
    data["scenario"] = {"family": "SC-01", "definition_version": "sc01-explicit/1"}
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(data)
    data = config().model_dump(mode="json")
    data["treatment"] = {
        "exposure": "hypothetical",
        "category": "chemotherapy",
        "events": [
            {"event_id": "start", "relative_day": "0", "category": "hypothetical_exposure_start"}
        ],
    }
    with pytest.raises(ValueError, match="unreviewed"):
        build_registry().generate(SimulationConfig.model_validate(data), Decimal(100))


def test_registry_rejects_omitted_or_changed_turning_metadata():
    legitimate = build_registry().resolve("SC-04", "sc04-explicit/1")

    class IncompletePlugin:
        family = "SC-04"
        definition_version = "sc04-explicit/1"

        def validate(self, value):
            legitimate.validate(value)

        def generate(self, value, baseline):
            return legitimate.generate(value, baseline).model_copy(update={"turning_point": None})

    registry = PluginRegistry()
    registry.register(IncompletePlugin())
    with pytest.raises(ValueError, match="turning points"):
        registry.generate(config(), Decimal(100))
