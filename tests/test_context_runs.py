"""Snapshot-bound immutable context; synthetic fixtures, no clinical advice."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from test_evidence_runs import evidence_db, staged
from test_imaging_ingestion import http_session, imaging_db
from test_patient_linkage import keys
from test_source_registry import registry_db
from test_state_fusion import PATIENT as FIXTURE_PATIENT
from test_state_fusion import PROJECT as FIXTURE_PROJECT
from test_state_fusion import clinical as fixture_clinical
from test_state_fusion import imaging as fixture_imaging
from test_state_fusion import view as fixture_view

from canceros.context_contracts import ContextBuildInput, InterpretationContext
from canceros.context_runs import build_context, context_export_view
from canceros.evidence_contracts import CorpusBuildInput
from canceros.evidence_runs import (
    CorpusActivationInput,
    activate_corpus,
    build_corpus,
    import_document,
    read_passage,
)
from canceros.identity import Identity

__all__ = ["evidence_db", "imaging_db", "registry_db"]


def read_passage_for_fixture(c, i, p, corpus_id, passage_id):
    return read_passage(c, i, p, corpus_id, passage_id)

PATIENT = FIXTURE_PATIENT
PROJECT = FIXTURE_PROJECT


def state_view(day="10"):
    built = fixture_view(
        clinical_members=[fixture_clinical(day=day)], imaging_members=[fixture_imaging(day=day)]
    )
    return built


SNAPSHOT_ID = uuid4()


def build(monkeypatch, value: ContextBuildInput, day="10", stale=False):
    view = state_view(day)
    view = view.model_copy(update={"stale": stale})
    value = value.model_copy(update={"snapshot_id": SNAPSHOT_ID})
    monkeypatch.setattr("canceros.context_runs.read_state", lambda *a, **k: view)
    monkeypatch.setattr("canceros.context_runs.authorize_patient", lambda *a, **k: None)
    monkeypatch.setattr("canceros.context_runs.authorize_project", lambda *a, **k: None)
    return build_context(None, Identity("u", {}), PROJECT, PATIENT, value)


def test_context_separates_measurements_and_preserves_snapshot_identity(monkeypatch):
    context = build(
        monkeypatch,
        ContextBuildInput(patient_id=PATIENT, snapshot_id=uuid4()),
    )
    expected_hash = state_view().snapshot_hash
    assert context.snapshot_hash == expected_hash
    assert context.patient_id == PATIENT and not context.stale
    assert len(context.measurements) == 2
    assert {m.origin for m in context.measurements} == {"SYNTHETIC_GENERATED"}
    assert context.passages == () and context.assertions == ()
    assert len({m.reference_id for m in context.measurements}) == 2
    again = build(
        monkeypatch,
        ContextBuildInput(patient_id=PATIENT, snapshot_id=uuid4()),
    )
    assert again.context_hash == context.context_hash
    assert again.payload_hash == context.payload_hash
    assert "no clinical interpretation" in " ".join(context.limitations).lower()


def test_expected_hash_patient_and_cross_branch_comparison_are_strict(monkeypatch):
    value = ContextBuildInput(
        patient_id=PATIENT, snapshot_id=SNAPSHOT_ID, expected_snapshot_hash="b" * 64
    )
    with pytest.raises(HTTPException) as denied:
        build(monkeypatch, value)
    assert denied.value.status_code == 409
    with pytest.raises(HTTPException) as wrong_patient:
        build(
            monkeypatch,
            ContextBuildInput(patient_id=uuid4(), snapshot_id=uuid4()),
        )
    assert wrong_patient.value.status_code == 404
    with pytest.raises(HTTPException) as same_snapshot:
        build(
            monkeypatch,
            ContextBuildInput(
                patient_id=PATIENT,
                snapshot_id=SNAPSHOT_ID,
                comparison_snapshot_id=SNAPSHOT_ID,
            ),
        )
    assert same_snapshot.value.status_code == 422
    with pytest.raises(ValidationError):
        ContextBuildInput(
            patient_id=PATIENT, snapshot_id=uuid4(), comparison_snapshot_id=uuid4(), max_items=0
        )


def test_truncation_budget_keeps_critical_state_and_records_omissions(monkeypatch):
    with pytest.raises(HTTPException) as over_budget:
        build(
            monkeypatch, ContextBuildInput(patient_id=PATIENT, snapshot_id=uuid4(), max_items=1)
        )
    assert over_budget.value.status_code == 409
    context = build(
        monkeypatch, ContextBuildInput(patient_id=PATIENT, snapshot_id=uuid4(), max_items=2)
    )
    assert context.omitted == ()


def test_export_view_excludes_local_only_fields(monkeypatch):
    context = build(
        monkeypatch, ContextBuildInput(patient_id=PATIENT, snapshot_id=uuid4())
    )
    exported = context_export_view(context)
    assert exported["schema_version"] == "provider-input/1"
    assert exported["input_snapshot_hash"] == context.snapshot_hash
    assert "signed URLs" in exported["excluded_local_only_fields"]
    assert "source maps" in exported["excluded_local_only_fields"]
    text = str(exported)
    assert "storage credentials" in text and "artifact_id" not in text


def test_retrieval_passages_require_active_corpus_and_current_rights(evidence_db, monkeypatch):
    c, i, p, _, storage = evidence_db
    metadata, content = staged(evidence_db, "Artificial alpha signal in a fixture paragraph.")
    document = import_document(c, i, p, metadata, content, storage)
    corpus = build_corpus(c, i, p, CorpusBuildInput(document_ids=[document.id]))
    activate_corpus(c, i, p, CorpusActivationInput(corpus_id=corpus.id))
    passage = read_passage_for_fixture(c, i, p, corpus.id, document.passage_ids[0])

    def fake_state(c2, i2, p2, u2, identifier):
        state = state_view()
        if identifier == document.passage_ids[0]:
            raise HTTPException(404)
        return state

    def fake_passage(c2, i2, p2, corpus_id, pid):
        assert corpus_id == corpus.id and pid == document.passage_ids[0]
        return passage

    monkeypatch.setattr("canceros.context_runs.read_state", fake_state)
    monkeypatch.setattr("canceros.context_runs.read_passage", fake_passage)
    monkeypatch.setattr(
        "canceros.context_runs.read_current_corpus",
        lambda *a, **k: type("H", (), {"status": "active", "corpus_id": corpus.id})(),
    )
    context = build(
        monkeypatch,
        ContextBuildInput(
            patient_id=PATIENT,
            snapshot_id=uuid4(),
            retrieval_corpus_id=corpus.id,
            retrieval_passage_ids=(document.passage_ids[0],),
        ),
    )
    assert len(context.passages) == 1
    assert context.passages[0].passage_id == document.passage_ids[0]
    with pytest.raises(HTTPException) as stale:
        build(
            monkeypatch,
            ContextBuildInput(
                patient_id=PATIENT,
                snapshot_id=uuid4(),
                retrieval_corpus_id=uuid4(),
                retrieval_passage_ids=(document.passage_ids[0],),
            ),
        )
    assert stale.value.status_code == 409


def test_context_http_build_and_owner_isolation(imaging_db, monkeypatch):
    c, i, p, patient, _, _, _ = imaging_db
    returned_snapshot = uuid4()
    fake = InterpretationContext.model_validate(
        {
            "patient_id": patient.patient_id,
            "branch_id": uuid4(),
            "snapshot_id": returned_snapshot,
            "snapshot_hash": "a" * 64,
            "purpose": "research_summary",
            "stale": False,
            "measurements": [],
            "context_hash": "b" * 64,
            "payload_hash": "c" * 64,
            "exportable": False,
            "next_action": "fixture",
        }
    )
    monkeypatch.setattr("canceros.context_runs.build_context", lambda *a, **k: fake)
    monkeypatch.setattr("canceros.context_api.build_context", lambda *a, **k: fake)
    monkeypatch.setattr("canceros.context_runs.record_context_build", lambda *a, **k: None)
    monkeypatch.setattr("canceros.context_api.record_context_build", lambda *a, **k: None)
    client, headers = http_session((c, i, p, patient, None, None, keys()))
    root = f"/api/v1/projects/{p}/patients/{patient.patient_id}/interpretation-contexts"
    body = {"patient_id": str(patient.patient_id), "snapshot_id": str(uuid4())}
    with client:
        assert client.post(root, json=body).status_code == 401
        response = client.post(root, json=body, headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["snapshot_hash"] == "a" * 64
        assert response.headers["cache-control"] == "private, no-store"
        denied = client.post(root, json=body, headers={'Authorization': 'Bearer invalid'})
        assert denied.status_code in (401, 403, 404)
