"""Event-time/knowledge-time windows retain ambiguity and never fill measurements."""

from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError
from test_clinical_generation import materialize, numeric

from canceros.clinical_contracts import ClinicalRecord, ClinicalTime
from canceros.contracts import Availability, Context, Provenance
from canceros.simulation_contracts import GeneratedMissing
from canceros.temporal_timeline import (
    TimelinePoint,
    TimelineScope,
    TimelineWindow,
    extract_features,
    from_clinical_record,
    from_generated_event,
    select_window,
)

PATIENT, BRANCH, RUN, ORIGIN = (UUID(int=i) for i in (1, 2, 3, 4))
KNOWN = datetime(2026, 10, 1, tzinfo=timezone.utc)
LATER = datetime(2026, 10, 5, tzinfo=timezone.utc)


def relative(day, origin=ORIGIN):
    return {
        "basis": "relative_day",
        "value": day,
        "time_domain": "simulation",
        "timeline_origin_id": origin,
    }


def point(identifier=10, day="0", **changes):
    values = dict(
        id=UUID(int=identifier),
        patient_id=PATIENT,
        time=ClinicalTime(reference=relative(day), precision="relative_day"),
        recorded_at=KNOWN,
        revision=1,
        origin=Provenance.SYNTHETIC_GENERATED,
        context=Context.SYNTHETIC,
        modality="laboratory",
        concept="hemoglobin",
        numeric_result={"form": "exact", "quantity": {"value": "12", "unit": "g/dL"}},
        availability=Availability.AVAILABLE,
        source_ids=[UUID(int=90)],
        source_hash="a" * 64,
        method_version="local-units/1",
        branch_id=BRANCH,
        run_id=RUN,
    )
    return TimelinePoint.model_validate({**values, **changes})


def window(day="30", **changes):
    values = dict(
        scope=TimelineScope(mode="simulation", branch_id=BRANCH, run_id=RUN, data_revision=2),
        event_cutoff=relative(day),
        knowledge_as_of=KNOWN,
    )
    return TimelineWindow.model_validate({**values, **changes})


def test_irregular_intervals_latest_age_and_missing_value_are_metadata_not_forward_fill():
    points = [
        point(day="0"),
        point(11, "7"),
        point(
            12,
            "21",
            numeric_result={"form": "missing", "missing_reason": "not_collected"},
            missing_reason="not_collected",
            availability=Availability.UNAVAILABLE,
        ),
    ]
    features = extract_features(points, window())
    assert len(features.series) == 1
    series = features.series[0]
    assert series.interval_days == ["7", "14"]
    assert series.usable_count == 2 and series.missing_count == 1
    assert series.latest_available_id == UUID(int=11) and series.age_days == "23"
    assert points[-1].numeric_result.form == "missing"
    assert not hasattr(series, "latest_value")


def test_event_cutoff_and_future_recorded_correction_are_both_filtered():
    old = point(day="5")
    future_event = point(11, "31")
    future_correction = point(12, "5", recorded_at=LATER, supersedes_id=old.id)
    assert [
        item.id for item in select_window([old, future_event, future_correction], window())
    ] == [old.id]
    assert future_correction.recorded_at == LATER


def test_unknown_and_incomparable_times_remain_visible_but_have_no_numeric_features():
    unknown = point(
        11,
        time=ClinicalTime(
            reference={
                "basis": "unknown",
                "time_domain": "simulation",
                "missing_reason": "not_recorded",
            },
            precision="unknown",
        ),
    )
    other_anchor = point(
        12, time=ClinicalTime(reference=relative("99", UUID(int=99)), precision="relative_day")
    )
    features = extract_features([point(), unknown, other_anchor], window())
    assert set(features.selected_point_ids) == {UUID(int=10), UUID(int=11), UUID(int=12)}
    assert set(features.unresolved_point_ids) == {unknown.id, other_anchor.id}
    assert len(features.series) == 1 and features.series[0].ordered_point_ids == [UUID(int=10)]


