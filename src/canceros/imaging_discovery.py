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


class SegmentationDiscovery(Contract):
    segmentation_id: UUID
    batch_id: UUID
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
        ).scalars().all()
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
                label_value=annotation.label,
                mask_type=annotation.annotation.annotation_class,
                qc_status=annotation.technical_qc,
            )
        )
    if not found:
        raise HTTPException(404)
    return found
