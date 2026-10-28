"""Actual private S3/SQL; cleanup deletes only objects created by these tests."""

from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
from urllib.request import urlopen
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_imaging_ingestion import imaging_db, registry_db, stage

from canceros.identity import Identity
from canceros.imaging_storage import AssetGrantInput, apply_cleanup, grant_asset, plan_cleanup
from canceros.lineage import WithdrawalInput, withdraw_resource

__all__ = ["imaging_db", "registry_db"]


def test_grant_actual_version_and_private_audit(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    receipt, _ = stage(imaging_db)
    value = grant_asset(
        c, i, p, patient.patient_id, receipt.artifact_id, AssetGrantInput(), storage
    )
    query = parse_qs(urlsplit(value.url).query)
    assert query["X-Amz-Expires"] == ["120"] and query["versionId"]
    with urlopen(value.url, timeout=5) as downloaded:
        assert downloaded.read().startswith(b"\\x5c\\x01") is False  # actual signed GET succeeds
    row = c.execute(
        text("SELECT to_jsonb(e)::text FROM imaging.asset_grant_events e WHERE artifact_id=:id"),
        {"id": receipt.artifact_id},
    ).scalar_one()
    assert str(i.user_id) in row and "http" not in row and "X-Amz" not in row
    with pytest.raises(ValidationError):
        AssetGrantInput(expires_seconds=121)
    with pytest.raises(HTTPException):
        grant_asset(c, i, p, patient.patient_id, uuid4(), AssetGrantInput(), storage)
    c.execute(
        text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:actor,'admin')"),
        {"p": p, "actor": i.user_id},
    )
    c.execute(
        text(
            "INSERT INTO access.patient_grants(project_id,patient_id,user_id,permission) VALUES(:p,:u,:actor,'edit')"
        ),
        {"p": p, "u": patient.patient_id, "actor": i.user_id},
    )
    with pytest.raises(HTTPException):
        grant_asset(
            c,
            Identity(i.user_id, {p: "editor"}),
            p,
            patient.patient_id,
            receipt.artifact_id,
            AssetGrantInput(),
            storage,
        )
    withdraw_resource(
        c,
        i,
        p,
        patient.patient_id,
        receipt.artifact_id,
        WithdrawalInput(reason_code="privacy_review"),
    )
    with pytest.raises(HTTPException):
        grant_asset(c, i, p, patient.patient_id, receipt.artifact_id, AssetGrantInput(), storage)


def test_fixture_cleanup_reservations_idempotency_and_retention(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    receipt, _ = stage(imaging_db)
    referenced = c.execute(
        text("SELECT object_key,object_version FROM ops.artifacts WHERE id=:id"),
        {"id": receipt.artifact_id},
    ).one()
    eligible = storage.write_verified(
        p, b"ARTIFICIAL UNREFERENCED TEMPORARY", cleanup_scope="engineering_fixture"
    )
    untagged = storage.write_verified(p, b"ARTIFICIAL UNTAGGED RETAIN")
    other = storage.write_verified(
        uuid4(), b"ARTIFICIAL OTHER PROJECT", cleanup_scope="engineering_fixture"
    )
    future = datetime.now(timezone.utc) + timedelta(days=8)
    plan = plan_cleanup(c, i, p, patient.patient_id, storage, now=future)
    assert plan.candidate_count >= 2
    with pytest.raises(HTTPException) as error:
        apply_cleanup(c, i, p, patient.patient_id, plan.plan_id, storage, now=future)
    assert error.value.status_code == 409  # reservation must durably precede deletion
    c.commit()
    with pytest.raises(DBAPIError), c.begin_nested():
        c.execute(
            text(
                "INSERT INTO ops.artifacts(id,project_id,patient_id,object_key,object_version,byte_size,sha256,provenance,availability) VALUES(:id,:p,:u,:k,:v,:size,:h,'SYNTHETIC_GENERATED','verified')"
            ),
            {
                "id": uuid4(),
                "p": p,
                "u": patient.patient_id,
                "k": eligible.key,
                "v": eligible.version,
                "size": eligible.byte_size,
                "h": eligible.sha256,
            },
        )
    result = apply_cleanup(c, i, p, patient.patient_id, plan.plan_id, storage, now=future)
    assert result.deleted_count == plan.candidate_count and result.retryable_failure_count == 0
    assert apply_cleanup(c, i, p, patient.patient_id, plan.plan_id, storage, now=future) == result
    for key, version in (
        (referenced.object_key, referenced.object_version),
        (untagged.key, untagged.version),
        (other.key, other.version),
    ):
        assert storage.client.head_object(Bucket=storage.bucket, Key=key, VersionId=version)
    with pytest.raises(ClientError):
        storage.client.head_object(
            Bucket=storage.bucket, Key=eligible.key, VersionId=eligible.version
        )
    assert "object_key" not in result.model_dump_json()


def test_cleanup_failed_delete_retry_and_missing_outcome_recovery(imaging_db, monkeypatch):
    c, i, p, patient, _, storage, _ = imaging_db
    storage.write_verified(p, b"ARTIFICIAL RETRY TEMPORARY", cleanup_scope="engineering_fixture")
    future = datetime.now(timezone.utc) + timedelta(days=8)
    plan = plan_cleanup(c, i, p, patient.patient_id, storage, now=future)
    c.commit()
    original = storage.client.delete_object

    def fail(**kwargs):
        raise ClientError({"Error": {"Code": "ServiceUnavailable"}}, "DeleteObject")

    monkeypatch.setattr(storage.client, "delete_object", fail)
    result = apply_cleanup(c, i, p, patient.patient_id, plan.plan_id, storage, now=future)
    assert result.retryable_failure_count == plan.candidate_count
    c.commit()
    monkeypatch.setattr(storage.client, "delete_object", original)
    # Simulate object success followed by SQL outcome rollback. Committed reservations remain.
    with c.begin_nested() as savepoint:
        assert (
            apply_cleanup(
                c, i, p, patient.patient_id, plan.plan_id, storage, now=future
            ).deleted_count
            == plan.candidate_count
        )
        savepoint.rollback()
    assert (
        apply_cleanup(c, i, p, patient.patient_id, plan.plan_id, storage, now=future).deleted_count
        == plan.candidate_count
    )


def test_cleanup_fresh_versions_and_live_jobs_are_retained(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    obj = storage.write_verified(
        p, b"ARTIFICIAL FRESH FIXTURE", cleanup_scope="engineering_fixture"
    )
    assert plan_cleanup(c, i, p, patient.patient_id, storage).candidate_count == 0
    c.execute(
        text(
            "INSERT INTO ops.jobs(id,project_id,patient_id,kind,input_manifest,input_hash,status) VALUES(:id,:p,:u,'engineering.digest','{}',:h,'queued')"
        ),
        {"id": uuid4(), "p": p, "u": patient.patient_id, "h": "a" * 64},
    )
    with pytest.raises(HTTPException) as error:
        plan_cleanup(
            c, i, p, patient.patient_id, storage, now=datetime.now(timezone.utc) + timedelta(days=8)
        )
    assert error.value.status_code == 409
    assert storage.client.head_object(Bucket=storage.bucket, Key=obj.key, VersionId=obj.version)