def test_same_time_conflicts_never_choose_arbitrary_id_as_latest():
    features = extract_features([point(), point(11, "10"), point(12, "10")], window())
    series = features.series[0]
    assert set(series.conflict_point_ids) == {UUID(int=11), UUID(int=12)}
    assert series.latest_available_id is None and series.age_days is None
    assert series.interval_days == ["10", "0"]


def test_censored_threshold_is_not_an_exact_value_and_method_or_metric_partitions_stay_separate():
    censored = point(
        11,
        "10",
        numeric_result={
            "form": "censored",
            "comparator": "<",
            "threshold": {"value": "1", "unit": "g/dL"},
        },
    )
    series = extract_features([point(), censored], window()).series[0]
    assert series.censored_count == 1 and series.usable_count == 1
    separate = point(12, "15", method_version="other/1", metric_definition="different_measurement")
    assert len(extract_features([point(), separate], window()).series) == 2
    with pytest.raises(ValidationError):
        TimelinePoint.model_validate({**censored.model_dump(), "exact_value": "1"})


def test_branch_run_context_and_revision_scopes_cannot_merge_histories():
    other_branch = point(11, branch_id=UUID(int=99))
    other_run = point(12, run_id=UUID(int=98))
    future_revision = point(13, revision=3)
    source_fixture = point(14, branch_id=None, run_id=None)
    selected = select_window(
        [point(), other_branch, other_run, future_revision, source_fixture], window()
    )
    assert [item.id for item in selected] == [UUID(int=10)]
    source = TimelineWindow(
        scope=TimelineScope(mode="source_fixture", data_revision=2), knowledge_as_of=KNOWN
    )
    assert select_window([point(), source_fixture], source) == [source_fixture]
    observed = TimelineWindow(
        scope=TimelineScope(mode="observed", data_revision=2), knowledge_as_of=KNOWN
    )
    assert select_window([point(), source_fixture], observed) == []


def test_mixed_patients_and_invalid_scope_fail_closed():
    with pytest.raises(ValueError, match="one authorized patient"):
        select_window([point(), point(11, patient_id=UUID(int=500))], window())
    with pytest.raises(ValidationError):
        TimelineScope(mode="simulation", data_revision=1, branch_id=BRANCH)
    with pytest.raises(ValidationError):
        point(origin=Provenance.SYNTHETIC_GENERATED, context=Context.OBSERVED)


def test_shifted_time_basis_and_calendar_date_timestamp_are_not_silently_converted():
    date_point = point(
        time=ClinicalTime(
            reference={"basis": "date", "value": "2020-01-02", "time_domain": "source_shifted"},
            precision="day",
            date_shift_basis="shift-policy-A",
        )
    )
    cutoff = {"basis": "date", "value": "2020-01-05", "time_domain": "source_shifted"}
    match = window(event_cutoff=cutoff, event_cutoff_shift_basis="shift-policy-A")
    features = extract_features([date_point], match)
    assert features.series[0].age_days == "3"
    incompatible = window(event_cutoff=cutoff, event_cutoff_shift_basis="shift-policy-B")
    assert extract_features([date_point], incompatible).unresolved_point_ids == [date_point.id]
    timestamp_cutoff = {
        "basis": "timestamp",
        "value": "2020-01-05T00:00:00Z",
        "time_domain": "source_shifted",
    }
    assert (
        extract_features(
            [date_point],
            window(event_cutoff=timestamp_cutoff, event_cutoff_shift_basis="shift-policy-A"),
        ).series
        == []
    )


def test_timestamp_nominal_interval_uses_offsets_without_inventing_calendar_dates():
    first = point(
        time=ClinicalTime(
            reference={
                "basis": "timestamp",
                "value": "2020-01-01T10:00:00+01:00",
                "time_domain": "source_calendar",
            },
            precision="second",
        )
    )
    second = point(
        11,
        time=ClinicalTime(
            reference={
                "basis": "timestamp",
                "value": "2020-01-02T09:00:00Z",
                "time_domain": "source_calendar",
            },
            precision="second",
        ),
    )
    features = extract_features(
        [first, second],
        window(
            event_cutoff={
                "basis": "timestamp",
                "value": "2020-01-03T09:00:00Z",
                "time_domain": "source_calendar",
            }
        ),
    )
    assert features.series[0].interval_days == ["1"] and features.series[0].age_days == "1"


