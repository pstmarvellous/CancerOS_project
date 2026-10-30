"""Exact computed context, source disagreement and independent hypothetical dimensions."""

from uuid import UUID

import numpy as np
import pytest

from canceros.clinical_contracts import ClinicalRecord, ClinicalTime
from canceros.contracts import RelativeTime
from canceros.imaging_geometry import canonical_geometry
from canceros.measurement_runs import MeasurementReport
from canceros.persistence import science_hash
from canceros.physical_measurements import measure_region
from canceros.state_fusion import GroundedNoteAssertion, fuse_state
from canceros.temporal_trends import PointComparison
from canceros.twin_states import SnapshotReport, StateView

PATIENT, BRANCH, ORIGIN, PROJECT, STATE, RUN = (UUID(int=n) for n in range(1, 7))


def time(day="10"):
    return RelativeTime(
        basis="relative_day", value=day, time_domain="simulation", timeline_origin_id=ORIGIN
    )


def clinical(
    identifier=20, role="current", day="10", value="12", unit="g/dL", kind="laboratory", **changes
):
    item = dict(
        kind=kind,
        concept="hemoglobin",
        client_record_key=str(identifier),
        source_locator_id=UUID(int=100),
        time=ClinicalTime(reference=time(day), precision="relative_day"),
        original_term="Artificial fixture",
        certainty="documented",
        negation="affirmed",
    )
    if kind == "note":
        item.update(
            concept="source_note", artifact_id=UUID(int=150), content_sha256="c" * 64, language="en"
        )
    else:
        item.update(
            result={"form": "exact", "quantity": {"value": value, "unit": unit}},
            original_value=value,
            original_unit=unit,
        )
    record = ClinicalRecord.model_validate(
        dict(
            id=UUID(int=identifier),
            project_id=PROJECT,
            patient_id=PATIENT,
            item=item,
            origin="SYNTHETIC_GENERATED",
            context="SYNTHETIC",
            quality=changes.pop("quality", "pass"),
            availability="available",
            **changes,
        )
    )
    return dict(
        membership={"record_id": record.id, "role": role},
        record=record,
        source_hash=science_hash(record.model_dump(mode="json")),
    )


def imaging(day="10", role="current"):
    mask = np.ones((2, 2, 2), dtype=np.uint8)
    measurement = MeasurementReport(
        id=UUID(int=30),
        input_revision=1,
        selections=[],
        definition="numerical_region_volume",
        values=measure_region(mask, canonical_geometry(mask.shape, np.eye(4))),
        geometry_sha256="d" * 64,
        source_time_basis="not_recorded",
        eligibility_blocks=[],
        next_action="Review scientific meaning",
    )
    return dict(
        membership={"measurement_id": measurement.id, "role": role},
        time=time(day),
        measurement=measurement,
        source_hash=science_hash(measurement.model_dump(mode="json")),
        association=None,
        mesh_qc=None,
    )


def view(clinical_members=None, imaging_members=None, generated_clinical_members=None, **changes):
    snapshot = SnapshotReport.model_validate(
        dict(
            id=STATE,
            patient_id=PATIENT,
            branch_id=BRANCH,
            time=time(),
            input_revision=1,
            patient_event_head=0,
            request_manifest_hash="a" * 64,
            revision_manifest_hash="b" * 64,
            baseline_hash="e" * 64,
            clinical_members=clinical_members or [],
            imaging_members=imaging_members or [],
            generated_clinical_members=generated_clinical_members or [],
            missing=[],
            conflicts=[],
            status="ready_partial",
            technical_readiness="ready",
            next_action="Review engineering state",
        )
    )
    return StateView(
        snapshot=snapshot,
        snapshot_hash=science_hash(snapshot.model_dump(mode="json")),
        stale=False,
        current_use_allowed=False,
        restrictions=[],
        review=None,
        publication=None,
        available_actions=[],
        next_action="Review",
        **changes,
    )


