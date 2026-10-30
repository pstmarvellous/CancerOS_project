"""V1–V8 software validation of a complete hypothetical run, separate from clinical review."""

import hashlib
import json
from decimal import Decimal, localcontext
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from canceros.clinical_generation import (
    ClinicalBatch,
    _note,
    generate_clinical,
    materialize_measurement_only,
)
from canceros.contracts import Contract, DecimalString, Hash, Provenance
from canceros.sampling import SampledObservations, sample_observations
from canceros.scenario_families import check_family_realized
from canceros.simulation_contracts import SimulationConfig, StableId
from canceros.simulation_plugins import PluginOutput

Level = Literal["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"]
LEVELS: tuple[Level, ...] = ("V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8")


class RealizedGeometryEvidence(Contract):
    slot_id: StableId
    branch_id: UUID
    relative_day: DecimalString
    geometry_id: UUID
    mask_sha256: Hash
    actual_mm3: DecimalString
    target_mm3: DecimalString
    voxel_mm3: DecimalString
    technical_qc_valid: bool = Field(strict=True)
    origin: Literal[Provenance.SYNTHETIC_GENERATED] = Provenance.SYNTHETIC_GENERATED


class ValidationFinding(Contract):
    level: Level
    status: Literal["passed", "failed", "not_evaluated"]
    code: str


class CompleteValidationReport(Contract):
    status: Literal["engineering_passed", "blocked"]
    findings: list[ValidationFinding]
    semantic_digest: Hash
    scientific_review: Literal["pending"] = "pending"
    scope: Literal["anatomical_engineering", "measurement_only"]
    external_gates: tuple[str, ...] = (
        "authentic_baseline_and_current_source_rights_rechecked_by_server",
        "qualified_scientific_policy_review_pending",
        "explicit_authorized_complete_run_publication_required",
    )


def semantic_digest(
    config: SimulationConfig,
    sampling: SampledObservations,
    clinical: ClinicalBatch,
    realizations: list[RealizedGeometryEvidence],
) -> str:
    """Scientific equality excludes generated UUIDs, while retaining values, units and mask bytes."""
    configuration = config.model_dump(mode="json")
    for field in ("branch_id", "baseline_state_id"):
        configuration.pop(field, None)
    payload: dict[str, Any] = {
        "version": "complete-simulation-semantics/1",
        "configuration": configuration,
        "sampling": sampling.model_dump(mode="json"),
        "clinical_events": [
            {
                "slot_id": event.slot_id,
                "relative_day": event.relative_day,
                "modality": event.modality,
                "value": event.value.model_dump(mode="json"),
                "origin": event.origin.value,
            }
            for event in clinical.events
        ],
        "notes": [
            {"relative_day": note.relative_day, "text": note.text} for note in clinical.notes
        ],
        "adverse_events": [event.model_dump(mode="json") for event in clinical.adverse_events],
        "imaging_measurement_basis": clinical.imaging_measurement_basis,
        "geometry": [
            {
                key: value
                for key, value in evidence.model_dump(mode="json").items()
                if key not in ("geometry_id", "branch_id")
            }
            for evidence in realizations
        ],
    }
    for key in ("clinical_events", "notes", "geometry"):
        payload[key].sort(key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "ascii"
        )
    ).hexdigest()


