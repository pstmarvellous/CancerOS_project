"""Real shared worker, revision-pinned state assembly and explicit private HTTP publication."""

from test_clinical_ingestion import row
from test_imaging_ingestion import http_session, imaging_db
from test_imaging_jobs import runtime
from test_source_registry import registry_db
from test_twin_states import clinical, setup, time

from canceros.imaging_jobs import (
    ImagingJobInput,
    StateCommand,
    dispatch_imaging,
    enqueue_imaging,
    process_imaging_one,
    read_imaging_job,
)
from canceros.twin_states import ClinicalMember, ImagingMember, StateBuildInput, read_state

__all__ = ["imaging_db", "registry_db", "runtime"]


def test_worker_pins_old_revision_and_http_publication_is_explicit(runtime):
    data, queue, config = runtime
    c, i, p, patient, _, storage, _ = data
    u = patient.patient_id
    branch, association, measures, origin = setup(data)
    imported = clinical(data, origin, [row(origin)])
    value = StateBuildInput(
        target_revision=2,
        association_head=association.sequence,
        branch_id=branch.id,
        time=time(origin),
        clinical_members=[ClinicalMember(record_id=imported.record_ids[0])],
        imaging_members=[
            ImagingMember(measurement_id=measures[0].id, association_event_id=association.id)
        ],
    )
    request = ImagingJobInput(
        expected_revision=2, command=StateCommand(operation="state_assembly", input=value)
    )
    job = enqueue_imaging(c, i, p, u, request, "state-before-correction", storage)
    changed = row(
        origin,
        original_value="10",
        result={"form": "exact", "quantity": {"value": "10", "unit": "g/dL"}},
    )
    corrected = clinical(
        data,
        origin,
        [changed],
        revision=2,
        corrects=imported.record_ids[0],
        key="state-after-enqueue-correction",
    )
    assert corrected.result_revision == 3
    c.commit()
    assert dispatch_imaging(c.engine, queue, p) == 1
    assert process_imaging_one(c.engine, queue, storage, config) == job.id
    with c.engine.begin() as connection:
        result = read_imaging_job(connection, i, p, u, job.id)
        assert result.status == "succeeded" and result.result_report_id
        old = read_state(connection, i, p, u, result.result_report_id)
        assert old.stale and old.snapshot.input_revision == 2
        assert old.snapshot.clinical_members[0].record.id == imported.record_ids[0]
        assert old.publication is None and old.review is None
    current_value = value.model_copy(
        update={
            "target_revision": 3,
            "clinical_members": [ClinicalMember(record_id=corrected.record_ids[0])],
        }
    )
    current_request = ImagingJobInput(
        expected_revision=3, command=StateCommand(operation="state_assembly", input=current_value)
    )
    fresh = enqueue_imaging(c, i, p, u, current_request, "current-state", storage)
    c.commit()
    assert dispatch_imaging(c.engine, queue, p) == 1
    assert process_imaging_one(c.engine, queue, storage, config) == fresh.id
    with c.engine.begin() as connection:
        result = read_imaging_job(connection, i, p, u, fresh.id)
        assert result.status == "succeeded"
        current = read_state(connection, i, p, u, result.result_report_id)
        assert not current.stale and current.publication is None
    client, headers = http_session(data)
    root = f"/api/v1/projects/{p}/patients/{u}"
    with client:
        path = root + f"/states/{current.snapshot.id}"
        assert client.get(path).status_code == 401
        assert client.get(path, headers=headers).json()["publication"] is None
        assert (
            client.get(root + f"/branches/{branch.id}", headers=headers).json()["baseline_hash"]
            == branch.baseline_hash
        )
        response = client.post(
            path + "/reviews",
            json={
                "snapshot_hash": current.snapshot_hash,
                "decision": "accepted_engineering",
                "evidence_sha256": "a" * 64,
            },
            headers={**headers, "Idempotency-Key": "http-state-review"},
        )
        assert response.status_code == 201
        publication = {
            "snapshot_hash": current.snapshot_hash,
            "expected_patient_revision": 3,
            "expected_association_head": association.sequence,
            "expected_review_id": response.json()["id"],
        }
        response = client.post(
            path + "/publications",
            json=publication,
            headers={**headers, "Idempotency-Key": "http-private-state-publication"},
        )
        assert (
            response.status_code == 201
            and response.json()["scope"] == "private_engineering_fixture"
        )
        assert response.json()["scientific_review"] == "pending"
        assert (
            client.post(
                path + "/publications",
                json=publication,
                headers={**headers, "Idempotency-Key": "http-private-state-publication"},
            ).json()["id"]
            == response.json()["id"]
        )
        page = client.get(
            root + f"/states?branch_id={branch.id}&published_only=true", headers=headers
        )
        assert page.status_code == 200 and len(page.json()["items"]) == 1
        assert page.json()["snapshot_revision"] == 3
