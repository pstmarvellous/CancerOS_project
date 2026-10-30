"""Owned frozen schedules, visible missingness and actual sampled geometry integration."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_imaging_ingestion import http_session, imaging_db
from test_scenario_geometry import queued
from test_simulation_runs import TEST, request
from test_source_registry import registry_db

from canceros.clinical_generation_runs import ClinicalGenerationInput, materialize_clinical
from canceros.simulation_contracts import SimulationConfig
from canceros.simulation_runs import (
    SaveConfigInput,
    preview_config_schedule,
    queue_run,
    read_run_geometry_targets,
    read_run_sampling,
    save_config,
)
from canceros.synthetic_geometry import GeometryInput, generate_geometry

__all__ = ["imaging_db", "registry_db"]


def sampled_run(data, missing_imaging=False, invalid_noise=False):
    c, i, p, patient, _, storage, _ = data
    branch, draft, _ = queued(data, mode="near_stable")
    value = draft.config.model_dump(mode="json")
    value["sampling"] = {
        "jitter_rules": [
            {"slot_id": "scan-1", "min_offset_days": "1", "max_offset_days": "1"},
            {"slot_id": "lab-1", "min_offset_days": "2.25", "max_offset_days": "2.25"},
        ],
        "noise_rules": [
            {
                "slot_id": "scan-1",
                "channel": "numerical_region_volume",
                "min_offset": "2",
                "max_offset": "2",
            }
        ]
        if invalid_noise
        else [],
        "missingness_rules": [
            {
                "slot_id": "scan-2" if missing_imaging else "lab-1",
                "channel": "numerical_region_volume" if missing_imaging else "hemoglobin",
                "probability": "1",
                "reason": "not_collected",
            }
        ],
    }
    changed = save_config(
        c,
        i,
        p,
        patient.patient_id,
        branch.id,
        SaveConfigInput(expected_draft_revision=1, config=SimulationConfig.model_validate(value)),
        storage,
        "sampling-config",
        TEST,
    )
    run = queue_run(
        c, i, p, patient.patient_id, branch.id, request(changed), storage, "sampling-run", TEST
    )
    return branch, changed, run


def test_schedule_preview_missing_lab_and_actual_jittered_geometry(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, draft, run = sampled_run(imaging_db)
    samples = read_run_sampling(c, i, p, u, run.id)
    assert preview_config_schedule(c, i, p, u, draft.id) == samples
    assert samples.tumor_targets[0].relative_day == "11"
    assert samples.clinical_values[0].relative_day == "12.25"
    assert samples.clinical_values[0].value is None
    assert samples.clinical_values[0].missing_reason == "not_collected"
    batch = materialize_clinical(
        c,
        i,
        p,
        u,
        ClinicalGenerationInput(run_id=run.id, expected_config_hash=run.config_hash),
        storage,
        "sampled-clinical",
        TEST,
    )
    assert batch.batch.events[0].value.kind == "missing"
    assert batch.batch.events[0].value.channel == "hemoglobin"
    assert batch.batch.sampling == samples and "not_collected" in batch.batch.notes[0].text
    geometry = generate_geometry(
        c,
        i,
        p,
        u,
        GeometryInput(run_id=run.id, baseline_hash=branch.baseline_hash, target_index=0),
        storage,
        "sampled-shape",
        TEST,
    )
    assert geometry.status == "ready" and geometry.geometry.time.value == "11"
    assert geometry.geometry.shape.target_mm3 == "24"
    assert run.config.schedule.slots[0].relative_day == "10"
    c.commit()
    client, headers = http_session(imaging_db)
    root = f"/api/v1/projects/{p}/patients/{u}"
    with client:
        assert client.get(root + f"/simulation-runs/{run.id}/sampling").status_code == 401
        response = client.get(
            root + f"/simulation-configs/{draft.id}/schedule-preview", headers=headers
        )
        assert response.status_code == 200 and response.json()["prng_version"] == "sha256-counter/1"
        assert (
            client.get(
                root.replace(str(u), str(uuid4())) + f"/simulation-runs/{run.id}/sampling",
                headers=headers,
            ).status_code
            == 404
        )


@pytest.mark.parametrize("missing", [True, False])
def test_missing_required_imaging_or_noise_erasing_family_blocks_geometry(imaging_db, missing):
    c, i, p, patient, _, storage, _ = imaging_db
    branch, _, run = sampled_run(imaging_db, missing_imaging=missing, invalid_noise=not missing)
    samples = read_run_sampling(c, i, p, patient.patient_id, run.id)
    assert (samples.tumor_targets[1].target_mm3 is None) == missing
    with pytest.raises(HTTPException) as blocked:
        read_run_geometry_targets(c, i, p, patient.patient_id, run.id)
    assert blocked.value.status_code == 409
    with pytest.raises(HTTPException):
        generate_geometry(
            c,
            i,
            p,
            patient.patient_id,
            GeometryInput(run_id=run.id, baseline_hash=branch.baseline_hash, target_index=0),
            storage,
            "blocked-shape",
            TEST,
        )