def _actual_clinical_course(config: SimulationConfig, clinical: ClinicalBatch) -> None:
    parameters = config.sc05_parameters
    if parameters is None:
        return
    onset = Decimal(parameters.onset_day)
    recovery = Decimal(parameters.recovery_day) if parameters.recovery_day is not None else None
    for affected in parameters.affected_concepts:
        values = []
        for event in clinical.events:
            value = event.value
            if value.kind == "quantity" and value.code == affected.concept:
                if value.canonical_value is None:
                    raise ValueError("SC05 actual clinical quantity lacks canonical normalization")
                values.append((Decimal(event.relative_day), Decimal(value.canonical_value)))
            elif value.kind == "symptom" and value.concept == affected.concept:
                values.append((Decimal(event.relative_day), Decimal(value.rating)))
        values.sort()
        if len(values) < 2 or any(a[0] >= b[0] for a, b in zip(values, values[1:])):
            raise ValueError("SC05 actual affected course is missing, duplicated or insufficient")
        direction = Decimal(-1) if affected.numeric_direction == "decreasing" else Decimal(1)
        before_recovery = [item for item in values if recovery is None or item[0] < recovery]
        if (
            len(before_recovery) < 2
            or (before_recovery[-1][1] - before_recovery[0][1]) * direction <= 0
        ):
            raise ValueError("SC05 actual deterioration was erased by sampling or missingness")
        if not any(
            (b[1] - a[1]) * direction > 0
            and b[0] >= onset
            and (recovery is None or b[0] < recovery)
            for a, b in zip(values, values[1:])
        ):
            raise ValueError("SC05 actual deterioration does not match configured onset")
        if recovery is not None and not (
            (values[-1][1] - before_recovery[-1][1]) * direction < 0
            and any(
                (b[1] - a[1]) * direction < 0 and b[0] >= recovery
                for a, b in zip(values, values[1:])
            )
        ):
            raise ValueError("SC05 actual recovery was erased or lacks its configured timing")


def validate_complete_run(
    config: SimulationConfig,
    output: PluginOutput,
    sampling: SampledObservations,
    clinical: ClinicalBatch,
    baseline_mm3: Decimal,
    realizations: list[RealizedGeometryEvidence],
) -> CompleteValidationReport:
    with localcontext() as context:
        context.prec = 100
        return _validate(config, output, sampling, clinical, baseline_mm3, realizations)


