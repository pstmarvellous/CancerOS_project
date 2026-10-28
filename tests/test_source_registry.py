"""Synthetic examples against real PostgreSQL; no actual source rights asserted."""

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dotenv import dotenv_values
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from canceros.api import create_app
from canceros.identity import Identity
from canceros.settings import Settings
from canceros.source_registry import (
    RightsReviewInput,
    SourceAction,
    SourceVersionInput,
    add_review,
    add_source,
    capability,
    get_source,
    require_source_action,
)


def example(**changes):
    return SourceVersionInput.model_validate(
        {
            "record_key": "fixture-" + str(uuid4()),
            "version": 1,
            "kind": "collection",
            "title": "SYNTHETIC ENGINEERING EXAMPLE — no patient data",
            "source_url": "https://example.org/canceros-engineering-fixture",
            "citation": "CancerOS artificial test data, not a licensed clinical cohort",
            "accession": "ENGINEERING-EXAMPLE",
            "retrieved_on": "2026-10-27",
            "manifest_sha256": "a" * 64,
            "license_reference": "EXAMPLE ONLY — no legal determination or real dataset rights",
            "attribution": "CancerOS synthetic engineering fixture",
            "access_conditions": "Isolated engineering tests only",
            "retention_policy": "Disposable test DB; no patient content",
            "availability": "available",
            "origin": "synthetic_engineering_fixture",
            **changes,
        }
    )


@pytest.fixture
def registry_db():
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(".env").get("TEST_DATABASE_URL")
    assert url and "disposable" in url
    engine = create_engine(url, hide_parameters=True)
    with engine.connect() as connection:
        transaction = connection.begin()
        project, user = uuid4(), uuid4()
        connection.execute(
            text("INSERT INTO access.projects(id,name) VALUES(:p,'Synthetic rights fixture')"),
            {"p": project},
        )
        connection.execute(
            text("INSERT INTO access.users(id,issuer,subject) VALUES(:u,'engineering',:s)"),
            {"u": user, "s": str(user)},
        )
        yield connection, Identity(user, {project: "admin"}), project
        if transaction.is_active:
            transaction.rollback()
    engine.dispose()


def hierarchy(connection, identity, project):
    collection = add_source(connection, identity, project, example())
    release = add_source(
        connection, identity, project, example(kind="release", parent_version_id=collection.id)
    )
    component = add_source(
        connection, identity, project, example(kind="component", parent_version_id=release.id)
    )
    artifact = add_source(
        connection,
        identity,
        project,
        example(kind="artifact_source", parent_version_id=component.id),
    )
    return collection, release, component, artifact


def review(**changes):
    return RightsReviewInput.model_validate(
        {
            "action": "internal_processing",
            "decision": "allowed",
            "basis": "engineering_fixture_example",
            "evidence_reference": "Synthetic example only",
            "evidence_sha256": "b" * 64,
            "valid_until": datetime.now(timezone.utc) + timedelta(hours=1),
            **changes,
        }
    )


