"""Forecast request provenance and mandatory abstention through actual owned windows."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_imaging_ingestion import http_session, imaging_db
from test_simulation_execution import publication_value
from test_simulation_runs import TEST
from test_source_registry import registry_db
from test_timeline_runs import prepared

from canceros.evaluation_splits import SplitInput, freeze_split
from canceros.forecast_baselines import ForecastProtocol
from canceros.forecast_runs import ForecastQuery, query_forecast
from canceros.identity import Identity
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.simulation_execution import publish_completion
from canceros.timeline_runs import query_timeline
from canceros.twin_states import read_state

__all__ = ["imaging_db", "registry_db"]


def test_public_estimates_always_disabled_and_history_owned(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    measurement, _, _, run, complete, timeline = prepared(imaging_db)
    publish_completion(
        c, i, p, u, complete.id, publication_value(run), storage, "forecast-publish", TEST
    )
    final = max(
        (read_state(c, i, p, u, identifier).snapshot for identifier in complete.state_ids),
        key=lambda state: float(state.time.value),
    )
    timeline = timeline.model_copy(
        update={
            "window": timeline.window.model_copy(update={"event_cutoff": final.time}),
            "limit": 100,
        }
    )
    page = query_timeline(c, i, p, u, timeline)
    point = next(
        point
        for point in page.items
        if point.measurement_basis == "simulated_target_no_mask_realization"
    )
    protocol = ForecastProtocol(
        metric_code=point.concept,
        unit="mm3",
        method_version=point.method_version,
        metric_definition=point.metric_definition,
        lesion_id=point.lesion_id,
        supported_horizons=["5"],
    )
    query = ForecastQuery(timeline=timeline, protocol=protocol, method="locf", horizon_days="5")
    result = query_forecast(c, i, p, u, query)
    assert (
        result.status == "abstained" and result.estimate is None and result.exact_estimate is None
    )
    assert (
        not result.patient_facing_enabled and "REAL_EVALUATION_UNAVAILABLE" in result.reason_codes
    )
    assert set(result.point_ids) == {point.id for point in page.items}
    split = freeze_split(
        c, i, p, SplitInput(seed=0, assignments=[{"patient_id": u, "role": "test"}])
    )
    grouped = query_forecast(c, i, p, u, query.model_copy(update={"split_id": split.id}))
    assert (
        grouped.estimate is None
        and "INDEPENDENT_REAL_EVALUATION_NOT_CLEARED" in grouped.reason_codes
    )
    with pytest.raises(HTTPException):
        query_forecast(c, i, p, u, query.model_copy(update={"split_id": uuid4()}))
    assert (
        "UNSUPPORTED_HORIZON"
        in query_forecast(c, i, p, u, query.model_copy(update={"horizon_days": "9"})).reason_codes
    )
    client, headers = http_session(imaging_db)
    path = f"/api/v1/projects/{p}/patients/{u}/forecast-queries"
    with client:
        assert client.post(path, json=query.model_dump(mode="json")).status_code == 401
        response = client.post(path, json=query.model_dump(mode="json"), headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["estimate"] is None and response.json()["status"] == "abstained"
    for actor, project, person in [
        (i, p, uuid4()),
        (i, uuid4(), u),
        (Identity(i.user_id, {p: "viewer"}), p, u),
    ]:
        with pytest.raises(HTTPException):
            query_forecast(c, actor, project, person, query)
    withdraw_resource(c, i, p, u, measurement.id, WithdrawalInput(reason_code="rights_withdrawn"))
    with pytest.raises(HTTPException):
        query_forecast(c, i, p, u, query)
