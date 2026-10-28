"""Fixture-only paired-exam rigid registration; numerical fit never grants anatomical overlay."""

import io
from itertools import product
from typing import Annotated, Literal
from uuid import UUID, uuid4

import numpy as np
from fastapi import HTTPException
from pydantic import Field, model_validator
from sqlalchemy import text

from canceros.annotation_import import load_annotation_mask
from canceros.contracts import Contract, Hash
from canceros.identity import authorize_project
from canceros.imaging_geometry import index_to_world, world_to_index
from canceros.imaging_ingestion import read_import, store_artifact
from canceros.lineage import (
    derive_resource,
    get_resource,
    lock_lineage,
    processing_spec,
    require_resource_action,
)
from canceros.mask_alignment import AlignmentConfig, AlignmentReport, align_mask
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import load_revision, science_hash
from canceros.preprocessing_runs import load_image
from canceros.rigid_registration import RegistrationError, RigidRegistrationReport, fit_rigid
from canceros.source_registry import SourceAction

Point = tuple[float, float, float]
FitPoints = Annotated[list[Point], Field(min_length=4, max_length=32)]
ReviewPoints = Annotated[list[Point], Field(min_length=1, max_length=32)]


class RegistrationInput(Contract):
    fixed_image_id: UUID
    moving_image_id: UUID
    moving_segmentation_id: UUID | None = None
    moving_qc_report_id: UUID | None = None
    fixed_relative_day: Annotated[int, Field(strict=True, ge=-3650, le=3650)]
    moving_relative_day: Annotated[int, Field(strict=True, ge=-3650, le=3650)]
    time_association_evidence_sha256: Hash
    association_basis: Literal["administrator_engineering_fixture_attestation"] = (
        "administrator_engineering_fixture_attestation"
    )
    moving_landmarks: FitPoints
    fixed_landmarks: FitPoints
    moving_holdout_landmarks: ReviewPoints
    fixed_holdout_landmarks: ReviewPoints

    @model_validator(mode="after")
    def paired_mask_evidence(self):
        if (self.moving_segmentation_id is None) != (self.moving_qc_report_id is None):
            raise ValueError("selected_mask_requires_pinned_qc_report")
        return self


class RegistrationReport(Contract):
    id: UUID
    input_revision: int
    fixed_image_id: UUID
    moving_image_id: UUID
    fixed_study_id: UUID
    moving_study_id: UUID
    fixed_relative_day: int
    moving_relative_day: int
    time_basis: Literal["engineering_relative_not_observed_examination_times"] = (
        "engineering_relative_not_observed_examination_times"
    )
    sequence: str
    status: Literal["fixture_aligned_pending_review", "blocked"]
    numerical: RigidRegistrationReport
    mapped_moving_bounds_ras_mm: tuple[Point, Point] | None
    fixed_bounds_ras_mm: tuple[Point, Point]
    bounds_overlap_fraction: float | None
    bounds_metric: Literal["axis_aligned_world_image_bounds_not_anatomical_overlap"] = (
        "axis_aligned_world_image_bounds_not_anatomical_overlap"
    )
    method: Literal["rigid_paired_landmarks_no_intensity_optimization"] = (
        "rigid_paired_landmarks_no_intensity_optimization"
    )
    image_interpolation: Literal["not_performed_original_images_preserved"] = (
        "not_performed_original_images_preserved"
    )
    mask_alignment: AlignmentReport | None
    output_artifact_id: UUID | None
    genuine_exam_pair_verified: Literal[False] = False
    anatomical_review: Literal["pending"] = "pending"
    overlay_allowed: Literal[False] = False
    scalar_comparison_policy: Literal[
        "independently_valid_measurements_and_reviewed_lesion_identity_required"
    ] = "independently_valid_measurements_and_reviewed_lesion_identity_required"
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    scientific_review: Literal["pending"] = "pending"
    publication: Literal["draft"] = "draft"
    issues: list[str]
    next_action: str


