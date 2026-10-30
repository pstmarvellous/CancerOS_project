"""Exact state fusion reads and bounded historical comparisons over private fixtures."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_generated_clinical_states import generated
from test_imaging_ingestion import http_session, imaging_db
from test_simulation_execution import publication_value
from test_simulation_runs import TEST
from test_source_registry import registry_db
from test_timeline_runs import prepared

from canceros.fusion_runs import FusionQuery, query_fusion
from canceros.identity import Identity
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.persistence import canonical_bytes
from canceros.simulation_execution import publish_completion
from canceros.twin_states import build_state, read_state

__all__ = ["imaging_db", "registry_db"]


def test_exact_generated_membership_replay_http_scope_and_withdrawal(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    _, _, batch, events, value = generated(imaging_db)
    state = build_state(c, i, p, u, value, storage, "fusion-state")
    request = FusionQuery(state_id=state.id)
    before = canonical_bytes(read_state(c, i, p, u, state.id).snapshot.model_dump(mode="json"))
    report = query_fusion(c, i, p, u, request)
    assert report.canonical_state.snapshot.id == state.id
    assert {event.event_id for event in events} == {
        event.event_id
        for member in report.canonical_state.snapshot.generated_clinical_members
        for event in member.events
    }
    assert report == query_fusion(c, i, p, u, request)
    assert any("extract" in reason.lower() for block in report.blocks for reason in block.reasons)
    assert (
        canonical_bytes(read_state(c, i, p, u, state.id).snapshot.model_dump(mode="json")) == before
    )
    client, headers = http_session(imaging_db)
    path = f"/api/v1/projects/{p}/patients/{u}/fusion-queries"
    with client:
        assert client.post(path, json=request.model_dump(mode="json")).status_code == 401
        result = client.post(path, json=request.model_dump(mode="json"), headers=headers)
        assert result.status_code == 200, result.text
        assert result.json()["canonical_state"]["snapshot"]["id"] == str(state.id)
    for actor, project, person in [
        (i, p, uuid4()),
        (i, uuid4(), u),
        (Identity(i.user_id, {p: "viewer"}), p, u),
    ]:
        with pytest.raises(HTTPException):
            query_fusion(c, actor, project, person, request)
    withdraw_resource(c, i, p, u, batch.id, WithdrawalInput(reason_code="rights_withdrawn"))
    with pytest.raises(HTTPException):
        query_fusion(c, i, p, u, request)


def test_comparisons_end_at_selected_state_never_future_visits(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    _, _, _, run, completion, query = prepared(imaging_db)
    publish_completion(
        c, i, p, u, completion.id, publication_value(run), storage, "fusion-publish", TEST
    )
    states = [read_state(c, i, p, u, identifier).snapshot for identifier in completion.state_ids]
    target_day = [
        slot.relative_day for slot in run.config.schedule.slots if slot.modality == "imaging"
    ][1]
    target = next(state for state in states if state.time.value == target_day)
    report = query_fusion(c, i, p, u, FusionQuery(state_id=target.id, timeline=query))
    assert report.temporal_changes
    assert all(target.id in comparison.to_state_ids for comparison in report.temporal_changes)
    assert not any(
        state.id in comparison.from_state_ids
        for state in states
        if float(state.time.value) > float(target.time.value)
        for comparison in report.temporal_changes
    )
    assert report.canonical_state.snapshot == target
    outside = query.model_copy(
        update={
            "window": query.window.model_copy(
                update={"scope": query.window.scope.model_copy(update={"branch_id": uuid4()})}
            )
        }
    )
    with pytest.raises(HTTPException):
        query_fusion(c, i, p, u, FusionQuery(state_id=target.id, timeline=outside))
    early = query.model_copy(
        update={
            "window": query.window.model_copy(
                update={"knowledge_as_of": datetime(2000, 1, 1, tzinfo=timezone.utc)}
            )
        }
    )
    with pytest.raises(HTTPException):
        query_fusion(c, i, p, u, FusionQuery(state_id=target.id, timeline=early))
