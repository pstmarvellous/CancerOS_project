"""Durable, revision-pinned CPU imaging commands on the existing SQL/outbox worker."""

from __future__ import annotations

import hashlib
import secrets
import threading
import time
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4

import psutil
from fastapi import HTTPException
from pydantic import Field
from sqlalchemy import text

from canceros.alignment_runs import AlignmentInput, run_alignment
from canceros.clinical_generation_runs import ClinicalGenerationInput, materialize_clinical
from canceros.contracts import Contract, Hash
from canceros.dependent_updates import DependentUpdateInput, execute_update, freeze_update_inputs
from canceros.identity import Identity, authorize_project
from canceros.imaging_ingestion import read_import, store_artifact
from canceros.imaging_volumes import GeometryValidationInput, validate_volume
from canceros.lineage import (
    derive_resource,
    get_resource,
    lock_lineage,
    processing_spec,
    require_resource_action,
)
from canceros.mask_associations import mask_binding
from canceros.mesh_quality_runs import MeshQCInput, create_mesh_qc
from canceros.mesh_runs import MeshInput, create_mesh
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import canonical_bytes, load_revision, science_hash
from canceros.preprocessing_runs import PreprocessInput, run_preprocessing
from canceros.registration_runs import RegistrationInput, run_registration
from canceros.segmentation_reviews import SegmentationQCInput, run_segmentation_qc
from canceros.simulation_execution import CompleteRunInput, complete_run
from canceros.source_registry import SourceAction
from canceros.synthetic_geometry import GeometryInput, generate_geometry
from canceros.twin_states import StateBuildInput, build_state, freeze_state_inputs

KIND = "imaging.pipeline/1"
READY = "canceros:imaging:ready"
PROCESSING = "canceros:imaging:processing"
MAX_WALL_SECONDS = 120
MAX_RSS_BYTES = 512 * 1024 * 1024
LEASE_SECONDS = 150
HEARTBEAT_SECONDS = 5
WORKER_LOCK = 324032


class GeometryCommand(Contract):
    operation: Literal["geometry"]
    input: GeometryValidationInput


class PreprocessingCommand(Contract):
    operation: Literal["preprocessing"]
    input: PreprocessInput


class AlignmentCommand(Contract):
    operation: Literal["alignment"]
    input: AlignmentInput


class SegmentationQCCommand(Contract):
    operation: Literal["segmentation_qc"]
    input: SegmentationQCInput


class MeshCommand(Contract):
    operation: Literal["mesh"]
    input: MeshInput


class MeshQCCommand(Contract):
    operation: Literal["mesh_qc"]
    input: MeshQCInput


class RegistrationCommand(Contract):
    operation: Literal["registration"]
    input: RegistrationInput


class StateCommand(Contract):
    operation: Literal["state_assembly"]
    input: StateBuildInput


class SyntheticGeometryCommand(Contract):
    operation: Literal["synthetic_geometry"]
    input: GeometryInput


class ClinicalGenerationCommand(Contract):
    operation: Literal["clinical_generation"]
    input: ClinicalGenerationInput


class SimulationCompleteCommand(Contract):
    operation: Literal["simulation_complete"]
    input: CompleteRunInput


class DependentUpdateCommand(Contract):
    operation: Literal["dependent_update"]
    input: DependentUpdateInput


Command = Annotated[
    GeometryCommand
    | PreprocessingCommand
    | AlignmentCommand
    | SegmentationQCCommand
    | MeshCommand
    | MeshQCCommand
    | RegistrationCommand
    | StateCommand
    | SyntheticGeometryCommand
    | ClinicalGenerationCommand
    | SimulationCompleteCommand
    | DependentUpdateCommand,
    Field(discriminator="operation"),
]


class ImagingJobInput(Contract):
    expected_revision: Annotated[int, Field(strict=True, ge=1)]
    command: Command


