"""Explicit synthetic clinical materialization and grounded notes; no source patient records."""

from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError
from test_scenario_families import config as scenario
from test_scenario_sc05 import config as sc05_config
from test_scenario_sc05 import payload as sc05_payload

from canceros.clinical_contracts import LAB_CONCEPTS
from canceros.clinical_generation import ClinicalBatch, ClinicalGenerationError, generate_clinical
from canceros.scenario_families import build_registry
from canceros.simulation_contracts import GeneratedQuantity, SimulationConfig

RUN = UUID(int=22)


def numeric(points=()):
    data = scenario().model_dump(mode="json")
    slots = {}
    observations = []
    for code, value, unit, day in points:
        modality = "laboratory" if code in LAB_CONCEPTS else "vital"
        slot_id = modality + "-" + day
        slots[slot_id] = {"slot_id": slot_id, "modality": modality, "relative_day": day}
        observations.append({"slot_id": slot_id, "code": code, "value": value, "unit": unit})
    data["schedule"]["slots"].extend(
        sorted(slots.values(), key=lambda slot: Decimal(slot["relative_day"]))
    )
    data["clinical_profile"]["points"] = observations
    return SimulationConfig.model_validate(data)


def materialize(request, run=RUN):
    output = build_registry().generate(request, Decimal(100))
    return generate_clinical(request, output, run)


def test_exact_original_canonical_values_and_grounded_notes_without_source_changes():
    request = numeric([("hemoglobin", "120", "g/L", "3"), ("temperature", "-1", "Cel", "8")])
    before = request.model_dump_json()
    batch = materialize(request)
    assert batch.origin == "SYNTHETIC_GENERATED" and batch.branch_id == request.branch_id
    values = {event.value.code: event.value for event in batch.events}
    hemoglobin = values["hemoglobin"]
    assert (hemoglobin.value, hemoglobin.unit) == ("120", "g/L")
    assert (hemoglobin.canonical_value, hemoglobin.canonical_unit) == ("12", "g/dL")
    assert hemoglobin.definition_version == "canceros-local/1"
    for event, note in zip(batch.events, batch.notes, strict=True):
        assert note.evidence_event_ids == [event.event_id]
        assert note.relative_day == event.relative_day
        assert f"{event.value.value} {event.value.unit}" in note.text
        assert f"{event.value.canonical_value} {event.value.canonical_unit}" in note.text
        assert "Simulated research observation" in note.text
        assert "no physician encounter or actual clinical test" in note.text
    assert batch.baseline_clinical_values == "not_inferred_or_modified"
    assert request.model_dump_json() == before


def test_replay_ids_and_modality_isolation_are_stable():
    first = numeric([("hemoglobin", "12", "g/dL", "3")])
    expanded = numeric([("hemoglobin", "12", "g/dL", "3"), ("weight", "65", "kg", "4")])
    a, b = materialize(first), materialize(expanded)
    assert materialize(first) == a
    existing = next(event for event in b.events if event.value.code == "hemoglobin")
    assert existing == a.events[0]
    assert materialize(first, UUID(int=23)).events[0].event_id != a.events[0].event_id
    alternate = first.model_dump(mode="json")
    alternate["branch_id"] = str(UUID(int=55))
    assert (
        materialize(SimulationConfig.model_validate(alternate)).events[0].event_id
        != a.events[0].event_id
    )


@pytest.mark.parametrize(
    "anc,wbc,day,accepted",
    [("3", "4", "3", True), ("4", "4", "3", True), ("5", "4", "3", False), ("5", "4", "4", True)],
)
def test_anc_wbc_constraint_only_at_compatible_concurrent_times(anc, wbc, day, accepted):
    request = numeric([("anc", anc, "10[9]/L", day), ("wbc", wbc, "10[9]/L", "3")])
    if accepted:
        assert len(materialize(request).events) == 2
    else:
        with pytest.raises(ClinicalGenerationError, match="ANC"):
            materialize(request)


@pytest.mark.parametrize(
    "systolic,diastolic,accepted", [("120", "80", True), ("80", "80", False), ("70", "80", False)]
)
def test_concurrent_bp_components(systolic, diastolic, accepted):
    request = numeric(
        [("systolic_bp", systolic, "mmHg", "2"), ("diastolic_bp", diastolic, "mmHg", "2")]
    )
    if accepted:
        materialize(request)
    else:
        with pytest.raises(ClinicalGenerationError, match="systolic"):
            materialize(request)


def test_single_bp_component_is_not_filled_and_missing_baseline_is_not_repaired():
    request = numeric([("systolic_bp", "120", "mmHg", "2")])
    batch = materialize(request)
    assert len(batch.events) == 1
    assert request.baseline_state_id is None
    assert all(event.value.code != "diastolic_bp" for event in batch.events)


def test_nonpositive_weight_and_unrepresentable_canonical_precision_fail_without_rounding():
    with pytest.raises(ClinicalGenerationError, match="weight"):
        materialize(numeric([("weight", "0", "kg", "2")]))
    with pytest.raises(ValidationError):
        materialize(numeric([("hemoglobin", "12.345678901", "g/L", "2")]))
    with pytest.raises(ValidationError):
        GeneratedQuantity(
            kind="quantity",
            code="hemoglobin",
            value="120",
            unit="g/L",
            canonical_value="13",
            canonical_unit="g/dL",
        )


