"""Private fixed-grid geometry for isolated engineering runs; no clinical validation."""

import io
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID, uuid4

import numpy as np
from fastapi import HTTPException
from pydantic import Field, model_validator
from sqlalchemy import text

from canceros.annotation_import import load_annotation_mask
from canceros.contracts import Contract, DecimalString, Hash, RelativeTime
from canceros.identity import authorize_project
from canceros.imaging_ingestion import store_artifact
from canceros.lineage import derive_resource, lock_lineage, processing_spec, require_resource_action
from canceros.measurement_runs import load_usable_measurement
from canceros.mesh_quality import validate_surface
from canceros.mesh_reconstruction import MeshError, reconstruct
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import canonical_bytes, science_hash
from canceros.source_registry import SourceAction
from canceros.storage import StoredObject
from canceros.synthetic_contracts import GeneratedMesh, GeometrySummary
from canceros.synthetic_shape import ShapeConfig, ShapeError, generate_shape
from canceros.twin_states import GeneratedGeometryMember, StateBuildInput, build_state, read_branch


class TargetPoint(Contract):
    relative_day: DecimalString
    target_metric: Literal["numerical_region_volume"] = "numerical_region_volume"
    target_mm3: DecimalString

    @model_validator(mode="after")
    def valid_quantities(self):
        if not 0 < Decimal(self.relative_day) < Decimal("100000000") or not 0 <= Decimal(
            self.target_mm3
        ) < Decimal("1e15"):
            raise ValueError("positive_followup_time_and_nonnegative_bounded_target_required")
        return self


class FixtureRunInput(Contract):
    branch_id: UUID
    baseline_hash: Hash
    targets: Annotated[list[TargetPoint], Field(min_length=1, max_length=16)]
    shape_config: ShapeConfig

    @model_validator(mode="after")
    def ordered_targets(self):
        days = [Decimal(t.relative_day) for t in self.targets]
        if any(b <= a for a, b in zip(days, days[1:])):
            raise ValueError("strictly_ordered_explicit_target_times_required")
        return self


class FixtureRun(Contract):
    id: UUID
    input: FixtureRunInput
    input_revision: int
    association_head: int
    authority: Literal["isolated_test_mock"] = "isolated_test_mock"
    external_simulation_engine_integrated: Literal[False] = False
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"


class GeometryInput(Contract):
    run_id: UUID
    baseline_hash: Hash
    target_index: Annotated[int, Field(strict=True, ge=0, le=15)]


class GeometryResult(Contract):
    id: UUID
    geometry: GeometrySummary
    state_id: UUID | None
    status: Literal["ready", "zero", "blocked"]
    publication: Literal["draft"] = "draft"
    scientific_review: Literal["pending"] = "pending"
    simulation_engine_integration: Literal[
        "blocked_not_implemented",
        "partial_common_run_adapter_full_orchestration_pending",
        "common_run_workflow_available_explicit_completion_required",
    ] = "blocked_not_implemented"
    five_scenario_families: Literal["not_completed_by_geometry_component"] = (
        "not_completed_by_geometry_component"
    )


def _access(c, i, p, u):
    authorize_project(i, p, "admin")
    authorize_patient(c, i, p, u, edit=True)
    lock_lineage(c, p, u)


def _test_only(config):
    if config.mode != "test":
        raise HTTPException(409, detail="authorized_simulation_engine_integration_missing")


def _use(c, i, p, u, identifier):
    for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE):
        require_resource_action(c, i, p, u, identifier, action)


def _read(c, i, p, u, table, identifier, model):
    authorize_patient(c, i, p, u, edit=True)
    row = c.execute(
        text(
            f"SELECT report,report_hash FROM imaging.{table} WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": p, "u": u, "id": identifier},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.report) != row.report_hash:
        raise HTTPException(409)
    return model.model_validate(row.report)


def _prior(c, i, p, u, table, key, value, model):
    fingerprint = science_hash(value.model_dump(mode="json"))
    prior = c.execute(
        text(
            f"SELECT id,input_hash FROM imaging.{table} WHERE project_id=:p AND patient_id=:u AND actor_id=:a AND command_key=:k"
        ),
        {"p": p, "u": u, "a": i.user_id, "k": key},
    ).one_or_none()
    if prior:
        if prior.input_hash != fingerprint:
            raise HTTPException(409)
        _use(c, i, p, u, prior.id)
        return _read(c, i, p, u, table, prior.id, model), fingerprint
    return None, fingerprint


def _store(c, i, p, u, table, report, fingerprint, key, extra=None):
    values = {
        "id": report.id,
        "project_id": p,
        "patient_id": u,
        "actor_id": i.user_id,
        "command_key": key,
        "input_hash": fingerprint,
        "report": report.model_dump_json(),
        "report_hash": science_hash(report.model_dump(mode="json")),
        **(extra or {}),
    }
    c.execute(
        text(
            f"INSERT INTO imaging.{table}({','.join(values)}) VALUES({','.join('CAST(:report AS jsonb)' if name == 'report' else ':' + name for name in values)})"
        ),
        values,
    )


