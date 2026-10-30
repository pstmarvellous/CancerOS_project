"""Complete software validation and failure injection, without authentic or clinical review claims."""

from decimal import Decimal
from uuid import UUID

import pytest
from test_clinical_generation import materialize, numeric
from test_scenario_sc05 import config as sc05_config

from canceros.clinical_generation import materialize_measurement_only
from canceros.sampling import sample_observations
from canceros.scenario_families import build_registry
from canceros.simulation_contracts import SimulationConfig
from canceros.simulation_validation import (
    RealizedGeometryEvidence,
    semantic_digest,
    validate_complete_run,
)


def inputs(config=None, geometry=False):
    request = config or numeric([("hemoglobin", "12", "g/dL", "3")])
    if geometry:
        request = request.model_copy(update={"geometry_policy": "isotropic-fixed-grid/1"})
    output = build_registry().generate(request, Decimal(100))
    sampling = sample_observations(request, output)
    clinical = (
        materialize(request)
        if geometry
        else materialize_measurement_only(request, output, UUID(int=22))
    )
    evidence = (
        [
            RealizedGeometryEvidence(
                slot_id=target.slot_id,
                branch_id=request.branch_id,
                relative_day=target.relative_day,
                geometry_id=UUID(int=i + 80),
                mask_sha256=str(i + 1) * 64,
                actual_mm3=target.target_mm3,
                target_mm3=target.target_mm3,
                voxel_mm3="1",
                technical_qc_valid=True,
            )
            for i, target in enumerate(sampling.tumor_targets)
        ]
        if geometry
        else []
    )
    return request, output, sampling, clinical, Decimal(100), evidence


def failed_levels(report):
    return {finding.level for finding in report.findings if finding.status == "failed"}


@pytest.mark.parametrize("geometry", [False, True])
def test_eight_engineering_levels_and_external_gates_are_distinct(geometry):
    report = validate_complete_run(*inputs(geometry=geometry))
    assert report.status == "engineering_passed"
    assert {finding.level for finding in report.findings} == {f"V{i}" for i in range(1, 9)}
    assert report.scope == ("anatomical_engineering" if geometry else "measurement_only")
    assert report.scientific_review == "pending"
    assert "qualified_scientific_policy_review_pending" in report.external_gates
    # This test supplies typed evidence fixtures. It does not claim a mask was computed here.


@pytest.mark.parametrize(
    "problem,level",
    [
        ("missing_geometry", "V3"),
        ("bad_qc", "V3"),
        ("wrong_branch", "V3"),
        ("wrong_time", "V3"),
        ("missed_target", "V3"),
        ("plateau", "V4"),
        ("duplicate_report", "V1"),
    ],
)
def test_geometry_failures_block_without_measurement_rewrite(problem, level):
    request, output, sampling, clinical, baseline, evidence = inputs(geometry=True)
    if problem == "missing_geometry":
        evidence.pop()
    else:
        changes = {
            "bad_qc": {"technical_qc_valid": False},
            "wrong_branch": {"branch_id": UUID(int=999)},
            "wrong_time": {"relative_day": "8"},
            "missed_target": {"actual_mm3": "88"},
            "plateau": {"actual_mm3": "100"},
            "duplicate_report": {"geometry_id": evidence[1].geometry_id},
        }[problem]
        evidence[0] = evidence[0].model_copy(update=changes)
    original = [item.model_dump_json() for item in evidence]
    report = validate_complete_run(request, output, sampling, clinical, baseline, evidence)
    assert report.status == "blocked" and level in failed_levels(report)
    assert [item.model_dump_json() for item in evidence] == original


def test_wrong_clinical_branch_is_structural_failure():
    request, output, sampling, clinical, baseline, evidence = inputs()
    clinical = clinical.model_copy(update={"branch_id": UUID(int=999)})
    report = validate_complete_run(request, output, sampling, clinical, baseline, evidence)
    assert report.status == "blocked" and "V1" in failed_levels(report)


