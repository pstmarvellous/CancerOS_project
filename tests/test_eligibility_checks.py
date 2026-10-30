"""Server-only evidence and current restrictions; fixture publication is not scientific approval."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_clinical_ingestion import row
from test_imaging_ingestion import http_session, imaging_db
from test_simulation_runs import TEST, inputs, request
from test_source_registry import registry_db
from test_twin_states import clinical

from canceros.eligibility_checks import EligibilityCheckInput, check_eligibility, read_eligibility
from canceros.identity import Identity
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.simulation_runs import SaveConfigInput, queue_run, save_config

__all__ = ["imaging_db", "registry_db"]


def saved(data):
    c, i, p, patient, _, storage, _ = data
    branch, config, origin = inputs(data)
    draft = save_config(
        c,
        i,
        p,
        patient.patient_id,
        branch.id,
        SaveConfigInput(expected_draft_revision=0, config=config),
        storage,
        "eligibility-config",
        TEST,
    )
    return branch, draft, origin


def codes(result):
    return {reason.code for reason in result.reasons}


def test_current_mask_capabilities_and_missing_real_baseline_remain_separate(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, draft, _ = saved(imaging_db)
    check = EligibilityCheckInput(config_id=draft.id)
    result = check_eligibility(c, i, p, u, check)
    assert result.result.status == "insufficient_data"
    assert "baseline_observed_baseline_verified_missing" in codes(result.result)
    assert "baseline_metric_valid_failed" not in codes(result.result)
    assert {branch.id, branch.input.baseline_measurement_id, draft.id} <= set(
        result.result.evidence_ids
    )
    anatomical = check_eligibility(
        c, i, p, u, check.model_copy(update={"capability": "anatomical_mesh"})
    )
    assert anatomical.result.status == "ineligible"
    assert "anatomical_annotation_not_eligible" in codes(anatomical.result)
    run = queue_run(c, i, p, u, branch.id, request(draft), storage, "pending-mock", TEST)
    assert run.eligibility.status == "insufficient_data" and run.publication == "draft"
    assert not run.baseline_observed_verified


def test_source_withdrawal_and_correction_are_new_audit_results(imaging_db):
    c, i, p, patient, _, _, _ = imaging_db
    u = patient.patient_id
    branch, draft, origin = saved(imaging_db)
    value = EligibilityCheckInput(config_id=draft.id)
    first = check_eligibility(c, i, p, u, value)
    clinical(imaging_db, origin, [row(origin)])
    changed = check_eligibility(c, i, p, u, value)
    assert "baseline_revision_current_failed" in codes(changed.result)
    assert changed.input_revision < changed.current_patient_revision
    withdraw_resource(c, i, p, u, branch.id, WithdrawalInput(reason_code="rights_withdrawn"))
    restricted = check_eligibility(c, i, p, u, value)
    assert "baseline_source_rights_allowed_failed" in codes(restricted.result)
    assert read_eligibility(c, i, p, u, first.id) == first


def test_auth_ownership_and_client_assertion_injection(imaging_db):
    c, i, p, patient, _, _, _ = imaging_db
    u = patient.patient_id
    _, draft, _ = saved(imaging_db)
    value = EligibilityCheckInput(config_id=draft.id)
    with pytest.raises(HTTPException) as viewer:
        check_eligibility(c, Identity(i.user_id, {p: "viewer"}), p, u, value)
    assert viewer.value.status_code == 403
    with pytest.raises(HTTPException):
        check_eligibility(c, i, p, uuid4(), value)
    client, headers = http_session(imaging_db)
    root = f"/api/v1/projects/{p}/patients/{u}/eligibility-checks"
    with client:
        assert client.post(root, json={"config_id": str(draft.id)}).status_code == 401
        assert (
            client.post(
                root,
                json={"config_id": str(draft.id), "observed_baseline_verified": True},
                headers=headers,
            ).status_code
            == 422
        )
        report = client.post(root, json={"config_id": str(draft.id)}, headers=headers)
        assert report.status_code == 201
        assert report.json()["result"]["status"] == "insufficient_data"
        assert client.get(report.headers["Location"], headers=headers).json() == report.json()
