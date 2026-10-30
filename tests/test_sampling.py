"""Named-stream engineering sampling, with no claim of empirical care-pattern validity."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, localcontext

import pytest
from pydantic import ValidationError
from test_clinical_generation import materialize, numeric, treatment
from test_scenario_sc04 import config as sc04_config
from test_scenario_sc05 import config as sc05_config

from canceros.clinical_generation import ClinicalGenerationError
from canceros.sampling import SampledTumorTarget, SamplingError, sample_observations
from canceros.scenario_families import build_registry
from canceros.simulation_contracts import SimulationConfig


def sampled_config(request=None, **policy):
    data = (request or numeric([("hemoglobin", "12", "g/dL", "3")])).model_dump(mode="json")
    data["sampling"] = policy
    return SimulationConfig.model_validate(data)


def preview(config):
    return sample_observations(config, build_registry().generate(config, Decimal(100)))


def noise(slot="laboratory-3", channel="hemoglobin", low="-1", high="1"):
    return {"slot_id": slot, "channel": channel, "min_offset": low, "max_offset": high}


def jitter(slot="laboratory-3", low="-0.5", high="0.5"):
    return {"slot_id": slot, "min_offset_days": low, "max_offset_days": high}


def omission(slot="laboratory-3", channel="hemoglobin", probability="0.5"):
    return {
        "slot_id": slot,
        "channel": channel,
        "probability": probability,
        "reason": "not_collected",
    }


def test_sequential_parallel_retry_replay_and_original_configuration_unchanged():
    config = sampled_config(
        jitter_rules=[jitter()],
        noise_rules=[noise()],
        missingness_rules=[omission(probability="0.25")],
    )
    before = config.model_dump_json()
    sequential = [preview(config).model_dump_json() for _ in range(8)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        concurrent = list(pool.map(lambda _: preview(config).model_dump_json(), range(8)))
    assert concurrent == sequential
    assert len(set(sequential)) == 1
    assert config.model_dump_json() == before


def test_unrelated_analyte_does_not_change_existing_streams():
    a = sampled_config(
        jitter_rules=[jitter()], noise_rules=[noise()], missingness_rules=[omission()]
    )
    b = sampled_config(
        numeric([("hemoglobin", "12", "g/dL", "3"), ("weight", "65", "kg", "4")]),
        jitter_rules=[jitter()],
        noise_rules=[noise(), noise("vital-4", "weight")],
        missingness_rules=[omission()],
    )
    first, expanded = preview(a), preview(b)
    assert first.clinical_values[0] == expanded.clinical_values[0]
    assert first.tumor_targets == expanded.tumor_targets
    assert first.slots[3] == expanded.slots[3]


def test_declared_constant_jitter_and_noise_have_exact_observed_values_and_grounded_notes():
    config = sampled_config(
        jitter_rules=[jitter(low="0.125", high="0.125")],
        noise_rules=[noise(low="1.25", high="1.25")],
    )
    report = preview(config)
    value = report.clinical_values[0]
    assert value.relative_day == "3.125" and value.value == "13.25"
    assert report.slots[-1].configured_day == "3"
    batch = materialize(config)
    assert batch.sampling == report
    assert batch.events[0].relative_day == "3.125"
    assert batch.events[0].value.canonical_value == "13.25"
    assert "13.25 g/dL" in batch.notes[0].text
    assert "12 g/dL" not in batch.notes[0].text


@pytest.mark.parametrize("probability,missing", [("0", False), ("1", True)])
def test_explicit_missingness_extremes_preserve_reason_and_hide_value(probability, missing):
    config = sampled_config(missingness_rules=[omission(probability=probability)])
    report = preview(config)
    event = materialize(config).events[0]
    assert (report.clinical_values[0].value is None) == missing
    if missing:
        assert report.clinical_values[0].missing_reason == "not_collected"
        assert event.value.kind == "missing" and event.value.channel == "hemoglobin"
        assert "12" not in materialize(config).notes[0].text
    else:
        assert event.value.kind == "quantity" and event.value.value == "12"


def test_required_tumor_missingness_is_explicit_not_zero_or_deleted_slot():
    config = sampled_config(missingness_rules=[omission("scan-1", "numerical_region_volume", "1")])
    report = preview(config)
    assert len(report.tumor_targets) == 3
    assert report.tumor_targets[1].target_mm3 is None
    assert report.tumor_targets[1].missing_reason == "not_collected"
    assert len(report.slots) == len(config.schedule.slots)


@pytest.mark.parametrize(
    "slot,offset,message",
    [
        ("scan-0", "28", "collision"),
        ("scan-0", "29", "reordering"),
        ("scan-0", "-7", "nonpositive"),
    ],
)
def test_post_jitter_collision_ordering_and_nonpositive_times_rejected(slot, offset, message):
    config = sampled_config(jitter_rules=[jitter(slot, offset, offset)])
    with pytest.raises(SamplingError, match=message):
        preview(config)


def test_cross_modality_same_times_are_preserved_and_controls_cannot_jitter():
    request = numeric([("hemoglobin", "12", "g/dL", "3"), ("weight", "65", "kg", "3")])
    assert preview(sampled_config(request)).clinical_values[0].relative_day == "3"
    config = sampled_config(treatment(), jitter_rules=[jitter("treatment-0", "1", "1")])
    with pytest.raises(SamplingError, match="control jitter"):
        preview(config)


def test_jitter_interval_requires_representable_four_decimal_offset_and_precision_not_rounded():
    with pytest.raises(SamplingError, match="lattice"):
        preview(sampled_config(jitter_rules=[jitter(low="0.00001", high="0.00002")]))
    request = numeric([("hemoglobin", "12", "g/dL", "3.00001")])
    with pytest.raises(SamplingError, match="precision"):
        preview(sampled_config(request))


@pytest.mark.parametrize(
    "change",
    [
        {"noise_rules": [noise(low="1", high="-1")]},
        {"missingness_rules": [omission(probability="1.000000001")]},
        {"noise_rules": [noise(), noise()]},
        {"jitter_rules": [jitter("nonexistent")]},
        {"missingness_rules": [omission(channel="unsupported")]},
    ],
)
def test_invalid_sampling_rules_fail_validation(change):
    with pytest.raises(ValidationError):
        sampled_config(**change)


def test_ambiguous_fixed_and_random_same_purpose_profiles_are_rejected():
    data = sampled_config(noise_rules=[noise()]).model_dump(mode="json")
    data["noise"] = {
        "mode": "explicit",
        "points": [{"slot_id": "laboratory-3", "channel": "hemoglobin", "additive_offset": "1"}],
    }
    with pytest.raises(ValidationError, match="fixed and random"):
        SimulationConfig.model_validate(data)


def test_post_noise_structural_and_concurrent_constraints_fail_closed():
    with pytest.raises(SamplingError, match="negative"):
        preview(sampled_config(noise_rules=[noise(low="-13", high="-13")]))
    request = numeric([("anc", "3", "10[9]/L", "3"), ("wbc", "4", "10[9]/L", "3")])
    with pytest.raises(ClinicalGenerationError, match="ANC"):
        materialize(sampled_config(request, noise_rules=[noise("laboratory-3", "anc", "2", "2")]))


def test_sc04_configured_control_is_not_jittered_or_promoted_to_observation():
    config = sampled_config(sc04_config(), jitter_rules=[jitter("scan-0", "1", "1")])
    output = build_registry().generate(config, Decimal(100))
    report = sample_observations(config, output)
    assert output.turning_point.configured_day == "20"
    assert [point.relative_day for point in report.tumor_targets] == ["11", "30", "40"]
    assert len(report.tumor_targets) == 3


def test_symptom_sampling_remains_integer_and_missing_does_not_imply_absence():
    request = sc05_config(symptom=True)
    valid = sampled_config(request, noise_rules=[noise("clinical-0", "fatigue", "1", "1")])
    assert materialize(valid).events[0].value.rating == 2
    invalid = sampled_config(request, noise_rules=[noise("clinical-0", "fatigue", "0.1", "0.1")])
    with pytest.raises(SamplingError, match="integer"):
        preview(invalid)
    missing = sampled_config(request, missingness_rules=[omission("clinical-0", "fatigue", "1")])
    assert materialize(missing).events[0].value.kind == "missing"


def test_decimal_context_and_non_sampling_ids_do_not_change_scientific_values():
    config = sampled_config(noise_rules=[noise()])
    output = build_registry().generate(config, Decimal(100))
    expected = sample_observations(config, output)
    with localcontext() as context:
        context.prec = 5
        assert sample_observations(config, output) == expected
    assert expected.seed_derivation == "framed_sha256_named_streams/1"
    assert expected.policy == "explicit_demo_distributions_not_real_care"


def test_sampler_rejects_changed_latent_output_and_incoherent_missing_dto():
    config = sampled_config()
    output = build_registry().generate(config, Decimal(100))
    changed = output.tumor_targets.copy()
    changed[0] = changed[0].model_copy(update={"target_mm3": "89"})
    with pytest.raises(SamplingError, match="frozen"):
        sample_observations(config, output.model_copy(update={"tumor_targets": changed}))
    with pytest.raises(ValidationError):
        SampledTumorTarget(
            slot_id="scan-0", relative_day="7", target_mm3="90", missing_reason="not_collected"
        )
