"""Administrator fixture attestations; never qualified approval of a real source pair."""

from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from canceros.contracts import Contract, Hash
from canceros.identity import authorize_project
from canceros.imaging_ingestion import read_staged
from canceros.lineage import derive_resource, lock_lineage, processing_spec, require_resource_action
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import science_hash
from canceros.preprocessing_runs import load_image
from canceros.source_registry import SourceAction


class MaskAssociationInput(Contract):
    mask_file_id: UUID
    target_image_id: UUID
    expected_study_id: UUID
    evidence_sha256: Hash


class MaskAssociation(Contract):
    id: UUID
    patient_id: UUID
    source_mask_id: UUID
    target_image_id: UUID
    study_id: UUID
    evidence_sha256: Hash
    verification_basis: Literal["administrator_fixture_attestation_real_review_not_established"] = (
        "administrator_fixture_attestation_real_review_not_established"
    )
    scientific_review: Literal["pending"] = "pending"


def bind_mask(connection, identity, project, patient, value, storage):
    authorize_project(identity, project, "admin")
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    geometry, image, import_id = load_image(
        connection, identity, project, patient, value.target_image_id, storage
    )
    imported = connection.execute(
        text(
            "SELECT association FROM imaging.imports WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": import_id},
    ).scalar_one()
    if str(value.expected_study_id) != imported["study_id"]:
        raise HTTPException(409)
    mask_row, _ = read_staged(connection, identity, project, patient, value.mask_file_id, storage)
    if str(mask_row["mapping_id"]) != imported["mapping_id"]:
        raise HTTPException(404)
    if mask_row["format"] != "nifti" or image.ndim != 3 or geometry is None:
        raise HTTPException(422)
    for artifact in (value.mask_file_id, value.target_image_id):
        require_resource_action(
            connection, identity, project, patient, artifact, SourceAction.DERIVATIVE
        )
    prior = connection.execute(
        text(
            "SELECT report,report_hash FROM imaging.mask_associations WHERE project_id=:p AND patient_id=:u AND source_mask_id=:id"
        ),
        {"p": project, "u": patient, "id": value.mask_file_id},
    ).one_or_none()
    if prior:
        if science_hash(prior.report) != prior.report_hash:
            raise HTTPException(409)
        result = MaskAssociation.model_validate(prior.report)
        if (
            result.target_image_id != value.target_image_id
            or result.study_id != value.expected_study_id
            or result.evidence_sha256 != value.evidence_sha256
        ):
            raise HTTPException(409)
        require_resource_action(
            connection, identity, project, patient, result.id, SourceAction.INTERNAL
        )
        return result
    result = MaskAssociation(
        id=uuid4(),
        patient_id=patient,
        source_mask_id=value.mask_file_id,
        target_image_id=value.target_image_id,
        study_id=value.expected_study_id,
        evidence_sha256=value.evidence_sha256,
    )
    digest = science_hash(result.model_dump(mode="json"))
    connection.execute(
        text(
            "INSERT INTO imaging.mask_associations(id,project_id,patient_id,source_mask_id,target_image_id,study_id,report,report_hash,attested_by) VALUES(:id,:p,:u,:mask,:target,:study,CAST(:report AS jsonb),:hash,:actor)"
        ),
        {
            "id": result.id,
            "p": project,
            "u": patient,
            "mask": result.source_mask_id,
            "target": result.target_image_id,
            "study": result.study_id,
            "report": result.model_dump_json(),
            "hash": digest,
            "actor": identity.user_id,
        },
    )
    derive_resource(
        connection,
        identity,
        project,
        patient,
        result.id,
        "mask_study_association",
        digest,
        [result.source_mask_id, result.target_image_id],
        processing_spec(
            __file__,
            "mask-study-binding/1",
            "mask-study-binding/1",
            {"attestation": result.model_dump(mode="json")},
        ),
    )
    audit(connection, project, result.id, "MASK_STUDY_ASSOCIATION_ATTESTED")
    return result


def mask_binding(connection, identity, project, patient, association_id):
    authorize_patient(connection, identity, project, patient, edit=True)
    row = connection.execute(
        text(
            "SELECT report,report_hash FROM imaging.mask_associations WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": association_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.report) != row.report_hash:
        raise HTTPException(409)
    return MaskAssociation.model_validate(row.report)
