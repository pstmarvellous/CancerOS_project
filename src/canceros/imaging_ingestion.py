"""Private, deliberately bounded imaging staging; no real-source onboarding or publication."""

import base64
import hashlib
import hmac
import json
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import Field, SecretStr
from sqlalchemy import text

from canceros.contracts import Contract, Hash
from canceros.identity import authorize_project
from canceros.lineage import (
    derive_resource,
    lock_lineage,
    processing_spec,
    register_root,
    require_resource_action,
)
from canceros.patient_linkage import LinkageKeys, audit, authorize_patient, release_for
from canceros.persistence import science_hash
from canceros.source_registry import SourceAction, require_source_action
from canceros.storage import StoredObject


class ImagingStageInput(Contract):
    source_version_id: UUID
    mapping_id: UUID
    format: Literal["dicom", "nifti"]
    sha256: Hash
    content_base64: SecretStr = Field(
        min_length=1, max_length=900000, json_schema_extra={"writeOnly": True}
    )


class ImagingStageReceipt(Contract):
    artifact_id: UUID
    patient_id: UUID
    format: Literal["dicom", "nifti"]
    sha256: Hash
    status: Literal["privately_staged"] = "privately_staged"
    next_action: str = (
        "Create an import preview with an explicit patient/study/sequence association"
    )


class ImagingAssociation(Contract):
    mapping_id: UUID
    study_id: UUID
    series_id: UUID
    source_study_key: SecretStr = Field(
        min_length=1, max_length=200, json_schema_extra={"writeOnly": True}
    )
    source_series_key: SecretStr = Field(
        min_length=1, max_length=200, json_schema_extra={"writeOnly": True}
    )
    sequence: Literal["t1", "t2", "dce", "other_mr", "unknown"]
    fourth_axis: Literal["dce_phase"] | None = None
    acquisition_time_status: Literal["source_private", "not_recorded", "shifted_source_private"]
    association_basis: Literal["administrator_manifest_attestation"]
    evidence_sha256: Hash


class ImagingPreviewInput(Contract):
    file_ids: Annotated[list[UUID], Field(min_length=1, max_length=64)]
    association: ImagingAssociation


class ImagingImportReport(Contract):
    id: UUID
    patient_id: UUID
    patient_label: str
    study_id: UUID
    series_id: UUID
    sequence: Literal["t1", "t2", "dce", "other_mr", "unknown"]
    format: Literal["dicom", "nifti"]
    file_ids: list[UUID]
    input_sha256: list[Hash]
    dimensions: list[int] | None
    status: Literal["awaiting_confirmation", "quarantined", "staged_pending_geometry"]
    issue_codes: list[str]
    privacy_review: Literal["required_before_sharing"] = "required_before_sharing"
    privacy_flags: list[str] = [
        "source_metadata_requires_review",
        "burned_in_identifiers_not_excluded",
    ]
    geometry_review: Literal["pending"] = "pending"
    scientific_review: Literal["pending"] = "pending"
    publication: Literal["draft"] = "draft"
    parser_version: Literal["bounded-imaging/1"] = "bounded-imaging/1"
    verification_scope: Literal["synthetic_engineering_fixture_only"] = (
        "synthetic_engineering_fixture_only"
    )
    next_action: str


