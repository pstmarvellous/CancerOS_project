"""Patient/study-owned alignment adapter; numerical overlay is never annotation approval."""

import io
from typing import Literal
from uuid import UUID, uuid4

import numpy as np
from fastapi import HTTPException
from sqlalchemy import text

from canceros.contracts import Contract, Hash
from canceros.imaging_formats import parse_nifti
from canceros.imaging_geometry import CanonicalGeometry, geometry_for
from canceros.imaging_ingestion import read_staged, store_artifact
from canceros.lineage import derive_resource, lock_lineage, processing_spec, require_resource_action
from canceros.mask_alignment import AlignmentConfig, AlignmentReport, align_mask
from canceros.mask_associations import mask_binding
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import science_hash
from canceros.preprocessing_runs import load_image
from canceros.quality import record_technical_validation
from canceros.source_registry import SourceAction
from canceros.storage import StoredObject


class AlignmentInput(Contract):
    association_id: UUID
    mask_file_id: UUID
    target_image_id: UUID
    mask_study_id: UUID
    association_evidence_sha256: Hash
    config: AlignmentConfig


class AlignmentRun(Contract):
    id: UUID
    source_mask_id: UUID
    target_image_id: UUID
    study_id: UUID
    output_artifact_id: UUID | None
    preview_artifact_id: UUID | None
    geometry: CanonicalGeometry | None
    alignment: AlignmentReport | None
    status: Literal["aligned_pending_review", "quarantined"]
    issue_codes: list[str]
    publication: Literal["draft"] = "draft"
    reviewer_acceptance: Literal["pending"] = "pending"
    next_action: str


class OverlayPreview(Contract):
    kind: Literal["SYNTHETIC_ENGINEERING_FIXTURE_OVERLAY"] = "SYNTHETIC_ENGINEERING_FIXTURE_OVERLAY"
    target_shape_xyz: tuple[int, int, int]
    index_z: int
    sampled_x: list[int]
    sampled_y: list[int]
    intensity_rows: list[list[int]]
    label_rows: list[list[int]]
    coordinate_frame: Literal["RAS_mm_via_target_geometry"] = "RAS_mm_via_target_geometry"
    sampling: Literal["nearest_sampled_thumbnail_may_omit_small_regions"] = (
        "nearest_sampled_thumbnail_may_omit_small_regions"
    )
    meaning: Literal["technical_preview_not_anatomical_or_scientific_approval"] = (
        "technical_preview_not_anatomical_or_scientific_approval"
    )


def overlay(image, mask):
    foreground = np.argwhere(mask > 0)
    z = int(np.median(foreground[:, 2])) if len(foreground) else image.shape[2] // 2
    xs = np.unique(np.linspace(0, image.shape[0] - 1, min(64, image.shape[0])).astype(int))
    ys = np.unique(np.linspace(0, image.shape[1] - 1, min(64, image.shape[1])).astype(int))
    values = image[:, :, z][np.ix_(xs, ys)].T
    minimum, maximum = float(values.min()), float(values.max())
    scaled = (
        np.zeros_like(values, dtype=np.uint8)
        if maximum == minimum
        else np.clip((values - minimum) / (maximum - minimum) * 255, 0, 255).astype(np.uint8)
    )
    labels = mask[:, :, z][np.ix_(xs, ys)].T
    return OverlayPreview(
        target_shape_xyz=image.shape,
        index_z=z,
        sampled_x=xs.tolist(),
        sampled_y=ys.tolist(),
        intensity_rows=scaled.tolist(),
        label_rows=labels.tolist(),
    )


