"""Artificial identifiers only; encryption, review history and concurrent SQL writes."""

import base64
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_source_registry import hierarchy, registry_db, review

from canceros.api import create_app
from canceros.identity import Identity
from canceros.patient_linkage import (
    LinkageInput,
    LinkageKeys,
    PersonLinkInput,
    append_person_link,
    authorize_patient,
    mapping_summary,
    resolve_mapping,
    rotate_mapping,
)
from canceros.settings import Settings
from canceros.source_registry import add_review

__all__ = ["registry_db"]


def keys(active="k1", ring=None):
    return Settings(
        mode="test",
        linkage_active_key=active,
        linkage_keys=ring or {"k1": base64.b64encode(os.urandom(32)).decode()},
        _env_file=None,
    )


def setup_mapping(registry_db):
    connection, identity, project = registry_db
    _, _, component, artifact = hierarchy(connection, identity, project)
    add_review(connection, identity, project, component.id, review())
    value = LinkageInput(
        source_version_id=artifact.id, source_patient_key="ARTIFICIAL-SOURCE-KEY-NO-PATIENT"
    )
    return connection, identity, project, value


def test_encrypted_repeat_lookup_scope_and_no_plaintext_summary(registry_db):
    connection, identity, project, value = setup_mapping(registry_db)
    config = keys()
    result = resolve_mapping(connection, identity, project, value, config)
    assert resolve_mapping(connection, identity, project, value, config) == result
    assert value.source_patient_key.get_secret_value() not in result.model_dump_json()
    assert value.source_patient_key.get_secret_value() not in repr(value)
    row = (
        connection.execute(
            text("SELECT * FROM source.mapping_secrets WHERE mapping_id=:id"),
            {"id": result.mapping_id},
        )
        .mappings()
        .one()
    )
    assert value.source_patient_key.get_secret_value().encode() not in row["ciphertext"]
    ring = LinkageKeys(config)
    assert (
        ring.decrypt(
            "k1",
            project,
            result.release_version_id,
            result.mapping_id,
            row["nonce"],
            row["ciphertext"],
        )
        == value.source_patient_key.get_secret_value()
    )
    with pytest.raises(InvalidTag):
        ring.decrypt(
            "k1",
            uuid4(),
            result.release_version_id,
            result.mapping_id,
            row["nonce"],
            row["ciphertext"],
        )
    for role in ("viewer", "editor"):
        with pytest.raises(HTTPException) as denied:
            mapping_summary(
                connection, Identity(identity.user_id, {project: role}), project, result.mapping_id
            )
        assert denied.value.status_code == 403
    with pytest.raises(HTTPException) as hidden:
        mapping_summary(connection, identity, uuid4(), result.mapping_id)
    assert hidden.value.status_code == 404
    with pytest.raises(DBAPIError), connection.begin_nested():
        connection.execute(
            text("DELETE FROM source.mapping_secrets WHERE mapping_id=:id"),
            {"id": result.mapping_id},
        )


def test_rotation_preserves_identity_and_lookup_after_old_key_removed(registry_db):
    connection, identity, project, value = setup_mapping(registry_db)
    config = keys()
    result = resolve_mapping(connection, identity, project, value, config)
    new_key = base64.b64encode(os.urandom(32)).decode()
    rotating = keys("k2", {"k1": config.linkage_keys["k1"], "k2": new_key})
    assert rotate_mapping(connection, identity, project, result.mapping_id, rotating) == result
    assert rotate_mapping(connection, identity, project, result.mapping_id, rotating) == result
    assert (
        resolve_mapping(connection, identity, project, value, keys("k2", {"k2": new_key})) == result
    )
    assert (
        connection.execute(
            text("SELECT count(*) FROM source.mapping_secrets WHERE mapping_id=:id"),
            {"id": result.mapping_id},
        ).scalar_one()
        == 2
    )
    with pytest.raises(HTTPException):
        resolve_mapping(
            connection,
            identity,
            project,
            value,
            keys("lost", {"lost": base64.b64encode(os.urandom(32)).decode()}),
        )


