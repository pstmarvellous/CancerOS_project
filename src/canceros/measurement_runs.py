"""Owned region measurements with immutable source selection and separate claim eligibility."""

from typing import Annotated, Literal
from uuid import UUID, uuid4

import numpy as np
from fastapi import HTTPException
from pydantic import Field
from sqlalchemy import text

from canceros.annotation_import import load_annotation_mask
from canceros.contracts import Contract, Hash
from canceros.lineage import derive_resource, lock_lineage, processing_spec, require_resource_action
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import load_revision, science_hash
from canceros.physical_measurements import RegionMeasurement, measure_region
from canceros.quality import record_technical_validation
from canceros.source_registry import SourceAction


class MeasurementInput(Contract):
    segmentation_ids: Annotated[list[UUID], Field(min_length=1, max_length=32)]
    expected_revision: Annotated[int, Field(strict=True, ge=1)]
    definition: Literal[
        "numerical_region_volume", "functional_region_volume", "anatomical_tumor_volume"
    ] = "numerical_region_volume"


class AnnotationSelection(Contract):
    segmentation_id: UUID
    label: int
    mask_artifact_id: UUID
    mask_sha256: Hash
    qc_validation_id: UUID | None
    qc_report_id: UUID | None
    selected_voxels: int


class MeasurementReport(Contract):
    id: UUID
    input_revision: int
    selections: list[AnnotationSelection]
    definition: Literal[
        "numerical_region_volume", "functional_region_volume", "anatomical_tumor_volume"
    ]
    selection_definition: Literal["union_of_explicit_annotation_ids_no_double_counting"] = (
        "union_of_explicit_annotation_ids_no_double_counting"
    )
    values: RegionMeasurement
    geometry_sha256: Hash
    source_time_basis: Literal["source_private", "not_recorded", "shifted_source_private"]
    eligibility_blocks: list[str]
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    scientific_review: Literal["pending"] = "pending"
    publication: Literal["draft"] = "draft"
    next_action: str


