"""Immutable display selection under an explicitly limited engineering mesh policy."""

import hashlib
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import Field
from sqlalchemy import text

from canceros.contracts import Contract
from canceros.imaging_ingestion import store_artifact
from canceros.lineage import derive_resource, lock_lineage, processing_spec, require_resource_action
from canceros.measurement_runs import load_usable_measurement
from canceros.mesh_quality import LODComparison, SurfaceQuality, simplify_convex, validate_surface
from canceros.mesh_runs import MeshAsset, MeshObject, load_mesh
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import canonical_bytes, science_hash
from canceros.source_registry import SourceAction
from canceros.storage import StoredObject


class MeshQCInput(Contract):
    mesh_run_id: UUID
    triangle_budget: Annotated[int, Field(strict=True, ge=4, le=100_000)] = 20_000
    simplify: bool = True


class ObjectQC(Contract):
    segmentation_id: UUID
    original: SurfaceQuality
    lod: SurfaceQuality | None
    comparison: LODComparison | None
    mask_volume_mm3: float
    original_minus_mask_mm3: float | None


class MeshQCReport(Contract):
    id: UUID
    mesh_run_id: UUID
    measurement_id: UUID
    input_revision: int
    status: Literal["validated", "blocked"]
    objects: list[ObjectQC]
    original_artifact_id: UUID
    lod_artifact_id: UUID | None
    output_artifact_id: UUID | None
    selection: Literal["original", "lod", "none"]
    selected_byte_size: int | None
    selected_triangles: int | None
    requested_triangle_budget: int
    budget_met: bool
    policy: Literal["mesh-display/1"] = "mesh-display/1"
    measurement_authority: Literal["source_mask"] = "source_mask"
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    scientific_review: Literal["pending"] = "pending"
    publication: Literal["draft"] = "draft"
    next_action: str


