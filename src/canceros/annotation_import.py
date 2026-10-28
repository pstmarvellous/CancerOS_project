"""Per-label source annotations; technical and qualified review remain independent."""

from typing import Literal
from uuid import UUID, uuid4

import numpy as np
from fastapi import HTTPException
from sqlalchemy import text

from canceros.alignment_runs import load_aligned_mask
from canceros.annotation_contracts import (
    AnnotationCapabilities,
    AnnotationInput,
    TechnicalQCState,
    annotation_capabilities,
)
from canceros.contracts import Contract, Provenance
from canceros.imaging_geometry import CanonicalGeometry
from canceros.lineage import (
    derive_resource,
    lock_lineage,
    processing_spec,
    require_resource_action,
    resource_restrictions,
)
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import science_hash
from canceros.source_registry import SourceAction


class SegmentationAnnotation(Contract):
    id: UUID
    label: int
    batch_id: UUID
    alignment_run_id: UUID
    source_version_id: UUID
    mask_artifact_id: UUID
    source_image_id: UUID
    study_id: UUID
    annotation: AnnotationInput
    geometry: CanonicalGeometry
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    scientific_review: Literal["pending"] = "pending"
    technical_qc: Literal["pending", "pass", "fail"] = "pending"
    qc_evidence_status: Literal["not_run", "current", "withdrawn_or_unavailable"] = "not_run"
    publication: Literal["draft"] = "draft"
    capabilities: AnnotationCapabilities


class AnnotationBatch(Contract):
    id: UUID
    alignment_run_id: UUID
    segmentation_ids: list[UUID]
    labels: list[int]
    status: Literal["imported_pending_qc_and_review"] = "imported_pending_qc_and_review"
    scientific_review: Literal["pending"] = "pending"
    publication: Literal["draft"] = "draft"
    next_action: str = "Inspect annotation class and each label; run technical QC, then obtain qualified scientific review before anatomical claims"


def import_annotations(connection, identity, project, patient, value, storage):
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    aligned, mask = load_aligned_mask(
        connection, identity, project, patient, value.alignment_run_id, storage
    )
    require_resource_action(
        connection, identity, project, patient, aligned.output_artifact_id, SourceAction.DERIVATIVE
    )
    observed_labels = set(int(v) for v in np.unique(mask) if v)
    if observed_labels != {label.label for label in value.labels}:
        raise HTTPException(422)
    normalized = value.model_dump(mode="json")
    normalized["labels"] = sorted(normalized["labels"], key=lambda item: item["label"])
    fingerprint = science_hash(normalized)
    prior = connection.execute(
        text(
            "SELECT id FROM imaging.annotation_batches WHERE project_id=:p AND patient_id=:u AND input_hash=:hash"
        ),
        {"p": project, "u": patient, "hash": fingerprint},
    ).scalar_one_or_none()
    if prior:
        previous = read_annotation_batch(connection, identity, project, patient, prior)
        for segmentation_id in previous.segmentation_ids:
            require_resource_action(
                connection, identity, project, patient, segmentation_id, SourceAction.INTERNAL
            )
            require_resource_action(
                connection, identity, project, patient, segmentation_id, SourceAction.DERIVATIVE
            )
        return previous
    source_version = connection.execute(
        text(
            "SELECT source_version_id FROM imaging.staged_files WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": aligned.source_mask_id},
    ).scalar_one()
    assert aligned.output_artifact_id is not None and aligned.geometry is not None
    batch_id = uuid4()
    annotations = []
    capabilities = annotation_capabilities(
        value.annotation_class,
        alignment_state="pass",
        fixture_origin=True,
        source_rights_permitted=True,
    )
    for label in sorted(value.labels, key=lambda item: item.label):
        annotations.append(
            SegmentationAnnotation(
                id=uuid4(),
                label=label.label,
                batch_id=batch_id,
                alignment_run_id=aligned.id,
                source_version_id=source_version,
                mask_artifact_id=aligned.output_artifact_id,
                source_image_id=aligned.target_image_id,
                study_id=aligned.study_id,
                annotation=value,
                geometry=aligned.geometry,
                capabilities=capabilities,
            )
        )
    report = AnnotationBatch(
        id=batch_id,
        alignment_run_id=aligned.id,
        segmentation_ids=[item.id for item in annotations],
        labels=[item.label for item in annotations],
    )
    connection.execute(
        text(
            "INSERT INTO imaging.annotation_batches(id,project_id,patient_id,alignment_run_id,input_hash,report,report_hash) VALUES(:id,:p,:u,:alignment,:hash,CAST(:report AS jsonb),:rh)"
        ),
        {
            "id": batch_id,
            "p": project,
            "u": patient,
            "alignment": aligned.id,
            "hash": fingerprint,
            "report": report.model_dump_json(),
            "rh": science_hash(report.model_dump(mode="json")),
        },
    )
    processing = processing_spec(
        __file__,
        "reference-annotation-import/1",
        "annotation-meaning/1",
        {"classification": value.model_dump(mode="json"), "alignment_run_id": str(aligned.id)},
    )
    for item in annotations:
        metadata = item.model_dump(mode="json")
        digest = science_hash(metadata)
        connection.execute(
            text(
                "INSERT INTO imaging.segmentations(id,project_id,patient_id,batch_id,label_value,mask_artifact_id,metadata,metadata_hash) VALUES(:id,:p,:u,:batch,:label,:mask,CAST(:metadata AS jsonb),:hash)"
            ),
            {
                "id": item.id,
                "p": project,
                "u": patient,
                "batch": batch_id,
                "label": item.label,
                "mask": aligned.output_artifact_id,
                "metadata": item.model_dump_json(),
                "hash": digest,
            },
        )
        derive_resource(
            connection,
            identity,
            project,
            patient,
            item.id,
            "segmentation",
            digest,
            [aligned.output_artifact_id],
            processing,
            expected_origin=Provenance.SYNTHETIC_GENERATED,
        )
    audit(connection, project, batch_id, "REFERENCE_ANNOTATION_IMPORTED")
    return report