def assertion(state, **changes):
    note = next(
        member for member in state.snapshot.clinical_members if member.record.item.kind == "note"
    )
    return GroundedNoteAssertion.model_validate(
        dict(
            id=UUID(int=60),
            patient_id=PATIENT,
            branch_id=BRANCH,
            note_record_id=note.record.id,
            note_source_hash=note.source_hash,
            note_content_sha256="c" * 64,
            target_member_id=UUID(int=20),
            concept="hemoglobin",
            modality="laboratory",
            time=ClinicalTime(reference=time(), precision="relative_day"),
            result={"form": "exact", "quantity": {"value": "9", "unit": "g/dL"}},
            excerpt="Artificial unverified assertion",
            origin="SYNTHETIC_GENERATED",
            context="SYNTHETIC",
            **changes,
        )
    )


def categories(report):
    return {finding.category for finding in report.conflicts}


def comparison(concept="numerical_region_volume", **changes):
    return PointComparison.model_validate(
        dict(
            status="comparable",
            left_point_id=UUID(int=70),
            right_point_id=UUID(int=71),
            from_state_ids=[UUID(int=72)],
            to_state_ids=[STATE],
            concept=concept,
            origin="SYNTHETIC_GENERATED",
            context="SYNTHETIC",
            comparison_context="within_simulation",
            change="decreased",
            reason_codes=[],
            description="Configured region volume decreased",
            **changes,
        )
    )


def test_imaging_only_preserves_exact_measurement_meaning_and_absent_services():
    selected = view(imaging_members=[imaging()])
    report = fuse_state(selected)
    assert report.canonical_state == selected
    assert report.available_modalities == ["imaging"]
    assert report.tumor_state[0].exact_value == "8"
    assert report.tumor_state[0].metric_definition == "numerical_region_volume"
    assert not report.clinical_indicators and not report.treatment_history
    missing = next(block for block in report.blocks if block.title == "Missing")
    assert "source_note_extraction_unavailable" in missing.reasons
    assert "retrieved_evidence_unavailable" in missing.reasons
    assert all(block.next_action for block in report.blocks)
    assert {block.title for block in report.blocks} == {
        "Available",
        "Historical",
        "Missing",
        "Conflicting",
    }


def test_lab_only_does_not_supplement_missing_imaging_or_infer_clinical_condition():
    report = fuse_state(view(clinical_members=[clinical()]))
    assert report.available_modalities == ["laboratory"]
    assert not report.tumor_state
    member = report.clinical_indicators[0]
    assert (
        member.numeric_result.quantity.value == "12"
        and member.numeric_result.quantity.unit == "g/dL"
    )
    assert "scientific_review:pending" in member.uncertainty
    assert member.primary_for_display
    assert not report.temporal_changes


def test_historical_imaging_never_becomes_current_and_stale_state_is_explicit():
    selected = view(
        clinical_members=[clinical()], imaging_members=[imaging("0", "historical_context")]
    )
    selected = selected.model_copy(
        update={"stale": True, "restrictions": ["patient_revision_changed"]}
    )
    report = fuse_state(selected)
    assert report.tumor_state[0].role == "historical_context"
    available, historical, missing, _ = report.blocks
    assert UUID(int=30) not in available.member_ids and UUID(int=30) in historical.member_ids
    assert "patient_revision_changed" in historical.reasons
    assert "imaging_not_selected_as_current" in missing.reasons
    assert report.canonical_state.snapshot.input_revision == 1


def test_current_time_mismatch_blocks_primary_and_retains_original_time():
    report = fuse_state(view(clinical_members=[clinical(day="9")]))
    assert "DATE_MISMATCH" in categories(report)
    assert not report.clinical_indicators[0].primary_for_display
    assert report.clinical_indicators[0].time.reference.value == "9"