class ImagingJobRecord(Contract):
    id: UUID
    patient_id: UUID
    data_revision: int
    operation: Literal[
        "geometry",
        "preprocessing",
        "alignment",
        "segmentation_qc",
        "mesh",
        "mesh_qc",
        "registration",
        "state_assembly",
        "synthetic_geometry",
        "clinical_generation",
        "simulation_complete",
        "dependent_update",
    ]
    input_hash: Hash
    status: Literal["queued", "running", "succeeded", "failed", "cancelled"]
    stage: Literal["queued", "processing", "completed", "failed", "cancelled"]
    attempt_count: int
    cancel_requested: bool
    result_artifact_id: UUID | None
    result_report_id: UUID | None
    error_code: str | None
    publication: Literal["draft"] = "draft"
    scientific_review: Literal["pending"] = "pending"
    publication_allowed: Literal[False] = False
    publication_blocked_reason: Literal[
        "qualified_review_and_state_publication_workflow_not_established"
    ] = "qualified_review_and_state_publication_workflow_not_established"
    next_action: str


def _code_hash():
    root = Path(__file__).parent
    names = (
        "imaging_jobs.py",
        "dependent_updates.py",
        "temporal_timeline.py",
        "temporal_trends.py",
        "timeline_runs.py",
        "timeline_source.py",
        "state_fusion.py",
        "imaging_volumes.py",
        "imaging_geometry.py",
        "imaging_formats.py",
        "preprocessing_runs.py",
        "imaging_preprocessing.py",
        "alignment_runs.py",
        "mask_alignment.py",
        "mask_associations.py",
        "annotation_import.py",
        "annotation_contracts.py",
        "segmentation_reviews.py",
        "segmentation_qc.py",
        "mesh_reconstruction.py",
        "mesh_runs.py",
        "mesh_quality.py",
        "mesh_quality_runs.py",
        "measurement_runs.py",
        "physical_measurements.py",
        "registration_runs.py",
        "rigid_registration.py",
        "twin_states.py",
        "lesion_tracking.py",
        "temporal_measurements.py",
        "synthetic_shape.py",
        "synthetic_geometry.py",
        "synthetic_contracts.py",
        "simulation_contracts.py",
        "clinical_generation.py",
        "clinical_generation_runs.py",
        "clinical_validation.py",
        "sampling.py",
        "simulation_execution.py",
        "simulation_validation.py",
        "simulation_plugins.py",
        "simulation_runs.py",
        "simulation_eligibility.py",
        "eligibility_checks.py",
        "scenario_families.py",
        "lineage.py",
        "source_registry.py",
        "patient_linkage.py",
        "storage.py",
    )
    return science_hash(
        {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}
    )


def _identity(connection, actor, project):
    role = connection.execute(
        text("SELECT role FROM access.memberships WHERE project_id=:p AND user_id=:a"),
        {"p": project, "a": actor},
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(403)
    return Identity(actor, {project: role})


def _resource_ids(connection, identity, project, patient, command, storage=None):
    if command.operation == "dependent_update":
        return freeze_update_inputs(connection, identity, project, patient, command.input, storage)
    if command.operation in ("synthetic_geometry", "clinical_generation", "simulation_complete"):
        authorize_project(identity, project, "admin")
        return [command.input.run_id]
    if command.operation == "state_assembly":
        return freeze_state_inputs(connection, identity, project, patient, command.input, storage)
    if command.operation == "geometry":
        imported = read_import(connection, identity, project, patient, command.input.import_id)
        if imported.status != "staged_pending_geometry":
            raise HTTPException(409)
        manifest = connection.execute(
            text(
                "SELECT private_manifest_id FROM imaging.imports WHERE project_id=:p AND patient_id=:u AND id=:id"
            ),
            {"p": project, "u": patient, "id": imported.id},
        ).scalar_one()
        return [manifest, *imported.file_ids]
    if command.operation == "preprocessing":
        # A canonical volume is immutable; the actual adapter validates its type.
        return [command.input.volume_artifact_id]
    if command.operation == "alignment":
        binding = mask_binding(connection, identity, project, patient, command.input.association_id)
        if (
            binding.source_mask_id != command.input.mask_file_id
            or binding.target_image_id != command.input.target_image_id
            or binding.study_id != command.input.mask_study_id
            or binding.evidence_sha256 != command.input.association_evidence_sha256
        ):
            raise HTTPException(409)
        return [binding.id, command.input.mask_file_id, command.input.target_image_id]
    if command.operation == "mesh":
        return [command.input.measurement_id]
    if command.operation == "mesh_qc":
        from canceros.mesh_runs import read_mesh

        return [
            read_mesh(
                connection, identity, project, patient, command.input.mesh_run_id
            ).output_artifact_id
        ]
    if command.operation == "registration":
        authorize_project(identity, project, "admin")
        return [command.input.fixed_image_id, command.input.moving_image_id] + (
            [command.input.moving_segmentation_id, command.input.moving_qc_report_id]
            if command.input.moving_segmentation_id
            else []
        )
    return [command.input.segmentation_id] + (
        [command.input.reference_segmentation_id] if command.input.reference_segmentation_id else []
    )


def _pins(connection, identity, project, patient, ids):
    pins = []
    for resource_id in sorted(set(ids), key=str):
        resource = get_resource(connection, identity, project, patient, resource_id)
        if resource["origin"] != "SYNTHETIC_GENERATED":
            raise HTTPException(409)
        for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE):
            require_resource_action(connection, identity, project, patient, resource_id, action)
        pins.append(
            {
                "id": str(resource_id),
                "content_hash": resource["content_hash"],
                "manifest_hash": resource["manifest_hash"],
                "origin": resource["origin"],
            }
        )
    return pins