def _validate(config, output, sampling, clinical, baseline_mm3, realizations):
    findings: list[ValidationFinding] = []
    scope: Literal["anatomical_engineering", "measurement_only"] = (
        "anatomical_engineering" if config.geometry_policy != "none" else "measurement_only"
    )
    try:
        config = SimulationConfig.model_validate_json(config.model_dump_json())
        output = PluginOutput.model_validate_json(output.model_dump_json())
        sampling = SampledObservations.model_validate_json(sampling.model_dump_json())
        clinical = ClinicalBatch.model_validate_json(clinical.model_dump_json())
        realizations = [
            RealizedGeometryEvidence.model_validate_json(item.model_dump_json())
            for item in realizations
        ]
        if (
            clinical.branch_id != config.branch_id
            or not baseline_mm3.is_finite()
            or baseline_mm3 <= 0
        ):
            raise ValueError("Invalid branch membership or baseline")
        digest = semantic_digest(config, sampling, clinical, realizations)
    except ValueError:
        return CompleteValidationReport(
            status="blocked",
            scope=scope,
            semantic_digest="0" * 64,
            findings=[
                ValidationFinding(
                    level=level,
                    status="failed" if level == "V1" else "not_evaluated",
                    code="invalid_structural_inputs" if level == "V1" else "prerequisite_failed",
                )
                for level in LEVELS
            ],
        )

    def check(level, operation, code):
        try:
            operation()
        except ValueError:
            findings.append(ValidationFinding(level=level, status="failed", code=code))
        else:
            findings.append(ValidationFinding(level=level, status="passed", code=code))

    def structural():
        if len(sampling.tumor_targets) < 3 or len(
            {target.slot_id for target in sampling.tumor_targets}
        ) != len(sampling.tumor_targets):
            raise ValueError("Incomplete or duplicated follow-up membership")
        if config.geometry_policy == "none" and realizations:
            raise ValueError(
                "Measurement-only configuration cannot claim anatomical geometry evidence"
            )
        if len({item.geometry_id for item in realizations}) != len(realizations):
            raise ValueError(
                "Different follow-up slots cannot reuse the same immutable geometry report"
            )

    def temporal():
        slots = {slot.slot_id: slot for slot in sampling.slots}
        for event in clinical.events:
            slot = slots.get(event.slot_id)
            if (
                slot is None
                or slot.modality != event.modality
                or Decimal(slot.relative_day) != Decimal(event.relative_day)
            ):
                raise ValueError("Clinical observation does not match its sampled slot")
        if clinical.sampling != sampling:
            raise ValueError("Clinical report uses a different sampled schedule")

    def numerical():
        if config.geometry_policy == "none":
            return
        targets = {target.slot_id: target for target in sampling.tumor_targets}
        if (
            len(realizations) != len(targets)
            or {item.slot_id for item in realizations} != targets.keys()
        ):
            raise ValueError("Incomplete or duplicated realized geometry")
        for item in realizations:
            target = targets[item.slot_id]
            if (
                item.branch_id != config.branch_id
                or not item.technical_qc_valid
                or target.target_mm3 is None
                or Decimal(item.relative_day) != Decimal(target.relative_day)
                or Decimal(item.target_mm3) != Decimal(target.target_mm3)
            ):
                raise ValueError("Invalid realized geometry source, time or QC")
            actual, intended, voxel = (
                Decimal(item.actual_mm3),
                Decimal(item.target_mm3),
                Decimal(item.voxel_mm3),
            )
            if actual < 0 or intended < 0 or voxel <= 0:
                raise ValueError("Invalid measured geometry quantity")
            if abs(actual - intended) > max(voxel, intended * Decimal("0.01")):
                raise ValueError("Realized geometry misses engineering target tolerance")

    def scenario():
        realized = {item.slot_id: item for item in realizations}
        values = [
            None
            if target.target_mm3 is None
            else Decimal(realized[target.slot_id].actual_mm3)
            if config.geometry_policy != "none" and target.slot_id in realized
            else Decimal(target.target_mm3)
            if config.geometry_policy == "none"
            else None
            for target in sampling.tumor_targets
        ]
        if not check_family_realized(
            config, output.tumor_targets, values, baseline_mm3
        ).ordering_valid:
            raise ValueError(
                "Observed or realized trajectory does not preserve the requested family"
            )
        _actual_clinical_course(config, clinical)

    def cross_modal():
        expected = (
            materialize_measurement_only(config, output, clinical.run_id)
            if config.geometry_policy == "none"
            else generate_clinical(config, output, clinical.run_id)
        )
        if clinical != expected:
            raise ValueError(
                "Clinical observations or notes differ from deterministic sampled generation"
            )
        for event, note in zip(clinical.events, clinical.notes, strict=True):
            if note != _note(event):
                raise ValueError("Research note is not exactly grounded in its structured record")

    def provenance():
        if any(
            item.origin != Provenance.SYNTHETIC_GENERATED
            for item in [*clinical.events, *clinical.notes, *realizations]
        ):
            raise ValueError("Generated descendant was promoted to observed origin")

    def safety():
        if (
            config.treatment.category != "no_specific_assumption"
            or output.assumptions != "unreviewed_demonstration_not_patient_prediction"
        ):
            raise ValueError("Unsupported scientific exposure or predictive assertion")
        for event in clinical.events:
            if event.value.kind == "adverse_event" and (
                event.value.grading != "ungraded"
                or event.value.attribution != "hypothetical_association_not_causal"
            ):
                raise ValueError("Unsupported adverse event grading or attribution")
        # Only deterministic templates are eligible; arbitrary unsafe prose is never accepted.
        if [note.text for note in clinical.notes] != [
            _note(event).text for event in clinical.events
        ]:
            raise ValueError("Unsupported or ungrounded narrative")

    def replay():
        if sample_observations(config, output) != sampling:
            raise ValueError("Observed sampling does not reproduce frozen seed and assumptions")
        expected = (
            materialize_measurement_only(config, output, clinical.run_id)
            if config.geometry_policy == "none"
            else generate_clinical(config, output, clinical.run_id)
        )
        if semantic_digest(config, sampling, expected, realizations) != digest:
            raise ValueError("Scientific semantics do not replay")

    for level, operation, code in (
        ("V1", structural, "structural_membership"),
        ("V2", temporal, "sampled_time_membership"),
        ("V3", numerical, "geometry_units_and_target_tolerance"),
        ("V4", scenario, "actual_family_and_clinical_course"),
        ("V5", cross_modal, "clinical_units_notes_and_exposure_grounding"),
        ("V6", provenance, "synthetic_descendants_preserved"),
        ("V7", safety, "controlled_scientific_and_narrative_claims"),
        ("V8", replay, "frozen_semantic_replay"),
    ):
        check(level, operation, code)
    return CompleteValidationReport(
        status="blocked"
        if any(finding.status == "failed" for finding in findings)
        else "engineering_passed",
        findings=findings,
        semantic_digest=digest,
        scope=scope,
    )
