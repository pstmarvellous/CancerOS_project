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
    snapshot_id = value.snapshot_id
    monkeypatch.setattr("canceros.context_runs.read_state", lambda *a, **k: view)
    monkeypatch.setattr("canceros.context_runs.authorize_patient", lambda *a, **k: None)
    monkeypatch.setattr("canceros.context_runs.authorize_project", lambda *a, **k: None)
    monkeypatch.setattr("canceros.context_runs._usable", lambda *a, **k: None)
    built = build_context(None, Identity("u", {}), PROJECT, PATIENT, value)
    assert built.snapshot_id == snapshot_id
    return built


def test_context_separates_measurements_and_preserves_snapshot_identity(monkeypatch):
    context = build(
        monkeypatch,
        ContextBuildInput(patient_id=PATIENT, snapshot_id=SNAPSHOT_ID),
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
        ContextBuildInput(patient_id=PATIENT, snapshot_id=SNAPSHOT_ID),
    )
    assert again.context_hash == context.context_hash
    assert again.payload_hash == context.payload_hash
    assert "no clinical interpretation" in " ".join(context.limitations).lower()
    assert all("Day 10 (simulation)" == m.member_time for m in context.measurements)


def test_comparison_uses_owned_prior_exact_revision_and_pins_values(monkeypatch):
    selected = state_view("37")
    selected = selected.model_copy(
        update={
            "snapshot": selected.snapshot.model_copy(
                update={"time": selected.snapshot.time.model_copy(update={"value": "37"})}
            )
        }
    )
    previous = state_view("0")
    previous = previous.model_copy(
        update={
            "snapshot": previous.snapshot.model_copy(
                update={"time": previous.snapshot.time.model_copy(update={"value": "0"})}
            )
        }
    )
    first, second = uuid4(), uuid4()
    monkeypatch.setattr("canceros.context_runs.authorize_patient", lambda *a, **k: None)
    monkeypatch.setattr("canceros.context_runs.authorize_project", lambda *a, **k: None)
    monkeypatch.setattr("canceros.context_runs._usable", lambda *a, **k: None)
    monkeypatch.setattr(
        "canceros.context_runs.read_state", lambda *a: selected if a[-1] == second else previous
    )
    request = ContextBuildInput(
        patient_id=PATIENT, snapshot_id=second, comparison_snapshot_id=first
    )
    context = build_context(None, Identity("u", {}), PROJECT, PATIENT, request)
    assert context.comparison_measurements and all(
        "Day 0" in m.member_time for m in context.comparison_measurements
    )
    assert all("Day 37" in m.member_time for m in context.measurements)
    previous = previous.model_copy(
        update={"snapshot": previous.snapshot.model_copy(update={"input_revision": 999})}
    )
    with pytest.raises(HTTPException) as mismatched:
        build_context(None, Identity("u", {}), PROJECT, PATIENT, request)
    assert mismatched.value.status_code == 409


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
        build(monkeypatch, ContextBuildInput(patient_id=PATIENT, snapshot_id=uuid4(), max_items=1))
    assert over_budget.value.status_code == 409
    context = build(
        monkeypatch, ContextBuildInput(patient_id=PATIENT, snapshot_id=uuid4(), max_items=2)
    )
    assert context.omitted == ()


def test_history_shares_aggregate_budget_and_filtered_measurements_abstain(monkeypatch):
    from canceros.state_fusion import fuse_state

    report = fuse_state(state_view())
    history = report.clinical_indicators[0].model_copy(
        update={"modality": "treatment", "concept": "exposure"}
    )
    monkeypatch.setattr(
        "canceros.context_runs.fuse_state",
        lambda *a: report.model_copy(update={"treatment_history": [history]}),
    )
    request = ContextBuildInput(patient_id=PATIENT, snapshot_id=uuid4(), max_items=2)
    built = build(monkeypatch, request)
    assert len(built.measurements) == 2 and built.treatment_history == ()
    assert any(
        reason.startswith("treatment:") and reason.endswith(":budget") for reason in built.omitted
    )
    bigger = build(monkeypatch, request.model_copy(update={"max_items": 3}))
    assert len(bigger.measurements) + len(bigger.treatment_history) == 3
    filtered = report.model_copy(
        update={
            "tumor_state": [
                m.model_copy(update={"primary_for_display": False}) for m in report.tumor_state
            ],
            "clinical_indicators": [
                m.model_copy(update={"primary_for_display": False})
                for m in report.clinical_indicators
            ],
        }
    )
    monkeypatch.setattr("canceros.context_runs.fuse_state", lambda *a: filtered)
    empty = build(monkeypatch, request)
    assert not empty.measurements
    assert empty.next_action == "narrow_scope_or_request_curator_review"
    assert any(
        reason.endswith(":quality_time_conflict_or_nonexact_excluded") for reason in empty.omitted
    )


