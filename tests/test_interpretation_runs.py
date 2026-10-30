"""Deterministic template interpretation; candidates stay private, no clinics."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from test_context_runs import (
    FIXTURE_PATIENT,
    SNAPSHOT_ID,
)
from test_context_runs import (
    build as build_context_fixture,
)
from test_imaging_ingestion import http_session, imaging_db
from test_patient_linkage import keys
from test_source_registry import registry_db

from canceros.context_contracts import ContextBuildInput
from canceros.interpretation_contracts import InterpretationInput, InterpretationReport
from canceros.interpretation_runs import (
    build_interpretation,
    export_input,
    render_template,
    template_summary_text,
)

__all__ = ["imaging_db", "registry_db"]


def context(monkeypatch):
    value = ContextBuildInput(patient_id=FIXTURE_PATIENT, snapshot_id=SNAPSHOT_ID)
    return build_context_fixture(monkeypatch, value)


def test_template_rendering_uses_verified_fields_only(monkeypatch):
    built = context(monkeypatch)
    report = render_template(built)
    assert report.execution_mode == "rule_based_summary"
    assert report.visibility == "visible_template"
    assert report.context_hash == built.context_hash
    assert f"{len(built.measurements)} retained measurements" in report.summary
    observed = [f for f in report.findings if f.kind == "observed_measurement"]
    assert len(observed) == len(built.measurements)
    for finding in observed:
        assert finding.metric_value is not None and finding.metric_unit is not None
        assert finding.measurement_refs and not finding.passage_refs
    assert "Rule-based summary" in report.summary or "rule_based" in report.execution_mode
    again = render_template(built)
    assert again.summary == report.summary and again.findings == report.findings
    assert "no clinical interpretation" in " ".join(report.limitations).lower()


def test_context_mismatch_and_external_mode_stay_private(monkeypatch):
    built = context(monkeypatch)
    with pytest.raises(HTTPException) as mismatch:
        build_interpretation(
            built,
            InterpretationInput(context_snapshot_id=uuid4(), mode="template"),
        )
    assert mismatch.value.status_code == 409
    with pytest.raises(HTTPException) as stale:
        build_interpretation(
            built,
            InterpretationInput(
                context_snapshot_id=built.snapshot_id,
                expected_context_hash="0" * 64,
                mode="template",
            ),
        )
    assert stale.value.status_code == 409
    with pytest.raises(HTTPException) as external:
        build_interpretation(
            built,
            InterpretationInput(context_snapshot_id=built.snapshot_id, mode="external_candidate"),
        )
    assert external.value.status_code == 409


def test_export_input_is_minimized_and_template_text_matches(monkeypatch):
    built = context(monkeypatch)
    exported = export_input(built)
    assert exported.input_snapshot_hash == built.snapshot_hash
    assert len(exported.measurements) == len(built.measurements)
    assert "artifact_id" not in exported.model_dump_json()
    assert "signed" not in exported.model_dump_json()
    text = template_summary_text(built)
    assert f"{len(built.measurements)} supplied measurements" in text


def test_interpretation_http_template_and_auth_boundary(imaging_db, monkeypatch):
    c, i, p, patient, _, _, _ = imaging_db
    fake = InterpretationReport.model_validate(
        {
            "context_snapshot_id": uuid4(),
            "context_hash": "b" * 64,
            "snapshot_hash": "a" * 64,
            "execution_mode": "rule_based_summary",
            "summary": "Rule-based summary fixture.",
            "findings": [],
            "visibility": "visible_template",
            "next_action": "fixture",
        }
    )
    monkeypatch.setattr("canceros.interpretation_api.build_context", lambda *a, **k: object())
    monkeypatch.setattr(
        "canceros.interpretation_api.build_interpretation", lambda *a, **k: fake
    )
    client, headers = http_session((c, i, p, patient, None, None, keys()))
    state_id = uuid4()
    root = f"/api/v1/projects/{p}/patients/{patient.patient_id}/states/{state_id}/interpretations"
    body = {"context_snapshot_id": str(state_id), "mode": "template"}
    with client:
        assert client.post(root, json=body).status_code == 401
        response = client.post(root, json=body, headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["execution_mode"] == "rule_based_summary"
        assert "Rule-based summary" in response.json()["summary"]
        assert response.headers["cache-control"] == "private, no-store"
        denied = client.post(root, json=body, headers={"Authorization": "Bearer invalid"})
        assert denied.status_code in (401, 403, 404)


def test_interpretation_input_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        InterpretationInput(
            context_snapshot_id=uuid4(), mode="template", unknown_field="no"
        )