def test_two_structured_conflicting_values_remain_and_neither_is_primary():
    report = fuse_state(view(clinical_members=[clinical(), clinical(21, value="13")]))
    assert "INCONSISTENT_VALUES" in categories(report)
    assert len(report.clinical_indicators) == 2
    assert not any(member.primary_for_display for member in report.clinical_indicators)
    assert [member.exact_value for member in report.clinical_indicators] == ["12", "13"]


def test_adopted_unit_conversion_does_not_create_false_disagreement():
    report = fuse_state(view(clinical_members=[clinical(), clinical(21, value="120", unit="g/L")]))
    assert "INCONSISTENT_VALUES" not in categories(report)
    assert "INCONSISTENT_UNITS" not in categories(report)
    assert report.canonical_state.snapshot.clinical_members[1].record.item.original_unit == "g/L"


def test_distinct_source_times_are_not_averaged_or_reported_as_same_time_conflict():
    report = fuse_state(
        view(
            clinical_members=[
                clinical(),
                clinical(21, role="historical_context", day="0", value="13"),
            ]
        )
    )
    assert "INCONSISTENT_VALUES" not in categories(report)
    assert len(report.clinical_indicators) == 2


def test_unverified_note_conflict_retains_assertion_and_verified_structured_display_priority():
    selected = view(clinical_members=[clinical(), clinical(22, kind="note")])
    note = assertion(selected)
    report = fuse_state(selected, note_assertions=[note])
    finding = next(f for f in report.conflicts if f.category == "INCONSISTENT_VALUES")
    assert finding.primary_member_id == UUID(int=20)
    assert report.note_assertions == [note]
    assert report.clinical_indicators[0].exact_value == "12"
    assert report.clinical_indicators[0].primary_for_display
    assert "scientific_review:pending" in report.clinical_indicators[0].uncertainty


@pytest.mark.parametrize(
    "field,value,category",
    [
        (
            "result",
            {"form": "exact", "quantity": {"value": "12", "unit": "kg"}},
            "INCONSISTENT_UNITS",
        ),
        ("time", ClinicalTime(reference=time("9"), precision="relative_day"), "DATE_MISMATCH"),
        ("concept", "weight", "SOURCE_AMBIGUITY"),
        ("modality", "imaging", "INCOMPATIBLE_MODALITIES"),
        ("result", {"form": "missing", "missing_reason": "not_recorded"}, "INSUFFICIENT_DATA"),
    ],
)
def test_note_conflict_categories_are_explicit(field, value, category):
    selected = view(clinical_members=[clinical(), clinical(22, kind="note")])
    note = GroundedNoteAssertion.model_validate({**assertion(selected).model_dump(), field: value})
    assert category in categories(fuse_state(selected, note_assertions=[note]))


@pytest.mark.parametrize(
    "field,value",
    [
        ("patient_id", UUID(int=999)),
        ("branch_id", UUID(int=999)),
        ("note_source_hash", "f" * 64),
        ("note_content_sha256", "f" * 64),
        ("note_record_id", UUID(int=999)),
        ("target_member_id", UUID(int=999)),
        ("origin", "REAL_OBSERVED"),
        ("context", "OBSERVED"),
    ],
)
def test_assertion_requires_exact_patient_branch_note_hash_and_target_membership(field, value):
    selected = view(clinical_members=[clinical(), clinical(22, kind="note")])
    note = assertion(selected).model_copy(update={field: value})
    with pytest.raises(ValueError, match="fusion_note_assertion_membership_mismatch"):
        fuse_state(selected, note_assertions=[note])


def test_cross_patient_or_observed_clinical_member_is_rejected():
    selected = view(clinical_members=[clinical()])
    member = selected.snapshot.clinical_members[0]
    for record in [
        member.record.model_copy(update={"patient_id": UUID(int=999)}),
        member.record.model_copy(update={"origin": "REAL_OBSERVED", "context": "OBSERVED"}),
    ]:
        changed = selected.model_copy(
            update={
                "snapshot": selected.snapshot.model_copy(
                    update={"clinical_members": [member.model_copy(update={"record": record})]}
                )
            }
        )
        with pytest.raises(
            ValueError, match="fusion_(clinical_membership|member_context)_mismatch"
        ):
            fuse_state(changed)


