"""REC-01 navigation authorization contracts: inaccessible cases and stale state.

Service-layer negatives against the disposable database with artificial patients.
A viewer granted Patient A only must be denied Patient B's context and saved
results; mismatched or stale selections must fail without content.
"""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from test_context_runs import FIXTURE_PATIENT, SNAPSHOT_ID
from test_context_runs import build as build_context_fixture
from test_evidence_runs import evidence_db
from test_imaging_ingestion import imaging_db
from test_patient_linkage import keys
from test_source_registry import registry_db

from canceros.context_contracts import ContextBuildInput
from canceros.context_runs import build_context
from canceros.identity import Identity
from canceros.interpretation_contracts import InterpretationInput
from canceros.interpretation_runs import build_interpretation
from canceros.saved_runs import persist_validated
from canceros.saved_runs_contracts import InterpretationPersistInput

__all__ = ["evidence_db", "imaging_db", "registry_db"]


def viewer_with_grant(c, project, patient):
    viewer_id = uuid4()
    c.execute(
        text("INSERT INTO access.users(id,issuer,subject) VALUES(:id,'engineering',:s)"),
        {"id": viewer_id, "s": str(viewer_id)},
    )
    c.execute(
        text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:id,'viewer')"),
        {"p": project, "id": viewer_id},
    )
    c.execute(
        text("INSERT INTO source.research_patients(id,project_id,display_code) VALUES(:u,:p,:label)"),
        {"u": patient, "p": project, "label": "Research-" + patient.hex},
    )
    c.execute(
        text("INSERT INTO access.patient_grants(project_id,patient_id,user_id,permission) VALUES(:p,:u,:actor,'view')"),
        {"p": project, "u": patient, "actor": viewer_id},
    )
    return Identity(viewer_id, {project: "viewer"})


def other_patient(c, project):
    peer = uuid4()
    c.execute(
        text("INSERT INTO source.research_patients(id,project_id,display_code) VALUES(:u,:p,:label)"),
        {"u": peer, "p": project, "label": "Research-" + peer.hex},
    )
    return peer


def test_context_build_denies_inaccessible_patient(evidence_db):
    c, i, p = evidence_db[:3]
    granted = uuid4()
    viewer = viewer_with_grant(c, p, granted)
    peer = other_patient(c, p)
    with pytest.raises(HTTPException) as denied:
        build_context(c, viewer, p, peer, ContextBuildInput(patient_id=peer, snapshot_id=SNAPSHOT_ID))
    assert denied.value.status_code == 404


def test_context_build_rejects_body_patient_mismatch(registry_db, monkeypatch):
    from test_state_fusion import view as fixture_view
    from test_state_fusion import clinical as fixture_clinical
    from test_state_fusion import imaging as fixture_imaging

    c, i, p = registry_db
    built_view = fixture_view(
        clinical_members=[fixture_clinical(day="10")], imaging_members=[fixture_imaging(day="10")]
    )
    monkeypatch.setattr("canceros.context_runs.read_state", lambda *a, **k: built_view)
    with pytest.raises(HTTPException) as denied:
        build_context(c, i, p, FIXTURE_PATIENT, ContextBuildInput(patient_id=uuid4(), snapshot_id=SNAPSHOT_ID))
    assert denied.value.status_code == 404


def test_persist_validated_denies_patient_without_grant(evidence_db, monkeypatch):
    c, i, p = evidence_db[:3]
    granted = uuid4()
    viewer = viewer_with_grant(c, p, granted)
    peer = other_patient(c, p)
    built = build_context_fixture(
        monkeypatch, ContextBuildInput(patient_id=FIXTURE_PATIENT, snapshot_id=SNAPSHOT_ID)
    )
    report = build_interpretation(
        built, InterpretationInput(context_snapshot_id=built.snapshot_id, mode="template")
    )
    assert InterpretationPersistInput(
        interpretation_snapshot_id=built.snapshot_id, idempotency_key="rec01-denied"
    ).idempotency_key == "rec01-denied"
    with pytest.raises(HTTPException) as denied:
        persist_validated(c, viewer, p, built.model_copy(update={"patient_id": peer}), report, "rec01-denied")
    assert denied.value.status_code == 404
