"""Owned persistence adapter for bounded CPU preprocessing with inherited source rights."""

import io
from typing import Literal
from uuid import UUID, uuid4

import numpy as np
from fastapi import HTTPException
from sqlalchemy import text

from canceros.contracts import Contract, Hash
from canceros.imaging_geometry import CanonicalGeometry
from canceros.imaging_ingestion import store_artifact
from canceros.imaging_preprocessing import PreprocessingConfig, PreprocessingReport, preprocess
from canceros.imaging_volumes import load_volume
from canceros.lineage import derive_resource, lock_lineage, processing_spec, require_resource_action
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import science_hash
from canceros.source_registry import SourceAction
from canceros.storage import StoredObject


class PreprocessInput(Contract):
    volume_artifact_id: UUID
    config: PreprocessingConfig


class PreprocessRun(Contract):
    id: UUID
    input_artifact_id: UUID
    input_sha256: Hash
    output_artifact_id: UUID | None
    output_sha256: Hash | None
    geometry: CanonicalGeometry | None
    processing: PreprocessingReport | None
    config: PreprocessingConfig
    status: Literal["processed", "blocked"]
    issue_codes: list[str]
    publication: Literal["draft"] = "draft"
    scientific_review: Literal["pending"] = "pending"
    next_action: str


def run_preprocessing(connection, identity, project, patient, value, storage):
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    source, array = load_volume(
        connection, identity, project, patient, value.volume_artifact_id, storage
    )
    require_resource_action(
        connection, identity, project, patient, value.volume_artifact_id, SourceAction.DERIVATIVE
    )
    fingerprint = science_hash(value.model_dump(mode="json"))
    prior = connection.execute(
        text(
            "SELECT id FROM imaging.preprocess_runs WHERE project_id=:p AND patient_id=:u AND input_hash=:hash"
        ),
        {"p": project, "u": patient, "hash": fingerprint},
    ).scalar_one_or_none()
    if prior:
        previous = read_preprocessing(connection, identity, project, patient, prior)
        if previous.output_artifact_id:
            require_resource_action(
                connection,
                identity,
                project,
                patient,
                previous.output_artifact_id,
                SourceAction.INTERNAL,
            )
            require_resource_action(
                connection,
                identity,
                project,
                patient,
                previous.output_artifact_id,
                SourceAction.DERIVATIVE,
            )
        return previous
    imported = connection.execute(
        text("SELECT report FROM imaging.imports WHERE project_id=:p AND patient_id=:u AND id=:id"),
        {"p": project, "u": patient, "id": source.import_id},
    ).scalar_one()
    result, issues = None, []
    try:
        result = preprocess(array, source.geometry, value.config, imported["sequence"])
    except ValueError:
        issues = ["INVALID_SEQUENCE_PHASE_OR_INTENSITY"]
    artifact, digest = None, None
    if result is not None:
        output = io.BytesIO()
        np.save(output, result.array, allow_pickle=False)
        artifact, digest = store_artifact(connection, project, patient, output.getvalue(), storage)
        derive_resource(
            connection,
            identity,
            project,
            patient,
            artifact,
            "preprocessed_imaging_volume",
            digest,
            [value.volume_artifact_id],
            processing_spec(
                __file__,
                "preprocessing/1",
                "preprocessing/1",
                {
                    "config": value.config.model_dump(mode="json"),
                    "processing": result.report.model_dump(mode="json"),
                    "geometry": result.geometry.model_dump(mode="json"),
                },
            ),
        )
    assert source.volume_sha256 is not None
    report = PreprocessRun(
        id=uuid4(),
        input_artifact_id=value.volume_artifact_id,
        input_sha256=source.volume_sha256,
        output_artifact_id=artifact,
        output_sha256=digest,
        geometry=result.geometry if result else None,
        processing=result.report if result else None,
        config=value.config,
        status="blocked" if issues else "processed",
        issue_codes=issues,
        next_action="Provide source-supported sequence/phase ordering or a nonconstant finite volume; unsupported steps stay disabled"
        if issues
        else "Inspect the retained source and numerical processing details before mask alignment; no calibrated perfusion or biological response is inferred",
    )
    connection.execute(
        text(
            "INSERT INTO imaging.preprocess_runs(id,project_id,patient_id,input_artifact_id,output_artifact_id,input_hash,report,report_hash) VALUES(:id,:p,:u,:input,:output,:hash,CAST(:report AS jsonb),:rh)"
        ),
        {
            "id": report.id,
            "p": project,
            "u": patient,
            "input": value.volume_artifact_id,
            "output": artifact,
            "hash": fingerprint,
            "report": report.model_dump_json(),
            "rh": science_hash(report.model_dump(mode="json")),
        },
    )
    audit(connection, project, report.id, "MRI_PREPROCESSING_RUN")
    return report


def read_preprocessing(connection, identity, project, patient, run_id):
    authorize_patient(connection, identity, project, patient, edit=True)
    row = connection.execute(
        text(
            "SELECT report,report_hash FROM imaging.preprocess_runs WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": run_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.report) != row.report_hash:
        raise HTTPException(409)
    return PreprocessRun.model_validate(row.report)


def load_image(connection, identity, project, patient, artifact_id, storage):
    """Internal read of canonical or explicitly selected/preprocessed image, never a guessed channel."""
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    require_resource_action(
        connection, identity, project, patient, artifact_id, SourceAction.INTERNAL
    )
    run = connection.execute(
        text(
            "SELECT id,input_artifact_id FROM imaging.preprocess_runs WHERE project_id=:p AND patient_id=:u AND output_artifact_id=:id"
        ),
        {"p": project, "u": patient, "id": artifact_id},
    ).one_or_none()
    if run is None:
        report, array = load_volume(connection, identity, project, patient, artifact_id, storage)
        return report.geometry, array, report.import_id
    processed = read_preprocessing(connection, identity, project, patient, run.id)
    if processed.status != "processed" or processed.geometry is None:
        raise HTTPException(409)
    source, _ = load_volume(connection, identity, project, patient, run.input_artifact_id, storage)
    row = (
        connection.execute(
            text("SELECT * FROM ops.artifacts WHERE project_id=:p AND patient_id=:u AND id=:id"),
            {"p": project, "u": patient, "id": artifact_id},
        )
        .mappings()
        .one()
    )
    raw = storage.read(
        StoredObject(
            project, row["object_key"], row["object_version"], row["sha256"], row["byte_size"]
        ),
        project,
    )
    array = np.load(io.BytesIO(raw), allow_pickle=False)
    if (
        array.dtype != np.float64
        or tuple(array.shape) != processed.geometry.shape_xyz
        or not np.isfinite(array).all()
    ):
        raise HTTPException(409)
    array.setflags(write=False)
    return processed.geometry, array, source.import_id