def test_default_deny_action_expiry_and_fixture_cannot_authorize_real_data(registry_db):
    connection, identity, project = registry_db
    _, _, component, artifact = hierarchy(connection, identity, project)
    assert not capability(connection, identity, project, artifact.id, SourceAction.PUBLIC).permitted
    added = add_review(connection, identity, project, component.id, review())
    assert added.reviewed_by == identity.user_id
    assert capability(connection, identity, project, artifact.id, SourceAction.INTERNAL).permitted
    assert not capability(
        connection, identity, project, artifact.id, SourceAction.EXTERNAL
    ).permitted
    with pytest.raises(HTTPException):
        require_source_action(
            connection, identity, project, artifact.id, SourceAction.INTERNAL, real_data=True
        )
    add_review(connection, identity, project, component.id, review(decision="denied"))
    assert not capability(
        connection, identity, project, artifact.id, SourceAction.INTERNAL
    ).permitted
    # Expired rows are valid historical decisions. Test time without rewriting immutable records.
    import canceros.source_registry as registry

    class Later(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.now(timezone.utc) + timedelta(days=2)

    from unittest.mock import patch

    with patch.object(registry, "datetime", Later):
        assert (
            capability(connection, identity, project, artifact.id, SourceAction.INTERNAL).reason
            == "expired"
        )


def test_versions_immutable_and_new_release_does_not_inherit_review(registry_db):
    connection, identity, project = registry_db
    collection, release, component, artifact = hierarchy(connection, identity, project)
    add_review(connection, identity, project, component.id, review())
    release2 = add_source(
        connection,
        identity,
        project,
        example(
            record_key=release.record_key,
            version=2,
            kind="release",
            parent_version_id=collection.id,
            license_reference="EXAMPLE changed license, distinct release",
        ),
    )
    component2 = add_source(
        connection, identity, project, example(kind="component", parent_version_id=release2.id)
    )
    assert not capability(
        connection, identity, project, component2.id, SourceAction.INTERNAL
    ).permitted
    assert get_source(connection, identity, project, artifact.id).parent_version_id == component.id
    assert (
        get_source(connection, identity, project, release.id).license_reference
        == release.license_reference
    )
    for table in ("registry_versions", "rights_reviews"):
        with pytest.raises(DBAPIError), connection.begin_nested():
            connection.execute(
                text(f"DELETE FROM source.{table} WHERE project_id=:p"), {"p": project}
            )
    with pytest.raises(HTTPException) as collision:
        add_source(
            connection,
            identity,
            project,
            example(record_key=release.record_key, kind="release", parent_version_id=collection.id),
        )
    assert collision.value.status_code == 409


def test_roles_ownership_and_hierarchy(registry_db):
    connection, identity, project = registry_db
    collection, _, component, _ = hierarchy(connection, identity, project)
    for role in ("viewer", "editor"):
        with pytest.raises(HTTPException) as denied:
            add_review(
                connection,
                Identity(identity.user_id, {project: role}),
                project,
                component.id,
                review(),
            )
        assert denied.value.status_code == 403
    with pytest.raises(HTTPException) as hidden:
        get_source(connection, identity, uuid4(), component.id)
    assert hidden.value.status_code == 404
    with pytest.raises(HTTPException):
        add_source(
            connection,
            identity,
            project,
            example(kind="artifact_source", parent_version_id=collection.id),
        )
    with pytest.raises(HTTPException):
        add_review(
            connection, identity, project, component.id, review(basis="documented_rights_review")
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://example.org",
        "https://127.0.0.1/a",
        "https://localhost/a",
        "https://metadata.internal/a",
        "https://user:secret@example.org/a",
        "https://example.org/a?token=secret",
    ],
)
def test_url_metadata_rejects_private_or_secret_locations(url):
    with pytest.raises(ValidationError):
        example(source_url=url)


def test_actual_registry_api_authentication_generated_contracts_and_safe_errors():
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(".env").get("TEST_DATABASE_URL")
    assert url and "disposable" in url
    engine = create_engine(url, hide_parameters=True)
    project, user = uuid4(), uuid4()
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        private.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    config = Settings(mode="test", database_url=url, identity_public_key=public, _env_file=None)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO access.projects(id,name) VALUES(:p,'Synthetic API fixture')"),
            {"p": project},
        )
        connection.execute(
            text("INSERT INTO access.users(id,issuer,subject) VALUES(:u,:iss,:s)"),
            {"u": user, "iss": config.identity_issuer, "s": str(user)},
        )
        connection.execute(
            text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:u,'admin')"),
            {"p": project, "u": user},
        )
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user),
            "iss": config.identity_issuer,
            "aud": config.identity_audience,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=5),
        },
        private,
        algorithm="RS256",
    )
    headers = {"Authorization": "Bearer " + token, "Idempotency-Key": str(uuid4())}
    path = f"/api/v1/projects/{project}/sources"
    with TestClient(create_app(config)) as client:
        assert (
            client.post(
                path,
                json=example().model_dump(mode="json"),
                headers={"Idempotency-Key": str(uuid4())},
            ).status_code
            == 401
        )
        payload = example().model_dump(mode="json")
        response = client.post(path, json=payload, headers=headers)
        assert response.status_code == 201, response.text
        assert client.post(path, json=payload, headers=headers).json() == response.json()
        assert (
            client.post(path, json=example().model_dump(mode="json"), headers=headers).status_code
            == 409
        )
        assert (
            client.get(response.headers["Location"], headers=headers).json()["id"]
            == response.json()["id"]
        )
        assert (
            client.get(
                response.headers["Location"].replace(str(project), str(uuid4())), headers=headers
            ).status_code
            == 404
        )
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE access.memberships SET role='viewer' WHERE user_id=:u"), {"u": user}
            )
        assert (
            client.post(path, json=example().model_dump(mode="json"), headers=headers).status_code
            == 403
        )
        bad = client.post(
            path,
            json={
                **example().model_dump(mode="json"),
                "source_url": "https://secret:private@example.org",
            },
            headers=headers,
        )
        assert bad.status_code == 422 and "private" not in bad.text
        injected = client.post(
            path,
            json={**payload, "protected-source-value-as-extra-key": "ignored"},
            headers=headers,
        )
        assert injected.status_code == 422
        assert "protected-source-value-as-extra-key" not in injected.text
    engine.dispose()
