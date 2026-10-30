"""COS-066 closure: patient/visit/observation reads and source-backed diagnosis."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_clinical_ingestion import clinical_db
from test_clinical_ingestion import row as clinical_row
from test_clinical_ingestion import stage as stage_source
from test_imaging_ingestion import http_session
from test_patient_linkage import keys
from test_source_registry import registry_db

from canceros.clinical_ingestion import BatchCommand, accept_batch
from canceros.patient_runs import (
    ObservationFilter,
    create_source_diagnosis,
    list_patients,
    list_visits,
    patient_detail,
    query_observations,
)

__all__ = ["clinical_db", "registry_db"]

def seeded(data):
    c, i, p, patient, origin, _, storage = data
    lab = clinical_row(origin, client_record_key="closure-lab-1")
    pathology = clinical_row(origin, client_record_key="closure-dx-1")
    for field in ("result", "original_value", "original_unit"):
        pathology.pop(field, None)
    pathology.update(
        kind="diagnosis",
        concept="source_pathology",
        side="unknown",
        er_status="negative",
        pr_status="not_recorded",
        her2_status="not_tested",
    )
    from canceros.clinical_ingestion import validate_batch as _vv
    pv, _ = _vv(c, i, p, patient.patient_id, BatchCommand(source_artifact_id=stage_source(data, [lab]).artifact_id, expected_revision=1), storage)
    print('LABONLY', pv.status, [(x.path, x.reason) for x in pv.issues])
    receipt = stage_source(data, [lab, pathology])
    accepted = accept_batch(
        c, i, p, patient.patient_id,
        BatchCommand(source_artifact_id=receipt.artifact_id, expected_revision=1),
        "closure-seed-1",
        storage,
    )
    return data, accepted




def test_patient_list_detail_are_grant_scoped_without_plaintext_export(clinical_db):
    c, i, p, patient, *_ = clinical_db
    u = patient.patient_id
    seeded(clinical_db)
    page = list_patients(c, i, p)
    assert any(item.patient_id == u for item in page.items)
    assert all(item.display_code and item.data_revision >= 1 for item in page.items)
    detail = patient_detail(c, i, p, u)
    assert detail.patient_id == u and detail.observation_count >= 1
    assert detail.next_action.startswith("review_observations")
    with pytest.raises(HTTPException) as unknown:
        patient_detail(c, i, p, uuid4())
    assert unknown.value.status_code == 404


def test_visit_list_and_filtered_observation_queries_are_snapshot_stable(clinical_db):
    c, i, p, patient, *_ = clinical_db
    u = patient.patient_id
    seeded(clinical_db)
    visits = list_visits(c, i, p, u)
    assert isinstance(visits.items, tuple)
    all_obs = query_observations(c, i, p, u, ObservationFilter())
    assert all_obs.items and all_obs.snapshot_cursor
    again = query_observations(c, i, p, u, ObservationFilter())
    assert again.snapshot_cursor == all_obs.snapshot_cursor
    assert {o.record_id for o in again.items} == {o.record_id for o in all_obs.items}
    kinds = {o.kind for o in all_obs.items}
    assert kinds
    filtered = query_observations(
        c, i, p, u, ObservationFilter(kind=next(iter(kinds)), limit=1)
    )
    assert len(filtered.items) == 1
    assert filtered.snapshot_cursor != all_obs.snapshot_cursor or len(all_obs.items) == 1
    with pytest.raises(Exception):
        query_observations(c, i, p, u, ObservationFilter(concept="x" * 121))


def test_diagnosis_is_source_backed_observation_without_parallel_store(clinical_db):
    c, i, p, patient, *_ = clinical_db
    u = patient.patient_id
    seeded(clinical_db)
    diagnosed = [o for o in query_observations(c, i, p, u, ObservationFilter(kind="diagnosis")).items]
    if not diagnosed:
        pytest.skip("fixture has no diagnosis observation")
    confirmed = create_source_diagnosis(c, i, p, u, diagnosed[0].record_id)
    assert confirmed["source_backed"] is True
    assert "no_parallel_store" in confirmed["next_action"]
    non_diagnosis = next(
        o for o in query_observations(c, i, p, u, ObservationFilter()).items if o.kind != "diagnosis"
    )
    with pytest.raises(HTTPException) as rejected:
        create_source_diagnosis(c, i, p, u, non_diagnosis.record_id)
    assert rejected.value.status_code == 422


def test_closure_http_patient_observation_visit_diagnosis_paths(clinical_db):
    c, i, p, patient, *_ = clinical_db
    u = patient.patient_id
    seeded(clinical_db)
    client, headers = http_session((c, i, p, None, None, None, keys()))
    with client:
        assert client.get(f"/api/v1/projects/{p}/patients").status_code == 401
        listed = client.get(f"/api/v1/projects/{p}/patients", headers=headers)
        assert listed.status_code == 200, listed.text
        assert listed.json()["items"]
        detail = client.get(f"/api/v1/projects/{p}/patients/{u}", headers=headers)
        assert detail.status_code == 200 and detail.json()["patient_id"] == str(u)
        queried = client.post(
            f"/api/v1/projects/{p}/patients/{u}/observation-queries", json={}, headers=headers
        )
        assert queried.status_code == 200, queried.text
        assert queried.json()["snapshot_cursor"]
        visits = client.get(f"/api/v1/projects/{p}/patients/{u}/visits", headers=headers)
        assert visits.status_code == 200, visits.text
        record_id = queried.json()["items"][0]["record_id"]
        exact = client.get(
            f"/api/v1/projects/{p}/patients/{u}/observations/{record_id}", headers=headers
        )
        assert exact.status_code == 200
        assert exact.headers["cache-control"] == "private, no-store"
        stranger = client.get(
            f"/api/v1/projects/{p}/patients/{uuid4()}", headers=headers
        )
        assert stranger.status_code in (403, 404)
