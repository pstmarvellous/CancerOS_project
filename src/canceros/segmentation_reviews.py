"""Technical QC attempts and explicit lack of independent real accuracy evidence."""

from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from canceros.annotation_import import load_annotation_mask
from canceros.contracts import Contract
from canceros.lineage import derive_resource, lock_lineage, processing_spec, require_resource_action
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import science_hash
from canceros.quality import record_technical_validation
from canceros.segmentation_qc import (
    SegmentationMetrics,
    TechnicalMaskQC,
    evaluate_masks,
    inspect_mask,
)
from canceros.source_registry import SourceAction


class SegmentationQCInput(Contract):
    segmentation_id: UUID
    reference_segmentation_id: UUID | None = None
    rule_version: Literal["segmentation-qc/1"] = "segmentation-qc/1"


class SegmentationQCReport(Contract):
    id: UUID
    segmentation_id: UUID
    reference_segmentation_id: UUID | None
    technical: TechnicalMaskQC
    independent_accuracy: SegmentationMetrics
    reference_eligibility_reason: Literal[
        "no_independent_reference",
        "self_or_shared_mask",
        "qualified_authentic_reference_review_not_established",
    ]
    case_attempt_number: int
    technical_failed_attempts: int
    scientific_review: Literal["pending"] = "pending"
    publication: Literal["draft"] = "draft"
    verification_scope: Literal["synthetic_engineering_fixture_only"] = (
        "synthetic_engineering_fixture_only"
    )
    next_action: str


def run_segmentation_qc(connection, identity, project, patient, value, storage, command_key):
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    annotation, mask = load_annotation_mask(
        connection, identity, project, patient, value.segmentation_id, storage
    )
    require_resource_action(
        connection, identity, project, patient, annotation.id, SourceAction.DERIVATIVE
    )
    if not annotation.capabilities.technical_qc_allowed:
        raise HTTPException(409)
    reference, reference_mask = None, None
    if value.reference_segmentation_id:
        reference, reference_mask = load_annotation_mask(
            connection, identity, project, patient, value.reference_segmentation_id, storage
        )
        require_resource_action(
            connection, identity, project, patient, reference.id, SourceAction.DERIVATIVE
        )
    fingerprint = science_hash(value.model_dump(mode="json"))
    prior = connection.execute(
        text(
            "SELECT id,input_hash FROM imaging.segmentation_qc_reports WHERE project_id=:p AND patient_id=:u AND actor_id=:actor AND command_key=:key"
        ),
        {"p": project, "u": patient, "actor": identity.user_id, "key": command_key},
    ).one_or_none()
    if prior:
        if prior.input_hash != fingerprint:
            raise HTTPException(409)
        require_resource_action(
            connection, identity, project, patient, prior.id, SourceAction.INTERNAL
        )
        return read_segmentation_qc(connection, identity, project, patient, prior.id)
    technical = inspect_mask(mask, annotation.geometry)
    self_comparison = reference is not None and (
        reference.id == annotation.id or reference.mask_artifact_id == annotation.mask_artifact_id
    )
    # All currently onboarded annotations are fixtures with qualified review pending.
    # Do not make client assertions or different annotation IDs independent reference proof.
    metrics = evaluate_masks(
        mask,
        reference_mask,
        annotation.geometry,
        independent_reference=False,
        self_comparison=self_comparison,
    )
    reason: Literal[
        "no_independent_reference",
        "self_or_shared_mask",
        "qualified_authentic_reference_review_not_established",
    ] = (
        "no_independent_reference"
        if reference is None
        else "self_or_shared_mask"
        if self_comparison
        else "qualified_authentic_reference_review_not_established"
    )
    previous = (
        connection.execute(
            text(
                "SELECT report FROM imaging.segmentation_qc_reports WHERE project_id=:p AND patient_id=:u AND segmentation_id=:id"
            ),
            {"p": project, "u": patient, "id": annotation.id},
        )
        .scalars()
        .all()
    )
    failed = sum(r["technical"]["technical_status"] == "fail" for r in previous) + (
        technical.technical_status == "fail"
    )
    report = SegmentationQCReport(
        id=uuid4(),
        segmentation_id=annotation.id,
        reference_segmentation_id=value.reference_segmentation_id,
        technical=technical,
        independent_accuracy=metrics,
        reference_eligibility_reason=reason,
        case_attempt_number=len(previous) + 1,
        technical_failed_attempts=failed,
        next_action="Technical checks passed; inspect source overlay and obtain qualified annotation/reference review. Independent accuracy was not evaluated"
        if technical.technical_status == "pass"
        else "Repair the reported mask/geometry issue; retain this failed attempt and rerun with a new command key",
    )
    digest = science_hash(report.model_dump(mode="json"))
    connection.execute(
        text(
            "INSERT INTO imaging.segmentation_qc_reports(id,project_id,patient_id,segmentation_id,reference_segmentation_id,actor_id,command_key,input_hash,report,report_hash) VALUES(:id,:p,:u,:seg,:ref,:actor,:key,:hash,CAST(:report AS jsonb),:rh)"
        ),
        {
            "id": report.id,
            "p": project,
            "u": patient,
            "seg": annotation.id,
            "ref": value.reference_segmentation_id,
            "actor": identity.user_id,
            "key": command_key,
            "hash": fingerprint,
            "report": report.model_dump_json(),
            "rh": digest,
        },
    )
    parents = [annotation.id] + (
        [reference.id] if reference and reference.id != annotation.id else []
    )
    derive_resource(
        connection,
        identity,
        project,
        patient,
        report.id,
        "segmentation_qc_report",
        digest,
        parents,
        processing_spec(
            __file__, "segmentation-qc/1", "segmentation-qc/1", value.model_dump(mode="json")
        ),
    )
    record_technical_validation(
        connection,
        identity,
        project,
        patient,
        annotation.id,
        technical.technical_status,
        "segmentation-qc/1",
        {"qc_report_id": str(report.id), "technical": technical.model_dump(mode="json")},
    )
    audit(connection, project, report.id, "SEGMENTATION_QC_ATTEMPT")
    return report


def read_segmentation_qc(connection, identity, project, patient, report_id):
    authorize_patient(connection, identity, project, patient, edit=True)
    row = connection.execute(
        text(
            "SELECT report,report_hash FROM imaging.segmentation_qc_reports WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": report_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.report) != row.report_hash:
        raise HTTPException(409)
    return SegmentationQCReport.model_validate(row.report)