def _derive(c, i, p, u, identifier, kind, digest, parents, fingerprint):
    derive_resource(
        c,
        i,
        p,
        u,
        identifier,
        kind,
        digest,
        sorted(set(parents), key=str),
        processing_spec(
            __file__,
            "synthetic-geometry/1",
            "isotropic-fixed-grid/1",
            {"request_sha256": fingerprint},
        ),
    )


def authorize_fixture_run(c, i, p, u, value, storage, key, config):
    _test_only(config)
    _access(c, i, p, u)
    prior, fingerprint = _prior(c, i, p, u, "simulation_fixture_runs", key, value, FixtureRun)
    if prior:
        return prior
    branch = read_branch(c, i, p, u, value.branch_id)
    _use(c, i, p, u, branch.id)
    measurement = load_usable_measurement(c, i, p, u, branch.input.baseline_measurement_id)
    if branch.baseline_hash != value.baseline_hash or len(measurement.selections) != 1:
        raise HTTPException(409, detail="exact_single_region_branch_baseline_required")
    if c.execute(
        text("SELECT id FROM imaging.simulation_fixture_runs WHERE id=:id"),
        {"id": branch.input.run_id},
    ).scalar_one_or_none():
        raise HTTPException(409, detail="run_already_frozen")
    revision = c.execute(
        text("SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"),
        {"p": p, "u": u},
    ).scalar_one()
    head = c.execute(
        text(
            "SELECT COALESCE(max(sequence),0) FROM imaging.lesion_association_events WHERE project_id=:p AND patient_id=:u"
        ),
        {"p": p, "u": u},
    ).scalar_one()
    report = FixtureRun(
        id=branch.input.run_id, input=value, input_revision=revision, association_head=head
    )
    _store(
        c, i, p, u, "simulation_fixture_runs", report, fingerprint, key, {"branch_id": branch.id}
    )
    _derive(
        c,
        i,
        p,
        u,
        report.id,
        "simulation_fixture_run",
        science_hash(report.model_dump(mode="json")),
        [branch.id, measurement.id],
        fingerprint,
    )
    audit(c, p, report.id, "ISOLATED_GEOMETRY_RUN_AUTHORIZED")
    return report


def read_fixture_run(c, i, p, u, identifier):
    return _read(c, i, p, u, "simulation_fixture_runs", identifier, FixtureRun)


def resolve_geometry_run(c, i, p, u, identifier):
    """Normalize a frozen common test run; legacy fixture authorization stays isolated."""
    common_exists = c.execute(
        text(
            "SELECT id FROM imaging.simulation_runs WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": p, "u": u, "id": identifier},
    ).scalar_one_or_none()
    if common_exists is None:
        return read_fixture_run(c, i, p, u, identifier)
    from canceros.simulation_runs import read_run, read_run_geometry_targets

    common = read_run(c, i, p, u, identifier)
    _use(c, i, p, u, identifier)
    if common.association_head is None or common.config.geometry_policy != "isotropic-fixed-grid/1":
        raise HTTPException(409, detail="frozen_geometry_policy_and_association_head_required")
    targets = read_run_geometry_targets(c, i, p, u, identifier)
    return FixtureRun(
        id=common.id,
        input=FixtureRunInput(
            branch_id=common.branch_id,
            baseline_hash=common.config.baseline_hash,
            targets=[
                TargetPoint(relative_day=t.relative_day, target_mm3=t.target_mm3) for t in targets
            ],
            shape_config=ShapeConfig(seed=common.config.seed),
        ),
        input_revision=common.input_revision,
        association_head=common.association_head,
    )


def read_geometry_result(c, i, p, u, identifier):
    return _read(c, i, p, u, "synthetic_geometry_results", identifier, GeometryResult)


def load_ready_geometry(c, i, p, u, identifier):
    report = _read(c, i, p, u, "synthetic_geometries", identifier, GeometrySummary)
    _use(c, i, p, u, identifier)
    if report.status not in ("ready", "zero"):
        raise HTTPException(409, detail="hypothetical_geometry_not_ready")
    return report