def test_generated_factory_preserves_canonical_quantity_origin_and_actual_state_membership():
    request = numeric([("hemoglobin", "120", "g/L", "3")])
    event = materialize(request).events[0]
    converted = from_generated_event(
        event, PATIENT, KNOWN, 2, "b" * 64, timeline_origin_id=ORIGIN, state_ids=[UUID(int=50)]
    )
    assert converted.numeric_result.quantity.value == "12"
    assert converted.exact_value == "12" and converted.time.reference.value == "3"
    assert converted.branch_id == event.branch_id and converted.run_id == event.run_id
    assert converted.origin == Provenance.SYNTHETIC_GENERATED
    assert converted.state_ids == [UUID(int=50)]


def test_source_factory_preserves_source_time_qualifier_and_db_recorded_at():
    record = ClinicalRecord.model_validate(
        {
            "id": UUID(int=1),
            "project_id": UUID(int=2),
            "patient_id": PATIENT,
            "origin": "REAL_OBSERVED",
            "context": "OBSERVED",
            "quality": "pending",
            "availability": "available",
            "item": {
                "kind": "laboratory",
                "client_record_key": "lab",
                "source_locator_id": UUID(int=8),
                "time": {
                    "reference": {
                        "basis": "date",
                        "value": "2020-01-02",
                        "time_domain": "source_calendar",
                    },
                    "precision": "day",
                },
                "original_term": "hemoglobin",
                "certainty": "documented",
                "negation": "affirmed",
                "concept": "hemoglobin",
                "result": {
                    "form": "censored",
                    "comparator": "<",
                    "threshold": {"value": "1", "unit": "g/dL"},
                },
                "original_value": "<1",
                "original_unit": "g/dL",
            },
        }
    )
    converted = from_clinical_record(record, LATER, 3, "c" * 64, supersedes_id=UUID(int=77))
    assert converted.recorded_at == LATER and converted.supersedes_id == UUID(int=77)
    assert (
        converted.numeric_result.form == "censored" and converted.numeric_result.comparator == "<"
    )
    assert converted.exact_value is None and converted.time.precision == "day"
    assert converted.source_ids == [record.id, record.item.source_locator_id]


def test_exact_physical_calculation_is_retained_when_display_rounds_to_zero():
    tiny = point(
        concept="numerical_region_volume",
        modality="imaging",
        numeric_result={"form": "exact", "quantity": {"value": "0", "unit": "mm3"}},
        exact_value="0.00000000000001",
        metric_definition="functional_region_volume",
    )
    features = extract_features([tiny], window())
    assert features.series[0].usable_count == 1
    assert features.series[0].metric_definition == "functional_region_volume"
    assert tiny.exact_value == "0.00000000000001"


def test_generated_missing_dictionary_unit_is_metadata_and_preserves_same_series_gap():
    request = numeric([("hemoglobin", "12", "g/dL", "3")])
    event = materialize(request).events[0]
    missing = event.model_copy(
        update={
            "event_id": UUID(int=987),
            "relative_day": "7",
            "value": GeneratedMissing(kind="missing", reason="not_collected", channel="hemoglobin"),
        }
    )
    known_point = from_generated_event(
        event, PATIENT, KNOWN, 1, "a" * 64, timeline_origin_id=ORIGIN
    )
    gap = from_generated_event(missing, PATIENT, KNOWN, 1, "b" * 64, timeline_origin_id=ORIGIN)
    assert gap.canonical_unit == "g/dL" and gap.numeric_result is None
    scope = TimelineScope(
        mode="simulation", branch_id=event.branch_id, run_id=event.run_id, data_revision=1
    )
    features = extract_features([known_point, gap], window(scope=scope))
    assert len(features.series) == 1
    assert features.series[0].ordered_point_ids == [known_point.id, gap.id]
    assert features.series[0].unit == "g/dL" and features.series[0].missing_count == 1
