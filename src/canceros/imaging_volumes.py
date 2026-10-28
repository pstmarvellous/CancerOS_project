"""Persist source-pinned canonical arrays and server-calculated physical geometry."""

import io
from typing import Literal
from uuid import UUID, uuid4

import numpy as np
from fastapi import HTTPException
from sqlalchemy import text

from canceros.contracts import Contract, Hash
from canceros.imaging_geometry import CanonicalGeometry, geometry_for
from canceros.imaging_ingestion import parse_staged, read_import, read_staged, store_artifact
from canceros.lineage import derive_resource, lock_lineage, processing_spec, require_resource_action
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import science_hash
from canceros.quality import record_technical_validation
from canceros.source_registry import SourceAction
from canceros.storage import StoredObject


class GeometryValidationInput(Contract):
    import_id: UUID
    rule_version: Literal["geometry/1"] = "geometry/1"


class GeometryReport(Contract):
    id: UUID
    import_id: UUID
    source_file_ids: list[UUID]
    volume_artifact_id: UUID | None
    volume_sha256: Hash | None
    geometry: CanonicalGeometry | None
    status: Literal["valid", "invalid"]
    issue_codes: list[str]
    scientific_review: Literal["pending"] = "pending"
    publication: Literal["draft"] = "draft"
    longitudinal_alignment: Literal["not_established"] = "not_established"
    verification_scope: Literal["synthetic_engineering_fixture_only"] = (
        "synthetic_engineering_fixture_only"
    )
    next_action: str


def validate_volume(connection, identity, project, patient, value, storage):
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    imported = read_import(connection, identity, project, patient, value.import_id)
    if imported.status != "staged_pending_geometry":
        raise HTTPException(409)
    row = connection.execute(
        text(
            "SELECT association,private_manifest_id FROM imaging.imports WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": value.import_id},
    ).one()
    require_resource_action(
        connection, identity, project, patient, row.private_manifest_id, SourceAction.INTERNAL
    )
    require_resource_action(
        connection, identity, project, patient, row.private_manifest_id, SourceAction.DERIVATIVE
    )
    fingerprint = science_hash(
        {
            "import_id": str(value.import_id),
            "rule_version": value.rule_version,
            "parser_version": imported.parser_version,
        }
    )
    existing = connection.execute(
        text(
            "SELECT id FROM imaging.volume_validations WHERE project_id=:p AND patient_id=:u AND input_hash=:hash"
        ),
        {"p": project, "u": patient, "hash": fingerprint},
    ).scalar_one_or_none()
    if existing:
        report = read_geometry(connection, identity, project, patient, existing)
        if report.volume_artifact_id:
            require_resource_action(
                connection,
                identity,
                project,
                patient,
                report.volume_artifact_id,
                SourceAction.INTERNAL,
            )
        return report
    rows = [
        read_staged(connection, identity, project, patient, f, storage) for f in imported.file_ids
    ]
    geometry, array, issues = None, None, []
    try:
        parsed = parse_staged(rows, row.association.get("fourth_axis"))
        geometry = geometry_for(parsed)
        array = parsed.array
    except ValueError:
        issues = ["INVALID_PHYSICAL_GRID"]
    artifact, digest = None, None
    if not issues:
        assert geometry is not None and array is not None
        output = io.BytesIO()
        np.save(output, array, allow_pickle=False)
        artifact, digest = store_artifact(connection, project, patient, output.getvalue(), storage)
        derive_resource(
            connection,
            identity,
            project,
            patient,
            artifact,
            "imaging_volume",
            digest,
            [row.private_manifest_id],
            processing_spec(
                __file__,
                "canonical-volume/1",
                "geometry/1",
                {
                    "import_id": str(value.import_id),
                    "geometry": geometry.model_dump(mode="json"),
                    "array_format": "npy_float64_no_pickle",
                },
            ),
        )
        record_technical_validation(
            connection,
            identity,
            project,
            patient,
            artifact,
            "pass",
            "geometry/1",
            {
                "finite_invertible": True,
                "physical_grid": True,
                "geometry_hash": science_hash(geometry.model_dump(mode="json")),
            },
        )
    report = GeometryReport(
        id=uuid4(),
        import_id=value.import_id,
        source_file_ids=imported.file_ids,
        volume_artifact_id=artifact,
        volume_sha256=digest,
        geometry=geometry,
        status="invalid" if issues else "valid",
        issue_codes=issues,
        next_action="Supply verified spatial metadata or reject this source; original bytes remain unchanged"
        if issues
        else "Inspect sequence/preprocessing and annotation QC; a valid grid does not establish clinical readiness or longitudinal alignment",
    )
    connection.execute(
        text(
            "INSERT INTO imaging.volume_validations(id,project_id,patient_id,import_id,artifact_id,input_hash,report,report_hash) VALUES(:id,:p,:u,:import,:artifact,:hash,CAST(:report AS jsonb),:rh)"
        ),
        {
            "id": report.id,
            "p": project,
            "u": patient,
            "import": value.import_id,
            "artifact": artifact,
            "hash": fingerprint,
            "report": report.model_dump_json(),
            "rh": science_hash(report.model_dump(mode="json")),
        },
    )
    audit(connection, project, report.id, "IMAGING_GEOMETRY_VALIDATED")
    return report


def read_geometry(connection, identity, project, patient, report_id):
    authorize_patient(connection, identity, project, patient, edit=True)
    row = connection.execute(
        text(
            "SELECT report,report_hash FROM imaging.volume_validations WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": report_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.report) != row.report_hash:
        raise HTTPException(409)
    return GeometryReport.model_validate(row.report)


def load_volume(connection, identity, project, patient, artifact_id, storage):
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    require_resource_action(
        connection, identity, project, patient, artifact_id, SourceAction.INTERNAL
    )
    row = (
        connection.execute(
            text(
                "SELECT a.*,v.report,v.report_hash FROM imaging.volume_validations v JOIN ops.artifacts a ON (a.project_id,a.patient_id,a.id)=(v.project_id,v.patient_id,v.artifact_id) WHERE v.project_id=:p AND v.patient_id=:u AND v.artifact_id=:id"
            ),
            {"p": project, "u": patient, "id": artifact_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404)
    if science_hash(row["report"]) != row["report_hash"]:
        raise HTTPException(409)
    report = GeometryReport.model_validate(row["report"])
    raw = storage.read(
        StoredObject(
            project, row["object_key"], row["object_version"], row["sha256"], row["byte_size"]
        ),
        project,
    )
    array = np.load(io.BytesIO(raw), allow_pickle=False)
    if (
        report.geometry is None
        or tuple(array.shape[:3]) != report.geometry.shape_xyz
        or array.dtype != np.float64
        or not np.isfinite(array).all()
    ):
        raise HTTPException(409)
    array.setflags(write=False)
    return report, array
