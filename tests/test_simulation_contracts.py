"""Contract/replay checks on explicit fixture targets, without clinical parameter fitting."""

from copy import deepcopy
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from canceros.simulation_contracts import GeneratedEvent, SimulationConfig
from canceros.simulation_plugins import PluginOutput, PluginRegistry, TumorTarget, seed_stream


def configuration():
    return {
        "baseline_state_id": None,
        "baseline_hash": "a" * 64,
        "branch_id": str(UUID(int=1)),
        "input_revision": 1,
        "scenario": {
            "family": "SC-01",
            "definition_version": "fixture-explicit/1".replace("/", "-"),
        },
        "treatment": {"exposure": "none"},
        "schedule": {
            "slots": [
                {"slot_id": f"scan-{i}", "modality": "imaging", "relative_day": str(i * 10)}
                for i in range(1, 4)
            ]
            + [{"slot_id": "lab-1", "modality": "laboratory", "relative_day": "10"}]
        },
        "tumor_profile": {
            "points": [{"slot_id": f"scan-{i}", "target_mm3": str(100 - i)} for i in range(1, 4)]
        },
        "clinical_profile": {
            "configuration": "moderate_deterioration",
            "points": [{"slot_id": "lab-1", "code": "hemoglobin", "unit": "g/dL", "value": "12"}],
        },
        "noise": {"mode": "none"},
        "missingness": {"mode": "none"},
        "geometry_policy": "none",
        "seed": 42,
    }


def test_round_trip_preserves_independent_explicit_configuration():
    value = SimulationConfig.model_validate(configuration())
    assert SimulationConfig.model_validate_json(value.model_dump_json()) == value
    assert value.clinical_profile.configuration == "moderate_deterioration"
    assert value.tumor_profile.points[0].target_mm3 == "99"
    assert value.scientific_policy == "unreviewed_demo"


@pytest.mark.parametrize(
    "field,value",
    [
        ("seed", True),
        ("seed", -1),
        ("seed", 2**32),
        ("input_revision", True),
        ("input_revision", 0),
        ("scientific_policy", "clinically_approved"),
        ("simulator_version", "slre/2"),
        ("geometry_policy", "invented"),
        ("unknown", 1),
    ],
)
def test_invalid_scalar_contract(field, value):
    data = configuration()
    data[field] = value
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(data)


@pytest.mark.parametrize(
    "problem",
    [
        "missing_scan",
        "negative_day",
        "duplicate_slot",
        "unsorted",
        "negative_target",
        "bad_target_ref",
        "bad_unit",
        "wrong_modality",
        "duplicate_clinical",
        "implicit_noise",
        "missing_unknown_channel",
        "duplicate_missing",
        "exposure_without_events",
        "extra_profile",
    ],
)
def test_cross_reference_and_assumption_errors(problem):
    data = deepcopy(configuration())
    slots = data["schedule"]["slots"]
    if problem == "missing_scan":
        slots.pop(0)
    elif problem == "negative_day":
        slots[0]["relative_day"] = "-1"
    elif problem == "duplicate_slot":
        slots[1]["slot_id"] = slots[0]["slot_id"]
    elif problem == "unsorted":
        slots[1]["relative_day"] = "1"
    elif problem == "negative_target":
        data["tumor_profile"]["points"][0]["target_mm3"] = "-1"
    elif problem == "bad_target_ref":
        data["tumor_profile"]["points"][0]["slot_id"] = "elsewhere"
    elif problem == "bad_unit":
        data["clinical_profile"]["points"][0]["unit"] = "mm3"
    elif problem == "wrong_modality":
        data["clinical_profile"]["points"][0]["slot_id"] = "scan-1"
    elif problem == "duplicate_clinical":
        data["clinical_profile"]["points"] *= 2
    elif problem == "implicit_noise":
        data["noise"] = {"mode": "explicit"}
    elif problem == "missing_unknown_channel":
        data["missingness"] = {
            "mode": "explicit",
            "points": [{"slot_id": "scan-1", "channel": "unsupported", "reason": "not_collected"}],
        }
    elif problem == "duplicate_missing":
        data["missingness"] = {
            "mode": "explicit",
            "points": [
                {
                    "slot_id": "scan-1",
                    "channel": "numerical_region_volume",
                    "reason": "not_collected",
                }
            ]
            * 2,
        }
    elif problem == "exposure_without_events":
        data["treatment"] = {"exposure": "hypothetical"}
    elif problem == "extra_profile":
        data["tumor_profile"]["distribution"] = "normal"
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(data)


