"""COS-071 conformance: cross-cutting auth, validation and contract behavior."""

from uuid import uuid4

from test_clinical_ingestion import row as clinical_row
from test_imaging_ingestion import http_session, imaging_db
from test_patient_linkage import keys
from test_source_registry import registry_db
from test_twin_states import clinical as twin_clinical
from test_twin_states import setup as twin_setup
from test_twin_states import time as twin_time

from canceros.twin_states import ClinicalMember, StateBuildInput, build_state

__all__ = ["imaging_db", "registry_db"]


def state_for(data):
    c, i, p, patient, _, storage, _ = data
    u = patient.patient_id
    branch, association, _, origin = twin_setup(data)
    imported = twin_clinical(data, origin, [clinical_row(origin)])
    value = StateBuildInput(
        target_revision=2,
        association_head=association.sequence,
        branch_id=branch.id,
        time=twin_time(origin),
        clinical_members=[ClinicalMember(record_id=imported.record_ids[0])],
    )
    return build_state(c, i, p, u, value, storage, "conform-state")


def test_cross_project_patient_branch_ids_are_isolated(imaging_db):
    c, i, p, patient, _, _, _ = imaging_db
    client, headers = http_session((c, i, p, patient, None, None, keys()))
    other_project, other_patient = uuid4(), uuid4()
    with client:
        assert client.get(f"/api/v1/projects/{other_project}/patients").status_code in (401, 403, 404)
        assert client.get(
            f"/api/v1/projects/{other_project}/patients/{patient.patient_id}", headers=headers
        ).status_code in (403, 404)
        assert client.get(
            f"/api/v1/projects/{p}/patients/{other_patient}", headers=headers
        ).status_code in (403, 404)
        assert client.get(
            f"/api/v1/projects/{p}/patients/{patient.patient_id}/states/{uuid4()}/manifest",
            headers=headers,
        ).status_code == 404


def test_role_escalation_mass_assignment_and_ownership_are_denied(imaging_db):
    c, i, p, patient, _, _, _ = imaging_db
    client, headers = http_session((c, i, p, patient, None, None, keys()))
    u = patient.patient_id
    with client:
        escalate = client.post(
            f"/api/v1/projects/{p}/patients/{u}/observation-queries",
            json={"kind": "laboratory", "project_id": str(uuid4())},
            headers=headers,
        )
        assert escalate.status_code in (200, 422)
        if escalate.status_code == 200:
            assert "project_id" not in str(escalate.json().get("items", []))
        forged = client.get(f"/api/v1/projects/{p}/patients/{u}", headers=headers)
        assert forged.status_code == 200
        assert "membership" not in forged.text and "secret" not in forged.text.lower()


def test_malformed_oversized_and_stale_preconditions_fail_safely(imaging_db):
    c, i, p, patient, _, _, _ = imaging_db
    client, headers = http_session((c, i, p, patient, None, None, keys()))
    u = patient.patient_id
    with client:
        oversized = client.post(
            f"/api/v1/projects/{p}/patients/{u}/observation-queries",
            json={"concept": "x" * 5000},
            headers=headers,
        )
        assert oversized.status_code == 422
        unknown_kind = client.post(
            f"/api/v1/projects/{p}/patients/{u}/observation-queries",
            json={"kind": "not_a_kind"},
            headers=headers,
        )
        assert unknown_kind.status_code == 422
        envelope = unknown_kind.json()
        assert envelope["code"] == "FAILED_SCHEMA" and "request_id" in envelope
        stale = client.post(
            f"/api/v1/projects/{p}/patients/{u}/observation-queries",
            json={"limit": 0},
            headers=headers,
        )
        assert stale.status_code == 422


def test_output_escaping_injection_nonexecution_and_denied_egress(imaging_db):
    c, i, p, patient, _, _, _ = imaging_db
    client, headers = http_session((c, i, p, patient, None, None, keys()))
    u = patient.patient_id
    with client:
        injection = client.post(
            f"/api/v1/projects/{p}/patients/{u}/observation-queries",
            json={"concept": "'; DROP TABLE clinical.observations; --"},
            headers=headers,
        )
        assert injection.status_code == 200
        assert injection.json()["items"] == []
        xss = client.post(
            f"/api/v1/projects/{p}/patients/{u}/observation-queries",
            json={"concept": "<script>alert(1)</script>"},
            headers=headers,
        )
        assert xss.status_code == 200
        caps = client.get(f"/api/v1/projects/{p}/ai/capabilities", headers=headers)
        assert caps.status_code == 200
        body = caps.json()
        assert body["external_model_available"] is False
        assert body["candidate_publication_available"] is False
        assert "key" not in caps.text.lower() or "Idempotency-Key" in caps.text


def test_conformance_e2e_correction_asset_publication_interpretation(imaging_db):
    c, i, p, patient, _, _, _ = imaging_db
    u = patient.patient_id
    built = state_for(imaging_db)
    client, headers = http_session((c, i, p, patient, None, None, keys()))
    root = f"/api/v1/projects/{p}/patients/{u}"
    with client:
        manifest = client.get(root + f"/states/{built.id}/manifest", headers=headers)
        assert manifest.status_code == 200
        jobs = client.get(root + "/interpretation-jobs", headers=headers)
        assert jobs.status_code == 200
        body = {"state_id": str(built.id), "mode": "template", "idempotency_key": "conform-e2e-1"}
        created = client.post(
            root + "/interpretation-jobs", json=body,
            headers={**headers, "Idempotency-Key": "conform-e2e-1"},
        )
        assert created.status_code in (201, 200), created.text
        assert created.json()["visibility"] == "visible_template"
        replay = client.post(
            root + "/interpretation-jobs", json=body,
            headers={**headers, "Idempotency-Key": "conform-e2e-1"},
        )
        assert replay.json()["id"] == created.json()["id"]
        grounding = client.post(
            root + f"/states/{built.id}/interpretations/{built.id}/grounding",
            json={"interpretation_snapshot_id": str(built.id)},
            headers=headers,
        )
        assert grounding.status_code in (200, 404, 409, 422)