def run_alignment(connection, identity, project, patient, value, storage):
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    binding = mask_binding(connection, identity, project, patient, value.association_id)
    if (
        binding.source_mask_id != value.mask_file_id
        or binding.target_image_id != value.target_image_id
        or binding.study_id != value.mask_study_id
        or binding.evidence_sha256 != value.association_evidence_sha256
    ):
        raise HTTPException(409)
    require_resource_action(
        connection, identity, project, patient, binding.id, SourceAction.DERIVATIVE
    )
    target_geometry, image, import_id = load_image(
        connection, identity, project, patient, value.target_image_id, storage
    )
    imported = connection.execute(
        text(
            "SELECT association FROM imaging.imports WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": import_id},
    ).scalar_one()
    if str(value.mask_study_id) != imported["study_id"]:
        raise HTTPException(409)
    mask_row, raw = read_staged(connection, identity, project, patient, value.mask_file_id, storage)
    if str(mask_row["mapping_id"]) != imported["mapping_id"]:
        raise HTTPException(404)
    for artifact in (value.mask_file_id, value.target_image_id):
        require_resource_action(
            connection, identity, project, patient, artifact, SourceAction.DERIVATIVE
        )
    fingerprint = science_hash(value.model_dump(mode="json"))
    prior = connection.execute(
        text(
            "SELECT id FROM imaging.alignment_runs WHERE project_id=:p AND patient_id=:u AND input_hash=:hash"
        ),
        {"p": project, "u": patient, "hash": fingerprint},
    ).scalar_one_or_none()
    if prior:
        previous = read_alignment(connection, identity, project, patient, prior)
        for artifact in (previous.output_artifact_id, previous.preview_artifact_id):
            if artifact:
                require_resource_action(
                    connection, identity, project, patient, artifact, SourceAction.INTERNAL
                )
        return previous
    result, issues = None, []
    try:
        if mask_row["format"] != "nifti" or image.ndim != 3 or target_geometry is None:
            raise ValueError()
        source = parse_nifti(raw)
        result = align_mask(source.array, geometry_for(source), target_geometry, value.config)
        if result.array is None:
            issues = list(result.report.issues)
    except ValueError:
        issues = ["INVALID_MASK_OR_EXPLICIT_3D_TARGET_REQUIRED"]
    artifact, preview_id = None, None
    if result is not None and result.array is not None and not issues:
        output = io.BytesIO()
        np.save(output, result.array, allow_pickle=False)
        artifact, digest = store_artifact(connection, project, patient, output.getvalue(), storage)
        processing = processing_spec(
            __file__,
            "alignment/1",
            "alignment/1",
            {
                "request": value.model_dump(mode="json"),
                "alignment": result.report.model_dump(mode="json"),
            },
        )
        derive_resource(
            connection,
            identity,
            project,
            patient,
            artifact,
            "aligned_mask_pending_annotation",
            digest,
            [binding.id],
            processing,
        )
        record_technical_validation(
            connection,
            identity,
            project,
            patient,
            artifact,
            "pass",
            "alignment/1",
            result.report.model_dump(mode="json"),
        )
        preview = overlay(image, result.array)
        preview_id, preview_hash = store_artifact(
            connection, project, patient, preview.model_dump_json().encode(), storage
        )
        derive_resource(
            connection,
            identity,
            project,
            patient,
            preview_id,
            "mask_overlay_preview",
            preview_hash,
            [artifact, value.target_image_id],
            processing,
        )
    report = AlignmentRun(
        id=uuid4(),
        source_mask_id=value.mask_file_id,
        target_image_id=value.target_image_id,
        study_id=value.mask_study_id,
        output_artifact_id=artifact,
        preview_artifact_id=preview_id,
        geometry=target_geometry if artifact else None,
        alignment=result.report if result else None,
        status="quarantined" if issues else "aligned_pending_review",
        issue_codes=issues,
        next_action="Review source grid, labels, study evidence and clipping/volume errors; supply corrected metadata"
        if issues
        else "Inspect the aligned overlay and annotation meaning; technical alignment is not scientific acceptance",
    )
    connection.execute(
        text(
            "INSERT INTO imaging.alignment_runs(id,project_id,patient_id,source_mask_id,target_image_id,output_artifact_id,preview_artifact_id,input_hash,report,report_hash) VALUES(:id,:p,:u,:source,:target,:output,:preview,:hash,CAST(:report AS jsonb),:rh)"
        ),
        {
            "id": report.id,
            "p": project,
            "u": patient,
            "source": value.mask_file_id,
            "target": value.target_image_id,
            "output": artifact,
            "preview": preview_id,
            "hash": fingerprint,
            "report": report.model_dump_json(),
            "rh": science_hash(report.model_dump(mode="json")),
        },
    )
    audit(connection, project, report.id, "MASK_ALIGNMENT_RUN")
    return report


def read_alignment(connection, identity, project, patient, run_id):
    authorize_patient(connection, identity, project, patient, edit=True)
    row = connection.execute(
        text(
            "SELECT report,report_hash FROM imaging.alignment_runs WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": run_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.report) != row.report_hash:
        raise HTTPException(409)
    return AlignmentRun.model_validate(row.report)


def read_overlay(connection, identity, project, patient, run_id, storage):
    report = read_alignment(connection, identity, project, patient, run_id)
    if not report.preview_artifact_id:
        raise HTTPException(409)
    require_resource_action(
        connection, identity, project, patient, report.preview_artifact_id, SourceAction.INTERNAL
    )
    row = (
        connection.execute(
            text("SELECT * FROM ops.artifacts WHERE project_id=:p AND patient_id=:u AND id=:id"),
            {"p": project, "u": patient, "id": report.preview_artifact_id},
        )
        .mappings()
        .one()
    )
    raw = storage.read(
        StoredObject(
            project, row["object_key"], row["object_version"], row["sha256"], row["byte_size"]
        ),
        project,
    )
    return OverlayPreview.model_validate_json(raw)


def load_aligned_mask(connection, identity, project, patient, run_id, storage):
    report = read_alignment(connection, identity, project, patient, run_id)
    if (
        report.status != "aligned_pending_review"
        or report.output_artifact_id is None
        or report.geometry is None
    ):
        raise HTTPException(409)
    require_resource_action(
        connection, identity, project, patient, report.output_artifact_id, SourceAction.INTERNAL
    )
    row = (
        connection.execute(
            text("SELECT * FROM ops.artifacts WHERE project_id=:p AND patient_id=:u AND id=:id"),
            {"p": project, "u": patient, "id": report.output_artifact_id},
        )
        .mappings()
        .one()
    )
    raw = storage.read(
        StoredObject(
            project, row["object_key"], row["object_version"], row["sha256"], row["byte_size"]
        ),
        project,
    )
    array = np.load(io.BytesIO(raw), allow_pickle=False)
    if array.dtype != np.uint16 or tuple(array.shape) != report.geometry.shape_xyz:
        raise HTTPException(409)
    array.setflags(write=False)
    return report, array