def read_annotation_batch(connection, identity, project, patient, batch_id):
    authorize_patient(connection, identity, project, patient, edit=True)
    row = connection.execute(
        text(
            "SELECT report,report_hash FROM imaging.annotation_batches WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": batch_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.report) != row.report_hash:
        raise HTTPException(409)
    return AnnotationBatch.model_validate(row.report)


def read_annotation(connection, identity, project, patient, segmentation_id):
    authorize_patient(connection, identity, project, patient, edit=True)
    row = connection.execute(
        text(
            "SELECT metadata,metadata_hash FROM imaging.segmentations WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": segmentation_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.metadata) != row.metadata_hash:
        raise HTTPException(409)
    annotation = SegmentationAnnotation.model_validate(row.metadata)
    permitted = not any(
        resource_restrictions(connection, identity, project, patient, segmentation_id, action)
        for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE)
    )
    latest = connection.execute(
        text(
            "SELECT status,checks,checks_hash FROM source.technical_validations WHERE project_id=:p AND patient_id=:u AND resource_id=:id AND rule_version='segmentation-qc/1' ORDER BY sequence DESC LIMIT 1"
        ),
        {"p": project, "u": patient, "id": segmentation_id},
    ).one_or_none()
    qc: TechnicalQCState = "pending"
    qc_evidence = "not_run"
    if latest:
        if science_hash(latest.checks) != latest.checks_hash:
            raise HTTPException(409)
        qc = latest.status
        report_id = latest.checks.get("qc_report_id")
        if report_id and not any(
            resource_restrictions(connection, identity, project, patient, UUID(report_id), action)
            for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE)
        ):
            qc_evidence = "current"
        else:
            qc, qc_evidence = "pending", "withdrawn_or_unavailable"
    return annotation.model_copy(
        update={
            "technical_qc": qc,
            "qc_evidence_status": qc_evidence,
            "capabilities": annotation_capabilities(
                annotation.annotation.annotation_class,
                technical_qc_state=qc,
                alignment_state="pass",
                fixture_origin=True,
                source_rights_permitted=permitted,
            ),
        }
    )


def load_annotation_mask(connection, identity, project, patient, segmentation_id, storage):
    annotation = read_annotation(connection, identity, project, patient, segmentation_id)
    require_resource_action(
        connection, identity, project, patient, annotation.id, SourceAction.INTERNAL
    )
    aligned, mask = load_aligned_mask(
        connection, identity, project, patient, annotation.alignment_run_id, storage
    )
    if (
        annotation.mask_artifact_id != aligned.output_artifact_id
        or annotation.geometry != aligned.geometry
    ):
        raise HTTPException(409)
    selected = np.asarray(mask == annotation.label, dtype=np.uint8)
    selected.setflags(write=False)
    return annotation, selected