def generate_geometry(c, i, p, u, value: GeometryInput, storage, key, config):
    _test_only(config)
    _access(c, i, p, u)
    prior, fingerprint = _prior(
        c, i, p, u, "synthetic_geometry_results", key, value, GeometryResult
    )
    if prior:
        return prior
    run = resolve_geometry_run(c, i, p, u, value.run_id)
    _use(c, i, p, u, run.id)
    branch = read_branch(c, i, p, u, run.input.branch_id)
    if (
        value.baseline_hash != branch.baseline_hash
        or value.baseline_hash != run.input.baseline_hash
        or value.target_index >= len(run.input.targets)
    ):
        raise HTTPException(409, detail="frozen_run_or_baseline_mismatch")
    measurement = load_usable_measurement(c, i, p, u, branch.input.baseline_measurement_id)
    if len(measurement.selections) != 1:
        raise HTTPException(409)
    selected = measurement.selections[0]
    annotation, mask = load_annotation_mask(c, i, p, u, selected.segmentation_id, storage)
    if not annotation.capabilities.numerical_region_volume_allowed:
        raise HTTPException(409)
    target = run.input.targets[value.target_index]
    try:
        generated = generate_shape(
            mask, annotation.geometry, target.target_mm3, run.input.shape_config
        )
    except ShapeError as error:
        raise HTTPException(422, detail=str(error)) from None
    identifier = uuid4()
    parents = [run.id, branch.id, measurement.id]
    mask_id, mesh_id, qc = None, None, None
    status = generated.report.status
    reasons = list(generated.report.reasons)
    if generated.array is not None:
        buffer = io.BytesIO()
        np.save(buffer, generated.array, allow_pickle=False)
        mask_id, digest = store_artifact(c, p, u, buffer.getvalue(), storage)
        _derive(c, i, p, u, mask_id, "synthetic_followup_mask", digest, parents, fingerprint)
        parents.append(mask_id)
        if status == "ready":
            try:
                surface = reconstruct(generated.array, annotation.geometry)
                qc = validate_surface(surface)
                if qc.display_allowed:
                    asset = GeneratedMesh(
                        geometry_id=identifier,
                        baseline_segmentation_id=annotation.id,
                        surface=surface,
                    )
                    mesh_id, digest = store_artifact(
                        c, p, u, canonical_bytes(asset.model_dump(mode="json")), storage
                    )
                    _derive(
                        c, i, p, u, mesh_id, "synthetic_followup_mesh", digest, parents, fingerprint
                    )
                    parents.append(mesh_id)
                else:
                    status = "blocked"
                    reasons.append("generated_mesh_qc_not_supported_or_failed")
            except MeshError:
                status = "blocked"
                reasons.append("generated_mesh_reconstruction_failed")
    time = RelativeTime(
        basis="relative_day",
        value=target.relative_day,
        time_domain="simulation",
        timeline_origin_id=branch.input.timeline_origin_id,
    )
    report = GeometrySummary(
        id=identifier,
        branch_id=branch.id,
        run_id=run.id,
        baseline_hash=branch.baseline_hash,
        baseline_measurement_id=measurement.id,
        baseline_segmentation_id=annotation.id,
        baseline_mask_sha256=selected.mask_sha256,
        grid_geometry=annotation.geometry,
        input_revision=run.input_revision,
        association_head=run.association_head,
        time=time,
        shape=generated.report,
        mask_artifact_id=mask_id,
        mesh_artifact_id=mesh_id,
        mesh_qc=qc,
        status=status,
        next_action="; ".join(reasons)
        if reasons
        else "Simulated geometry only; inspect target versus realized measurement and request separate private state review/publication",
    )
    _store(
        c,
        i,
        p,
        u,
        "synthetic_geometries",
        report,
        fingerprint,
        "geometry-" + str(identifier),
        {"run_id": run.id, "branch_id": branch.id},
    )
    _derive(
        c,
        i,
        p,
        u,
        report.id,
        "synthetic_geometry",
        science_hash(report.model_dump(mode="json")),
        parents,
        fingerprint,
    )
    state = None
    if status in ("ready", "zero"):
        state = build_state(
            c,
            i,
            p,
            u,
            StateBuildInput(
                target_revision=run.input_revision,
                association_head=run.association_head,
                branch_id=branch.id,
                time=time,
                generated_geometry_members=[GeneratedGeometryMember(geometry_id=report.id)],
            ),
            storage,
            "synthetic-state-" + str(identifier),
        )
    result = GeometryResult(
        id=uuid4(),
        geometry=report,
        state_id=state.id if state else None,
        status=status,
        simulation_engine_integration=(
            "common_run_workflow_available_explicit_completion_required"
            if c.execute(
                text(
                    "SELECT id FROM imaging.simulation_runs WHERE project_id=:p AND patient_id=:u AND id=:id"
                ),
                {"p": p, "u": u, "id": run.id},
            ).scalar_one_or_none()
            else "blocked_not_implemented"
        ),
    )
    _store(
        c,
        i,
        p,
        u,
        "synthetic_geometry_results",
        result,
        fingerprint,
        key,
        {"geometry_id": report.id, "state_id": state.id if state else None},
    )
    _derive(
        c,
        i,
        p,
        u,
        result.id,
        "synthetic_geometry_result",
        science_hash(result.model_dump(mode="json")),
        [report.id] + ([state.id] if state else []),
        fingerprint,
    )
    audit(c, p, result.id, "HYPOTHETICAL_GEOMETRY_RECORDED")
    return result


def read_generated_mesh(c, i, p, u, result_id, storage):
    result = read_geometry_result(c, i, p, u, result_id)
    _use(c, i, p, u, result.id)
    report = load_ready_geometry(c, i, p, u, result.geometry.id)
    if report.mesh_artifact_id is None:
        raise HTTPException(409, detail="configured_zero_has_no_surface")
    _use(c, i, p, u, report.mesh_artifact_id)
    row = c.execute(
        text(
            "SELECT object_key,object_version,sha256,byte_size FROM ops.artifacts WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": p, "u": u, "id": report.mesh_artifact_id},
    ).one()
    return GeneratedMesh.model_validate_json(
        storage.read(
            StoredObject(p, row.object_key, row.object_version, row.sha256, row.byte_size), p
        )
    )
