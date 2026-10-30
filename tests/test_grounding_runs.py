"""Fail-closed grounding gate with frozen 60-case fixture suite."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_context_runs import FIXTURE_PATIENT, SNAPSHOT_ID
from test_context_runs import build as build_context_fixture
from test_imaging_ingestion import http_session, imaging_db
from test_patient_linkage import keys
from test_source_registry import registry_db

from canceros.context_contracts import ContextBuildInput
from canceros.grounding_runs import (
    _prohibited,
    require_published,
    validate_private_candidate,
    validate_publication,
)
from canceros.grounding_suite import SUITE_VERSION, frozen_suite
from canceros.interpretation_runs import render_template

__all__ = ["imaging_db", "registry_db"]

__all__ = ["registry_db"]


def context(monkeypatch):
    return build_context_fixture(
        monkeypatch, ContextBuildInput(patient_id=FIXTURE_PATIENT, snapshot_id=SNAPSHOT_ID)
    )


def mutate(report, context, kind, prohibited_text=None):
    findings = [f.model_copy(deep=True) for f in report.findings]
    index = next(
        (n for n, f in enumerate(findings) if f.kind == "observed_measurement"), 0
    )
    target = findings[index]
    if kind == "numeric_mismatch":
        findings[index] = target.model_copy(update={"metric_value": "9999"})
    elif kind == "unit_mismatch":
        findings[index] = target.model_copy(update={"metric_unit": "wrong_unit"})
    elif kind == "unresolved_reference":
        findings[index] = target.model_copy(update={"measurement_refs": (uuid4(),)})
    elif kind == "context_mismatch":
        return report.model_copy(
            update={"context_hash": "0" * 64, "findings": tuple(findings)}
        )
    elif kind == "unsupported_prose":
        findings[index] = target.model_copy(
            update={
                "kind": "general_background",
                "text": "A novel assertion without any permitted background marker.",
                "measurement_refs": (),
                "passage_refs": (uuid4(),),
            }
        )
    elif kind == "prohibited_claim":
        findings[index] = target.model_copy(
            update={"kind": "general_background", "text": prohibited_text or "Stage II cancer."}
        )
    return report.model_copy(update={"findings": tuple(findings)})


def test_template_passes_gate_with_full_numeric_origin_fidelity(monkeypatch):
    built = context(monkeypatch)
    report = render_template(built)
    grounded = validate_publication(built, report)
    assert grounded.verdict == "published"
    assert grounded.reason_codes == ()
    assert grounded.numeric_statements == grounded.numeric_matched == len(built.measurements)
    assert grounded.prohibited_critical == 0
    assert grounded.unsupported_claims == 0
    require_published(grounded)


def test_numeric_unit_reference_and_context_mismatches_fail_closed(monkeypatch):
    built = context(monkeypatch)
    base = render_template(built)
    for kind, code in (
        ("numeric_mismatch", "NUMERIC_MISMATCH"),
        ("unit_mismatch", "NUMERIC_MISMATCH"),
        ("unresolved_reference", "UNRESOLVED_REFERENCE"),
    ):
        grounded = validate_publication(built, mutate(base, built, kind))
        assert grounded.verdict == "failed_grounding"
        assert code in grounded.reason_codes
        with pytest.raises(HTTPException):
            require_published(grounded)
    stale = mutate(base, built, "context_mismatch")
    grounded = validate_publication(built, stale)
    assert grounded.verdict == "failed_grounding" and "CONTEXT_MISMATCH" in grounded.reason_codes


def test_prohibited_patterns_are_detected_without_silent_remnants(monkeypatch):
    assert "staging_or_grade" in _prohibited("The TNM stage is II.")
    assert "survival_or_prognosis" in _prohibited("Five-year survival is 80%.")
    assert "treatment_advice" in _prohibited("I recommend starting dose today.")
    assert "diagnosis" in _prohibited("Diagnosis: invasive carcinoma.")
    assert "invented_confidence" in _prohibited("I am 95% confident in this claim.")
    assert _prohibited("Retained hemoglobin value 9 g/dL.") == []
    built = context(monkeypatch)
    base = render_template(built)
    grounded = validate_publication(
        built, mutate(base, built, "prohibited_claim", "RECIST complete response; prescribe now.")
    )
    assert grounded.verdict == "failed_grounding"
    assert grounded.prohibited_critical >= 1
    assert "PROHIBITED_CLAIM" in grounded.reason_codes


def test_private_candidate_requires_publication_or_raises(monkeypatch):
    built = context(monkeypatch)
    measurement = built.measurements[0]
    good = validate_private_candidate(
        built,
        [
            {
                "kind": "observed_measurement",
                "text": f"Retained {measurement.metric_code} value {measurement.value} {measurement.unit} (member time basis {measurement.member_time}).",
                "measurement_refs": [measurement.reference_id],
                "passage_refs": [],
                "metric_code": measurement.metric_code,
                "metric_value": measurement.value,
                "metric_unit": measurement.unit,
            }
        ],
    )
    assert good.verdict == "published"
    with pytest.raises(Exception):
        validate_private_candidate(
            built,
            [
                {
                    "kind": "observed_measurement",
                    "text": "Stage II diagnosis with 90% confidence.",
                    "measurement_refs": [measurement.reference_id],
                    "passage_refs": [],
                    "metric_code": measurement.metric_code,
                    "metric_value": "wrong",
                    "metric_unit": measurement.unit,
                }
            ],
        )


def test_frozen_sixty_case_suite_reports_denominators_and_gates(monkeypatch):
    assert (SUITE_VERSION.grounded_cases, SUITE_VERSION.edge_cases, SUITE_VERSION.adversarial_cases) == (20, 20, 20)
    cases = frozen_suite()
    assert len(cases) == 60
    assert len({c["case_id"] for c in cases}) == 60
    built = context(monkeypatch)
    base = render_template(built)
    totals = {"published": 0, "failed_grounding": 0, "withheld_insufficient_evidence": 0}
    critical_prohibited_published = 0
    for case in cases:
        if case["category"] == "grounded":
            candidate = base
        else:
            candidate = mutate(base, built, case["mutate"], case.get("prohibited_text"))
        grounded = validate_publication(built, candidate)
        totals[grounded.verdict] += 1
        if case["critical"] and case["category"] == "adversarial":
            if grounded.verdict == "published":
                critical_prohibited_published += 1
    assert critical_prohibited_published == 0
    assert totals["published"] == 20
    assert totals["failed_grounding"] == 40
    assert sum(totals.values()) == 60


def test_grounding_http_gate_and_auth_boundary(imaging_db, monkeypatch):
    c, i, p, patient, _, _, _ = imaging_db
    from canceros.grounding_contracts import GroundingReport as Report

    fake = Report.model_validate(
        {
            "interpretation_snapshot_id": uuid4(),
            "context_snapshot_id": uuid4(),
            "verdict": "published",
            "reason_codes": [],
            "numeric_statements": 1,
            "numeric_matched": 1,
            "supported_claims": 1,
            "unsupported_claims": 0,
            "prohibited_critical": 0,
            "next_action": "publish_visible_template",
        }
    )
    monkeypatch.setattr("canceros.grounding_api.build_context", lambda *a, **k: object())
    monkeypatch.setattr(
        "canceros.grounding_api.build_interpretation", lambda *a, **k: object()
    )
    monkeypatch.setattr(
        "canceros.grounding_api.validate_publication", lambda *a, **k: fake
    )
    monkeypatch.setattr("canceros.grounding_api.require_published", lambda *a, **k: None)
    client, headers = http_session((c, i, p, patient, None, None, keys()))
    state_id, interpretation_id = uuid4(), uuid4()
    root = f"/api/v1/projects/{p}/patients/{patient.patient_id}/states/{state_id}/interpretations/{interpretation_id}/grounding"
    body = {"interpretation_snapshot_id": str(interpretation_id)}
    with client:
        assert client.post(root, json=body).status_code == 401
        response = client.post(root, json=body, headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["verdict"] == "published"
        denied = client.post(root, json=body, headers={"Authorization": "Bearer invalid"})
        assert denied.status_code in (401, 403, 404)
