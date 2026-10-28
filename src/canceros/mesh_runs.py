"""Private immutable reconstructions, invoked by the shared revision-pinned CPU worker."""

import hashlib
import json
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from canceros.annotation_import import load_annotation_mask
from canceros.contracts import Contract, Hash
from canceros.imaging_ingestion import store_artifact
from canceros.lineage import derive_resource, lock_lineage, processing_spec, require_resource_action
from canceros.measurement_runs import load_usable_measurement
from canceros.mesh_reconstruction import (
    MAX_TRIANGLES,
    MAX_VERTICES,
    MeshError,
    Surface,
    reconstruct,
)
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import canonical_bytes, science_hash
from canceros.source_registry import SourceAction
from canceros.storage import StoredObject


class MeshInput(Contract):
    measurement_id: UUID
    purpose: Literal["engineering_region_preview"] = "engineering_region_preview"


class MeshObject(Contract):
    segmentation_id: UUID
    label: int
    annotation_class: str
    mask_sha256: Hash
    surface: Surface


class MeshAsset(Contract):
    format: Literal["canceros-mesh-json/1"] = "canceros-mesh-json/1"
    objects: list[MeshObject]
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    anatomical_review: Literal["not_established"] = "not_established"


class MeshReport(Contract):
    id: UUID
    measurement_id: UUID
    input_revision: int
    output_artifact_id: UUID
    artifact_sha256: Hash
    byte_size: int
    vertex_count: int
    triangle_count: int
    object_ids: list[UUID]
    frame: Literal["RAS"] = "RAS"
    unit: Literal["mm"] = "mm"
    status: Literal["generated_pending_mesh_qc"] = "generated_pending_mesh_qc"
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    publication: Literal["draft"] = "draft"
    scientific_review: Literal["pending"] = "pending"
    next_action: str = "Run mesh QC before display; retain source-mask measurements"


def create_mesh(connection, identity, project, patient, value: MeshInput, storage, command_key):
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    measurement = load_usable_measurement(
        connection, identity, project, patient, value.measurement_id
    )
    fingerprint = science_hash(value.model_dump(mode="json"))
    prior = connection.execute(
        text(
            "SELECT id,input_hash FROM imaging.mesh_runs WHERE project_id=:p AND patient_id=:u AND actor_id=:a AND command_key=:k"
        ),
        {"p": project, "u": patient, "a": identity.user_id, "k": command_key},
    ).one_or_none()
    if prior:
        if prior.input_hash != fingerprint:
            raise HTTPException(409)
        report = read_mesh(connection, identity, project, patient, prior.id)
        require_resource_action(
            connection,
            identity,
            project,
            patient,
            report.output_artifact_id,
            SourceAction.DERIVATIVE,
        )
        return report
    objects = []
    for selection in measurement.selections:
        annotation, mask = load_annotation_mask(
            connection, identity, project, patient, selection.segmentation_id, storage
        )
        if not annotation.capabilities.numerical_region_volume_allowed:
            raise HTTPException(409)
        try:
            surface = reconstruct(mask, annotation.geometry)
        except MeshError as error:
            raise HTTPException(422, detail=str(error)) from None
        objects.append(
            MeshObject(
                segmentation_id=annotation.id,
                label=annotation.label,
                annotation_class=annotation.annotation.annotation_class,
                mask_sha256=selection.mask_sha256,
                surface=surface,
            )
        )
        if (
            sum(len(o.surface.vertices) for o in objects) > MAX_VERTICES
            or sum(len(o.surface.triangles) for o in objects) > MAX_TRIANGLES
        ):
            raise HTTPException(422, detail="combined_surface_budget_exceeded")
    raw = canonical_bytes(MeshAsset(objects=objects).model_dump(mode="json"))
    artifact, digest = store_artifact(connection, project, patient, raw, storage)
    derive_resource(
        connection,
        identity,
        project,
        patient,
        artifact,
        "mesh",
        digest,
        [measurement.id],
        processing_spec(
            __file__,
            "mesh/1",
            "skimage-0.26.0-lewiner/1",
            {
                "request": value.model_dump(mode="json"),
                "implementation_sha256": hashlib.sha256(
                    Path(__file__).with_name("mesh_reconstruction.py").read_bytes()
                ).hexdigest(),
                "lockfile_sha256": hashlib.sha256(
                    Path(__file__).resolve().parents[2].joinpath("uv.lock").read_bytes()
                ).hexdigest(),
            },
        ),
    )
    report = MeshReport(
        id=uuid4(),
        measurement_id=measurement.id,
        input_revision=measurement.input_revision,
        output_artifact_id=artifact,
        artifact_sha256=digest,
        byte_size=len(raw),
        vertex_count=sum(len(o.surface.vertices) for o in objects),
        triangle_count=sum(len(o.surface.triangles) for o in objects),
        object_ids=[o.segmentation_id for o in objects],
    )
    connection.execute(
        text(
            "INSERT INTO imaging.mesh_runs(id,project_id,patient_id,actor_id,command_key,input_hash,measurement_id,output_artifact_id,report,report_hash) VALUES(:id,:p,:u,:a,:k,:h,:m,:out,CAST(:report AS jsonb),:rh)"
        ),
        {
            "id": report.id,
            "p": project,
            "u": patient,
            "a": identity.user_id,
            "k": command_key,
            "h": fingerprint,
            "m": measurement.id,
            "out": artifact,
            "report": report.model_dump_json(),
            "rh": science_hash(report.model_dump(mode="json")),
        },
    )
    audit(connection, project, report.id, "MESH_RECONSTRUCTED_PRIVATE")
    return report


def read_mesh(connection, identity, project, patient, run_id):
    authorize_patient(connection, identity, project, patient, edit=True)
    row = connection.execute(
        text(
            "SELECT report,report_hash FROM imaging.mesh_runs WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": run_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.report) != row.report_hash:
        raise HTTPException(409)
    return MeshReport.model_validate(row.report)


def load_mesh(connection, identity, project, patient, run_id, storage):
    report = read_mesh(connection, identity, project, patient, run_id)
    require_resource_action(
        connection, identity, project, patient, report.output_artifact_id, SourceAction.INTERNAL
    )
    row = connection.execute(
        text(
            "SELECT object_key,object_version,sha256,byte_size FROM ops.artifacts WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": report.output_artifact_id},
    ).one()
    raw = storage.read(
        StoredObject(project, row.object_key, row.object_version, row.sha256, row.byte_size),
        project,
    )
    if row.sha256 != report.artifact_sha256:
        raise HTTPException(409)
    return report, MeshAsset.model_validate(json.loads(raw))
