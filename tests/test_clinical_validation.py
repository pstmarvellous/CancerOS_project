from uuid import uuid4

import pytest
from pydantic import TypeAdapter
from sqlalchemy import text
from test_clinical_contracts import clinical_item
from test_clinical_ingestion import clinical_db, row, stage
from test_source_registry import registry_db

from canceros.clinical_contracts import ClinicalInput
from canceros.clinical_ingestion import BatchCommand, accept_batch, read_record
from canceros.clinical_validation import semantic_validation

__all__ = ["clinical_db", "registry_db"]


def validated(**changes):
    return TypeAdapter(ClinicalInput).validate_python(clinical_item(**changes))


def test_exact_unit_conversion_preserves_original_and_censoring():
    item = validated(
        original_value="125",
        original_unit="g/L",
        result={"form": "exact", "quantity": {"value": "125", "unit": "g/L"}},
    )
    normalized, issues = semantic_validation(item, "/records/0")
    assert issues == []
    assert normalized.original_value == "125" and normalized.original_unit == "g/L"
    assert (
        normalized.canonical_result.quantity.value == "12.5"
        and normalized.canonical_result.quantity.unit == "g/dL"
    )
    item = validated(
        original_value="<10",
        original_unit="g/L",
        result={"form": "censored", "comparator": "<", "threshold": {"value": "10", "unit": "g/L"}},
    )
    normalized, issues = semantic_validation(item, "/records/0")
    assert not issues and normalized.canonical_result.form == "censored"
    assert normalized.canonical_result.threshold.value == "1"


@pytest.mark.parametrize(
    "changes,rule",
    [
        (
            {
                "original_value": "-1",
                "result": {"form": "exact", "quantity": {"value": "-1", "unit": "g/dL"}},
            },
            "NONNEGATIVE-STRUCTURE-1",
        ),
        ({"original_value": "NaN"}, "ORIGINAL-NUMERIC-SYNTAX-1"),
        ({"original_value": "<12.5"}, "CENSOR-SEMANTICS-1"),
        ({"original_value": "13"}, "SOURCE-NUMERIC-MISMATCH-1"),
    ],
)
def test_structural_or_source_conflicts_do_not_become_normal(changes, rule):
    _, issues = semantic_validation(validated(**changes), "/records/0")
    assert rule in {issue["rule_id"] for issue in issues}
    assert all(issue["severity"] == "error" for issue in issues)


def test_missing_remains_missing_and_unusual_is_not_invalid():
    normalized, issues = semantic_validation(
        validated(
            result={"form": "missing", "missing_reason": "not_collected"},
            original_value=None,
            original_unit=None,
        ),
        "/records/0",
    )
    assert normalized.canonical_result.form == "missing" and not issues
    _, issues = semantic_validation(
        validated(
            original_value="999",
            result={"form": "exact", "quantity": {"value": "999", "unit": "g/dL"}},
        ),
        "/records/0",
    )
    assert issues == []  # No invented universal clinical range.


def test_source_interval_warning_not_rejection(clinical_db):
    connection, identity, project, patient, origin, _, storage = clinical_db
    receipt = stage(
        clinical_db,
        [
            row(
                origin,
                original_value="125",
                original_unit="g/L",
                result={"form": "exact", "quantity": {"value": "125", "unit": "g/L"}},
                reference_interval={
                    "low": "130",
                    "high": "170",
                    "unit": "g/L",
                    "source_description": "Artificial source interval",
                    "population_context": "Engineering fixture only",
                    "version": "fixture/1",
                },
            )
        ],
    )
    result = accept_batch(
        connection,
        identity,
        project,
        patient.patient_id,
        BatchCommand(source_artifact_id=receipt.artifact_id, expected_revision=1),
        "conversion",
        storage,
    )
    assert result.status == "accepted" and result.issues[0].severity == "warning"
    record = read_record(connection, identity, project, patient.patient_id, result.record_ids[0])
    assert (
        record.item.original_value == "125"
        and record.numeric_normalization.canonical_result.quantity.value == "12.5"
    )
    assert record.quality == "warning"
    typed = connection.execute(
        text(
            "SELECT value,unit,original_value,original_unit,conversion_version FROM clinical.numeric_results WHERE observation_id=:id"
        ),
        {"id": record.id},
    ).one()
    assert (
        str(typed.value) == "12.500000000" and typed.unit == "g/dL" and typed.original_unit == "g/L"
    )
    assert typed.conversion_version == "local-units/1"


def test_bad_values_quarantine_and_unknown_symptom_instrument():
    base = clinical_item()
    for key in ("result", "original_value", "original_unit"):
        base.pop(key)
    item = TypeAdapter(ClinicalInput).validate_python(
        {
            **base,
            "kind": "symptom",
            "concept": "pain",
            "presence": "present",
            "reporter": "patient",
            "severity": "2",
            "instrument": "unverified-scale",
            "instrument_version": "unknown",
        }
    )
    _, issues = semantic_validation(item, "/records/0")
    assert issues[0]["rule_id"] == "SYMPTOM-INSTRUMENT-1"
    item = TypeAdapter(ClinicalInput).validate_python(
        {
            **base,
            "kind": "symptom",
            "concept": "pain",
            "presence": "present",
            "reporter": "clinician",
            "severity": "11",
            "instrument": "engineering_ordinal",
            "instrument_version": "1",
        }
    )
    _, issues = semantic_validation(item, "/records/0")
    assert issues[0]["rule_id"] == "SYMPTOM-BOUNDS-1"


def test_bp_components_require_group_and_preserve_missing_partner():
    item = validated(
        kind="vital",
        concept="systolic_bp",
        original_value="120",
        original_unit="mmHg",
        result={"form": "exact", "quantity": {"value": "120", "unit": "mmHg"}},
    )
    _, issues = semantic_validation(item, "/records/0")
    assert issues[0]["rule_id"] == "BP-COMPONENT-GROUP-1"
    from canceros.clinical_validation import component_validation

    grouped = item.model_copy(update={"component_group": uuid4()})
    assert component_validation([(0, grouped)])[0]["severity"] == "warning"