def test_context_byte_budget_fails_closed_at_actual_serialized_size(monkeypatch):
    from canceros.persistence import canonical_bytes

    request = ContextBuildInput(patient_id=PATIENT, snapshot_id=uuid4())
    built = build(monkeypatch, request)
    size = len(canonical_bytes(built.model_dump(mode="json")))
    monkeypatch.setattr("canceros.context_runs.MAX_TEXT_BYTES", size)
    assert build(monkeypatch, request).context_hash == built.context_hash
    monkeypatch.setattr("canceros.context_runs.MAX_TEXT_BYTES", size - 1)
    with pytest.raises(HTTPException) as exceeded:
        build(monkeypatch, request)
    assert exceeded.value.status_code == 409
    assert exceeded.value.detail == "interpretation_context_budget_exceeded_narrow_scope"


def test_assembly_version_participates_in_context_hash(monkeypatch):
    request = ContextBuildInput(patient_id=PATIENT, snapshot_id=uuid4())
    current = build(monkeypatch, request)
    monkeypatch.setattr(
        "canceros.context_runs.ASSEMBLY_VERSION", "interpretation-context-assembly/test-alternative"
    )
    changed = build(monkeypatch, request)
    assert current.snapshot_hash == changed.snapshot_hash
    assert current.context_hash != changed.context_hash


def test_export_view_excludes_local_only_fields(monkeypatch):
    context = build(monkeypatch, ContextBuildInput(patient_id=PATIENT, snapshot_id=uuid4()))
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
        denied = client.post(root, json=body, headers={"Authorization": "Bearer invalid"})
        assert denied.status_code in (401, 403, 404)


def test_real_context_interpretation_chain_isolates_two_patients(imaging_db):
    """Actual SQL/private source/state/HTTP path; no context/auth/state mocks."""
    from sqlalchemy import text
    from test_twin_states import setup, time

    from canceros.grounding_runs import validate_publication
    from canceros.interpretation_runs import render_template
    from canceros.patient_linkage import LinkageInput, resolve_mapping
    from canceros.settings import Settings
    from canceros.synthetic_geometry import (
        FixtureRunInput,
        GeometryInput,
        TargetPoint,
        authorize_fixture_run,
        generate_geometry,
    )
    from canceros.synthetic_shape import ShapeConfig
    from canceros.twin_states import ImagingMember, StateBuildInput, build_state

    c, i, p, patient, _, storage, config = imaging_db
    u = patient.patient_id
    branch, association, measures, origin = setup(imaging_db)
    baseline = build_state(
        c,
        i,
        p,
        u,
        StateBuildInput(
            target_revision=1,
            association_head=association.sequence,
            branch_id=branch.id,
            time=time(origin),
            imaging_members=[
                ImagingMember(measurement_id=measures[0].id, association_event_id=association.id)
            ],
        ),
        storage,
        "rec07-baseline",
    )
    settings = Settings(mode="test", _env_file=None)
    run = authorize_fixture_run(
        c,
        i,
        p,
        u,
        FixtureRunInput(
            branch_id=branch.id,
            baseline_hash=branch.baseline_hash,
            targets=[TargetPoint(relative_day="37", target_mm3="0")],
            shape_config=ShapeConfig(seed=42),
        ),
        storage,
        "rec07-run",
        settings,
    )
    generated = generate_geometry(
        c,
        i,
        p,
        u,
        GeometryInput(run_id=run.id, baseline_hash=branch.baseline_hash, target_index=0),
        storage,
        "rec07-shape",
        settings,
    )
    assert generated.state_id is not None
    from canceros.twin_states import read_state

    states = [baseline, read_state(c, i, p, u, generated.state_id).snapshot]
    source = c.execute(
        text(
            "SELECT source_version_id FROM source.patient_mappings WHERE project_id=:p AND id=:id"
        ),
        {"p": p, "id": patient.mapping_id},
    ).scalar_one()
    other = resolve_mapping(
        c,
        i,
        p,
        LinkageInput(source_version_id=source, source_patient_key="REC07-OTHER-ARTIFICIAL-PATIENT"),
        config,
    )
    request = ContextBuildInput(
        patient_id=u, snapshot_id=states[1].id, comparison_snapshot_id=states[0].id
    )
    built = build_context(c, i, p, u, request, storage=storage)
    report = render_template(built)
    assert any(
        "Day 37" in f.text and "0 mm3" in f.text and "hypothetical" in f.text
        for f in report.findings
    ), " | ".join(f.text for f in report.findings)
    assert any("Selected comparison at Day 0" in f.text for f in report.findings)
    assert validate_publication(built, report).verdict == "published"
    client, headers = http_session((c, i, p, patient, None, None, config))
    root = f"/api/v1/projects/{p}/patients"
    body = {
        "context_snapshot_id": str(states[1].id),
        "expected_context_hash": built.context_hash,
        "context_input": request.model_dump(mode="json"),
    }
    with client:
        response = client.post(
            f"{root}/{u}/states/{states[1].id}/interpretations", json=body, headers=headers
        )
        assert response.status_code == 200, response.text
        assert response.json()["context_hash"] == built.context_hash
        for path, value in [
            (
                f"{root}/{other.patient_id}/interpretation-contexts",
                {**request.model_dump(mode="json"), "patient_id": str(other.patient_id)},
            ),
            (
                f"{root}/{other.patient_id}/states/{states[1].id}/interpretations",
                {
                    **body,
                    "context_input": {
                        **request.model_dump(mode="json"),
                        "patient_id": str(other.patient_id),
                    },
                },
            ),
        ]:
            denied = client.post(path, json=value, headers=headers)
            assert denied.status_code == 404
            assert "mm3" not in denied.text and built.context_hash not in denied.text
    from canceros.lineage import WithdrawalInput, withdraw_resource

    withdraw_resource(c, i, p, u, measures[0].id, WithdrawalInput(reason_code="rights_withdrawn"))
    with pytest.raises(HTTPException):
        build_context(c, i, p, u, request, storage=storage)


