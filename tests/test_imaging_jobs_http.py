"""Actual SQL/JWT imaging job and restricted-storage HTTP boundaries."""

from uuid import uuid4

from sqlalchemy import text
from test_imaging_ingestion import http_session, imaging_db
from test_segmentation_reviews import qc_input
from test_source_registry import registry_db

__all__ = ["registry_db", "imaging_db"]


def test_job_cancel_replay_private_grant_and_empty_cleanup_plan(imaging_db, caplog):
    c, _, project, patient, _, _, _ = imaging_db
    value = qc_input(imaging_db)
    artifact = c.execute(
        text("SELECT mask_artifact_id FROM imaging.segmentations WHERE id=:id"),
        {"id": value.segmentation_id},
    ).scalar_one()
    client, headers = http_session(imaging_db)
    base = f"/api/v1/projects/{project}/patients/{patient.patient_id}"
    payload = {
        "expected_revision": 1,
        "command": {"operation": "segmentation_qc", "input": value.model_dump(mode="json")},
    }
    with client:
        assert (
            client.post(
                base + "/imaging-jobs",
                json=payload,
                headers={"Idempotency-Key": "unauthenticated-fixture"},
            ).status_code
            == 401
        )
        request_headers = {**headers, "Idempotency-Key": "http-imaging-1"}
        result = client.post(base + "/imaging-jobs", json=payload, headers=request_headers)
        assert result.status_code == 202, result.text
        assert result.json()["status"] == "queued" and not result.json()["publication_allowed"]
        assert (
            client.post(base + "/imaging-jobs", json=payload, headers=request_headers).json()
            == result.json()
        )
        status_path = result.headers["Location"]
        assert client.get(status_path, headers=headers).json() == result.json()
        cancelled = client.post(status_path + "/cancellations", headers=headers)
        assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
        assert (
            client.post(status_path + "/cancellations", headers=headers).json() == cancelled.json()
        )
        foreign = status_path.replace(str(patient.patient_id), str(uuid4()))
        assert client.get(foreign, headers=headers).status_code == 404
        granted = client.post(
            base + f"/artifacts/{artifact}/read-grants",
            json={"purpose": "restricted_review"},
            headers=headers,
        )
        assert granted.status_code == 200
        assert granted.json()["artifact_id"] == str(artifact)
        assert "X-Amz" not in caplog.text
        # Fresh test project: no aged candidates; this never deletes existing user objects.
        plan = client.post(base + "/imaging-cleanup-plans", headers=headers)
        assert plan.status_code == 201 and plan.json()["candidate_count"] == 0
        applied = client.post(
            base + f"/imaging-cleanup-plans/{plan.json()['plan_id']}/applications", headers=headers
        )
        assert applied.status_code == 200 and applied.json()["deleted_count"] == 0
