"""Deterministic trends over full private windows and actual mask-derived point references."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_clinical_ingestion import clinical_db, row, stage
from test_imaging_ingestion import http_session, imaging_db
from test_simulation_execution import publication_value
from test_simulation_runs import TEST
from test_source_registry import registry_db
from test_timeline_runs import prepared

from canceros.clinical_ingestion import BatchCommand, accept_batch
from canceros.identity import Identity
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.simulation_execution import publish_completion
from canceros.temporal_timeline import TimelineScope, TimelineWindow
from canceros.timeline_runs import TimelineQuery, query_timeline
from canceros.trend_runs import TrendQuery, query_trends

__all__ = ["registry_db", "imaging_db", "clinical_db"]


def test_actual_mask_pair_full_window_pagination_and_http(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    measurement, _, _, run, complete, timeline = prepared(imaging_db, geometry=True)
    publish_completion(
        c, i, p, u, complete.id, publication_value(run), storage, "trend-publish", TEST
    )
    page = query_timeline(c, i, p, u, timeline.model_copy(update={"limit": 100}))
    physical = [point for point in page.items if point.measurement_basis == "mask_realized"]
    value = TrendQuery(
        timeline=timeline, left_point_id=physical[0].id, right_point_id=physical[-1].id
    )
    report = query_trends(c, i, p, u, value)
    pair = report.comparison
    assert pair.status == "comparable" and pair.absolute_change == "-63"
    assert pair.percentage_change == "-98.4375" and pair.elapsed_days == "53"
    assert abs(Decimal(pair.slope_per_day) * 53 - Decimal(-63)) < Decimal("0.0000001")
    assert (
        pair.from_state_ids == physical[0].state_ids and pair.to_state_ids == physical[-1].state_ids
    )
    assert any(len(series.points) > timeline.limit for series in report.series)
    outside = query_trends(c, i, p, u, value.model_copy(update={"right_point_id": uuid4()}))
    assert (
        outside.comparison.status == "insufficient_data"
        and "POINT_OUTSIDE_WINDOW" in outside.comparison.reason_codes
    )
    cursor = query_timeline(c, i, p, u, timeline).next_cursor
    with pytest.raises(HTTPException):
        query_trends(
            c,
            i,
            p,
            u,
            value.model_copy(update={"timeline": timeline.model_copy(update={"cursor": cursor})}),
        )
    client, headers = http_session(imaging_db)
    path = f"/api/v1/projects/{p}/patients/{u}/trend-queries"
    with client:
        assert client.post(path, json=value.model_dump(mode="json")).status_code == 401
        response = client.post(path, json=value.model_dump(mode="json"), headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["comparison"]["absolute_change"] == "-63"
    withdraw_resource(c, i, p, u, measurement.id, WithdrawalInput(reason_code="rights_withdrawn"))
    with pytest.raises(HTTPException):
        query_trends(c, i, p, u, value)


def test_source_unit_conversion_uses_frozen_revision_and_rejects_cross_patient(clinical_db):
    c, i, p, patient, origin, _, storage = clinical_db
    u = patient.patient_id
    first = row(
        origin,
        client_record_key="trend-first",
        original_value="12.5",
        result={"form": "exact", "quantity": {"value": "12.5", "unit": "g/dL"}},
    )
    second = row(
        origin,
        client_record_key="trend-second",
        original_value="130",
        original_unit="g/L",
        result={"form": "exact", "quantity": {"value": "130", "unit": "g/L"}},
    )
    second["time"] = {
        "reference": {
            "basis": "relative_day",
            "value": "4",
            "time_domain": "simulation",
            "timeline_origin_id": str(origin),
        },
        "precision": "relative_day",
    }
    staged = stage(clinical_db, [first, second])
    accepted = accept_batch(
        c,
        i,
        p,
        u,
        BatchCommand(source_artifact_id=staged.artifact_id, expected_revision=1),
        "trend-source",
        storage,
    )
    timeline = TimelineQuery(
        window=TimelineWindow(
            scope=TimelineScope(mode="source_fixture", data_revision=2),
            knowledge_as_of=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )
    points = query_timeline(c, i, p, u, timeline).items
    points.sort(key=lambda point: Decimal(point.time.reference.value))
    report = query_trends(
        c,
        i,
        p,
        u,
        TrendQuery(timeline=timeline, left_point_id=points[0].id, right_point_id=points[1].id),
    )
    assert set(accepted.record_ids) == {point.id for point in points}
    assert report.comparison.status == "comparable" and report.comparison.unit == "g/dL"
    assert report.comparison.absolute_change == "0.5" and report.comparison.percentage_change == "4"
    assert report.comparison.slope_per_day == "0.125"
    first_page = query_timeline(c, i, p, u, timeline.model_copy(update={"limit": 1}))
    assert first_page.next_cursor is not None
    next_page = query_timeline(
        c,
        i,
        p,
        u,
        timeline.model_copy(update={"limit": 1, "cursor": first_page.next_cursor}),
    )
    assert {first_page.items[0].id, next_page.items[0].id} == set(accepted.record_ids)
    for actor, project, person in [
        (i, p, uuid4()),
        (i, uuid4(), u),
        (Identity(i.user_id, {p: "viewer"}), p, u),
    ]:
        with pytest.raises(HTTPException):
            query_trends(c, actor, project, person, TrendQuery(timeline=timeline))
    withdraw_resource(
        c, i, p, u, accepted.record_ids[0], WithdrawalInput(reason_code="rights_withdrawn")
    )
    with pytest.raises(HTTPException):
        query_timeline(
            c,
            i,
            p,
            u,
            timeline.model_copy(update={"limit": 1, "cursor": first_page.next_cursor}),
        )
