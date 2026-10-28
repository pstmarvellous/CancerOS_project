"""Authenticated imaging staging/preview/confirmation; private bytes are never returned."""

from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Header, Response

from canceros.alignment_runs import (
    AlignmentInput,
    AlignmentRun,
    OverlayPreview,
    read_alignment,
    read_overlay,
    run_alignment,
)
from canceros.annotation_contracts import AnnotationInput
from canceros.annotation_import import (
    AnnotationBatch,
    SegmentationAnnotation,
    import_annotations,
    read_annotation,
    read_annotation_batch,
)
from canceros.identity import authenticate
from canceros.imaging_ingestion import (
    ImagingImportReport,
    ImagingPreviewInput,
    ImagingStageInput,
    ImagingStageReceipt,
    confirm_import,
    preview_imaging,
    read_import,
    stage_imaging,
)
from canceros.imaging_jobs import (
    ImagingJobInput,
    ImagingJobRecord,
    cancel_imaging_job,
    enqueue_imaging,
    read_imaging_job,
)
from canceros.imaging_storage import (
    AssetGrant,
    AssetGrantInput,
    CleanupReport,
    apply_cleanup,
    grant_asset,
    plan_cleanup,
)
from canceros.imaging_volumes import (
    GeometryReport,
    GeometryValidationInput,
    read_geometry,
    validate_volume,
)
from canceros.lesion_tracking import (
    AssociationEvent,
    AssociationInput,
    LesionIdentity,
    LesionInput,
    MeasurementSeries,
    SeriesInput,
    SeriesView,
    append_association,
    create_lesion,
    create_series,
    list_associations,
    list_lesions,
    read_association,
    read_lesion,
    read_series,
)
from canceros.mask_associations import (
    MaskAssociation,
    MaskAssociationInput,
    bind_mask,
    mask_binding,
)
from canceros.measurement_runs import (
    MeasurementInput,
    MeasurementReport,
    create_measurement,
    read_measurement,
)
from canceros.mesh_quality_runs import MeshQCReport, load_display_mesh, read_mesh_qc
from canceros.mesh_runs import MeshAsset, MeshReport, load_mesh, read_mesh
from canceros.persistence import engine_for
from canceros.preprocessing_runs import (
    PreprocessInput,
    PreprocessRun,
    read_preprocessing,
    run_preprocessing,
)
from canceros.registration_runs import RegistrationReport, read_registration
from canceros.segmentation_reviews import (
    SegmentationQCInput,
    SegmentationQCReport,
    read_segmentation_qc,
    run_segmentation_qc,
)
from canceros.storage import PrivateStorage