def test_different_releases_separate_until_review_and_correction_keeps_history(registry_db):
    connection, identity, project, value = setup_mapping(registry_db)
    config = keys()
    first = resolve_mapping(connection, identity, project, value, config)
    _, _, component, artifact = hierarchy(connection, identity, project)
    add_review(connection, identity, project, component.id, review())
    second = resolve_mapping(
        connection,
        identity,
        project,
        value.model_copy(update={"source_version_id": artifact.id}),
        config,
    )
    assert first.patient_id != second.patient_id
    event = PersonLinkInput(
        left_patient_id=first.patient_id,
        right_patient_id=second.patient_id,
        status="uncertain",
        confidence="0.5",
        evidence_reference="Synthetic engineering identity example",
        evidence_sha256="a" * 64,
    )
    uncertain = append_person_link(connection, identity, project, event)
    confirmed = append_person_link(
        connection,
        identity,
        project,
        event.model_copy(update={"status": "confirmed", "supersedes_id": uncertain.id}),
    )
    withdrawn = append_person_link(
        connection,
        identity,
        project,
        event.model_copy(update={"status": "withdrawn", "supersedes_id": confirmed.id}),
    )
    assert withdrawn.supersedes_id == confirmed.id
    assert (
        connection.execute(
            text("SELECT count(*) FROM source.person_link_events WHERE project_id=:p"),
            {"p": project},
        ).scalar_one()
        == 3
    )
    assert (
        connection.execute(
            text("SELECT data_revision FROM source.research_patients WHERE id=:id"),
            {"id": first.patient_id},
        ).scalar_one()
        == 4
    )
    assert (
        mapping_summary(connection, identity, project, second.mapping_id).patient_id
        == second.patient_id
    )
    with pytest.raises(HTTPException):
        append_person_link(connection, identity, project, event)


def test_missing_key_and_unapproved_source_block_linkage(registry_db):
    connection, identity, project, value = setup_mapping(registry_db)
    with pytest.raises(HTTPException) as missing:
        resolve_mapping(connection, identity, project, value, Settings(mode="test", _env_file=None))
    assert missing.value.status_code == 409
    _, _, _, artifact = hierarchy(connection, identity, project)
    with pytest.raises(HTTPException):
        resolve_mapping(
            connection,
            identity,
            project,
            value.model_copy(update={"source_version_id": artifact.id}),
            keys(),
        )


def test_patient_scope_requires_explicit_grant(registry_db):
    connection, identity, project, value = setup_mapping(registry_db)
    result = resolve_mapping(connection, identity, project, value, keys())
    editor = Identity(identity.user_id, {project: "editor"})
    connection.execute(
        text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:u,'editor')"),
        {"p": project, "u": identity.user_id},
    )
    with pytest.raises(HTTPException):
        authorize_patient(connection, editor, project, result.patient_id)
    connection.execute(
        text(
            "INSERT INTO access.patient_grants(project_id,patient_id,user_id,permission) VALUES(:p,:id,:u,'view')"
        ),
        {"p": project, "id": result.patient_id, "u": identity.user_id},
    )
    authorize_patient(connection, editor, project, result.patient_id)
    with pytest.raises(HTTPException):
        authorize_patient(connection, editor, project, result.patient_id, edit=True)


def test_concurrent_mapping_creation_one_patient(registry_db):
    connection, identity, project, value = setup_mapping(registry_db)
    # Commit this artificial setup so independent worker connections can see it.
    connection.commit()
    engine = connection.engine
    config = keys()

    def perform(_):
        with engine.begin() as worker:
            return resolve_mapping(worker, identity, project, value, config).patient_id

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(perform, range(3)))
    assert len(set(results)) == 1


def test_http_linkage_never_echoes_or_logs_source_key_and_checks_sql_role(registry_db, caplog):
    connection, identity, project, value = setup_mapping(registry_db)
    connection.execute(
        text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:u,'admin')"),
        {"p": project, "u": identity.user_id},
    )
    connection.commit()
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        private.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    config = Settings(
        mode="test",
        identity_issuer="engineering",
        identity_public_key=public,
        database_url=connection.engine.url.render_as_string(hide_password=False),
        linkage_keys=keys().linkage_keys,
        linkage_active_key="k1",
        _env_file=None,
    )
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(identity.user_id),
            "iss": config.identity_issuer,
            "aud": config.identity_audience,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=5),
        },
        private,
        algorithm="RS256",
    )
    headers = {"Authorization": "Bearer " + token}
    payload = {
        "source_version_id": str(value.source_version_id),
        "source_patient_key": value.source_patient_key.get_secret_value(),
    }
    path = f"/api/v1/projects/{project}/source-patient-resolutions"
    with TestClient(create_app(config)) as client:
        assert client.post(path, json=payload).status_code == 401
        result = client.post(path, json=payload, headers=headers)
        assert result.status_code == 200, result.text
        assert payload["source_patient_key"] not in result.text
        assert payload["source_patient_key"] not in caplog.text
        assert client.post(path, json=payload, headers=headers).json() == result.json()
        with connection.engine.begin() as writer:
            writer.execute(
                text("UPDATE access.memberships SET role='editor' WHERE user_id=:u"),
                {"u": identity.user_id},
            )
        assert client.post(path, json=payload, headers=headers).status_code == 403
        summary = f"/api/v1/projects/{project}/patient-mappings/{result.json()['mapping_id']}"
        assert client.get(summary, headers=headers).status_code == 403
