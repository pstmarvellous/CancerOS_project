"""Frozen revision, knowledge-time correction recovery and current source restrictions."""

from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from test_clinical_ingestion import clinical_db, row, stage
from test_source_registry import registry_db

from canceros.clinical_ingestion import BatchCommand, RetractionInput, accept_batch, retract_record
from canceros.identity import Identity
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.temporal_timeline import TimelineScope, TimelineWindow
from canceros.timeline_source import load_source_points

__all__ = ["clinical_db", "registry_db"]


def accept(
    data,
    *,
    revision=1,
    previous=None,
    value="12.5",
    key="timeline-initial",
    logical_key="engineering-row-1",
):
    c, i, p, patient, origin, _, storage = data
    receipt = stage(
        data,
        [
            row(
                origin,
                client_record_key=logical_key,
                original_value=value,
                result={"form": "exact", "quantity": {"value": value, "unit": "g/dL"}},
            )
        ],
    )
    return accept_batch(
        c,
        i,
        p,
        patient.patient_id,
        BatchCommand(
            source_artifact_id=receipt.artifact_id,
            expected_revision=revision,
            corrects_record_id=previous,
        ),
        key,
        storage,
    ).record_ids[0]


def clock(c):
    return c.execute(text("SELECT clock_timestamp()")).scalar_one()


def window(revision, knowledge, mode="source_fixture"):
    return TimelineWindow(
        scope=TimelineScope(mode=mode, data_revision=revision),
        event_cutoff=None,
        knowledge_as_of=knowledge,
    )


def ids(points):
    return {identifier for point in points for identifier in point.source_ids}


def test_future_correction_and_retraction_recover_only_known_source_version(clinical_db):
    c, i, p, patient, _, _, _ = clinical_db
    u = patient.patient_id
    before = clock(c)
    original = accept(clinical_db)
    original_known = clock(c)
    corrected = accept(
        clinical_db, revision=2, previous=original, value="13.5", key="timeline-correction"
    )
    correction_known = clock(c)
    retract_record(
        c, i, p, u, corrected, RetractionInput(expected_revision=3, reason_code="entered_in_error")
    )
    retraction_known = clock(c)
    # The revision stays fixed at 4 while availability is reconstructed as of knowledge time.
    for cutoff, expected, absent in [
        (before, None, corrected),
        (original_known, original, corrected),
        (correction_known, corrected, original),
        (retraction_known, None, original),
    ]:
        points, restrictions = load_source_points(c, i, p, u, window(4, cutoff))
        assert not restrictions
        assert absent not in ids(points)
        if expected is None:
            assert not points
        else:
            assert len(points) == 1 and expected in ids(points)
            assert points[0].revision == 4
    # Historical revision 2 never acquires a later correction or later retraction.
    old, _ = load_source_points(c, i, p, u, window(2, retraction_known + timedelta(seconds=1)))
    assert original in ids(old) and corrected not in ids(old)


def test_source_fixture_never_becomes_observed_and_distinct_keys_remain_distinct(clinical_db):
    c, i, p, patient, _, _, _ = clinical_db
    first = accept(clinical_db)
    second = accept(
        clinical_db, revision=2, key="second-logical-key", logical_key="another-reading"
    )
    known = clock(c)
    fixture, _ = load_source_points(c, i, p, patient.patient_id, window(3, known))
    assert len(fixture) == 2 and {first, second} <= ids(fixture)
    observed, _ = load_source_points(c, i, p, patient.patient_id, window(3, known, "observed"))
    assert observed == []
    assert all(point.origin.value == "SYNTHETIC_GENERATED" for point in fixture)


def test_current_rights_and_patient_project_boundaries_apply_to_historical_source(clinical_db):
    c, i, p, patient, _, _, _ = clinical_db
    record = accept(clinical_db)
    selection = window(2, clock(c))
    for identity, project, patient_id in [
        (i, p, uuid4()),
        (i, uuid4(), patient.patient_id),
        (Identity(i.user_id, {p: "viewer"}), p, patient.patient_id),
    ]:
        with pytest.raises(HTTPException):
            load_source_points(c, identity, project, patient_id, selection)
    withdraw_resource(
        c, i, p, patient.patient_id, record, WithdrawalInput(reason_code="scientific_review")
    )
    points, restrictions = load_source_points(c, i, p, patient.patient_id, selection)
    assert not points and restrictions == ["current_source_access_restricted"]