def imaging_routes(config, memberships):
    router = APIRouter(prefix="/api/v1/projects/{project_id}/patients/{patient_id}")

    @contextmanager
    def session(header):
        identity = authenticate(header, config, memberships)
        engine = engine_for(config)
        try:
            with engine.begin() as connection:
                yield connection, identity
        finally:
            engine.dispose()

    @router.post("/imaging-files", response_model=ImagingStageReceipt, status_code=201)
    def stage(
        project_id: UUID,
        patient_id: UUID,
        value: ImagingStageInput,
        response: Response,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = stage_imaging(
                connection, identity, project_id, patient_id, value, PrivateStorage(config)
            )
            # The receipt is a staging command result, not a public file-download resource.
            return result

    @router.post("/imaging-import-previews", response_model=ImagingImportReport, status_code=201)
    def preview(
        project_id: UUID,
        patient_id: UUID,
        value: ImagingPreviewInput,
        response: Response,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = preview_imaging(
                connection, identity, project_id, patient_id, value, PrivateStorage(config), config
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/imaging-imports/{result.id}"
            )
            return result

    @router.get("/imaging-imports/{import_id}", response_model=ImagingImportReport)
    def detail(
        project_id: UUID,
        patient_id: UUID,
        import_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_import(connection, identity, project_id, patient_id, import_id)

    @router.post("/imaging-imports/{import_id}/confirmations", response_model=ImagingImportReport)
    def confirm(
        project_id: UUID,
        patient_id: UUID,
        import_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return confirm_import(connection, identity, project_id, patient_id, import_id)

    @router.post("/geometry-validations", response_model=GeometryReport, status_code=201)
    def geometry_validation(
        project_id: UUID,
        patient_id: UUID,
        value: GeometryValidationInput,
        response: Response,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = validate_volume(
                connection, identity, project_id, patient_id, value, PrivateStorage(config)
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/geometry-validations/{result.id}"
            )
            return result

    @router.get("/geometry-validations/{report_id}", response_model=GeometryReport)
    def geometry_detail(
        project_id: UUID,
        patient_id: UUID,
        report_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_geometry(connection, identity, project_id, patient_id, report_id)

    @router.post("/preprocessing-runs", response_model=PreprocessRun, status_code=201)
    def preprocessing(
        project_id: UUID,
        patient_id: UUID,
        value: PreprocessInput,
        response: Response,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = run_preprocessing(
                connection, identity, project_id, patient_id, value, PrivateStorage(config)
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/preprocessing-runs/{result.id}"
            )
            return result

    @router.get("/preprocessing-runs/{run_id}", response_model=PreprocessRun)
    def preprocessing_detail(
        project_id: UUID,
        patient_id: UUID,
        run_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_preprocessing(connection, identity, project_id, patient_id, run_id)

    @router.post("/mask-alignments", response_model=AlignmentRun, status_code=201)
    def alignment(
        project_id: UUID,
        patient_id: UUID,
        value: AlignmentInput,
        response: Response,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = run_alignment(
                connection, identity, project_id, patient_id, value, PrivateStorage(config)
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/mask-alignments/{result.id}"
            )
            return result

    @router.get("/mask-alignments/{run_id}", response_model=AlignmentRun)
    def alignment_detail(
        project_id: UUID,
        patient_id: UUID,
        run_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_alignment(connection, identity, project_id, patient_id, run_id)

    @router.get("/mask-alignments/{run_id}/overlay", response_model=OverlayPreview)
    def alignment_overlay(
        project_id: UUID,
        patient_id: UUID,
        run_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_overlay(
                connection, identity, project_id, patient_id, run_id, PrivateStorage(config)
            )

    @router.post("/annotation-batches", response_model=AnnotationBatch, status_code=201)
    def annotations(
        project_id: UUID,
        patient_id: UUID,
        value: AnnotationInput,
        response: Response,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = import_annotations(
                connection, identity, project_id, patient_id, value, PrivateStorage(config)
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/annotation-batches/{result.id}"
            )
            return result

    @router.get("/annotation-batches/{batch_id}", response_model=AnnotationBatch)
    def annotation_batch(
        project_id: UUID,
        patient_id: UUID,
        batch_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_annotation_batch(connection, identity, project_id, patient_id, batch_id)

    @router.get("/segmentations/{segmentation_id}", response_model=SegmentationAnnotation)
    def segmentation(
        project_id: UUID,
        patient_id: UUID,
        segmentation_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_annotation(connection, identity, project_id, patient_id, segmentation_id)

    @router.post("/mask-associations", response_model=MaskAssociation, status_code=201)
    def mask_association(
        project_id: UUID,
        patient_id: UUID,
        value: MaskAssociationInput,
        response: Response,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = bind_mask(
                connection, identity, project_id, patient_id, value, PrivateStorage(config)
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/mask-associations/{result.id}"
            )
            return result

    @router.get("/mask-associations/{association_id}", response_model=MaskAssociation)
    def mask_association_detail(
        project_id: UUID,
        patient_id: UUID,
        association_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return mask_binding(connection, identity, project_id, patient_id, association_id)

    @router.post("/segmentation-qc-reports", response_model=SegmentationQCReport, status_code=201)
    def segmentation_qc(
        project_id: UUID,
        patient_id: UUID,
        value: SegmentationQCInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = run_segmentation_qc(
                connection,
                identity,
                project_id,
                patient_id,
                value,
                PrivateStorage(config),
                idempotency_key,
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/segmentation-qc-reports/{result.id}"
            )
            return result

    @router.get("/segmentation-qc-reports/{report_id}", response_model=SegmentationQCReport)
    def segmentation_qc_detail(
        project_id: UUID,
        patient_id: UUID,
        report_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_segmentation_qc(connection, identity, project_id, patient_id, report_id)

    @router.post("/imaging-jobs", response_model=ImagingJobRecord, status_code=202)
    def imaging_job(
        project_id: UUID,
        patient_id: UUID,
        value: ImagingJobInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = enqueue_imaging(
                connection,
                identity,
                project_id,
                patient_id,
                value,
                idempotency_key,
                PrivateStorage(config),
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/imaging-jobs/{result.id}"
            )
            return result

    @router.get("/imaging-jobs/{job_id}", response_model=ImagingJobRecord)
    def imaging_job_detail(
        project_id: UUID,
        patient_id: UUID,
        job_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_imaging_job(connection, identity, project_id, patient_id, job_id)

    @router.post("/imaging-jobs/{job_id}/cancellations", response_model=ImagingJobRecord)
    def imaging_job_cancel(
        project_id: UUID,
        patient_id: UUID,
        job_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return cancel_imaging_job(connection, identity, project_id, patient_id, job_id)

    @router.post("/artifacts/{artifact_id}/read-grants", response_model=AssetGrant)
    def imaging_grant(
        project_id: UUID,
        patient_id: UUID,
        artifact_id: UUID,
        value: AssetGrantInput,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return grant_asset(
                connection,
                identity,
                project_id,
                patient_id,
                artifact_id,
                value,
                PrivateStorage(config),
            )

    @router.post("/imaging-cleanup-plans", response_model=CleanupReport, status_code=201)
    def cleanup_plan(
        project_id: UUID, patient_id: UUID, authorization: str | None = Header(default=None)
    ):
        with session(authorization) as (connection, identity):
            return plan_cleanup(
                connection, identity, project_id, patient_id, PrivateStorage(config)
            )

    @router.post("/imaging-cleanup-plans/{plan_id}/applications", response_model=CleanupReport)
    def cleanup_apply(
        project_id: UUID,
        patient_id: UUID,
        plan_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return apply_cleanup(
                connection, identity, project_id, patient_id, plan_id, PrivateStorage(config)
            )

    @router.post("/physical-measurements", response_model=MeasurementReport, status_code=201)
    def physical_measurement(
        project_id: UUID,
        patient_id: UUID,
        value: MeasurementInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = create_measurement(
                connection,
                identity,
                project_id,
                patient_id,
                value,
                PrivateStorage(config),
                idempotency_key,
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/physical-measurements/{result.id}"
            )
            return result

    @router.get("/physical-measurements/{report_id}", response_model=MeasurementReport)
    def physical_measurement_detail(
        project_id: UUID,
        patient_id: UUID,
        report_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_measurement(connection, identity, project_id, patient_id, report_id)

    @router.get("/mesh-runs/{run_id}", response_model=MeshReport)
    def get_mesh(
        project_id: UUID,
        patient_id: UUID,
        run_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_mesh(connection, identity, project_id, patient_id, run_id)

    @router.get("/mesh-runs/{run_id}/asset", response_model=MeshAsset)
    def get_mesh_asset(
        project_id: UUID,
        patient_id: UUID,
        run_id: UUID,
        response: Response,
        authorization: str | None = Header(default=None),
    ):
        response.headers["Cache-Control"] = "no-store"
        with session(authorization) as (connection, identity):
            return load_mesh(
                connection, identity, project_id, patient_id, run_id, PrivateStorage(config)
            )[1]

    @router.get("/mesh-qc-reports/{report_id}", response_model=MeshQCReport)
    def get_mesh_qc(
        project_id: UUID,
        patient_id: UUID,
        report_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_mesh_qc(connection, identity, project_id, patient_id, report_id)

    @router.get("/mesh-qc-reports/{report_id}/asset", response_model=MeshAsset)
    def get_display_mesh(
        project_id: UUID,
        patient_id: UUID,
        report_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return load_display_mesh(
                connection, identity, project_id, patient_id, report_id, PrivateStorage(config)
            )[1]

    @router.get("/registrations/{report_id}", response_model=RegistrationReport)
    def get_registration(
        project_id: UUID,
        patient_id: UUID,
        report_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_registration(connection, identity, project_id, patient_id, report_id)

    @router.post("/lesions", response_model=LesionIdentity, status_code=201)
    def post_lesion(
        project_id: UUID,
        patient_id: UUID,
        value: LesionInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = create_lesion(
                connection,
                identity,
                project_id,
                patient_id,
                value,
                PrivateStorage(config),
                idempotency_key,
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/lesions/{result.id}"
            )
            return result

    @router.get("/lesions", response_model=list[LesionIdentity])
    def get_lesions(
        project_id: UUID, patient_id: UUID, authorization: str | None = Header(default=None)
    ):
        with session(authorization) as (connection, identity):
            return list_lesions(connection, identity, project_id, patient_id)

    @router.get("/lesions/{lesion_id}", response_model=LesionIdentity)
    def get_lesion(
        project_id: UUID,
        patient_id: UUID,
        lesion_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_lesion(connection, identity, project_id, patient_id, lesion_id)

    @router.post("/lesion-associations", response_model=AssociationEvent, status_code=201)
    def post_lesion_association(
        project_id: UUID,
        patient_id: UUID,
        value: AssociationInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = append_association(
                connection,
                identity,
                project_id,
                patient_id,
                value,
                PrivateStorage(config),
                idempotency_key,
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/lesion-associations/{result.id}"
            )
            return result

    @router.get("/lesion-associations", response_model=list[AssociationEvent])
    def get_lesion_associations(
        project_id: UUID, patient_id: UUID, authorization: str | None = Header(default=None)
    ):
        with session(authorization) as (connection, identity):
            return list_associations(connection, identity, project_id, patient_id)

    @router.get("/lesion-associations/{event_id}", response_model=AssociationEvent)
    def get_lesion_association(
        project_id: UUID,
        patient_id: UUID,
        event_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_association(connection, identity, project_id, patient_id, event_id)

    @router.post("/measurement-series", response_model=MeasurementSeries, status_code=201)
    def post_measurement_series(
        project_id: UUID,
        patient_id: UUID,
        value: SeriesInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = create_series(
                connection,
                identity,
                project_id,
                patient_id,
                value,
                PrivateStorage(config),
                idempotency_key,
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/measurement-series/{result.id}"
            )
            return result

    @router.get("/measurement-series/{series_id}", response_model=SeriesView)
    def get_measurement_series(
        project_id: UUID,
        patient_id: UUID,
        series_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_series(connection, identity, project_id, patient_id, series_id)

    return router