class FixturePlugin:
    family = "SC-01"
    definition_version = "fixture-explicit-1"

    def validate(self, config):
        assert config.scenario.family == self.family

    def generate(self, config, baseline_quantity):
        slots = {slot.slot_id: slot for slot in config.schedule.slots}
        return PluginOutput(
            tumor_targets=[
                TumorTarget(
                    slot_id=point.slot_id,
                    relative_day=slots[point.slot_id].relative_day,
                    target_mm3=point.target_mm3,
                )
                for point in config.tumor_profile.points
            ],
            clinical_profile=config.clinical_profile,
        )


def test_explicit_plugin_replay_and_registry_fail_closed():
    config = SimulationConfig.model_validate(configuration())
    registry = PluginRegistry()
    with pytest.raises(ValueError, match="not registered"):
        registry.generate(config, Decimal(100))
    registry.register(FixturePlugin())
    first = registry.generate(config, Decimal(100))
    assert first == registry.generate(config, Decimal(100))
    assert first.clinical_profile == config.clinical_profile
    assert first.origin == "SYNTHETIC_GENERATED"
    with pytest.raises(ValueError, match="Duplicate"):
        registry.register(FixturePlugin())
    with pytest.raises(ValueError, match="finite positive"):
        registry.generate(config, Decimal("NaN"))


def test_seed_stream_is_stable_independent_and_unambiguous():
    args = (42, "SC-01", "fixture-explicit-1", "scan-1", "imaging", "volume")
    first = seed_stream(*args)
    assert first == seed_stream(*args)
    assert first != seed_stream(42, "SC-01", "fixture-explicit-1", "scan-2", "imaging", "volume")
    assert seed_stream(1, "ab", "c", "d", "e", "f") != seed_stream(1, "a", "bc", "d", "e", "f")
    with pytest.raises(ValueError):
        seed_stream(True, *args[1:])


def test_plugin_cannot_couple_independent_clinical_configuration():
    class BadPlugin(FixturePlugin):
        def generate(self, config, baseline_quantity):
            output = super().generate(config, baseline_quantity)
            return output.model_copy(
                update={
                    "clinical_profile": config.clinical_profile.model_copy(
                        update={"configuration": "stable"}
                    )
                }
            )

    registry = PluginRegistry()
    registry.register(BadPlugin())
    with pytest.raises(ValueError, match="independent clinical"):
        registry.generate(SimulationConfig.model_validate(configuration()), Decimal(100))


def test_generated_event_units_origin_and_modality():
    payload = {
        "event_id": UUID(int=1),
        "branch_id": UUID(int=2),
        "run_id": UUID(int=3),
        "slot_id": "scan-1",
        "relative_day": "10",
        "modality": "imaging",
        "value": {
            "kind": "quantity",
            "code": "numerical_region_volume",
            "value": "10",
            "unit": "mm3",
        },
    }
    assert GeneratedEvent.model_validate(payload).origin == "SYNTHETIC_GENERATED"
    for change in ({"origin": "REAL_OBSERVED"}, {"modality": "laboratory"}, {"relative_day": "0"}):
        with pytest.raises(ValidationError):
            GeneratedEvent.model_validate({**payload, **change})
    with pytest.raises(ValidationError):
        GeneratedEvent.model_validate({**payload, "value": {**payload["value"], "unit": "cm3"}})


@pytest.mark.parametrize("callback", ["validate", "generate"])
def test_plugin_nested_mutation_is_rejected_without_changing_caller(callback):
    class MutatingPlugin(FixturePlugin):
        def validate(self, config):
            if callback == "validate":
                config.clinical_profile.points.clear()

        def generate(self, config, baseline_quantity):
            if callback == "generate":
                config.clinical_profile.points.clear()
            return super().generate(config, baseline_quantity)

    config = SimulationConfig.model_validate(configuration())
    original = config.model_dump_json()
    registry = PluginRegistry()
    registry.register(MutatingPlugin())
    with pytest.raises(ValueError, match="mutated pinned"):
        registry.generate(config, Decimal(100))
    assert config.model_dump_json() == original


@pytest.mark.parametrize("volume", ["1000000000000000", "1000000000000001"])
def test_tumor_targets_match_geometry_engine_bound(volume):
    payload = configuration()
    payload["tumor_profile"]["points"][0]["target_mm3"] = volume
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(payload)
