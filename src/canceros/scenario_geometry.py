"""SC-01 realized measurement checks, independent of complete-run publication."""

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import Field

from canceros.contracts import Contract, DecimalString
from canceros.identity import authorize_project
from canceros.lineage import lock_lineage, require_resource_action
from canceros.measurement_runs import load_usable_measurement
from canceros.patient_linkage import authorize_patient
from canceros.scenario_families import TrajectoryValidation, build_registry, check_family_realized
from canceros.simulation_contracts import Family
from canceros.simulation_plugins import ModelTurningPoint, SC05ClinicalCondition
from canceros.simulation_runs import read_run, read_run_geometry_targets
from canceros.source_registry import SourceAction
from canceros.synthetic_geometry import read_geometry_result
from canceros.twin_states import read_branch


class GeometryValidationInput(Contract):
    result_ids: Annotated[list[UUID], Field(min_length=3, max_length=16)]


class RunGeometryValidation(Contract):
    run_id: UUID
    family: Family
    mode: Literal["modest_reduction", "near_stable"] | None
    configured_turning_point: ModelTurningPoint | None
    clinical_condition: SC05ClinicalCondition | None
    realized_minimum_slot_ids: list[str]
    realized_minimum_mm3: DecimalString | None
    result_ids: list[UUID]
    target_mm3: list[DecimalString]
    realized_mm3: list[DecimalString | None]
    ordering: TrajectoryValidation
    scientific_review: Literal["pending"] = "pending"
    publication: Literal["draft"] = "draft"
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    measurement_uncertainty: Literal["not_established"] = "not_established"
    next_action: str


def validate_run_geometry(c, i, p, u, run_id, value):
    authorize_project(i, p, "admin")
    authorize_patient(c, i, p, u, edit=True)
    lock_lineage(c, p, u)
    run = read_run(c, i, p, u, run_id)
    branch = read_branch(c, i, p, u, run.branch_id)
    measurement = load_usable_measurement(c, i, p, u, branch.input.baseline_measurement_id)
    baseline = Decimal(measurement.values.exact_volume_mm3)
    if run.config.scenario.family not in ("SC-01", "SC-02", "SC-03", "SC-04", "SC-05"):
        raise HTTPException(409, detail="scenario_order_validator_not_implemented_for_family")
    for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE):
        require_resource_action(c, i, p, u, run.id, action)
    try:
        output = build_registry().generate(run.config, baseline)
    except ValueError as error:
        raise HTTPException(409, detail=str(error)) from None
    sampled_targets = read_run_geometry_targets(c, i, p, u, run_id)
    if len(set(value.result_ids)) != len(value.result_ids) or len(value.result_ids) != len(
        output.tumor_targets
    ):
        raise HTTPException(422, detail="one_result_per_configured_target_required")
    realized = []
    for result_id, target in zip(value.result_ids, sampled_targets, strict=True):
        result = read_geometry_result(c, i, p, u, result_id)
        for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE):
            require_resource_action(c, i, p, u, result.id, action)
        geometry = result.geometry
        if (
            geometry.run_id != run_id
            or geometry.branch_id != run.branch_id
            or geometry.baseline_hash != run.config.baseline_hash
            or Decimal(geometry.time.value) != Decimal(target.relative_day)
            or Decimal(geometry.shape.target_mm3) != Decimal(target.target_mm3)
            or geometry.input_revision != run.input_revision
            or geometry.association_head != run.association_head
        ):
            raise HTTPException(409, detail="geometry_result_does_not_match_frozen_run_slot")
        measured = geometry.shape.realized_values
        realized.append(
            Decimal(measured.exact_volume_mm3)
            if measured
            and (
                (result.status == "ready" and measured.availability == "available")
                or (
                    result.status == "zero"
                    and measured.availability == "configured_simulated_absent"
                    and Decimal(target.target_mm3) == 0
                )
            )
            else None
        )
    ordering = check_family_realized(run.config, output.tumor_targets, realized, baseline)
    measured_values = [item for item in realized if item is not None]
    minimum = min(measured_values) if len(measured_values) == len(realized) else None
    return RunGeometryValidation(
        run_id=run.id,
        family=run.config.scenario.family,
        mode=output.mode,
        configured_turning_point=output.turning_point,
        clinical_condition=output.clinical_condition,
        realized_minimum_slot_ids=[
            target.slot_id
            for target, measured in zip(output.tumor_targets, realized, strict=True)
            if minimum is not None and measured == minimum
        ],
        realized_minimum_mm3=format(minimum, "f") if minimum is not None else None,
        result_ids=value.result_ids,
        target_mm3=[target.target_mm3 for target in sampled_targets],
        realized_mm3=[format(item, "f") if item is not None else None for item in realized],
        ordering=ordering,
        next_action="Complete remaining run gates and request separate review/publication"
        if ordering.ordering_valid
        else "Inspect target versus realized quantities; revise the draft or grid, then create a new run",
    )
