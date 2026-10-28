from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from canceros.clinical_contracts import (
    ClinicalInput,
    ClinicalRecord,
    ClinicalTime,
    clinical_dictionary,
    validate_anchor_graph,
)


def clinical_item(**changes):
    return {
        "kind": "laboratory",
        "concept": "hemoglobin",
        "client_record_key": "engineering-row-1",
        "source_locator_id": str(uuid4()),
        "time": {
            "reference": {
                "basis": "relative_day",
                "value": "0",
                "time_domain": "source_relative",
                "timeline_origin_id": str(uuid4()),
            },
            "precision": "relative_day",
        },
        "original_term": "Artificial fixture HGB",
        "certainty": "documented",
        "negation": "affirmed",
        "result": {"form": "exact", "quantity": {"value": "12.5", "unit": "g/dL"}},
        "original_value": "12.5",
        "original_unit": "g/dL",
        **changes,
    }


def test_generated_schema_round_trip_relative_zero_no_date():
    item = TypeAdapter(ClinicalInput).validate_python(clinical_item())
    record = ClinicalRecord(
        id=uuid4(),
        project_id=uuid4(),
        patient_id=uuid4(),
        item=item,
        origin="REAL_OBSERVED",
        context="OBSERVED",
        quality="pending",
        availability="available",
    )
    assert ClinicalRecord.model_validate_json(record.model_dump_json()) == record
    assert record.item.time.reference.value == "0"
    assert "date_value" not in record.model_dump_json()


@pytest.mark.parametrize("unit", ["kg", "mg/L", "unknown"])
def test_wrong_units_rejected(unit):
    with pytest.raises(ValidationError):
        TypeAdapter(ClinicalInput).validate_python(
            clinical_item(result={"form": "exact", "quantity": {"value": "1", "unit": unit}})
        )


def test_missing_censored_negative_receptor_and_absent_are_distinct():
    missing = TypeAdapter(ClinicalInput).validate_python(
        clinical_item(
            result={"form": "missing", "missing_reason": "not_collected"},
            original_value=None,
            original_unit=None,
        )
    )
    assert missing.result.form == "missing"
    censored = TypeAdapter(ClinicalInput).validate_python(
        clinical_item(
            result={
                "form": "censored",
                "comparator": "<",
                "threshold": {"value": "1", "unit": "g/dL"},
            },
            original_value="<1",
        )
    )
    assert censored.result.comparator == "<"
    base = clinical_item()
    for name in ("result", "original_value", "original_unit"):
        base.pop(name)
    diagnosis = {
        **base,
        "kind": "diagnosis",
        "concept": "source_pathology",
        "side": "unknown",
        "er_status": "negative",
        "pr_status": "not_recorded",
        "her2_status": "not_tested",
    }
    item = TypeAdapter(ClinicalInput).validate_python(diagnosis)
    assert len({item.er_status, item.pr_status, item.her2_status}) == 3


def test_provenance_self_anchor_and_cyclic_graph_denied():
    item = TypeAdapter(ClinicalInput).validate_python(clinical_item())
    with pytest.raises(ValidationError):
        ClinicalRecord(
            id=uuid4(),
            project_id=uuid4(),
            patient_id=uuid4(),
            item=item,
            origin="SYNTHETIC_GENERATED",
            context="OBSERVED",
            quality="pass",
            availability="available",
        )
    a, b = uuid4(), uuid4()
    first = ClinicalTime.model_validate(
        {
            "reference": {
                "basis": "relative_day",
                "value": "0",
                "time_domain": "source_relative",
                "anchor_state_id": b,
            },
            "precision": "relative_day",
        }
    )
    second = ClinicalTime.model_validate(
        {
            "reference": {
                "basis": "relative_day",
                "value": "1",
                "time_domain": "source_relative",
                "anchor_state_id": a,
            },
            "precision": "relative_day",
        }
    )
    with pytest.raises(ValueError, match="Cyclic"):
        validate_anchor_graph({a: first, b: second})
    with pytest.raises(ValueError, match="Unresolved"):
        validate_anchor_graph({a: first})
    self_item = clinical_item(
        time={
            "reference": {
                "basis": "relative_day",
                "value": "0",
                "time_domain": "source_relative",
                "anchor_state_id": a,
            },
            "precision": "relative_day",
        }
    )
    with pytest.raises(ValidationError):
        ClinicalRecord(
            id=a,
            project_id=uuid4(),
            patient_id=uuid4(),
            item=self_item,
            origin="REAL_OBSERVED",
            context="OBSERVED",
            quality="pass",
            availability="available",
        )


def test_precision_timezone_shift_and_unknown_time_preserved():
    time = ClinicalTime.model_validate(
        {
            "reference": {
                "basis": "timestamp",
                "value": "2026-01-01T12:30:00+01:00",
                "time_domain": "source_calendar",
            },
            "precision": "minute",
        }
    )
    assert time.reference.value.utcoffset().total_seconds() == 3600
    with pytest.raises(ValidationError):
        ClinicalTime.model_validate(
            {
                "reference": {
                    "basis": "date",
                    "value": "2026-01-01",
                    "time_domain": "source_shifted",
                },
                "precision": "day",
            }
        )
    unknown = ClinicalTime.model_validate(
        {
            "reference": {
                "basis": "unknown",
                "missing_reason": "not_recorded",
                "time_domain": "source_relative",
            },
            "precision": "unknown",
        }
    )
    assert not hasattr(unknown.reference, "value")


def test_dictionary_is_versioned_local_and_has_no_invented_reference_ranges():
    dictionary = clinical_dictionary()
    assert dictionary.external_terminology == "none_adopted"
    assert dictionary.units["hemoglobin"] == ["g/dL", "g/L"]
    assert "normal" not in dictionary.model_dump_json()


def test_order_is_not_delivery_and_interval_cannot_reverse():
    item = clinical_item()
    for name in ("result", "original_value", "original_unit"):
        item.pop(name)
    item.update(
        kind="treatment",
        concept="chemotherapy",
        event_type="ordered",
        exposure_status="documented_delivery",
    )
    with pytest.raises(ValidationError):
        TypeAdapter(ClinicalInput).validate_python(item)
    item.update(
        event_type="administered",
        exposure_status="documented_delivery",
        ended_time={
            "reference": {**item["time"]["reference"], "value": "-1"},
            "precision": "relative_day",
        },
    )
    with pytest.raises(ValidationError):
        TypeAdapter(ClinicalInput).validate_python(item)