def enqueue_imaging(
    connection,
    identity,
    project,
    patient,
    value: ImagingJobInput,
    command_key,
    storage=None,
    *,
    allow_dependent=False,
):
    authorize_patient(connection, identity, project, patient, edit=True)
    if value.command.operation == "dependent_update" and not allow_dependent:
        raise HTTPException(
            409, detail="dependent_update_requires_transactional_domain_event_dispatch"
        )
    lock_lineage(connection, project, patient)
    if (
        not isinstance(command_key, str)
        or not 1 <= len(command_key) <= 128
        or any(ord(c) < 32 for c in command_key)
    ):
        raise HTTPException(422)
    request_hash = science_hash(value.model_dump(mode="json"))
    prior = connection.execute(
        text(
            "SELECT job_id,request_hash FROM imaging.job_commands WHERE project_id=:p AND patient_id=:u AND actor_id=:a AND command_key=:k"
        ),
        {"p": project, "u": patient, "a": identity.user_id, "k": command_key},
    ).one_or_none()
    if prior:
        if prior.request_hash != request_hash:
            raise HTTPException(409)
        record = read_imaging_job(connection, identity, project, patient, prior.job_id)
        row = connection.execute(
            text("SELECT input_manifest FROM ops.jobs WHERE id=:id"), {"id": prior.job_id}
        ).scalar_one()
        _verify_inputs(connection, identity, project, patient, row)
        if record.result_artifact_id:
            require_resource_action(
                connection,
                identity,
                project,
                patient,
                record.result_artifact_id,
                SourceAction.INTERNAL,
            )
        return record
    current = connection.execute(
        text("SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"),
        {"p": project, "u": patient},
    ).scalar_one()
    if current != value.expected_revision:
        raise HTTPException(409)
    revision = load_revision(connection, project, patient, current)
    pins = _pins(
        connection,
        identity,
        project,
        patient,
        _resource_ids(connection, identity, project, patient, value.command, storage),
    )
    manifest = {
        "version": KIND,
        "actor_id": str(identity.user_id),
        "project_id": str(project),
        "patient_id": str(patient),
        "data_revision": current,
        "revision_hash": science_hash(revision),
        "command": value.command.model_dump(mode="json"),
        "inputs": pins,
        "code_hash": _code_hash(),
        "limits": {"wall_seconds": MAX_WALL_SECONDS, "rss_bytes": MAX_RSS_BYTES, "concurrency": 1},
        "fixture_only": True,
    }
    job = uuid4()
    connection.execute(
        text(
            "INSERT INTO ops.jobs(id,project_id,patient_id,kind,input_manifest,input_hash,status) VALUES(:id,:p,:u,:kind,CAST(:m AS jsonb),:h,'queued')"
        ),
        {
            "id": job,
            "p": project,
            "u": patient,
            "kind": KIND,
            "m": canonical_bytes(manifest).decode(),
            "h": science_hash(manifest),
        },
    )
    connection.execute(
        text(
            "INSERT INTO imaging.job_commands(job_id,project_id,patient_id,actor_id,command_key,request_hash) VALUES(:id,:p,:u,:a,:k,:h)"
        ),
        {
            "id": job,
            "p": project,
            "u": patient,
            "a": identity.user_id,
            "k": command_key,
            "h": request_hash,
        },
    )
    connection.execute(
        text("INSERT INTO ops.outbox(id,job_id) VALUES(:id,:job)"), {"id": uuid4(), "job": job}
    )
    audit(connection, project, job, "IMAGING_JOB_ENQUEUED")
    return read_imaging_job(connection, identity, project, patient, job)


