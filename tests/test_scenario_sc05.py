"""SC-05 explicit simulated clinical changes, without dose, causality or formal grading."""

from decimal import Decimal

import pytest
from pydantic import ValidationError
from test_scenario_families import config as shrinking
from test_scenario_sc02 import stable
from test_scenario_sc03 import config as growing

from canceros.contracts import Provenance
from canceros.scenario_families import build_registry, check_family_realized, sc05_base_config
from canceros.simulation_contracts import SimulationConfig
from canceros.simulation_eligibility import (
    ExposureConfig,
    PathologyFact,
    PureBaselineFacts,
    evaluate,
)
from canceros.simulation_plugins import SimulationAdverseEvent, seed_stream


def payload(family="SC-01", symptom=False, recovery=False):
    base = {"SC-01": shrinking, "SC-02": stable, "SC-03": growing}[family]()
    data = base.model_dump(mode="json")
    data["scenario"] = {"family": "SC-05", "definition_version": "sc05-explicit/1"}
    modality = "symptom" if symptom else "laboratory"
    data["schedule"]["slots"].extend(
        [
            {"slot_id": f"clinical-{i}", "modality": modality, "relative_day": day}
            for i, day in enumerate(("5", "15", "35"))
        ]
    )
    data["clinical_profile"] = {"configuration": "mild_deterioration", "points": []}
    parameters = {
        "profile_version": "clinical-condition/1",
        "tumor_family": family,
        "affected_concepts": [{"concept": "fatigue"}]
        if symptom
        else [{"concept": "hemoglobin", "numeric_direction": "decreasing"}],
        "onset_day": "0",
        "recovery_day": "30" if recovery else None,
        "internal_severity": "mild",
        "symptom_course": [],
    }
    if symptom:
        values = (1, 5, 2) if recovery else (1, 3, 5)
        parameters["symptom_course"] = [
            {
                "slot_id": f"clinical-{i}",
                "concept": "fatigue",
                "rating": value,
                "presence": "present",
            }
            for i, value in enumerate(values)
        ]
    else:
        values = ("12", "10", "11") if recovery else ("12", "11", "10")
        data["clinical_profile"]["points"] = [
            {"slot_id": f"clinical-{i}", "code": "hemoglobin", "unit": "g/dL", "value": value}
            for i, value in enumerate(values)
        ]
    data["sc05_parameters"] = parameters
    return data


def config(**kwargs):
    return SimulationConfig.model_validate(payload(**kwargs))


@pytest.mark.parametrize("family,symptom", [("SC-01", False), ("SC-02", True), ("SC-03", False)])
def test_clinical_deterioration_composes_independent_selected_tumor_family(family, symptom):
    request = config(family=family, symptom=symptom)
    before = request.model_dump_json()
    registry = build_registry()
    output = registry.generate(request, Decimal(100))
    underlying = registry.generate(sc05_base_config(request), Decimal(100))
    assert output.tumor_targets == underlying.tumor_targets
    assert output.family == "SC-05"
    assert output.clinical_profile == request.clinical_profile
    condition = output.clinical_condition
    assert condition is not None and condition.parameters.tumor_family == family
    assert condition.severity_meaning == "internal_simulation_setting_not_ctcae"
    assert condition.origin == "SYNTHETIC_GENERATED"
    assert request.baseline_state_id is None  # No clinical source baseline was invented.
    assert request.model_dump_json() == before
    actual = [Decimal(point.target_mm3) for point in output.tumor_targets]
    assert check_family_realized(request, output.tumor_targets, actual, Decimal(100)).ordering_valid


def test_events_are_ungraded_explicit_controls_with_actual_evidence_slots():
    request = config(symptom=True, recovery=True)
    condition = build_registry().generate(request, Decimal(100)).clinical_condition
    event = condition.events[0]
    assert event.grading == "ungraded"
    assert event.attribution == "hypothetical_association_not_causal"
    assert event.onset_day == "0" and event.resolution_day == "30"
    assert event.evidence_slot_ids == ["clinical-0", "clinical-1", "clinical-2"]
    assert "30" not in [slot.relative_day for slot in request.schedule.slots]
    assert condition.exposure_context.exposure == "none"
    for change in ({"grading": "grade_3"}, {"ctcae_grade": 3}, {"attribution": "drug_caused"}):
        with pytest.raises(ValidationError):
            SimulationAdverseEvent.model_validate({**event.model_dump(), **change})


@pytest.mark.parametrize("symptom", [False, True])
def test_recovery_requires_supporting_explicit_course(symptom):
    request = config(symptom=symptom, recovery=True)
    build_registry().generate(request, Decimal(100))
    data = payload(symptom=symptom)
    data["sc05_parameters"]["recovery_day"] = "30"
    with pytest.raises(ValueError, match="recovery"):
        build_registry().generate(SimulationConfig.model_validate(data), Decimal(100))


@pytest.mark.parametrize(
    "change",
    [
        {"onset_day": "-1"},
        {"onset_day": "NaN"},
        {"recovery_day": "0"},
        {"recovery_day": "100000000"},
        {"internal_severity": "CTCAE_grade_3"},
        {"affected_concepts": [{"concept": "invented_marker", "numeric_direction": "decreasing"}]},
        {"affected_concepts": [{"concept": "hemoglobin"}]},
        {"affected_concepts": [{"concept": "fatigue", "numeric_direction": "increasing"}]},
        {"profile_version": "clinically-approved"},
        {"ctcae_grade": 1},
    ],
)
def test_invalid_or_official_grading_assumptions_rejected(change):
    data = payload()
    data["sc05_parameters"].update(change)
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(data)