def test_symptom_scale_negation_and_configured_resolution_preserved():
    data = sc05_payload(symptom=True, recovery=True)
    data["sc05_parameters"]["symptom_course"][-1].update({"rating": 0, "presence": "absent"})
    batch = materialize(SimulationConfig.model_validate(data))
    symptoms = [event.value for event in batch.events if event.value.kind == "symptom"]
    assert [value.rating for value in symptoms] == [1, 5, 0]
    assert all(value.scale == "engineering_ordinal/1" for value in symptoms)
    assert all(value.configured_scale == "simulation_0_10" for value in symptoms)
    assert (
        symptoms[-1].negation == "negated"
        and symptoms[-1].resolution_status == "configured_resolution"
    )
    assert symptoms[-1].report_type == "hypothetical_self_report"


def test_unsampled_adverse_control_does_not_become_fake_visit_or_source_event():
    request = sc05_config(symptom=True)
    batch = materialize(request)
    assert len(batch.adverse_events) == 1
    assert batch.adverse_events[0].onset_day == "0"
    assert not any(event.modality == "adverse_event" for event in batch.events)
    assert not any(event.relative_day == "0" for event in batch.events)
    data = request.model_dump(mode="json")
    data["schedule"]["slots"].append(
        {"slot_id": "adverse-onset", "modality": "adverse_event", "relative_day": "0"}
    )
    scheduled = materialize(SimulationConfig.model_validate(data))
    event = next(event for event in scheduled.events if event.modality == "adverse_event")
    assert event.relative_day == "0" and event.value.grading == "ungraded"
    assert event.value.attribution == "hypothetical_association_not_causal"


def treatment(starts=("0",), stops=("10",), schedule=True):
    data = numeric().model_dump(mode="json")
    events = [
        {
            "event_id": "start-" + str(i),
            "relative_day": day,
            "category": "hypothetical_exposure_start",
        }
        for i, day in enumerate(starts)
    ]
    events.extend(
        {
            "event_id": "stop-" + str(i),
            "relative_day": day,
            "category": "hypothetical_exposure_stop",
        }
        for i, day in enumerate(stops)
    )
    events.sort(key=lambda event: Decimal(event["relative_day"]))
    data["treatment"] = {"exposure": "hypothetical", "events": events}
    if schedule:
        data["schedule"]["slots"].extend(
            [
                {"slot_id": "treatment-" + day, "modality": "treatment", "relative_day": day}
                for day in sorted(set([*starts, *stops]), key=Decimal)
            ]
        )
    return SimulationConfig.model_validate(data)


def test_explicit_treatment_zero_start_stop_interruption_and_restart():
    batch = materialize(treatment(starts=("0", "20"), stops=("10", "30")))
    assert len(batch.events) == 4
    assert [event.relative_day for event in batch.events] == ["0", "10", "20", "30"]
    assert all(event.value.assumption == "hypothetical_not_prescription" for event in batch.events)


@pytest.mark.parametrize(
    "configuration",
    [
        treatment(starts=("0", "5"), stops=("10",)),
        treatment(starts=(), stops=("10",)),
        treatment(starts=("0",), stops=("0",)),
        treatment(schedule=False),
    ],
)
def test_invalid_or_unscheduled_exposure_windows_rejected(configuration):
    with pytest.raises(ClinicalGenerationError):
        materialize(configuration)


@pytest.mark.parametrize("profile", ["noise", "missingness"])
def test_explicit_sampling_profiles_materialize_as_configured(profile):
    data = numeric([("hemoglobin", "12", "g/dL", "3")]).model_dump(mode="json")
    point = {"slot_id": "laboratory-3", "channel": "hemoglobin"}
    point.update({"additive_offset": "1"} if profile == "noise" else {"reason": "not_collected"})
    data[profile] = {"mode": "explicit", "points": [point]}
    event = materialize(SimulationConfig.model_validate(data)).events[0]
    if profile == "noise":
        assert event.value.kind == "quantity" and event.value.value == "13"
    else:
        assert event.value.kind == "missing" and event.value.reason == "not_collected"
        assert event.value.channel == "hemoglobin"


def test_unconfigured_lab_slot_stays_unmaterialized_and_zero_day_lab_rejected():
    data = numeric().model_dump(mode="json")
    data["schedule"]["slots"].append(
        {"slot_id": "planned-lab", "modality": "laboratory", "relative_day": "3"}
    )
    batch = materialize(SimulationConfig.model_validate(data))
    assert batch.events == [] and batch.unmaterialized_slot_ids == ["planned-lab"]
    data["schedule"]["slots"][-1]["relative_day"] = "0"
    with pytest.raises(ValidationError):
        SimulationConfig.model_validate(data)


def test_batch_graph_rejects_cross_branch_members_or_ungrounded_notes():
    batch = materialize(numeric([("hemoglobin", "12", "g/dL", "3")]))
    data = batch.model_dump(mode="json")
    data["events"][0]["branch_id"] = str(UUID(int=88))
    with pytest.raises(ValidationError):
        ClinicalBatch.model_validate(data)
    data = batch.model_dump(mode="json")
    data["notes"][0]["evidence_event_ids"] = [str(UUID(int=99))]
    with pytest.raises(ValidationError):
        ClinicalBatch.model_validate(data)