def read_imaging_job(connection, identity, project, patient, job_id):
    authorize_patient(connection, identity, project, patient, edit=True)
    row = (
        connection.execute(
            text(
                "SELECT * FROM ops.jobs WHERE id=:id AND project_id=:p AND patient_id=:u AND kind=:kind"
            ),
            {"id": job_id, "p": project, "u": patient, "kind": KIND},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404)
    if science_hash(row["input_manifest"]) != row["input_hash"]:
        raise HTTPException(409)
    result = connection.execute(
        text("SELECT result,result_hash FROM imaging.job_results WHERE job_id=:id"), {"id": job_id}
    ).one_or_none()
    if result and science_hash(result.result) != result.result_hash:
        raise HTTPException(409)
    stage: Literal["queued", "processing", "completed", "failed", "cancelled"] = {
        "queued": "queued",
        "running": "processing",
        "succeeded": "completed",
        "failed": "failed",
        "cancelled": "cancelled",
    }[row["status"]]  # type: ignore[assignment]
    return ImagingJobRecord(
        id=job_id,
        patient_id=patient,
        data_revision=row["input_manifest"]["data_revision"],
        operation=row["input_manifest"]["command"]["operation"],
        input_hash=row["input_hash"],
        status=row["status"],
        stage=stage,
        attempt_count=row["attempt_count"],
        cancel_requested=row["cancel_requested"],
        result_artifact_id=row["result_artifact_id"],
        result_report_id=UUID(result.result["id"]) if result else None,
        error_code=row["error_code"],
        next_action="Inspect completed private technical report; scientific review and publication remain pending"
        if row["status"] == "succeeded"
        else "Inspect the safe error and repair the input or access; retry transport failures through bounded recovery"
        if row["status"] == "failed"
        else "Wait for the current CPU operation or request cancellation; no percentage is inferred",
    )


def cancel_imaging_job(connection, identity, project, patient, job_id):
    record = read_imaging_job(connection, identity, project, patient, job_id)
    if record.status not in ("succeeded", "failed", "cancelled"):
        connection.execute(
            text(
                "UPDATE ops.jobs SET cancel_requested=true,status=CASE WHEN status='queued' THEN 'cancelled' ELSE status END,finished_at=CASE WHEN status='queued' THEN clock_timestamp() ELSE finished_at END WHERE id=:id"
            ),
            {"id": job_id},
        )
        audit(connection, project, job_id, "IMAGING_JOB_CANCEL_REQUESTED")
    return read_imaging_job(connection, identity, project, patient, job_id)


def dispatch_imaging(engine, queue, project_id=None):
    with engine.begin() as connection:
        clause = " AND j.project_id=:p" if project_id else ""
        rows = connection.execute(
            text(
                "SELECT o.id,o.job_id FROM ops.outbox o JOIN ops.jobs j ON j.id=o.job_id WHERE o.delivered_at IS NULL AND j.kind=:kind AND j.next_attempt_at<=clock_timestamp() AND j.status='queued'"
                + clause
                + " ORDER BY o.created_at FOR UPDATE OF o SKIP LOCKED LIMIT 25"
            ),
            {"kind": KIND, **({"p": project_id} if project_id else {})},
        ).all()
        for row in rows:
            queue.lpush(READY, str(row.job_id))
            connection.execute(
                text("UPDATE ops.outbox SET delivered_at=clock_timestamp() WHERE id=:id"),
                {"id": row.id},
            )
    return len(rows)


def recover_imaging(engine, queue, project_id=None):
    """SQL is the authoritative transport repair source, including lost Redis lists."""
    with engine.begin() as connection:
        clause = " AND project_id=:p" if project_id else ""
        rows = connection.execute(
            text(
                "SELECT id,attempt_count FROM ops.jobs WHERE kind=:kind AND status='running' AND leased_until<clock_timestamp()"
                + clause
                + " FOR UPDATE SKIP LOCKED"
            ),
            {"kind": KIND, **({"p": project_id} if project_id else {})},
        ).all()
        for row in rows:
            attempt_token = connection.execute(
                text(
                    "SELECT lease_token FROM ops.job_attempts WHERE job_id=:id AND attempt_number=:a"
                ),
                {"id": row.id, "a": row.attempt_count},
            ).scalar_one_or_none()
            if attempt_token is not None:
                _evidence(
                    connection,
                    row.id,
                    row.attempt_count,
                    attempt_token,
                    "lease_expired",
                    "WORKER_LOST_LEASE",
                    None,
                    None,
                )
            connection.execute(
                text(
                    "UPDATE ops.job_attempts SET outcome='lease_expired' WHERE job_id=:id AND attempt_number=:a AND outcome='running'"
                ),
                {"id": row.id, "a": row.attempt_count},
            )
            connection.execute(
                text(
                    "UPDATE ops.jobs SET status=CASE WHEN cancel_requested THEN 'cancelled' WHEN attempt_count>=3 THEN 'failed' ELSE 'queued' END,lease_token=NULL,leased_until=NULL,error_code='WORKER_LOST_LEASE' WHERE id=:id"
                ),
                {"id": row.id},
            )
            connection.execute(
                text("UPDATE ops.outbox SET delivered_at=NULL WHERE job_id=:id"), {"id": row.id}
            )
        # Repair queued jobs whose delivered Redis transport was lost; duplicates are safe.
        connection.execute(
            text(
                "UPDATE ops.outbox o SET delivered_at=NULL FROM ops.jobs j WHERE j.id=o.job_id AND j.kind=:kind AND j.status='queued' AND j.next_attempt_at<=clock_timestamp()"
                + (" AND j.project_id=:p" if project_id else "")
            ),
            {"kind": KIND, **({"p": project_id} if project_id else {})},
        )
    for raw in queue.lrange(PROCESSING, 0, -1):
        with engine.connect() as connection:
            row = connection.execute(
                text("SELECT status FROM ops.jobs WHERE id=:id AND kind=:kind"),
                {"id": UUID(raw), "kind": KIND},
            ).one_or_none()
        if row is None or row.status != "running":
            queue.lrem(PROCESSING, 0, raw)
    return len(rows)


def _verify_inputs(connection, identity, project, patient, manifest):
    if (
        manifest.get("version") != KIND
        or manifest.get("fixture_only") is not True
        or manifest.get("project_id") != str(project)
        or manifest.get("patient_id") != str(patient)
    ):
        raise HTTPException(409)
    revision = load_revision(connection, project, patient, manifest["data_revision"])
    if science_hash(revision) != manifest["revision_hash"]:
        raise HTTPException(409)
    ids = [UUID(pin["id"]) for pin in manifest["inputs"]]
    if _pins(connection, identity, project, patient, ids) != manifest["inputs"]:
        raise HTTPException(409)


def heartbeat_imaging(engine, job_id, token):
    with engine.begin() as connection:
        return bool(
            connection.execute(
                text(
                    "UPDATE ops.jobs SET leased_until=clock_timestamp()+make_interval(secs=>:seconds) WHERE id=:id AND kind=:kind AND lease_token=:t AND status='running' AND leased_until>clock_timestamp() AND NOT cancel_requested RETURNING id"
                ),
                {"id": job_id, "kind": KIND, "t": token, "seconds": LEASE_SECONDS},
            ).scalar_one_or_none()
        )


def _execute(connection, identity, project, patient, manifest, storage, job_id, config=None):
    value = ImagingJobInput.model_validate(
        {"expected_revision": manifest["data_revision"], "command": manifest["command"]}
    )
    command = value.command
    if command.operation == "dependent_update":
        return execute_update(
            connection, identity, project, patient, command.input, storage, job_id
        )
    if command.operation == "simulation_complete":
        return complete_run(
            connection,
            identity,
            project,
            patient,
            command.input,
            storage,
            "job-" + str(job_id),
            config,
        )
    if command.operation == "clinical_generation":
        return materialize_clinical(
            connection,
            identity,
            project,
            patient,
            command.input,
            storage,
            "job-" + str(job_id),
            config,
        )
    if command.operation == "synthetic_geometry":
        return generate_geometry(
            connection,
            identity,
            project,
            patient,
            command.input,
            storage,
            "job-" + str(job_id),
            config,
        )
    if command.operation == "state_assembly":
        return build_state(
            connection, identity, project, patient, command.input, storage, "job-" + str(job_id)
        )
    if command.operation == "registration":
        return run_registration(
            connection,
            identity,
            project,
            patient,
            command.input,
            storage,
            "job-" + str(job_id),
            manifest["data_revision"],
        )
    if command.operation == "mesh_qc":
        return create_mesh_qc(
            connection, identity, project, patient, command.input, storage, "job-" + str(job_id)
        )
    if command.operation == "geometry":
        return validate_volume(connection, identity, project, patient, command.input, storage)
    if command.operation == "preprocessing":
        return run_preprocessing(connection, identity, project, patient, command.input, storage)
    if command.operation == "alignment":
        return run_alignment(connection, identity, project, patient, command.input, storage)
    if command.operation == "mesh":
        return create_mesh(
            connection, identity, project, patient, command.input, storage, "job-" + str(job_id)
        )
    return run_segmentation_qc(
        connection, identity, project, patient, command.input, storage, "job-" + str(job_id)
    )


class _Abandon(Exception):
    pass


def process_imaging_one(engine, queue, storage, config):
    """One CPU operation, global concurrency one; caller supervisor adds hard limits."""
    with engine.connect() as mutex:
        if not mutex.execute(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": WORKER_LOCK}
        ).scalar_one():
            return None
        try:
            return _process_locked(engine, queue, storage, config)
        finally:
            mutex.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": WORKER_LOCK})


def _process_locked(engine, queue, storage, config):
    raw = queue.rpoplpush(READY, PROCESSING)
    if raw is None:
        return None
    try:
        job_id = UUID(raw)
    except ValueError:
        queue.lrem(PROCESSING, 0, raw)
        return None
    token = uuid4()
    with engine.begin() as connection:
        row = (
            connection.execute(
                text(
                    "SELECT *,leased_until<clock_timestamp() AS expired FROM ops.jobs WHERE id=:id FOR UPDATE"
                ),
                {"id": job_id},
            )
            .mappings()
            .one_or_none()
        )
        if (
            row is None
            or row["kind"] != KIND
            or row["status"] in ("succeeded", "failed", "cancelled")
        ):
            queue.lrem(PROCESSING, 0, raw)
            return job_id
        if row["status"] == "running":
            return None
        if row["cancel_requested"] or row["attempt_count"] >= config.job_max_attempts:
            connection.execute(
                text("UPDATE ops.jobs SET status=:s,finished_at=clock_timestamp() WHERE id=:id"),
                {"s": "cancelled" if row["cancel_requested"] else "failed", "id": job_id},
            )
            queue.lrem(PROCESSING, 0, raw)
            return job_id
        if not connection.execute(
            text("SELECT next_attempt_at<=clock_timestamp() FROM ops.jobs WHERE id=:id"),
            {"id": job_id},
        ).scalar_one():
            queue.lrem(PROCESSING, 0, raw)
            return None
        attempt = row["attempt_count"] + 1
        manifest, project, patient = row["input_manifest"], row["project_id"], row["patient_id"]
        connection.execute(
            text(
                "UPDATE ops.jobs SET status='running',attempt_count=:a,lease_token=:t,leased_until=clock_timestamp()+make_interval(secs=>:seconds),error_code=NULL WHERE id=:id"
            ),
            {"id": job_id, "a": attempt, "t": token, "seconds": LEASE_SECONDS},
        )
        connection.execute(
            text(
                "INSERT INTO ops.job_attempts(job_id,attempt_number,lease_token,outcome) VALUES(:id,:a,:t,'running')"
            ),
            {"id": job_id, "a": attempt, "t": token},
        )
    start = time.monotonic()
    peak = psutil.Process().memory_info().rss
    stop = threading.Event()
    lost = threading.Event()

    def monitor():
        nonlocal peak
        while not stop.wait(HEARTBEAT_SECONDS):
            peak = max(peak, psutil.Process().memory_info().rss)
            try:
                if not heartbeat_imaging(engine, job_id, token):
                    lost.set()
            except Exception:
                lost.set()

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    error, retryable = None, False
    try:
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL statement_timeout='120s'"))
            connection.execute(text("SET LOCAL lock_timeout='10s'"))
            identity = _identity(connection, UUID(manifest["actor_id"]), project)
            authorize_patient(connection, identity, project, patient, edit=True)
            if manifest["command"]["operation"] == "dependent_update":
                # Clinical corrections lock patient then lineage; preserve that order.
                connection.execute(
                    text(
                        "SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u FOR UPDATE"
                    ),
                    {"p": project, "u": patient},
                ).scalar_one()
            lock_lineage(connection, project, patient)
            if science_hash(manifest) != row["input_hash"] or manifest["code_hash"] != _code_hash():
                raise HTTPException(409)
            _verify_inputs(connection, identity, project, patient, manifest)
            result = _execute(
                connection, identity, project, patient, manifest, storage, job_id, config
            )
            result_data = result.model_dump(mode="json")
            invalid = getattr(result, "status", None) in ("invalid", "blocked", "quarantined") or (
                hasattr(result, "technical") and result.technical.technical_status != "pass"
            )
            artifact, digest = store_artifact(
                connection, project, patient, canonical_bytes(result_data), storage
            )
            result_parents = [UUID(pin["id"]) for pin in manifest["inputs"]]
            for key in ("volume_artifact_id", "output_artifact_id", "preview_artifact_id"):
                if result_data.get(key):
                    result_parents.append(UUID(result_data[key]))
            if manifest["command"]["operation"] in (
                "segmentation_qc",
                "mesh_qc",
                "registration",
                "state_assembly",
                "synthetic_geometry",
                "clinical_generation",
                "simulation_complete",
                "dependent_update",
            ):
                result_parents.append(result.id)
            derive_resource(
                connection,
                identity,
                project,
                patient,
                artifact,
                "imaging_job_private_report",
                digest,
                sorted(set(result_parents), key=str),
                processing_spec(
                    __file__,
                    KIND,
                    KIND,
                    {
                        "job_id": str(job_id),
                        "input_hash": row["input_hash"],
                        "result_report_id": str(result.id),
                        "result_hash": science_hash(result_data),
                    },
                ),
            )
            peak = max(peak, psutil.Process().memory_info().rss)
            elapsed = time.monotonic() - start
            if elapsed > MAX_WALL_SECONDS or peak > MAX_RSS_BYTES:
                raise HTTPException(413)
            current = (
                connection.execute(
                    text(
                        "SELECT *,leased_until>clock_timestamp() AS live FROM ops.jobs WHERE id=:id FOR UPDATE"
                    ),
                    {"id": job_id},
                )
                .mappings()
                .one()
            )
            if (
                current["lease_token"] != token
                or current["status"] != "running"
                or not current["live"]
                or lost.is_set()
            ):
                raise _Abandon()
            if current["cancel_requested"]:
                raise HTTPException(499)
            connection.execute(
                text(
                    "INSERT INTO imaging.job_results(job_id,result,result_hash) VALUES(:id,CAST(:r AS jsonb),:h)"
                ),
                {
                    "id": job_id,
                    "r": canonical_bytes(result_data).decode(),
                    "h": science_hash(result_data),
                },
            )
            connection.execute(
                text(
                    "UPDATE ops.jobs SET status=:s,result_hash=:h,result_artifact_id=:artifact,publication_status='draft',finished_at=clock_timestamp(),leased_until=NULL,error_code=:e WHERE id=:id"
                ),
                {
                    "id": job_id,
                    "s": "failed" if invalid else "succeeded",
                    "h": digest,
                    "artifact": artifact,
                    "e": "VALIDATION_REJECTED" if invalid else None,
                },
            )
            connection.execute(
                text(
                    "UPDATE ops.job_attempts SET outcome=:o WHERE job_id=:id AND attempt_number=:a"
                ),
                {
                    "id": job_id,
                    "a": attempt,
                    "o": "validation_rejected" if invalid else "completed",
                },
            )
            _evidence(
                connection,
                job_id,
                attempt,
                token,
                "validation_rejected" if invalid else "completed",
                "VALIDATION_REJECTED" if invalid else None,
                elapsed,
                peak,
            )
            audit(connection, project, job_id, "IMAGING_JOB_TECHNICAL_RESULT_COMMITTED")
    except _Abandon:
        error, retryable = "STALE_OR_EXPIRED_LEASE", True
    except HTTPException as exc:
        error = (
            "CANCELLED"
            if exc.status_code == 499
            else "RESOURCE_LIMIT"
            if exc.status_code == 413
            else "INPUT_OR_ACCESS_REJECTED"
        )
    except (ValueError, LookupError):
        error = "INVALID_PINNED_INPUT"
    except Exception:
        error, retryable = "DEPENDENCY_OR_TRANSACTION_FAILURE", True
    finally:
        stop.set()
        thread.join(timeout=6)
    if error:
        elapsed = time.monotonic() - start
        with engine.begin() as connection:
            current = connection.execute(
                text(
                    "SELECT lease_token,status,cancel_requested FROM ops.jobs WHERE id=:id FOR UPDATE"
                ),
                {"id": job_id},
            ).one()
            if current.lease_token == token and current.status == "running":
                cancelled = current.cancel_requested or error == "CANCELLED"
                retry = retryable and attempt < config.job_max_attempts and not cancelled
                delay = 2**attempt + secrets.randbelow(1000) / 1000
                connection.execute(
                    text(
                        "UPDATE ops.jobs SET status=:s,error_code=:e,leased_until=NULL,lease_token=NULL,next_attempt_at=clock_timestamp()+make_interval(secs=>:delay),finished_at=CASE WHEN :terminal THEN clock_timestamp() ELSE NULL END WHERE id=:id"
                    ),
                    {
                        "id": job_id,
                        "s": "cancelled" if cancelled else "queued" if retry else "failed",
                        "e": error,
                        "delay": delay if retry else 0,
                        "terminal": not retry,
                    },
                )
                connection.execute(
                    text(
                        "UPDATE ops.job_attempts SET outcome=:o WHERE job_id=:id AND attempt_number=:a"
                    ),
                    {
                        "id": job_id,
                        "a": attempt,
                        "o": "cancelled" if cancelled else "retry_scheduled" if retry else "failed",
                    },
                )
                _evidence(
                    connection,
                    job_id,
                    attempt,
                    token,
                    "cancelled" if cancelled else "retry_scheduled" if retry else "failed",
                    error,
                    elapsed,
                    peak,
                )
                if retry:
                    connection.execute(
                        text("UPDATE ops.outbox SET delivered_at=NULL WHERE job_id=:id"),
                        {"id": job_id},
                    )
            else:
                # Late attempts may append diagnostics, never replace another lease's state.
                _evidence(
                    connection,
                    job_id,
                    attempt,
                    token,
                    "stale_completion_rejected",
                    "STALE_OR_EXPIRED_LEASE",
                    elapsed,
                    peak,
                )
    queue.lrem(PROCESSING, 0, raw)
    return job_id


def _evidence(connection, job_id, attempt, token, outcome, error, elapsed, peak):
    connection.execute(
        text(
            "INSERT INTO imaging.job_attempt_evidence(job_id,attempt_number,lease_token,outcome,error_code,wall_seconds,rss_peak_bytes) VALUES(:id,:a,:t,:o,:e,:wall,:rss) ON CONFLICT(job_id,attempt_number) DO NOTHING"
        ),
        {
            "id": job_id,
            "a": attempt,
            "t": token,
            "o": outcome,
            "e": error,
            "wall": elapsed,
            "rss": peak,
        },
    )