def image_pair(connection, identity, project, patient, value, storage):
    result = []
    for image in (value.fixed_image_id, value.moving_image_id):
        resource = get_resource(connection, identity, project, patient, image)
        if resource["origin"] != "SYNTHETIC_GENERATED":
            raise HTTPException(409, detail="D02_genuine_pair_and_source_rights_not_established")
        require_resource_action(
            connection, identity, project, patient, image, SourceAction.DERIVATIVE
        )
        geometry, array, import_id = load_image(
            connection, identity, project, patient, image, storage
        )
        imported = read_import(connection, identity, project, patient, import_id)
        if array.ndim != 3 or geometry.phase_count is not None:
            raise HTTPException(409, detail="select_explicit_three_dimensional_phase_first")
        result.append((geometry, imported))
    fixed, moving = result
    if value.fixed_image_id == value.moving_image_id or fixed[1].study_id == moving[1].study_id:
        raise HTTPException(409, detail="same_examination_phases_are_not_longitudinal")
    if fixed[1].sequence == "unknown" or fixed[1].sequence != moving[1].sequence:
        raise HTTPException(409, detail="sequence_correspondence_required")
    if value.moving_relative_day <= value.fixed_relative_day:
        raise HTTPException(422, detail="strictly_later_engineering_exam_time_required")
    return fixed, moving


def _bounds(geometry, transform=None):
    corners = np.array(list(product(*[(-0.5, size - 0.5) for size in geometry.shape_xyz])))
    world = index_to_world(geometry, corners)
    if transform is not None:
        t = np.asarray(transform)
        world = world @ t[:3, :3].T + t[:3, 3]
    return world.min(axis=0), world.max(axis=0)


def _point(row) -> Point:
    return float(row[0]), float(row[1]), float(row[2])


def _points_inside(geometry, points):
    values = np.asarray(points)
    if not np.isfinite(values).all():
        return False
    indices = world_to_index(geometry, values)
    return bool(
        np.all(indices >= -0.5 - 1e-7)
        and np.all(indices <= np.array(geometry.shape_xyz) - 0.5 + 1e-7)
    )