def test_simultaneous_tumor_reduction_and_increasing_symptom_direction_remain_independent():
    event = dict(
        event_id=UUID(int=40),
        branch_id=BRANCH,
        run_id=RUN,
        slot_id="symptom10",
        relative_day="10",
        modality="symptom",
        value={
            "kind": "symptom",
            "concept": "fatigue",
            "rating": 6,
            "presence": "present",
            "negation": "affirmed",
            "resolution_status": "present",
        },
    )
    selected = view(
        imaging_members=[imaging()],
        generated_clinical_members=[
            dict(batch_id=UUID(int=41), run_id=RUN, events=[event], source_hash="b" * 64)
        ],
    )
    tumor = comparison()
    symptom = comparison("fatigue").model_copy(
        update={
            "change": "ordinal_direction",
            "ordinal_direction": "increased",
            "description": "Configured fatigue rating increased; no clinical grade inferred",
        }
    )
    report = fuse_state(selected, [tumor, symptom])
    assert report.tumor_state[0].exact_value == "8"
    assert report.clinical_indicators[0].ordinal_value == "6"
    assert report.temporal_changes == [tumor, symptom]
    assert all(change.percentage_change is None for change in report.temporal_changes)
    assert not hasattr(report, "health_score")


@pytest.mark.parametrize(
    "changes", [{"to_state_ids": []}, {"context": "OBSERVED"}, {"origin": "REAL_DERIVED"}]
)
def test_comparison_requires_selected_endpoint_and_synthetic_context(changes):
    with pytest.raises(ValueError, match="fusion_comparison_membership_mismatch"):
        fuse_state(view(imaging_members=[imaging()]), [comparison().model_copy(update=changes)])


def test_exact_revision_membership_replay_and_no_input_mutation():
    selected = view(clinical_members=[clinical()], imaging_members=[imaging()])
    original = selected.model_dump_json()
    report = fuse_state(selected)
    assert fuse_state(selected).model_dump_json() == report.model_dump_json()
    assert selected.model_dump_json() == original
    assert report.canonical_state.snapshot_hash == selected.snapshot_hash
    assert report.canonical_state.snapshot.assembly_policy_version == "exact-membership/1"
    assert (
        report.canonical_state.snapshot.clinical_members[0].source_hash
        == selected.snapshot.clinical_members[0].source_hash
    )


def test_unavailable_measurement_remains_missing_and_not_in_available_modalities():
    selected = view(imaging_members=[imaging()])
    member = selected.snapshot.imaging_members[0]
    measurement = member.measurement.model_copy(
        update={"values": measure_region(None, canonical_geometry((2, 2, 2), np.eye(4)))}
    )
    selected = selected.model_copy(
        update={
            "snapshot": selected.snapshot.model_copy(
                update={"imaging_members": [member.model_copy(update={"measurement": measurement})]}
            )
        }
    )
    report = fuse_state(selected)
    assert report.tumor_state[0].availability == "unavailable"
    assert report.tumor_state[0].numeric_result is None
    assert report.available_modalities == []
    assert not report.blocks[0].member_ids
    assert "numerical_region_volume:unavailable" in report.blocks[2].reasons
    assert "imaging_not_selected_as_current" in report.blocks[2].reasons


def test_generated_explicit_missing_event_is_retained_without_a_scalar_or_primary_value():
    event = dict(
        event_id=UUID(int=40),
        branch_id=BRANCH,
        run_id=RUN,
        slot_id="missing10",
        relative_day="10",
        modality="laboratory",
        value={"kind": "missing", "reason": "not_collected", "channel": "hemoglobin"},
    )
    selected = view(
        generated_clinical_members=[
            dict(batch_id=UUID(int=41), run_id=RUN, events=[event], source_hash="b" * 64)
        ]
    )
    report = fuse_state(selected)
    member = report.clinical_indicators[0]
    assert member.availability == "unavailable" and not member.primary_for_display
    assert member.exact_value is None and member.numeric_result.form == "missing"
    assert not report.available_modalities and not report.blocks[0].member_ids
    assert "hemoglobin:not_collected" in report.blocks[2].reasons