def test_note_context_http_reads_private_text_only_for_retained_note(imaging_db):
    from test_clinical_ingestion import row
    from test_note_runs import stage_note
    from test_twin_states import clinical, setup, time

    from canceros.clinical_contracts import ClinicalTime
    from canceros.note_runs import (
        NoteExtractionCommand,
        NoteRegistration,
        extract_document,
        register_note,
    )
    from canceros.twin_states import ClinicalMember, StateBuildInput, build_state

    c, i, p, patient, component, storage, config = imaging_db
    u = patient.patient_id
    branch, association, _, origin = setup(imaging_db)
    note_row = row(origin)
    anchor = ClinicalTime.model_validate(note_row["time"])
    data = (c, i, p, patient, origin, component, storage)
    artifact = stage_note(data, "Patient reports pain.")
    note = register_note(c, i, p, u, NoteRegistration(artifact_id=artifact, anchor=anchor), storage)
    extraction = extract_document(c, i, p, u, NoteExtractionCommand(note_id=note.note_id), storage)
    for key in ("result", "original_value", "original_unit"):
        note_row.pop(key)
    note_row.update(
        kind="note",
        concept="source_note",
        artifact_id=str(artifact),
        note_document_id=str(note.note_id),
        content_sha256=note.source_sha256,
        language="en",
    )
    accepted = clinical(imaging_db, origin, [note_row])
    state = build_state(
        c,
        i,
        p,
        u,
        StateBuildInput(
            target_revision=2,
            association_head=association.sequence,
            branch_id=branch.id,
            time=time(origin),
            clinical_members=[ClinicalMember(record_id=accepted.record_ids[0])],
        ),
        storage,
        "rec07-note-state",
    )
    request = ContextBuildInput(
        patient_id=u, snapshot_id=state.id, note_extraction_ids=(extraction.extraction_id,)
    )
    unrelated_artifact = stage_note(data, "Patient reports nausea.")
    unrelated_note = register_note(
        c, i, p, u, NoteRegistration(artifact_id=unrelated_artifact, anchor=anchor), storage
    )
    unrelated = extract_document(
        c, i, p, u, NoteExtractionCommand(note_id=unrelated_note.note_id), storage
    )
    client, headers = http_session((c, i, p, patient, None, None, config))
    root = f"/api/v1/projects/{p}/patients/{u}"
    with client:
        response = client.post(
            f"{root}/interpretation-contexts", json=request.model_dump(mode="json"), headers=headers
        )
        assert response.status_code == 200, response.text
        context = response.json()
        assert context["assertions"][0]["excerpt"] == "Patient reports pain"
        result = client.post(
            f"{root}/states/{state.id}/interpretations",
            json={
                "context_snapshot_id": str(state.id),
                "expected_context_hash": context["context_hash"],
                "context_input": request.model_dump(mode="json"),
            },
            headers=headers,
        )
        assert result.status_code == 200, result.text
        assert result.json()["context_hash"] == context["context_hash"]
        denied = client.post(
            f"{root}/interpretation-contexts",
            json={
                **request.model_dump(mode="json"),
                "note_extraction_ids": [str(unrelated.extraction_id)],
            },
            headers=headers,
        )
        assert denied.status_code == 409
        assert "nausea" not in denied.text