def create_measurement(connection, identity, project, patient, value, storage, command_key):
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    if len(set(value.segmentation_ids)) != len(value.segmentation_ids):
        raise HTTPException(422)
    loaded = [
        load_annotation_mask(connection, identity, project, patient, selected, storage)
        for selected in sorted(value.segmentation_ids, key=str)
    ]
    first = loaded[0][0]
    selections, blocks = [], []
    for annotation, mask in loaded:
        require_resource_action(
            connection, identity, project, patient, annotation.id, SourceAction.DERIVATIVE
        )
        if (
            annotation.geometry != first.geometry
            or annotation.study_id != first.study_id
            or annotation.source_image_id != first.source_image_id
        ):
            raise HTTPException(409)
        if not annotation.capabilities.numerical_region_volume_allowed:
            blocks.append("passing_technical_qc_and_known_annotation_meaning_required")
        if (
            value.definition == "anatomical_tumor_volume"
            and not annotation.capabilities.anatomical_volume_allowed
        ):
            blocks.append("qualified_authentic_anatomical_review_not_established")
        if (
            value.definition == "functional_region_volume"
            and annotation.annotation.annotation_class != "functional_enhancement_region"
        ):
            blocks.append("functional_region_annotation_required")
        row = connection.execute(
            text(
                "SELECT sha256 FROM ops.artifacts WHERE project_id=:p AND patient_id=:u AND id=:id"
            ),
            {"p": project, "u": patient, "id": annotation.mask_artifact_id},
        ).scalar_one()
        qc_event = connection.execute(
            text(
                "SELECT id,checks FROM source.technical_validations WHERE project_id=:p AND patient_id=:u AND resource_id=:id AND rule_version='segmentation-qc/1' ORDER BY sequence DESC LIMIT 1"
            ),
            {"p": project, "u": patient, "id": annotation.id},
        ).one_or_none()
        qc_id = qc_event.id if qc_event else None
        qc_report_id = (
            UUID(qc_event.checks["qc_report_id"])
            if qc_event and qc_event.checks.get("qc_report_id")
            else None
        )
        if qc_id is None:
            # Retain an unavailable report without pretending a validation event exists.
            blocks.append("technical_qc_not_run")
        selections.append(
            AnnotationSelection(
                segmentation_id=annotation.id,
                label=annotation.label,
                mask_artifact_id=annotation.mask_artifact_id,
                mask_sha256=row,
                qc_validation_id=qc_id,
                qc_report_id=qc_report_id,
                selected_voxels=int(mask.sum()),
            )
        )
    normalized = value.model_dump(mode="json")
    normalized["segmentation_ids"] = sorted(normalized["segmentation_ids"])
    fingerprint = science_hash(normalized)
    prior = connection.execute(
        text(
            "SELECT id,input_hash FROM imaging.measurement_reports WHERE project_id=:p AND patient_id=:u AND actor_id=:actor AND command_key=:key"
        ),
        {"p": project, "u": patient, "actor": identity.user_id, "key": command_key},
    ).one_or_none()
    if prior:
        if prior.input_hash != fingerprint:
            raise HTTPException(409)
        previous = read_measurement(connection, identity, project, patient, prior.id)
        if previous.values.availability == "available" and blocks:
            raise HTTPException(409)
        require_resource_action(
            connection, identity, project, patient, prior.id, SourceAction.INTERNAL
        )
        return previous
    current = connection.execute(
        text("SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"),
        {"p": project, "u": patient},
    ).scalar_one()
    if current != value.expected_revision:
        raise HTTPException(409)
    load_revision(connection, project, patient, value.expected_revision)
    union = np.zeros(first.geometry.shape_xyz, dtype=np.uint8)
    for _, mask in loaded:
        union |= mask
    values = (
        RegionMeasurement(
            availability="unavailable",
            reason="measurement_eligibility_not_established",
            selected_labels=(1,),
        )
        if blocks
        else measure_region(union, first.geometry)
    )
    import_id = connection.execute(
        text(
            "SELECT import_id FROM imaging.volume_validations WHERE project_id=:p AND patient_id=:u AND artifact_id=:image"
        ),
        {"p": project, "u": patient, "image": first.source_image_id},
    ).scalar_one_or_none()
    if import_id is None:
        input_image = connection.execute(
            text(
                "SELECT input_artifact_id FROM imaging.preprocess_runs WHERE project_id=:p AND patient_id=:u AND output_artifact_id=:image"
            ),
            {"p": project, "u": patient, "image": first.source_image_id},
        ).scalar_one()
        import_id = connection.execute(
            text(
                "SELECT import_id FROM imaging.volume_validations WHERE project_id=:p AND patient_id=:u AND artifact_id=:image"
            ),
            {"p": project, "u": patient, "image": input_image},
        ).scalar_one()
    source_time = connection.execute(
        text(
            "SELECT association->>'acquisition_time_status' FROM imaging.imports WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": import_id},
    ).scalar_one()
    report = MeasurementReport(
        id=uuid4(),
        input_revision=value.expected_revision,
        selections=selections,
        definition=value.definition,
        values=values,
        geometry_sha256=science_hash(first.geometry.model_dump(mode="json")),
        source_time_basis=source_time,
        eligibility_blocks=sorted(set(blocks)),
        next_action="Inspect explicit selection, units and source time basis; numerical region measurements are not clinical response or anatomical approval"
        if not blocks
        else "Resolve the listed QC/annotation/review gaps; unavailable volume is not zero",
    )
    digest = science_hash(report.model_dump(mode="json"))
    connection.execute(
        text(
            "INSERT INTO imaging.measurement_reports(id,project_id,patient_id,input_revision,actor_id,command_key,input_hash,report,report_hash) VALUES(:id,:p,:u,:revision,:actor,:key,:hash,CAST(:report AS jsonb),:rh)"
        ),
        {
            "id": report.id,
            "p": project,
            "u": patient,
            "revision": report.input_revision,
            "actor": identity.user_id,
            "key": command_key,
            "hash": fingerprint,
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
        "physical_measurement",
        digest,
        sorted(
            set(value.segmentation_ids) | {s.qc_report_id for s in selections if s.qc_report_id},
            key=str,
        ),
        processing_spec(
            __file__,
            "physical-measurements/1",
            "physical-measurements/1",
            {
                "request": normalized,
                "mask_hashes": [s.mask_sha256 for s in selections],
                "qc_validation_ids": [
                    str(s.qc_validation_id) if s.qc_validation_id else None for s in selections
                ],
                "qc_report_ids": [
                    str(s.qc_report_id) if s.qc_report_id else None for s in selections
                ],
            },
        ),
    )
    record_technical_validation(
        connection,
        identity,
        project,
        patient,
        report.id,
        "pass" if values.availability == "available" else "fail",
        "physical-measurements/1",
        {
            "measurement_id": str(report.id),
            "availability": values.availability,
            "definition": value.definition,
        },
    )
    audit(connection, project, report.id, "PHYSICAL_MEASUREMENT_RECORDED")
    return report


def read_measurement(connection, identity, project, patient, report_id):
    authorize_patient(connection, identity, project, patient, edit=True)
    row = connection.execute(
        text(
            "SELECT report,report_hash FROM imaging.measurement_reports WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": report_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.report) != row.report_hash:
        raise HTTPException(409)
    return MeasurementReport.model_validate(row.report)


def load_usable_measurement(connection, identity, project, patient, report_id):
    report = read_measurement(connection, identity, project, patient, report_id)
    for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE):
        require_resource_action(connection, identity, project, patient, report.id, action)
    if report.values.availability != "available":
        raise HTTPException(409)
    return report