@pytest.mark.parametrize(
    "problem",
    ["no_points", "one_point", "wrong_direction", "late_onset", "mixed_units", "wrong_label"],
)
def test_missing_or_incoherent_numeric_clinical_course_rejected(problem):
    data = payload()
    if problem == "no_points":
        data["clinical_profile"]["points"] = []
    elif problem == "one_point":
        data["clinical_profile"]["points"] = data["clinical_profile"]["points"][:1]
    elif problem == "wrong_direction":
        data["sc05_parameters"]["affected_concepts"][0]["numeric_direction"] = "increasing"
    elif problem == "late_onset":
        data["sc05_parameters"]["onset_day"] = "50"
    elif problem == "mixed_units":
        data["clinical_profile"]["points"][0]["unit"] = "g/L"
    else:
        data["clinical_profile"]["configuration"] = "stable"
    with pytest.raises(ValueError):
        build_registry().generate(SimulationConfig.model_validate(data), Decimal(100))


@pytest.mark.parametrize(
    "change",
    [
        {"rating": True},
        {"rating": 11},
        {"rating": -1},
        {"rating": 0},
        {"presence": "absent"},
        {"scale": "CTCAE"},
    ],
)
def test_internal_symptom_scale_and_presence_are_explicit(change):
    data = payload(symptom=True)
    data["sc05_parameters"]["symptom_course"][0].update(change)
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(data)


def test_paired_seed_changes_clinical_course_without_changing_tumor_targets_or_stream_identity():
    first = config()
    data = payload()
    data["clinical_profile"]["points"][1]["value"] = "10"
    data["clinical_profile"]["points"][2]["value"] = "9"
    second = SimulationConfig.model_validate(data)
    registry = build_registry()
    a, b = registry.generate(first, Decimal(100)), registry.generate(second, Decimal(100))
    assert a.tumor_targets == b.tumor_targets
    assert a.clinical_profile != b.clinical_profile
    assert registry.generate(first, Decimal(100)) == a
    assert seed_stream(
        first.seed, "SC-05", "sc05-explicit/1", "scan-0", "imaging", "volume"
    ) == seed_stream(second.seed, "SC-05", "sc05-explicit/1", "scan-0", "imaging", "volume")


def test_clinical_profile_cannot_supply_observed_receptor_eligibility():
    request = config()
    output = build_registry().generate(request, Decimal(100))
    assert output.origin == Provenance.SYNTHETIC_GENERATED
    facts = PureBaselineFacts(
        baseline_hash=request.baseline_hash,
        observed_baseline_verified=True,
        published_baseline_verified=True,
        source_rights_allowed=True,
        patient_ownership_verified=True,
        revision_current=True,
        metric_valid=True,
        annotation_numeric_eligible=True,
        anatomy_eligible=True,
        pathology=[
            PathologyFact(
                source_id=request.branch_id, field="er", status="positive", origin=output.origin
            )
        ],
    )
    exposure = ExposureConfig(
        exposure="hypothetical",
        category="endocrine",
        events=[
            {"event_id": "start", "relative_day": "0", "category": "hypothetical_exposure_start"}
        ],
    )
    result = evaluate(facts, exposure)
    assert result.status == "insufficient_data"
    assert "er" in result.missing_fields


def test_specific_exposure_remains_unreviewed_and_no_dosage_input_allowed():
    data = payload()
    data["treatment"] = {
        "exposure": "hypothetical",
        "category": "chemotherapy",
        "events": [
            {"event_id": "start", "relative_day": "0", "category": "hypothetical_exposure_start"}
        ],
    }
    with pytest.raises(ValueError, match="unreviewed"):
        build_registry().generate(SimulationConfig.model_validate(data), Decimal(100))
    data["treatment"]["dose"] = "invented"
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(data)


def test_symptom_sampling_profile_remains_separate_when_reusing_tumor_plugin():
    data = payload(symptom=True)
    data["noise"] = {
        "mode": "explicit",
        "points": [{"slot_id": "clinical-0", "channel": "fatigue", "additive_offset": "1"}],
    }
    request = SimulationConfig.model_validate(data)
    output = build_registry().generate(request, Decimal(100))
    assert output.clinical_condition.parameters.symptom_course[0].rating == 1
    assert request.noise.points[0].channel == "fatigue"


def test_missing_dictionary_definition_and_unsupported_recovery_label_fail_closed(monkeypatch):
    from canceros.clinical_contracts import CLINICAL_UNITS

    with monkeypatch.context() as patch:
        patch.delitem(CLINICAL_UNITS, "hemoglobin")
        with pytest.raises(ValidationError):
            config()
    data = payload()
    data["clinical_profile"]["configuration"] = "recovery"
    with pytest.raises(ValueError, match="label conflicts"):
        build_registry().generate(SimulationConfig.model_validate(data), Decimal(100))


def test_unconfigured_return_to_initial_value_does_not_count_as_sustained_deterioration():
    data = payload()
    data["clinical_profile"]["points"][-1]["value"] = "12"
    with pytest.raises(ValueError, match="retain its configured deterioration direction"):
        build_registry().generate(SimulationConfig.model_validate(data), Decimal(100))
