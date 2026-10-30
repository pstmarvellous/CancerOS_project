"""Actual private timeline scopes, immutable pages and no hidden future observations."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from simulation_fixtures import setup_simulation_baseline
from sqlalchemy import text
from test_imaging_ingestion import http_session, imaging_db
from test_simulation_execution import command, freeze, publication_value
from test_simulation_runs import TEST
from test_source_registry import registry_db

from canceros.contracts import RelativeTime
from canceros.identity import Identity
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.persistence import capture_revision
from canceros.simulation_execution import complete_run, publish_completion
from canceros.temporal_timeline import TimelineScope, TimelineWindow
from canceros.timeline_runs import TimelineQuery, query_timeline

__all__ = ["imaging_db", "registry_db"]


def prepared(data, geometry=False):
    c, i, p, patient, _, storage, _ = data
    measurement, origin, _ = setup_simulation_baseline(data)
    branch, _, run = freeze(data, measurement, origin, "SC-01", geometry=geometry)
    complete = complete_run(
        c, i, p, patient.patient_id, command(run), storage, "timeline-complete", TEST
    )
    assert complete.status == "ready", complete
    window = TimelineWindow(
        scope=TimelineScope(mode="simulation", data_revision=1, branch_id=branch.id, run_id=run.id),
        knowledge_as_of=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    query = TimelineQuery(window=window, completion_id=complete.id, limit=2)
    return measurement, origin, branch, run, complete, query


def test_published_exact_membership_event_and_knowledge_cutoff_no_future_truth(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    _, origin, branch, run, complete, query = prepared(imaging_db)
    with pytest.raises(HTTPException):
        query_timeline(c, i, p, u, query)
    before = c.execute(text("SELECT clock_timestamp()")).scalar_one()
    publish_completion(
        c, i, p, u, complete.id, publication_value(run), storage, "timeline-publish", TEST
    )
    early = query.model_copy(
        update={"window": query.window.model_copy(update={"knowledge_as_of": before})}
    )
    assert query_timeline(c, i, p, u, early).total_points == 0
    cutoff = RelativeTime(
        basis="relative_day", value="19", time_domain="simulation", timeline_origin_id=origin
    )
    bounded = query.model_copy(
        update={"window": query.window.model_copy(update={"event_cutoff": cutoff}), "limit": 100}
    )
    page = query_timeline(c, i, p, u, bounded)
    assert page.total_points and all(
        float(point.time.reference.value) <= 19 for point in page.items
    )
    assert not any(
        point.measurement_basis == "simulated_target_no_mask_realization" for point in page.items
    )
    assert all(point.branch_id == branch.id and point.run_id == run.id for point in page.items)
    assert page.features.selected_point_ids == [point.id for point in page.items]
    assert all(point.origin.value == "SYNTHETIC_GENERATED" for point in page.items)
    observed = TimelineQuery(
        window=TimelineWindow(
            scope=TimelineScope(mode="observed", data_revision=1),
            knowledge_as_of=query.window.knowledge_as_of,
        )
    )
    assert query_timeline(c, i, p, u, observed).total_points == 0
    for changed in (
        query.model_copy(update={"completion_id": uuid4()}),
        query.model_copy(
            update={
                "window": query.window.model_copy(
                    update={"scope": query.window.scope.model_copy(update={"run_id": uuid4()})}
                )
            }
        ),
    ):
        with pytest.raises(HTTPException):
            query_timeline(c, i, p, u, changed)


def test_revision_pagination_scope_ownership_and_current_withdrawal(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    measurement, _, _, run, complete, query = prepared(imaging_db)
    publish_completion(
        c, i, p, u, complete.id, publication_value(run), storage, "timeline-pages-publish", TEST
    )
    first = query_timeline(c, i, p, u, query)
    assert first.next_cursor and len(first.items) == 2 and first.total_points > 2
    capture_revision(c, p, u, 2, {"members": [], "fixture_correction_after_cursor": True})
    c.execute(
        text("UPDATE source.research_patients SET data_revision=2 WHERE project_id=:p AND id=:u"),
        {"p": p, "u": u},
    )
    follow = query.model_copy(update={"cursor": first.next_cursor})
    second = query_timeline(c, i, p, u, follow)
    assert second.historical_revision and not (
        {point.id for point in first.items} & {point.id for point in second.items}
    )
    assert second.features == first.features and second.total_points == first.total_points
    with pytest.raises(HTTPException) as wrong_cursor:
        query_timeline(c, i, p, u, follow.model_copy(update={"limit": 3}))
    assert wrong_cursor.value.status_code == 409
    for actor, project, person in [
        (i, p, uuid4()),
        (i, uuid4(), u),
        (Identity(i.user_id, {p: "viewer"}), p, u),
    ]:
        with pytest.raises(HTTPException):
            query_timeline(c, actor, project, person, query)
    withdraw_resource(c, i, p, u, measurement.id, WithdrawalInput(reason_code="rights_withdrawn"))
    with pytest.raises(HTTPException) as restricted:
        query_timeline(c, i, p, u, follow)
    assert restricted.value.status_code == 409


def test_timeline_realized_geometry_ids_and_private_http(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    _, _, _, run, complete, query = prepared(imaging_db, geometry=True)
    publish_completion(
        c, i, p, u, complete.id, publication_value(run), storage, "timeline-geometry-publish", TEST
    )
    query = query.model_copy(update={"limit": 100})
    page = query_timeline(c, i, p, u, query)
    geometry = [point for point in page.items if point.measurement_basis == "mask_realized"]
    assert len(geometry) == 3 and {point.geometry_result_id for point in geometry} == set(
        complete.geometry_result_ids
    )
    assert [point.exact_value for point in geometry] == ["64", "8", "1"]
    assert all(point.state_ids and point.lesion_id for point in geometry)
    assert all(
        point.geometry_result_id is None for point in page.items if point.modality != "imaging"
    )
    client, headers = http_session(imaging_db)
    path = f"/api/v1/projects/{p}/patients/{u}/timeline-queries"
    with client:
        assert client.post(path, json=query.model_dump(mode="json")).status_code == 401
        response = client.post(path, json=query.model_dump(mode="json"), headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["features"]["version"] == "temporal-features/1"
