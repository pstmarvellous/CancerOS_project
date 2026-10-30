"""Generated state members stay scoped to a frozen run, batch and actual visit."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from test_clinical_generation_runs import counts
from test_imaging_ingestion import imaging_db
from test_scenario_geometry import queued
from test_simulation_runs import TEST
from test_source_registry import registry_db
from test_twin_states import time

from canceros.clinical_generation_runs import ClinicalGenerationInput, materialize_clinical
from canceros.identity import Identity
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.persistence import science_hash
from canceros.twin_states import (
    GeneratedClinicalMember,
    PublishInput,
    ReviewInput,
    StateBuildInput,
    build_state,
    create_branch,
    freeze_state_inputs,
    publish_state,
    read_state,
    review_state,
)

__all__ = ["imaging_db", "registry_db"]


def generated(data):
    c, i, p, patient, _, storage, _ = data
    branch, _, run = queued(data, mode="near_stable", deterioration="stable")
    batch = materialize_clinical(
        c,
        i,
        p,
        patient.patient_id,
        ClinicalGenerationInput(run_id=run.id, expected_config_hash=run.config_hash),
        storage,
        "state-clinical",
        TEST,
    )
    selected = [event for event in batch.batch.events if event.relative_day == "10"]
    assert selected
    value = StateBuildInput(
        target_revision=run.input_revision,
        association_head=run.association_head,
        branch_id=branch.id,
        time=time(branch.input.timeline_origin_id, "10"),
        generated_clinical_members=[
            GeneratedClinicalMember(
                batch_id=batch.id,
                event_ids=[event.event_id for event in selected],
            )
        ],
    )
    return branch, run, batch, selected, value


def test_exact_generated_visit_lineage_source_preservation_and_private_publication_guard(
    imaging_db,
):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, run, batch, selected, value = generated(imaging_db)
    before = counts(c, p, u)
    assert batch.id in freeze_state_inputs(c, i, p, u, value, storage)
    snapshot = build_state(c, i, p, u, value, storage, "generated-state")
    assert build_state(c, i, p, u, value, storage, "generated-state") == snapshot
    member = snapshot.generated_clinical_members[0]
    assert member.batch_id == batch.id and member.run_id == run.id
    assert member.events == selected and len(member.events) < len(batch.batch.events)
    assert member.source_hash == science_hash(batch.model_dump(mode="json"))
    assert not snapshot.clinical_members and not snapshot.imaging_members
    assert "clinical_not_available_at_this_visit" not in snapshot.missing
    assert "imaging_not_available_at_this_visit" in snapshot.missing
    assert counts(c, p, u) == before
    view = read_state(c, i, p, u, snapshot.id)
    review = review_state(
        c,
        i,
        p,
        u,
        snapshot.id,
        ReviewInput(
            snapshot_hash=view.snapshot_hash,
            decision="accepted_engineering",
            evidence_sha256="a" * 64,
        ),
        "generated-review",
    )
    assert "publish_private_fixture" not in read_state(c, i, p, u, snapshot.id).available_actions
    with pytest.raises(HTTPException) as blocked:
        publish_state(
            c,
            i,
            p,
            u,
            snapshot.id,
            PublishInput(
                snapshot_hash=view.snapshot_hash,
                expected_patient_revision=run.input_revision,
                expected_association_head=run.association_head,
                expected_review_id=review.id,
            ),
            "individual-generated-publication",
        )
    assert (
        blocked.value.detail == "common_run_requires_complete_validation_and_separate_publication"
    )
    assert snapshot.branch_id == branch.id


def test_generated_event_time_branch_membership_and_ownership_are_not_inferred(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, _, batch, selected, value = generated(imaging_db)
    other_branch = create_branch(c, i, p, u, branch.input, storage, "other-generated-branch")
    invalid = [
        value.model_copy(update={"time": time(branch.input.timeline_origin_id, "11")}),
        value.model_copy(update={"time": time(uuid4(), "10")}),
        value.model_copy(update={"branch_id": other_branch.id}),
        value.model_copy(update={"target_revision": value.target_revision + 1}),
        value.model_copy(
            update={
                "generated_clinical_members": [
                    GeneratedClinicalMember(
                        batch_id=batch.id,
                        event_ids=[uuid4()],
                    )
                ]
            }
        ),
        value.model_copy(
            update={
                "generated_clinical_members": [
                    GeneratedClinicalMember(
                        batch_id=batch.id,
                        event_ids=[
                            selected[0].event_id,
                            next(e.event_id for e in batch.batch.events if e.relative_day == "20"),
                        ],
                    )
                ]
            }
        ),
    ]
    for index, attempt in enumerate(invalid):
        with pytest.raises(HTTPException):
            build_state(c, i, p, u, attempt, storage, f"invalid-{index}")
    for identity, patient_id in [(Identity(i.user_id, {p: "viewer"}), u), (i, uuid4())]:
        with pytest.raises(HTTPException):
            build_state(c, identity, p, patient_id, value, storage, "wrong-owner")
    with pytest.raises(ValidationError):
        GeneratedClinicalMember(batch_id=batch.id, event_ids=[selected[0].event_id] * 2)


def test_generated_history_frozen_and_inherited_rights_rechecked(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    _, run, _, _, value = generated(imaging_db)
    snapshot = build_state(c, i, p, u, value, storage, "immutable-generated")
    before = read_state(c, i, p, u, snapshot.id)
    withdraw_resource(c, i, p, u, run.id, WithdrawalInput(reason_code="scientific_review"))
    after = read_state(c, i, p, u, snapshot.id)
    assert after.snapshot == before.snapshot and after.snapshot_hash == before.snapshot_hash
    assert not after.current_use_allowed and after.restrictions
    with pytest.raises(HTTPException):
        build_state(c, i, p, u, value, storage, "immutable-generated")
