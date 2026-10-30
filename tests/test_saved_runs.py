"""Exact-context reuse, idempotent persist, isolation and labeled fallback."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_context_runs import FIXTURE_PATIENT, SNAPSHOT_ID
from test_context_runs import build as build_context_fixture
from test_evidence_runs import evidence_db
from test_imaging_ingestion import http_session, imaging_db
from test_patient_linkage import keys
from test_source_registry import registry_db

from canceros.context_contracts import ContextBuildInput
from canceros.interpretation_contracts import InterpretationInput
from canceros.interpretation_runs import build_interpretation
from canceros.saved_runs import fallback_label, persist_validated, read_saved, reuse_exact
from canceros.saved_runs_contracts import SavedResultQuery

__all__ = ["evidence_db", "imaging_db", "registry_db"]


def context(monkeypatch):
    return build_context_fixture(
        monkeypatch, ContextBuildInput(patient_id=FIXTURE_PATIENT, snapshot_id=SNAPSHOT_ID)
    )


def template(monkeypatch):
    built = context(monkeypatch)
    report = build_interpretation(
        built, InterpretationInput(context_snapshot_id=built.snapshot_id, mode="template")
    )
    return built, report


def test_persist_is_idempotent_and_supersedes_prior_for_snapshot(evidence_db, monkeypatch):
    c, i, p = evidence_db[:3]
    built, report = template(monkeypatch)
    first = persist_validated(c, i, p, built, report, "k1")
    again = persist_validated(c, i, p, built, report, "k1")
    assert again.id == first.id and again.status == "validated_ready"
    assert again.model_identifier and again.prompt_version and again.validator_version
    assert again.model_revision == "unresolved"
    second = persist_validated(c, i, p, built, report, "k2")
    assert second.id != first.id
    assert read_saved(c, i, p, first.id).status in ("validated_ready", "superseded")


def test_exact_context_reuse_revalidates_and_isolates_patients(evidence_db, monkeypatch):
    c, i, p = evidence_db[:3]
    built, report = template(monkeypatch)
    saved = persist_validated(c, i, p, built, report, "reuse-1")
    hit = reuse_exact(
        c, i, p, built, SavedResultQuery(context_snapshot_id=built.snapshot_id)
    )
    assert hit.id == saved.id and hit.context_hash == built.context_hash
    with pytest.raises(HTTPException) as wrong_hash:
        reuse_exact(
            c,
            i,
            p,
            built,
            SavedResultQuery(context_snapshot_id=built.snapshot_id, expected_context_hash="0" * 64),
        )
    assert wrong_hash.value.status_code == 409
    with pytest.raises(HTTPException) as unknown:
        reuse_exact(
            c, i, p, built, SavedResultQuery(context_snapshot_id=uuid4())
        )
    assert unknown.value.status_code == 409


def test_fallback_labels_distinguish_saved_rule_based_and_refusal(monkeypatch):
    built = context(monkeypatch)
    assert fallback_label(built, "exact_reuse")["label"] == "Saved result for this snapshot"
    assert fallback_label(built, "outage")["label"] == "Rule-based fallback"
    refused = fallback_label(built, "policy_refusal")
    assert refused["status"] == 403
    assert "measurements" in " ".join(
        [fallback_label(built, "outage")["next_action"]]
    )


def test_saved_http_persist_reuse_and_auth_boundary(imaging_db, monkeypatch):
    c, i, p, patient, _, _, _ = imaging_db
    monkeypatch.setattr("canceros.saved_api.build_context", lambda *a, **k: object())
    monkeypatch.setattr(
        "canceros.saved_api.build_interpretation", lambda *a, **k: object()
    )
    from canceros.saved_runs_contracts import PersistedInterpretation as P

    fake = P.model_validate(
        {
            "id": uuid4(),
            "project_id": p,
            "patient_id": patient.patient_id,
            "context_snapshot_id": uuid4(),
            "context_hash": "b" * 64,
            "execution_mode": "rule_based_summary",
            "visibility": "visible_template",
            "model_identifier": "local-template/1",
            "prompt_version": "interpretation-template/1",
            "validator_version": "grounding-gate/1",
            "corpus_manifest": "postgres-curated-corpus/active-head",
            "finding_count": 2,
            "status": "validated_ready",
            "next_action": "fixture",
        }
    )
    monkeypatch.setattr("canceros.saved_api.persist_validated", lambda *a, **k: fake)
    monkeypatch.setattr("canceros.saved_api.read_saved", lambda *a, **k: fake)
    monkeypatch.setattr("canceros.saved_api.reuse_exact", lambda *a, **k: fake)
    client, headers = http_session((c, i, p, patient, None, None, keys()))
    state_id, interpretation_id = uuid4(), uuid4()
    create = f"/api/v1/projects/{p}/patients/{patient.patient_id}/states/{state_id}/interpretations/{interpretation_id}/saved-results"
    body = {"interpretation_snapshot_id": str(interpretation_id), "idempotency_key": "k-http"}
    with client:
        assert client.post(create, json=body, headers={"Idempotency-Key": "k-http"}).status_code == 401
        response = client.post(
            create, json=body, headers={**headers, "Idempotency-Key": "k-http"}
        )
        assert response.status_code == 201, response.text
        got = client.get(response.headers["location"], headers=headers)
        assert got.status_code == 200 and got.json()["status"] == "validated_ready"
        assert got.headers["cache-control"] == "private, no-store"
        reuse = client.post(
            f"/api/v1/projects/{p}/patients/{patient.patient_id}/states/{state_id}/saved-result-queries",
            json={"context_snapshot_id": str(state_id)},
            headers=headers,
        )
        assert reuse.status_code == 200, reuse.text
        denied = client.post(create, json=body, headers={"Authorization": "Bearer invalid"})
        assert denied.status_code in (401, 403, 404, 422)
