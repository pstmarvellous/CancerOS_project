"""Immutable config/run snapshots against private fixtures, SQL ownership and real HTTP auth."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_clinical_ingestion import row
from test_imaging_ingestion import http_session, imaging_db
from test_simulation_contracts import configuration
from test_source_registry import registry_db
from test_twin_states import clinical, setup

from canceros.identity import Identity
from canceros.lineage import WithdrawalInput, derive_resource, processing_spec, withdraw_resource
from canceros.persistence import science_hash
from canceros.settings import Settings
from canceros.simulation_contracts import SimulationConfig
from canceros.simulation_runs import (
    QueueRunInput,
    SaveConfigInput,
    queue_run,
    read_config,
    read_run,
    save_config,
)

__all__ = ["registry_db", "imaging_db"]
TEST = Settings(mode="test", _env_file=None)


def inputs(data):
    c, _, p, patient, _, _, _ = data
    branch, _, _, origin = setup(data)
    value = configuration()
    value.update(
        branch_id=str(branch.id),
        baseline_hash=branch.baseline_hash,
        input_revision=c.execute(
            text(
                "SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"
            ),
            {"p": p, "u": patient.patient_id},
        ).scalar_one(),
    )
    return branch, SimulationConfig.model_validate(value), origin


def request(draft):
    return QueueRunInput(
        config_id=draft.id,
        expected_draft_revision=draft.draft_revision,
        expected_config_hash=draft.config_hash,
    )


def test_snapshots_reruns_draft_optimism_and_source_correction(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, config, origin = inputs(imaging_db)
    value = SaveConfigInput(expected_draft_revision=0, config=config)
    draft = save_config(c, i, p, u, branch.id, value, storage, "draft", TEST)
    assert save_config(c, i, p, u, branch.id, value, storage, "draft", TEST) == draft
    first = queue_run(c, i, p, u, branch.id, request(draft), storage, "run-one", TEST)
    second = queue_run(c, i, p, u, branch.id, request(draft), storage, "run-two", TEST)
    assert first.id != second.id and first.config == second.config
    assert first.environment.code_hash == second.environment.code_hash
    assert first.publication == "draft" and first.job_id is None
    assert first.authority == "isolated_test_mock" and not first.baseline_observed_verified
    changed = config.model_copy(update={"seed": 43})
    newer = save_config(
        c,
        i,
        p,
        u,
        branch.id,
        SaveConfigInput(expected_draft_revision=1, config=changed),
        storage,
        "draft-two",
        TEST,
    )
    assert newer.draft_revision == 2
    for action in (
        lambda: save_config(c, i, p, u, branch.id, value, storage, "stale-edit", TEST),
        lambda: queue_run(c, i, p, u, branch.id, request(draft), storage, "stale-queue", TEST),
    ):
        with pytest.raises(HTTPException) as stale:
            action()
        assert stale.value.status_code == 409
    imported = clinical(imaging_db, origin, [row(origin)])
    assert imported.result_revision == config.input_revision + 1
    assert read_run(c, i, p, u, first.id) == first
    assert queue_run(c, i, p, u, branch.id, request(draft), storage, "run-one", TEST) == first
    with pytest.raises(HTTPException):
        queue_run(c, i, p, u, branch.id, request(newer), storage, "stale-source", TEST)
    assert read_config(c, i, p, u, draft.id).config.seed == 42
    with pytest.raises(DBAPIError), c.begin_nested():
        c.execute(
            text("UPDATE imaging.simulation_runs SET report='{}'::jsonb WHERE id=:id"),
            {"id": first.id},
        )


def test_ownership_production_gate_hashes_and_withdrawal(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, config, _ = inputs(imaging_db)
    value = SaveConfigInput(expected_draft_revision=0, config=config)
    editor = Identity(i.user_id, {p: "editor"})
    with pytest.raises(HTTPException) as denied:
        save_config(c, editor, p, u, branch.id, value, storage, "editor", TEST)
    assert denied.value.status_code == 403
    with pytest.raises(HTTPException):
        save_config(c, i, p, uuid4(), branch.id, value, storage, "wrong-patient", TEST)
    with pytest.raises(HTTPException):
        save_config(
            c,
            i,
            p,
            u,
            branch.id,
            value.model_copy(
                update={"config": config.model_copy(update={"baseline_hash": "0" * 64})}
            ),
            storage,
            "bad-hash",
            TEST,
        )
    draft = save_config(c, i, p, u, branch.id, value, storage, "draft", TEST)
    with pytest.raises(HTTPException) as blocked:
        queue_run(
            c,
            i,
            p,
            u,
            branch.id,
            request(draft),
            storage,
            "production",
            Settings(mode="development", _env_file=None),
        )
    assert blocked.value.detail == "authentic_baseline_and_reviewed_policy_required"
    run = queue_run(c, i, p, u, branch.id, request(draft), storage, "run", TEST)
    withdraw_resource(c, i, p, u, branch.id, WithdrawalInput(reason_code="scientific_review"))
    assert read_run(c, i, p, u, run.id) == run
    with pytest.raises(HTTPException):
        queue_run(c, i, p, u, branch.id, request(draft), storage, "run", TEST)


def test_concurrent_draft_edits_have_one_winner(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    branch, config, _ = inputs(imaging_db)
    value = SaveConfigInput(expected_draft_revision=0, config=config)
    c.commit()

    def edit(key):
        try:
            with c.engine.begin() as connection:
                saved = save_config(
                    connection, i, p, patient.patient_id, branch.id, value, storage, key, TEST
                )
                return saved.draft_revision
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(edit, ["writer-one", "writer-two"])) == [1, 409]


def test_authenticated_configuration_and_run_http(imaging_db):
    c, _, p, patient, _, _, _ = imaging_db
    branch, config, _ = inputs(imaging_db)
    client, headers = http_session(imaging_db)
    root = f"/api/v1/projects/{p}/patients/{patient.patient_id}"
    with client:
        body = {"expected_draft_revision": 0, "config": config.model_dump(mode="json")}
        path = root + f"/branches/{branch.id}/simulation-configs"
        assert (
            client.post(path, json=body, headers={"Idempotency-Key": "unauthenticated"}).status_code
            == 401
        )
        saved = client.post(path, json=body, headers={**headers, "Idempotency-Key": "http-config"})
        assert saved.status_code == 201
        draft = saved.json()
        assert client.get(saved.headers["Location"], headers=headers).json() == draft
        payload = {
            "config_id": draft["id"],
            "expected_draft_revision": 1,
            "expected_config_hash": draft["config_hash"],
        }
        queued = client.post(
            root + f"/branches/{branch.id}/simulation-runs",
            json=payload,
            headers={**headers, "Idempotency-Key": "http-run"},
        )
        assert queued.status_code == 201
        assert queued.json()["readiness"] == "isolated_engineering_execution_available"
        assert client.get(queued.headers["Location"]).status_code == 401
        assert client.get(queued.headers["Location"], headers=headers).json() == queued.json()


def test_older_config_bytes_stay_pinned_after_optional_contract_extension(imaging_db):
    import json

    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, config, _ = inputs(imaging_db)
    draft = save_config(
        c,
        i,
        p,
        u,
        branch.id,
        SaveConfigInput(expected_draft_revision=0, config=config),
        storage,
        "current",
        TEST,
    )
    legacy = draft.model_dump(mode="json")
    legacy_id = uuid4()
    legacy.update(id=str(legacy_id), draft_revision=2)
    for field in ("category", "setting", "intent"):
        legacy["config"]["treatment"].pop(field)
    legacy["config"].pop("sc02_parameters")
    legacy["config_hash"] = science_hash(legacy["config"])
    c.execute(
        text(
            "INSERT INTO imaging.simulation_config_versions(id,project_id,patient_id,branch_id,actor_id,command_key,input_hash,report,report_hash,draft_revision) VALUES(:id,:p,:u,:b,:a,'legacy-fixture',:input_hash,CAST(:report AS jsonb),:hash,2)"
        ),
        {
            "id": legacy_id,
            "p": p,
            "u": u,
            "b": branch.id,
            "a": i.user_id,
            "hash": science_hash(legacy),
            "input_hash": science_hash({"expected_draft_revision": 1, "config": legacy["config"]}),
            "report": json.dumps(legacy),
        },
    )
    derive_resource(
        c,
        i,
        p,
        u,
        legacy_id,
        "simulation_config_versions",
        science_hash(legacy),
        [branch.id],
        processing_spec(__file__, "legacy-fixture/1", "simulation-config/1", {}),
    )
    old = read_config(c, i, p, u, legacy_id)
    assert old.config_hash == legacy["config_hash"]
    assert old.config.treatment.category == "no_specific_assumption"
    assert (
        save_config(
            c,
            i,
            p,
            u,
            branch.id,
            SaveConfigInput(expected_draft_revision=1, config=old.config),
            storage,
            "legacy-fixture",
            TEST,
        )
        == old
    )
    with pytest.raises(HTTPException):
        save_config(
            c,
            i,
            p,
            u,
            branch.id,
            SaveConfigInput(
                expected_draft_revision=1, config=old.config.model_copy(update={"seed": 99})
            ),
            storage,
            "legacy-fixture",
            TEST,
        )
    with pytest.raises(HTTPException) as changed:
        queue_run(c, i, p, u, branch.id, request(old), storage, "legacy-new-run", TEST)
    assert changed.value.detail == "configuration_schema_changed_create_new_draft_version"
    assert read_config(c, i, p, u, legacy_id).config_hash == old.config_hash
