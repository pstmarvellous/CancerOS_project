"""COS-070 closure: job orchestration, discovery, viewer isolation."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_clinical_ingestion import row as clinical_row
from test_imaging_ingestion import http_session, imaging_db
from test_patient_linkage import keys
from test_source_registry import registry_db
from test_twin_states import clinical as twin_clinical
from test_twin_states import setup as twin_setup
from test_twin_states import time as twin_time

from canceros.interpretation_jobs import list_jobs, read_job, submit_job
from canceros.interpretation_jobs_contracts import InterpretationJobInput
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
    return build_state(c, i, p, u, value, storage, "ai-closure-state")


def submit(data, **changes):
    c, i, p, patient, *_ = data
    built = state_for(data)
    value = InterpretationJobInput(state_id=built.id, idempotency_key="ai-job-1", **changes)
    return c, i, p, patient, submit_job(c, i, p, patient.patient_id, value, "ai-job-1")


def test_job_submission_validates_grounds_persists_and_replays(imaging_db):
    c, i, p, patient, job = submit(imaging_db)
    assert job.status == "validated_ready"
    assert job.execution_mode == "rule_based_summary"
    assert job.finding_count >= 1 and job.saved_id is not None
    assert job.reason_codes == ()
    again = submit_job(
        c, i, p, patient.patient_id,
        InterpretationJobInput(state_id=job.context_snapshot_id, idempotency_key="ai-job-1"),
        "ai-job-1",
    )
    assert again.id == job.id
    assert read_job(c, i, p, patient.patient_id, job.id).id == job.id
    listed = list_jobs(c, i, p, patient.patient_id)
    assert any(item.id == job.id for item in listed)
    with pytest.raises(HTTPException) as stranger:
        read_job(c, i, p, uuid4(), job.id)
    assert stranger.value.status_code == 404


def test_external_mode_stays_closed_and_stale_hash_fails(imaging_db):
    c, i, p, patient, *_ = imaging_db
    built = state_for(imaging_db)
    with pytest.raises(HTTPException) as external:
        submit_job(
            c, i, p, patient.patient_id,
            InterpretationJobInput(state_id=built.id, idempotency_key="ai-ext", mode="external_candidate"),
            "ai-ext",
        )
    assert external.value.status_code in (409, 422)
    with pytest.raises(HTTPException) as stale:
        submit_job(
            c, i, p, patient.patient_id,
            InterpretationJobInput(
                state_id=built.id, idempotency_key="ai-stale", expected_snapshot_hash="0" * 64
            ),
            "ai-stale",
        )
    assert stale.value.status_code == 409


def test_closure_http_job_submit_read_list_and_auth(imaging_db):
    c, i, p, patient, *_ = imaging_db
    built = state_for(imaging_db)
    client, headers = http_session((c, i, p, patient, None, None, keys()))
    root = f"/api/v1/projects/{p}/patients/{patient.patient_id}"
    body = {"state_id": str(built.id), "mode": "template", "idempotency_key": "ai-http-1"}
    with client:
        assert client.post(root + "/interpretation-jobs", json=body, headers={"Idempotency-Key": "ai-http-1"}).status_code == 401
        created = client.post(
            root + "/interpretation-jobs", json=body,
            headers={**headers, "Idempotency-Key": "ai-http-1"},
        )
        assert created.status_code == 201, created.text
        assert created.json()["status"] == "validated_ready"
        assert created.json()["execution_mode"] == "rule_based_summary"
        detail = client.get(created.headers["location"], headers=headers)
        assert detail.status_code == 200 and detail.json()["id"] == created.json()["id"]
        listed = client.get(root + "/interpretation-jobs", headers=headers)
        assert listed.status_code == 200 and listed.json()["items"]
        assert listed.headers["cache-control"] == "private, no-store"
        denied = client.post(root + "/interpretation-jobs", json=body, headers={"Authorization": "Bearer invalid"})
        assert denied.status_code in (401, 403, 404, 422)
