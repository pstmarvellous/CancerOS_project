"""Durable captured revisions; clinical membership assembly is future domain work."""

import hashlib
import json

from sqlalchemy import create_engine, text

from canceros.settings import Settings


def canonical_bytes(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def science_hash(value: dict) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def engine_for(config: Settings):
    if not config.database_url:
        raise RuntimeError("Private database configuration required")
    return create_engine(
        config.database_url.get_secret_value(),
        hide_parameters=True,
        pool_pre_ping=True,
        connect_args={"connect_timeout": config.dependency_timeout_seconds},
        pool_timeout=config.dependency_timeout_seconds,
    )


def capture_revision(connection, project_id, patient_id, revision, manifest):
    connection.execute(
        text(
            "INSERT INTO source.patient_revisions(project_id,patient_id,revision,input_manifest,input_hash) VALUES(:p,:u,:r,CAST(:m AS jsonb),:h)"
        ),
        {
            "p": project_id,
            "u": patient_id,
            "r": revision,
            "m": canonical_bytes(manifest).decode(),
            "h": science_hash(manifest),
        },
    )


def load_revision(connection, project_id, patient_id, revision):
    row = connection.execute(
        text(
            "SELECT input_manifest,input_hash FROM source.patient_revisions WHERE project_id=:p AND patient_id=:u AND revision=:r"
        ),
        {"p": project_id, "u": patient_id, "r": revision},
    ).one_or_none()
    if row is None:
        raise LookupError("REVISION_UNAVAILABLE")
    if science_hash(row.input_manifest) != row.input_hash:
        raise ValueError("REVISION_INTEGRITY_FAILURE")
    return row.input_manifest