@pytest.mark.parametrize(
    "text", ["Confirmed drug resistance.", "hemoglobin 99 g/dL", "Actual physician encounter."]
)
def test_unsafe_or_conflicting_notes_are_withheld(text):
    request, output, sampling, clinical, baseline, evidence = inputs()
    notes = [clinical.notes[0].model_copy(update={"text": text})]
    report = validate_complete_run(
        request, output, sampling, clinical.model_copy(update={"notes": notes}), baseline, evidence
    )
    assert report.status == "blocked"
    assert {"V5", "V7", "V8"} <= failed_levels(report)


@pytest.mark.parametrize("profile", ["noise", "missingness"])
def test_sc05_actual_deterioration_erased_or_missing_blocks(profile):
    data = sc05_config(symptom=True).model_dump(mode="json")
    if profile == "noise":
        data["noise"] = {
            "mode": "explicit",
            "points": [{"slot_id": "clinical-2", "channel": "fatigue", "additive_offset": "-4"}],
        }
    else:
        data["missingness"] = {
            "mode": "explicit",
            "points": [
                {"slot_id": slot, "channel": "fatigue", "reason": "not_collected"}
                for slot in ("clinical-1", "clinical-2")
            ],
        }
    report = validate_complete_run(*inputs(SimulationConfig.model_validate(data)))
    assert report.status == "blocked" and "V4" in failed_levels(report)


def test_sc05_observed_recovery_is_checked_separately_from_configuration():
    request = sc05_config(symptom=True, recovery=True)
    assert validate_complete_run(*inputs(request)).status == "engineering_passed"
    data = request.model_dump(mode="json")
    data["noise"] = {
        "mode": "explicit",
        "points": [{"slot_id": "clinical-2", "channel": "fatigue", "additive_offset": "4"}],
    }
    report = validate_complete_run(*inputs(SimulationConfig.model_validate(data)))
    assert report.status == "blocked" and "V4" in failed_levels(report)


def test_semantic_digest_ignores_generated_uuids_but_preserves_mask_bytes_and_values():
    request, output, sampling, clinical, _, evidence = inputs(geometry=True)
    first = semantic_digest(request, sampling, clinical, evidence)
    same_values_other_run = materialize(request, UUID(int=900))
    renamed = [
        item.model_copy(update={"geometry_id": UUID(int=1000 + i)})
        for i, item in enumerate(evidence)
    ]
    assert semantic_digest(request, sampling, same_values_other_run, renamed) == first
    renamed[0] = renamed[0].model_copy(update={"mask_sha256": "e" * 64})
    assert semantic_digest(request, sampling, same_values_other_run, renamed) != first


def test_missing_required_tumor_observation_blocks_even_tabular_complete_run():
    data = numeric().model_dump(mode="json")
    data["missingness"] = {
        "mode": "explicit",
        "points": [
            {"slot_id": "scan-1", "channel": "numerical_region_volume", "reason": "not_collected"}
        ],
    }
    report = validate_complete_run(*inputs(SimulationConfig.model_validate(data)))
    assert report.status == "blocked" and "V4" in failed_levels(report)


def test_measurement_only_followups_are_explicitly_target_based_and_missing_is_not_zero():
    request, output, sampling, clinical, _, _ = inputs()
    imaging = [event for event in clinical.events if event.modality == "imaging"]
    assert len(imaging) == 3
    assert clinical.imaging_measurement_basis == "simulated_target_no_mask_realization"
    assert [event.value.value for event in imaging] == [
        target.target_mm3 for target in sampling.tumor_targets
    ]
    data = request.model_dump(mode="json")
    data["missingness"] = {
        "mode": "explicit",
        "points": [
            {"slot_id": "scan-1", "channel": "numerical_region_volume", "reason": "not_collected"}
        ],
    }
    _, _, _, missing, _, _ = inputs(SimulationConfig.model_validate(data))
    event = next(event for event in missing.events if event.slot_id == "scan-1")
    assert event.value.kind == "missing" and event.value.reason == "not_collected"