def test_unverified_structured_record_does_not_gain_display_priority_over_note_assertion():
    selected = view(clinical_members=[clinical(quality="pending"), clinical(22, kind="note")])
    report = fuse_state(selected, note_assertions=[assertion(selected)])
    finding = next(f for f in report.conflicts if f.category == "INCONSISTENT_VALUES")
    assert finding.primary_member_id is None
    assert not report.clinical_indicators[0].primary_for_display


def test_shifted_imaging_time_without_shift_basis_retains_original_and_explicit_unknown():
    selected = view(imaging_members=[imaging("0", "historical_context")])
    member = selected.snapshot.imaging_members[0]
    # Shifted dates cannot be converted to a simulation anchor or given fabricated midnight.
    from canceros.contracts import DateTimeReference

    shifted = DateTimeReference(basis="date", value="2026-01-02", time_domain="source_shifted")
    selected = selected.model_copy(
        update={
            "snapshot": selected.snapshot.model_copy(
                update={"imaging_members": [member.model_copy(update={"time": shifted})]}
            )
        }
    )
    report = fuse_state(selected)
    projected = report.tumor_state[0]
    assert projected.original_time == shifted
    assert projected.time is None
    assert not projected.primary_for_display
    assert "SOURCE_AMBIGUITY" in categories(report)


def test_tiny_physical_measurement_conflicts_use_exact_value_instead_of_rounded_display_zero():
    selected = view(clinical_members=[clinical(22, kind="note")], imaging_members=[imaging()])
    member = selected.snapshot.imaging_members[0]
    # Contract-boundary fixture: the fusion projection must never replace exact arithmetic
    # by display rounding, including values below the present imaging import resolution.
    values = member.measurement.values.model_copy(
        update={
            "volume_mm3": "0",
            "exact_volume_mm3": "0.000000000008",
        }
    )
    assert values.volume_mm3 == "0" and values.exact_volume_mm3 == "0.000000000008"
    selected = selected.model_copy(
        update={
            "snapshot": selected.snapshot.model_copy(
                update={
                    "imaging_members": [
                        member.model_copy(
                            update={
                                "measurement": member.measurement.model_copy(
                                    update={"values": values}
                                )
                            }
                        )
                    ]
                }
            )
        }
    )
    note = GroundedNoteAssertion.model_validate(
        {
            **assertion(selected).model_dump(),
            "target_member_id": UUID(int=30),
            "concept": "numerical_region_volume",
            "modality": "imaging",
            "result": {"form": "exact", "quantity": {"value": "0", "unit": "mm3"}},
        }
    )
    report = fuse_state(selected, note_assertions=[note])
    conflict = next(f for f in report.conflicts if f.category == "INCONSISTENT_VALUES")
    assert conflict.primary_member_id == UUID(int=30)
    assert report.tumor_state[0].exact_value == "0.000000000008"


@pytest.mark.parametrize("field,value", [("branch_id", UUID(int=999)), ("run_id", UUID(int=999))])
def test_generated_members_cannot_cross_branch_or_batch_run(field, value):
    event = dict(
        event_id=UUID(int=40),
        branch_id=BRANCH,
        run_id=RUN,
        slot_id="treatment10",
        relative_day="10",
        modality="treatment",
        value={
            "kind": "treatment",
            "event_reference": "control",
            "action": "hypothetical_exposure_start",
        },
    )
    selected = view(
        generated_clinical_members=[
            dict(
                batch_id=UUID(int=41),
                run_id=RUN,
                events=[{**event, field: value}],
                source_hash="b" * 64,
            )
        ]
    )
    with pytest.raises(ValueError, match="fusion_generated_membership_mismatch"):
        fuse_state(selected)