def create_mesh_qc(connection, identity, project, patient, value, storage, command_key):
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    original_report, asset = load_mesh(
        connection, identity, project, patient, value.mesh_run_id, storage
    )
    measurement = load_usable_measurement(
        connection, identity, project, patient, original_report.measurement_id
    )
    require_resource_action(
        connection,
        identity,
        project,
        patient,
        original_report.output_artifact_id,
        SourceAction.DERIVATIVE,
    )
    fingerprint = science_hash(value.model_dump(mode="json"))
    prior = connection.execute(
        text(
            "SELECT id,input_hash FROM imaging.mesh_qc_reports WHERE project_id=:p AND patient_id=:u AND actor_id=:a AND command_key=:k"
        ),
        {"p": project, "u": patient, "a": identity.user_id, "k": command_key},
    ).one_or_none()
    if prior:
        if fingerprint != prior.input_hash:
            raise HTTPException(409)
        previous = read_mesh_qc(connection, identity, project, patient, prior.id)
        require_resource_action(
            connection, identity, project, patient, previous.id, SourceAction.INTERNAL
        )
        return previous
    diagnostics, lod_objects = [], []
    selected_counts = {s.segmentation_id: s.selected_voxels for s in measurement.selections}
    for obj in asset.objects:
        qc = validate_surface(obj.surface)
        candidate, comparison = simplify_convex(obj.surface) if value.simplify else (None, None)
        lod_quality = validate_surface(candidate) if candidate else None
        # Distinct objects keep identity and count; no component is silently removed.
        if candidate:
            lod_objects.append(MeshObject(**{**obj.model_dump(), "surface": candidate}))
        else:
            lod_objects.append(obj)
        voxel_volume = float(measurement.values.exact_voxel_volume_mm3)
        mask_volume = selected_counts[obj.segmentation_id] * voxel_volume
        diagnostics.append(
            ObjectQC(
                segmentation_id=obj.segmentation_id,
                original=qc,
                lod=lod_quality,
                comparison=comparison,
                mask_volume_mm3=mask_volume,
                original_minus_mask_mm3=qc.mesh_volume_mm3 - mask_volume
                if qc.mesh_volume_mm3 is not None
                else None,
            )
        )
    valid = all(d.original.display_allowed for d in diagnostics)
    lod_id, lod_size = None, None
    lod_triangles = sum(len(o.surface.triangles) for o in lod_objects)
    # Every LOD is separate immutable bytes; never replace the original.
    if valid and lod_triangles < original_report.triangle_count:
        raw = canonical_bytes(MeshAsset(objects=lod_objects).model_dump(mode="json"))
        if len(raw) <= storage.cap:
            lod_id, digest = store_artifact(connection, project, patient, raw, storage)
            lod_size = len(raw)
            derive_resource(
                connection,
                identity,
                project,
                patient,
                lod_id,
                "mesh_lod",
                digest,
                [original_report.output_artifact_id],
                processing_spec(
                    __file__,
                    "mesh-lod/1",
                    "mesh-display/1",
                    {
                        "request": value.model_dump(mode="json"),
                        "algorithm": "convex-support-retriangulation/1",
                        "implementation_sha256": hashlib.sha256(
                            Path(__file__).with_name("mesh_quality.py").read_bytes()
                        ).hexdigest(),
                    },
                ),
            )
    selected = lod_id if valid and lod_id else original_report.output_artifact_id if valid else None
    selection: Literal["lod", "original", "none"] = (
        "lod" if lod_id else "original" if valid else "none"
    )
    triangle_count = lod_triangles if lod_id else original_report.triangle_count if valid else None
    byte_size = lod_size if lod_id else original_report.byte_size if valid else None
    budget_met = triangle_count is not None and triangle_count <= value.triangle_budget
    report = MeshQCReport(
        id=uuid4(),
        mesh_run_id=original_report.id,
        measurement_id=measurement.id,
        input_revision=measurement.input_revision,
        status="validated" if valid else "blocked",
        objects=diagnostics,
        original_artifact_id=original_report.output_artifact_id,
        lod_artifact_id=lod_id,
        output_artifact_id=selected,
        selection=selection,
        selected_byte_size=byte_size,
        selected_triangles=triangle_count,
        requested_triangle_budget=value.triangle_budget,
        budget_met=budget_met,
        next_action=(
            "Display the selected engineering region with origin, annotation class and mm visible"
            if budget_met
            else "Retain validated higher detail; requested budget cannot be met without changing shape"
        )
        if valid
        else "Keep source-mask measurements; general topology/intersection validation is required before display",
    )
    digest = science_hash(report.model_dump(mode="json"))
    connection.execute(
        text(
            "INSERT INTO imaging.mesh_qc_reports(id,project_id,patient_id,actor_id,command_key,input_hash,mesh_run_id,report,report_hash) VALUES(:id,:p,:u,:a,:k,:h,:mesh,CAST(:report AS jsonb),:rh)"
        ),
        {
            "id": report.id,
            "p": project,
            "u": patient,
            "a": identity.user_id,
            "k": command_key,
            "h": fingerprint,
            "mesh": original_report.id,
            "report": report.model_dump_json(),
            "rh": digest,
        },
    )
    derive_resource(
        connection,
        identity,
        project,
        patient,
        report.id,
        "mesh_quality_report",
        digest,
        [original_report.output_artifact_id] + ([lod_id] if lod_id else []),
        processing_spec(
            __file__,
            "mesh-quality/1",
            "mesh-display/1",
            {
                "request": value.model_dump(mode="json"),
                "implementation_sha256": hashlib.sha256(
                    Path(__file__).with_name("mesh_quality.py").read_bytes()
                ).hexdigest(),
            },
        ),
    )
    audit(connection, project, report.id, "MESH_QC_RECORDED")
    return report


def read_mesh_qc(connection, identity, project, patient, report_id):
    authorize_patient(connection, identity, project, patient, edit=True)
    row = connection.execute(
        text(
            "SELECT report,report_hash FROM imaging.mesh_qc_reports WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": report_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.report) != row.report_hash:
        raise HTTPException(409)
    return MeshQCReport.model_validate(row.report)


def load_display_mesh(connection, identity, project, patient, report_id, storage):
    report = read_mesh_qc(connection, identity, project, patient, report_id)
    require_resource_action(
        connection, identity, project, patient, report.id, SourceAction.INTERNAL
    )
    if report.status != "validated" or report.output_artifact_id is None:
        raise HTTPException(409, detail="display_geometry_not_validated")
    require_resource_action(
        connection, identity, project, patient, report.output_artifact_id, SourceAction.INTERNAL
    )
    row = connection.execute(
        text(
            "SELECT object_key,object_version,sha256,byte_size FROM ops.artifacts WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": report.output_artifact_id},
    ).one()
    return report, MeshAsset.model_validate_json(
        storage.read(
            StoredObject(project, row.object_key, row.object_version, row.sha256, row.byte_size),
            project,
        )
    )
