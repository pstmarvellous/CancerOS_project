"""Study/acquisition and segmentation discovery reads over owned imports."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text

from canceros.contracts import Contract
from canceros.patient_linkage import authorize_patient


class StudySummary(Contract):
    study_id: str
    import_count: int
    series_count: int
    status: str
    next_action: str = "select_study_for_geometry_or_segmentation_review"


class StudyPage(Contract):
    items: tuple[StudySummary, ...]


class AcquisitionSummary(Contract):
    import_id: UUID
    study_id: UUID
    series_id: UUID
    file_count: int
    status: str
    frame_shape: list[int]
    orientation: str


class ImportSummary(Contract):
    import_id: UUID
    study_id: UUID
    series_id: UUID
    sequence: str
    format: str
    status: str
    issue_codes: list[str]
    next_action: str = "review_source_and_provenance_then_confirm_or_run_geometry"


class ImportPage(Contract):
    items: tuple[ImportSummary, ...]


class SegmentationDiscovery(Contract):
    segmentation_id: UUID
    batch_id: UUID
    source_image_id: UUID
    study_id: UUID
    label_value: int
    mask_type: str
    qc_status: str
    next_action: str = "open_segmentation_qc_or_measurement_selection"


def list_studies(c, i, p: UUID, u: UUID) -> StudyPage:
    authorize_patient(c, i, p, u)
    rows = (
        c.execute(
            text(
                "SELECT a.study_id AS study,COUNT(DISTINCT a.import_id) AS imports,"
                "COUNT(DISTINCT a.series_id) AS series "
                "FROM imaging.associations a WHERE a.project_id=:p AND a.patient_id=:u "
                "GROUP BY a.study_id ORDER BY a.study_id"
            ),
            {"p": p, "u": u},
        )
        .mappings()
        .all()
    )
    return StudyPage(
        items=tuple(
            StudySummary(
                study_id=str(r["study"]),
                import_count=r["imports"],
                series_count=r["series"],
                status="associated",
            )
            for r in rows
        )
    )


def read_acquisition(c, i, p: UUID, u: UUID, import_id: UUID) -> AcquisitionSummary:
    from canceros.imaging_ingestion import read_import

    report = read_import(c, i, p, u, import_id)
    assoc = (
        c.execute(
            text(
                "SELECT study_id,series_id FROM imaging.associations WHERE project_id=:p AND patient_id=:u AND import_id=:id"
            ),
            {"p": p, "u": u, "id": import_id},
        )
        .mappings()
        .one_or_none()
    )
    if assoc is None:
        raise HTTPException(404)
    return AcquisitionSummary(
        import_id=import_id,
        study_id=assoc["study_id"],
        series_id=assoc["series_id"],
        file_count=len(report.file_ids),
        status=report.status,
        frame_shape=list(report.dimensions or []),
        orientation="unknown",
    )


def discovery_segmentations(c, i, p: UUID, u: UUID) -> list[SegmentationDiscovery]:
    from canceros.annotation_import import read_annotation

    authorize_patient(c, i, p, u)
    ids = (
        c.execute(
            text(
                "SELECT id FROM imaging.segmentations WHERE project_id=:p AND patient_id=:u ORDER BY id"
            ),
            {"p": p, "u": u},
        )
        .scalars()
        .all()
    )
    if not ids:
        raise HTTPException(404)
    found = []
    for segmentation_id in ids:
        try:
            annotation = read_annotation(c, i, p, u, segmentation_id)
        except HTTPException:
            continue
        found.append(
            SegmentationDiscovery(
                segmentation_id=annotation.id,
                batch_id=annotation.batch_id,
                source_image_id=annotation.source_image_id,
                study_id=annotation.study_id,
                label_value=annotation.label,
                mask_type=annotation.annotation.annotation_class,
                qc_status=annotation.technical_qc,
            )
        )
    if not found:
        raise HTTPException(404)
    return found


def list_imports(c, i, p: UUID, u: UUID) -> ImportPage:
    from canceros.imaging_ingestion import read_import

    authorize_patient(c, i, p, u)
    ids = (
        c.execute(
            text(
                "SELECT a.import_id AS id FROM imaging.associations a WHERE a.project_id=:p AND a.patient_id=:u GROUP BY a.import_id ORDER BY a.import_id"
            ),
            {"p": p, "u": u},
        )
        .scalars()
        .all()
    )
    items = []
    for import_id in ids:
        try:
            report = read_import(c, i, p, u, import_id)
        except HTTPException:
            continue
        items.append(
            ImportSummary(
                import_id=report.id,
                study_id=report.study_id,
                series_id=report.series_id,
                sequence=report.sequence,
                format=report.format,
                status=report.status,
                issue_codes=list(report.issue_codes),
            )
        )
    return ImportPage(items=tuple(items))


def lesion_geometry(c, i, p: UUID, u: UUID, lesion_id: UUID):
    """Resolve owned immutable report references; never reinterpret IDs as QC IDs."""
    from canceros.lesion_tracking import read_lesion
    from canceros.lineage import require_resource_action
    from canceros.measurement_runs import load_usable_measurement
    from canceros.mesh_quality_runs import read_mesh_qc
    from canceros.source_registry import SourceAction

    lesion = read_lesion(c, i, p, u, lesion_id)
    require_resource_action(c, i, p, u, lesion.id, SourceAction.INTERNAL)
    ids = (
        c.execute(
            text(
                "SELECT q.id FROM imaging.mesh_qc_reports q "
                "JOIN imaging.mesh_runs r ON (r.project_id,r.patient_id,r.id)="
                "(q.project_id,q.patient_id,q.mesh_run_id) "
                "JOIN imaging.measurement_reports m ON (m.project_id,m.patient_id,m.id)="
                "(r.project_id,r.patient_id,r.measurement_id) "
                "WHERE q.project_id=:p AND q.patient_id=:u "
                "AND m.report->'selections' @> CAST(:selection AS jsonb) "
                "ORDER BY (q.report->>'status'='validated') DESC,q.id LIMIT 101"
            ),
            {
                "p": p,
                "u": u,
                "selection": '[{"segmentation_id":"' + str(lesion.baseline_segmentation_id) + '"}]',
            },
        )
        .scalars()
        .all()
    )
    if len(ids) > 100:
        raise HTTPException(409, detail="geometry_selection_requires_narrower_scope")
    for identifier in ids:
        try:
            report = read_mesh_qc(c, i, p, u, identifier)
            require_resource_action(c, i, p, u, report.id, SourceAction.INTERNAL)
            if report.output_artifact_id is not None:
                require_resource_action(
                    c, i, p, u, report.output_artifact_id, SourceAction.INTERNAL
                )
            measurement = load_usable_measurement(c, i, p, u, report.measurement_id)
            if lesion.baseline_segmentation_id not in {
                s.segmentation_id for s in measurement.selections
            }:
                continue
            return report
        except HTTPException as error:
            if error.status_code not in (403, 404, 409):
                raise
    raise HTTPException(409, detail="no_current_geometry_for_lesion")