def run_registration(connection, identity, project, patient, value, storage, command_key, revision):
    authorize_project(identity, project, "admin")
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    load_revision(connection, project, patient, revision)
    fixed, moving = image_pair(connection, identity, project, patient, value, storage)
    parents = [value.fixed_image_id, value.moving_image_id]
    mask_source = None
    if value.moving_segmentation_id:
        annotation, mask = load_annotation_mask(
            connection, identity, project, patient, value.moving_segmentation_id, storage
        )
        if (
            annotation.source_image_id != value.moving_image_id
            or not annotation.capabilities.numerical_region_volume_allowed
        ):
            raise HTTPException(409)
        require_resource_action(
            connection, identity, project, patient, annotation.id, SourceAction.DERIVATIVE
        )
        parents.append(annotation.id)
        event = connection.execute(
            text(
                "SELECT checks FROM source.technical_validations WHERE project_id=:p AND patient_id=:u AND resource_id=:id AND rule_version='segmentation-qc/1' ORDER BY sequence DESC LIMIT 1"
            ),
            {"p": project, "u": patient, "id": annotation.id},
        ).scalar_one_or_none()
        if not event or not event.get("qc_report_id"):
            raise HTTPException(409)
        qc_id = UUID(event["qc_report_id"])
        if qc_id != value.moving_qc_report_id:
            raise HTTPException(409, detail="pinned_qc_changed_requeue_with_reviewed_inputs")
        require_resource_action(
            connection, identity, project, patient, qc_id, SourceAction.DERIVATIVE
        )
        parents.append(qc_id)
        mask_source = (annotation, mask)
    fingerprint = science_hash({"request": value.model_dump(mode="json"), "revision": revision})
    processing_parameters = {
        "request_sha256": fingerprint,
        "revision": revision,
        "fixed_image_id": str(value.fixed_image_id),
        "moving_image_id": str(value.moving_image_id),
        "moving_segmentation_id": str(value.moving_segmentation_id)
        if value.moving_segmentation_id
        else None,
        "moving_qc_report_id": str(value.moving_qc_report_id)
        if value.moving_qc_report_id
        else None,
        "time_association_evidence_sha256": value.time_association_evidence_sha256,
        "landmark_policy": "private_fit_and_independent_holdout_points_not_returned",
    }
    prior = connection.execute(
        text(
            "SELECT id,input_hash FROM imaging.registration_runs WHERE project_id=:p AND patient_id=:u AND actor_id=:a AND command_key=:k"
        ),
        {"p": project, "u": patient, "a": identity.user_id, "k": command_key},
    ).one_or_none()
    if prior:
        if prior.input_hash != fingerprint:
            raise HTTPException(409)
        require_resource_action(
            connection, identity, project, patient, prior.id, SourceAction.INTERNAL
        )
        return read_registration(connection, identity, project, patient, prior.id)
    if not (
        _points_inside(fixed[0], value.fixed_landmarks + value.fixed_holdout_landmarks)
        and _points_inside(moving[0], value.moving_landmarks + value.moving_holdout_landmarks)
    ):
        raise HTTPException(422, detail="landmarks_must_be_inside_their_declared_image_grids")
    try:
        numerical = fit_rigid(
            value.moving_landmarks,
            value.fixed_landmarks,
            review_moving=value.moving_holdout_landmarks,
            review_fixed=value.fixed_holdout_landmarks,
        )
    except RegistrationError as error:
        raise HTTPException(422, detail=str(error)) from None
    fixed_bounds = _bounds(fixed[0])
    mapped = (
        _bounds(moving[0], numerical.moving_to_fixed_world)
        if numerical.moving_to_fixed_world
        else None
    )
    overlap = None
    issues = []
    if mapped:
        intersection = np.maximum(
            0, np.minimum(mapped[1], fixed_bounds[1]) - np.maximum(mapped[0], fixed_bounds[0])
        )
        overlap = float(
            np.prod(intersection)
            / min(np.prod(mapped[1] - mapped[0]), np.prod(fixed_bounds[1] - fixed_bounds[0]))
        )
        if overlap < 0.1:
            issues.append("insufficient_transformed_image_bounds_overlap")
    output, alignment = None, None
    valid = numerical.status == "pass" and not issues
    if valid and mask_source:
        annotation, mask = mask_source
        aligned = align_mask(
            mask,
            annotation.geometry,
            fixed[0],
            AlignmentConfig(
                expected_labels=(1,),
                source_to_target_world=numerical.moving_to_fixed_world,
                transform_kind="rigid",
                mode="nearest_neighbor",
            ),
        )
        alignment = aligned.report
        if aligned.report.status == "pass" and aligned.array is not None:
            buffer = io.BytesIO()
            np.save(buffer, aligned.array, allow_pickle=False)
            output, digest = store_artifact(
                connection, project, patient, buffer.getvalue(), storage
            )
            derive_resource(
                connection,
                identity,
                project,
                patient,
                output,
                "registration_mask_preview_pending_review",
                digest,
                parents,
                processing_spec(
                    __file__,
                    "rigid-registration-mask/1",
                    "registration/1",
                    processing_parameters,
                ),
            )
        else:
            valid = False
            issues.extend(aligned.report.issues)
    issues.extend(numerical.reasons)
    report = RegistrationReport(
        id=uuid4(),
        input_revision=revision,
        fixed_image_id=value.fixed_image_id,
        moving_image_id=value.moving_image_id,
        fixed_study_id=fixed[1].study_id,
        moving_study_id=moving[1].study_id,
        fixed_relative_day=value.fixed_relative_day,
        moving_relative_day=value.moving_relative_day,
        sequence=fixed[1].sequence,
        status="fixture_aligned_pending_review" if valid else "blocked",
        numerical=numerical,
        mapped_moving_bounds_ras_mm=(_point(mapped[0]), _point(mapped[1])) if mapped else None,
        fixed_bounds_ras_mm=(_point(fixed_bounds[0]), _point(fixed_bounds[1])),
        bounds_overlap_fraction=overlap,
        mask_alignment=alignment,
        output_artifact_id=output,
        issues=sorted(set(issues)),
        next_action="D02 needs a genuine distinct-exam pair, reviewed identity/time/sequence and anatomical overlay review; use original side-by-side views and independently eligible scalar measures",
    )
    digest = science_hash(report.model_dump(mode="json"))
    connection.execute(
        text(
            "INSERT INTO imaging.registration_runs(id,project_id,patient_id,actor_id,command_key,input_hash,input_revision,fixed_image_id,moving_image_id,report,report_hash) VALUES(:id,:p,:u,:a,:k,:h,:r,:f,:m,CAST(:report AS jsonb),:rh)"
        ),
        {
            "id": report.id,
            "p": project,
            "u": patient,
            "a": identity.user_id,
            "k": command_key,
            "h": fingerprint,
            "r": revision,
            "f": value.fixed_image_id,
            "m": value.moving_image_id,
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
        "registration_report",
        digest,
        parents + ([output] if output else []),
        processing_spec(
            __file__,
            "rigid-landmarks/1",
            "registration/1",
            processing_parameters,
        ),
    )
    audit(connection, project, report.id, "FIXTURE_REGISTRATION_RECORDED")
    return report


def read_registration(connection, identity, project, patient, report_id):
    authorize_patient(connection, identity, project, patient, edit=True)
    row = connection.execute(
        text(
            "SELECT report,report_hash FROM imaging.registration_runs WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": report_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.report) != row.report_hash:
        raise HTTPException(409)
    return RegistrationReport.model_validate(row.report)
