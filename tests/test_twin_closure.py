"""COS-069 closure: state manifest, comparison semantics, stale selection."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_clinical_ingestion import row
from test_imaging_ingestion import http_session, imaging_db
from test_patient_linkage import keys
from test_source_registry import registry_db
from test_twin_states import clinical as clinical_batch
from test_twin_states import setup as twin_setup
from test_twin_states import time as twin_time

from canceros.state_manifest import state_manifest
from canceros.trend_runs import TrendQuery, query_trends
from canceros.twin_states import (
    ClinicalMember,
    ImagingMember,
    StateBuildInput,
    build_state,
    freeze_state_inputs,
)

__all__ = ["imaging_db", "registry_db"]


def snapshot(data):
    c, i, p, patient, _, storage, _ = data
    u = patient.patient_id
    branch, association, measures, origin = twin_setup(data)
    imported = clinical_batch(data, origin, [row(origin)])
    value = StateBuildInput(
        target_revision=2,
        association_head=association.sequence,
        branch_id=branch.id,
        time=twin_time(origin),
        clinical_members=[ClinicalMember(record_id=imported.record_ids[0])],
        imaging_members=[
            ImagingMember(measurement_id=measures[0].id, association_event_id=association.id)
        ],
    )
    freeze_state_inputs(c, i, p, u, value, storage)
    return build_state(c, i, p, u, value, storage, "closure-state"), branch


def test_state_manifest_resolves_selected_state_artifacts_only(imaging_db):
    c, i, p, patient, _, _, _ = imaging_db
    built, branch = snapshot(imaging_db)
    manifest = state_manifest(c, i, p, patient.patient_id, built.id)
    assert manifest.snapshot_id == built.id
    assert manifest.selection_identity == f"{patient.patient_id}:{branch.id}:{built.id}"
    kinds = {a.kind for a in manifest.artifacts}
    assert "measurement" in kinds and "observation" in kinds
    assert all(a.next_action for a in manifest.artifacts)
    with pytest.raises(HTTPException) as stranger:
        state_manifest(c, i, p, uuid4(), built.id)
    assert stranger.value.status_code == 404


def test_comparison_semantics_reject_partial_pairs_and_wrong_scope(imaging_db):
    c, i, p, patient, _, _, _ = imaging_db
    built, _ = snapshot(imaging_db)
    known = datetime.now(timezone.utc).isoformat()
    window = {"scope": {"mode": "observed", "data_revision": 2}, "knowledge_as_of": known}
    with pytest.raises(Exception):
        query_trends(
            c, i, p, patient.patient_id,
            TrendQuery.model_validate(
                {"timeline": {"window": window}, "tolerance": "0", "left_point_id": built.id}
            ),
        )
    with pytest.raises(HTTPException):
        query_trends(
            c, i, p, uuid4(),
            TrendQuery.model_validate({"timeline": {"window": window}, "tolerance": "0"}),
        )


def test_closure_http_manifest_timeline_trend_paths(imaging_db):
    c, i, p, patient, _, _, _ = imaging_db
    built, _ = snapshot(imaging_db)
    client, headers = http_session((c, i, p, patient, None, None, keys()))
    root = f"/api/v1/projects/{p}/patients/{patient.patient_id}"
    with client:
        assert client.get(root + f"/states/{built.id}/manifest").status_code == 401
        manifest = client.get(root + f"/states/{built.id}/manifest", headers=headers)
        assert manifest.status_code == 200, manifest.text
        assert manifest.json()["snapshot_id"] == str(built.id)
        assert manifest.json()["selection_identity"].endswith(str(built.id))
        assert manifest.headers["cache-control"] == "private, no-store"
        timeline = client.post(
            root + "/timeline-queries",
            json={"window": {"scope": {"mode": "observed", "data_revision": 2}, "knowledge_as_of": "2026-01-01T00:00:00+00:00"}},
            headers=headers,
        )
        assert timeline.status_code in (200, 409), timeline.text
        denied = client.get(
            root + f"/states/{built.id}/manifest", headers={"Authorization": "Bearer invalid"}
        )
        assert denied.status_code in (401, 403, 404, 422)