def owned_mapping(connection, identity, project, patient, mapping_id, release=None):
    authorize_project(identity, project, "admin")
    authorize_patient(connection, identity, project, patient, edit=True)
    row = (
        connection.execute(
            text(
                "SELECT * FROM source.patient_mappings WHERE project_id=:p AND patient_id=:u AND id=:id"
            ),
            {"p": project, "u": patient, "id": mapping_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None or (release is not None and row["release_version_id"] != release):
        raise HTTPException(404)
    return row


def store_artifact(connection, project, patient, raw, storage):
    if len(raw) > storage.cap:
        raise HTTPException(413)
    stored = storage.write_verified(project, raw, cleanup_scope="engineering_fixture")
    artifact = uuid4()
    connection.execute(
        text(
            "INSERT INTO ops.artifacts(id,project_id,patient_id,object_key,object_version,byte_size,sha256,provenance,availability) VALUES(:id,:p,:u,:key,:v,:size,:hash,'SYNTHETIC_GENERATED','verified')"
        ),
        {
            "id": artifact,
            "p": project,
            "u": patient,
            "key": stored.key,
            "v": stored.version,
            "size": stored.byte_size,
            "hash": stored.sha256,
        },
    )
    return artifact, stored.sha256


def stage_imaging(connection, identity, project, patient, value, storage):
    authorize_project(identity, project, "admin")
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    require_source_action(
        connection, identity, project, value.source_version_id, SourceAction.INTERNAL
    )
    source, release = release_for(connection, identity, project, value.source_version_id)
    if source.origin != "synthetic_engineering_fixture":
        raise HTTPException(409)
    owned_mapping(connection, identity, project, patient, value.mapping_id, release)
    try:
        raw = base64.b64decode(value.content_base64.get_secret_value(), validate=True)
    except ValueError:
        raise HTTPException(422) from None
    digest = hashlib.sha256(raw).hexdigest()
    if not raw or digest != value.sha256 or digest != source.manifest_sha256:
        raise HTTPException(422)
    params = {
        "p": project,
        "u": patient,
        "m": value.mapping_id,
        "s": source.id,
        "f": value.format,
        "h": digest,
    }
    previous = connection.execute(
        text(
            "SELECT id FROM imaging.staged_files WHERE project_id=:p AND patient_id=:u AND mapping_id=:m AND source_version_id=:s AND format=:f AND input_hash=:h"
        ),
        params,
    ).scalar_one_or_none()
    if previous is None:
        previous, _ = store_artifact(connection, project, patient, raw, storage)
        connection.execute(
            text(
                "INSERT INTO imaging.staged_files(id,project_id,patient_id,mapping_id,source_version_id,format,input_hash) VALUES(:id,:p,:u,:m,:s,:f,:h)"
            ),
            {**params, "id": previous},
        )
        register_root(
            connection, identity, project, patient, previous, "source_imaging", digest, source.id
        )
        audit(connection, project, previous, "IMAGING_FILE_STAGED")
    else:
        require_resource_action(
            connection, identity, project, patient, previous, SourceAction.INTERNAL
        )
    return ImagingStageReceipt(
        artifact_id=previous, patient_id=patient, format=value.format, sha256=digest
    )


def read_staged(connection, identity, project, patient, file_id, storage):
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    row = (
        connection.execute(
            text(
                "SELECT f.*,a.object_key,a.object_version,a.byte_size,a.sha256 FROM imaging.staged_files f JOIN ops.artifacts a ON (a.project_id,a.id)=(f.project_id,f.id) WHERE f.project_id=:p AND f.patient_id=:u AND f.id=:id"
            ),
            {"p": project, "u": patient, "id": file_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404)
    require_resource_action(connection, identity, project, patient, file_id, SourceAction.INTERNAL)
    raw = storage.read(
        StoredObject(
            project, row["object_key"], row["object_version"], row["sha256"], row["byte_size"]
        ),
        project,
    )
    return row, raw


def mapping_key(connection, project, mapping, keys):
    rows = (
        connection.execute(
            text(
                "SELECT * FROM source.mapping_secrets WHERE project_id=:p AND mapping_id=:m ORDER BY recorded_at DESC"
            ),
            {"p": project, "m": mapping["id"]},
        )
        .mappings()
        .all()
    )
    for row in rows:
        if row["key_version"] in keys.keys:
            return keys.decrypt(
                row["key_version"],
                project,
                mapping["release_version_id"],
                mapping["id"],
                row["nonce"],
                row["ciphertext"],
            )
    raise HTTPException(409)


def parse_staged(rows, fourth_axis=None):
    from canceros.imaging_formats import parse_dicom_series, parse_nifti

    formats = {row[0]["format"] for row in rows}
    if len(formats) != 1:
        raise ValueError("MIXED_FORMATS")
    if "dicom" in formats:
        return parse_dicom_series([row[1] for row in rows])
    if len(rows) != 1:
        raise ValueError("NIFTI_REQUIRES_ONE_FILE")
    return parse_nifti(rows[0][1], fourth_axis=fourth_axis)


def preview_imaging(connection, identity, project, patient, value, storage, config):
    authorize_project(identity, project, "admin")
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    assoc = value.association
    mapping = owned_mapping(connection, identity, project, patient, assoc.mapping_id)
    if len(value.file_ids) != len(set(value.file_ids)):
        raise HTTPException(422)
    keys = LinkageKeys(config)
    if keys.active is None:
        raise HTTPException(409)
    study_key, series_key = (
        assoc.source_study_key.get_secret_value(),
        assoc.source_series_key.get_secret_value(),
    )
    if (
        not study_key.strip()
        or not series_key.strip()
        or (assoc.fourth_axis and assoc.sequence != "dce")
    ):
        raise HTTPException(422)
    study_digest = hmac.new(
        keys.key(keys.active, b"imaging-association"),
        f"{project}:{assoc.mapping_id}:{study_key}".encode(),
        "sha256",
    ).hexdigest()
    series_digest = hmac.new(
        keys.key(keys.active, b"imaging-association"),
        f"{project}:{assoc.mapping_id}:{study_key}:{series_key}".encode(),
        "sha256",
    ).hexdigest()
    safe_assoc = assoc.model_dump(mode="json", exclude={"source_study_key", "source_series_key"})
    safe_assoc.update(
        key_version=keys.active, study_digest=study_digest, series_digest=series_digest
    )
    file_ids = sorted(value.file_ids, key=str)
    fingerprints = []
    for version in keys.keys:
        version_assoc = {
            **safe_assoc,
            "key_version": version,
            "study_digest": hmac.new(
                keys.key(version, b"imaging-association"),
                f"{project}:{assoc.mapping_id}:{study_key}".encode(),
                "sha256",
            ).hexdigest(),
            "series_digest": hmac.new(
                keys.key(version, b"imaging-association"),
                f"{project}:{assoc.mapping_id}:{study_key}:{series_key}".encode(),
                "sha256",
            ).hexdigest(),
        }
        fingerprints.append(
            science_hash(
                {
                    "files": [str(f) for f in file_ids],
                    "association": version_assoc,
                    "parser": "bounded-imaging/1",
                }
            )
        )
    fingerprint = fingerprints[list(keys.keys).index(keys.active)]
    rows = [read_staged(connection, identity, project, patient, f, storage) for f in file_ids]
    if any(row[0]["mapping_id"] != assoc.mapping_id for row in rows):
        raise HTTPException(404)
    for file_id in file_ids:
        require_resource_action(
            connection, identity, project, patient, file_id, SourceAction.DERIVATIVE
        )
    prior = connection.execute(
        text(
            "SELECT id FROM imaging.imports WHERE project_id=:p AND patient_id=:u AND input_hash=ANY(:hashes)"
        ),
        {"p": project, "u": patient, "hashes": fingerprints},
    ).scalar_one_or_none()
    if prior:
        return read_import(connection, identity, project, patient, prior)
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
        {"key": f"imaging-study:{project}:{assoc.study_id}"},
    )
    # Compare all recorded key versions, so key rotation cannot silently duplicate an exam.
    associations = (
        connection.execute(
            text(
                "SELECT * FROM imaging.associations WHERE project_id=:p AND (mapping_id=:m OR series_id=:s OR study_id=:study)"
            ),
            {"p": project, "m": assoc.mapping_id, "s": assoc.series_id, "study": assoc.study_id},
        )
        .mappings()
        .all()
    )
    for old in associations:
        if old["key_version"] not in keys.keys:
            raise HTTPException(409)
        old_study_digest = hmac.new(
            keys.key(old["key_version"], b"imaging-association"),
            f"{project}:{assoc.mapping_id}:{study_key}".encode(),
            "sha256",
        ).hexdigest()
        old_series_digest = hmac.new(
            keys.key(old["key_version"], b"imaging-association"),
            f"{project}:{assoc.mapping_id}:{study_key}:{series_key}".encode(),
            "sha256",
        ).hexdigest()
        if (old["study_id"] == assoc.study_id) != (old["study_digest"] == old_study_digest):
            raise HTTPException(409)
        if old["series_id"] == assoc.series_id or old["series_digest"] == old_series_digest:
            raise HTTPException(409)
    issues, parsed = [], None
    try:
        parsed = parse_staged(rows, assoc.fourth_axis)
        private = parsed.private_metadata
        if rows[0][0]["format"] == "dicom":
            expected_patient = mapping_key(connection, project, mapping, keys)
            if private.get("patient_id") != expected_patient or private.get("issuer_of_patient_id"):
                raise ValueError("ASSOCIATION_MISMATCH")
            if private.get("study_uid") != study_key or private.get("series_uid") != series_key:
                raise ValueError("ASSOCIATION_MISMATCH")
    except ValueError:
        # Never forward parser exception strings, tags, file paths, identifiers or metadata.
        issues = ["UNSUPPORTED_CORRUPT_OR_AMBIGUOUS_INPUT"]
        parsed = None
    private_manifest = {
        "association": {
            **safe_assoc,
            "source_study_key": study_key,
            "source_series_key": series_key,
        },
        "parser_version": "bounded-imaging/1",
        "source_file_ids": [str(f) for f in file_ids],
        "private_metadata": parsed.private_metadata if parsed else None,
        "source_order": list(parsed.source_order) if parsed else None,
        "affine_ras_mm": parsed.affine_ras_mm.tolist() if parsed else None,
    }
    manifest_id, manifest_hash = store_artifact(
        connection,
        project,
        patient,
        json.dumps(private_manifest, sort_keys=True, separators=(",", ":")).encode(),
        storage,
    )
    derive_resource(
        connection,
        identity,
        project,
        patient,
        manifest_id,
        "imaging_import_manifest",
        manifest_hash,
        file_ids,
        processing_spec(
            __file__,
            "bounded-imaging/1",
            "bounded-imaging/1",
            {"association_hash": science_hash(safe_assoc)},
        ),
    )
    label = connection.execute(
        text("SELECT display_code FROM source.research_patients WHERE project_id=:p AND id=:u"),
        {"p": project, "u": patient},
    ).scalar_one()
    report = ImagingImportReport(
        id=uuid4(),
        patient_id=patient,
        patient_label=label,
        study_id=assoc.study_id,
        series_id=assoc.series_id,
        sequence=assoc.sequence,
        format=rows[0][0]["format"],
        file_ids=file_ids,
        input_sha256=[r[0]["sha256"] for r in rows],
        dimensions=list(parsed.array.shape) if parsed else None,
        status="quarantined" if issues else "awaiting_confirmation",
        issue_codes=issues,
        next_action="Review source association and supported-format limits; preserved private bytes can be retried"
        if issues
        else "Check patient label, study and sequence, then confirm; geometry and annotation QC remain pending",
    )
    connection.execute(
        text(
            "INSERT INTO imaging.imports(id,project_id,patient_id,input_hash,report,association,private_manifest_id) VALUES(:id,:p,:u,:h,CAST(:r AS jsonb),CAST(:a AS jsonb),:manifest)"
        ),
        {
            "id": report.id,
            "p": project,
            "u": patient,
            "h": fingerprint,
            "r": report.model_dump_json(),
            "a": json.dumps(safe_assoc),
            "manifest": manifest_id,
        },
    )
    if not issues:
        connection.execute(
            text(
                "INSERT INTO imaging.studies(project_id,patient_id,mapping_id,study_id) VALUES(:p,:u,:m,:study) ON CONFLICT DO NOTHING"
            ),
            {"p": project, "u": patient, "m": assoc.mapping_id, "study": assoc.study_id},
        )
        connection.execute(
            text(
                "INSERT INTO imaging.associations(project_id,patient_id,mapping_id,study_id,series_id,key_version,study_digest,series_digest,import_id) VALUES(:p,:u,:m,:study,:series,:key,:sd,:rd,:id)"
            ),
            {
                "p": project,
                "u": patient,
                "m": assoc.mapping_id,
                "study": assoc.study_id,
                "series": assoc.series_id,
                "key": keys.active,
                "sd": study_digest,
                "rd": series_digest,
                "id": report.id,
            },
        )
    audit(connection, project, report.id, "IMAGING_IMPORT_PREVIEW")
    return report


def read_import(connection, identity, project, patient, import_id):
    authorize_patient(connection, identity, project, patient, edit=True)
    row = connection.execute(
        text("SELECT report FROM imaging.imports WHERE project_id=:p AND patient_id=:u AND id=:id"),
        {"p": project, "u": patient, "id": import_id},
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404)
    report = ImagingImportReport.model_validate(row)
    confirmed = connection.execute(
        text(
            "SELECT 1 FROM imaging.confirmations WHERE project_id=:p AND patient_id=:u AND import_id=:id"
        ),
        {"p": project, "u": patient, "id": import_id},
    ).scalar_one_or_none()
    if confirmed:
        return report.model_copy(
            update={
                "status": "staged_pending_geometry",
                "next_action": "Run geometry validation; publication and scientific review remain pending",
            }
        )
    return report


def confirm_import(connection, identity, project, patient, import_id):
    authorize_project(identity, project, "admin")
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    report = read_import(connection, identity, project, patient, import_id)
    if report.status == "quarantined":
        raise HTTPException(409)
    for file_id in report.file_ids:
        require_resource_action(
            connection, identity, project, patient, file_id, SourceAction.INTERNAL
        )
        require_resource_action(
            connection, identity, project, patient, file_id, SourceAction.DERIVATIVE
        )
    connection.execute(
        text(
            "INSERT INTO imaging.confirmations(project_id,patient_id,import_id,confirmed_by) VALUES(:p,:u,:id,:actor) ON CONFLICT DO NOTHING"
        ),
        {"p": project, "u": patient, "id": import_id, "actor": identity.user_id},
    )
    audit(connection, project, import_id, "IMAGING_IMPORT_CONFIRMED")
    return read_import(connection, identity, project, patient, import_id)
