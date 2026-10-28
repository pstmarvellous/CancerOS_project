"""Restricted imaging review grants and reserved, version-specific fixture orphan cleanup."""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4

from botocore.exceptions import ClientError
from fastapi import HTTPException
from pydantic import AwareDatetime, Field
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from canceros.contracts import Contract
from canceros.identity import authorize_project
from canceros.lineage import require_resource_action
from canceros.patient_linkage import authorize_patient
from canceros.source_registry import SourceAction
from canceros.storage import StoredObject

REVIEW_KINDS = {
    "imaging_volume",
    "preprocessed_imaging_volume",
    "aligned_mask_pending_annotation",
    "mask_overlay_preview",
    "imaging_job_private_report",
}


class AssetGrantInput(Contract):
    purpose: Literal["restricted_review"] = "restricted_review"
    expires_seconds: int = Field(default=120, ge=1, le=120)


class AssetGrant(Contract):
    artifact_id: UUID
    url: str
    expires_at: AwareDatetime
    method: Literal["GET"] = "GET"
    warning: str = "Private technical review only; URL may remain usable until expiry after withdrawal. Scientific clearance is pending."


class CleanupReport(Contract):
    plan_id: UUID
    candidate_count: int
    deleted_count: int = 0
    retained_count: int = 0
    retryable_failure_count: int = 0
    scan_limit: Literal[128] = 128
    candidate_limit: Literal[32] = 32
    scope: Literal["bounded_owned_engineering_fixture_versions_only"] = (
        "bounded_owned_engineering_fixture_versions_only"
    )


def grant_asset(connection, identity, project, patient, artifact_id, value, storage):
    authorize_patient(connection, identity, project, patient, edit=True)
    row = (
        connection.execute(
            text(
                "SELECT a.*,r.kind FROM ops.artifacts a JOIN ops.resource_registry r ON (r.project_id,r.patient_id,r.id)=(a.project_id,a.patient_id,a.id) WHERE a.project_id=:p AND a.patient_id=:u AND a.id=:id"
            ),
            {"p": project, "u": patient, "id": artifact_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404)
    if row["kind"] == "source_imaging":
        authorize_project(identity, project, "admin")
    elif row["kind"] not in REVIEW_KINDS:
        raise HTTPException(409)
    require_resource_action(
        connection, identity, project, patient, artifact_id, SourceAction.INTERNAL
    )
    if row["availability"] != "verified":
        raise HTTPException(409)
    stored = StoredObject(
        project, row["object_key"], row["object_version"], row["sha256"], row["byte_size"]
    )
    try:
        url = storage.read_grant(stored, project, value.expires_seconds)
    except (ValueError, ClientError):
        raise HTTPException(409) from None
    expiry = datetime.now(timezone.utc) + timedelta(seconds=value.expires_seconds)
    connection.execute(
        text(
            "INSERT INTO imaging.asset_grant_events(id,project_id,patient_id,artifact_id,actor_id,expires_at) VALUES(:id,:p,:u,:a,:actor,:expiry)"
        ),
        {
            "id": uuid4(),
            "p": project,
            "u": patient,
            "a": artifact_id,
            "actor": identity.user_id,
            "expiry": expiry,
        },
    )
    return AssetGrant(artifact_id=artifact_id, url=url, expires_at=expiry)


def _owned_key(key, project):
    parts = key.split("/")
    try:
        return (
            len(parts) == 3
            and parts[0] in {"verified", "quarantined"}
            and parts[1] == str(project)
            and str(UUID(parts[2])) == parts[2]
        )
    except ValueError:
        return False


def _eligible(connection, storage, project, key, version, now):
    if not _owned_key(key, project) or not version or version == "null":
        return None
    if connection.execute(
        text("SELECT 1 FROM ops.artifacts WHERE object_key=:k AND object_version=:v LIMIT 1"),
        {"k": key, "v": version},
    ).first():
        return None
    head = storage.client.head_object(Bucket=storage.bucket, Key=key, VersionId=version)
    meta = head.get("Metadata", {})
    try:
        created = datetime.fromisoformat(meta["cleanup-created-at"])
        digest = meta["sha256"]
        if (
            meta.get("cleanup-scope") != "engineering_fixture"
            or meta.get("owner-project") != str(project)
            or created.tzinfo is None
            or created > now - timedelta(days=7)
            or head["LastModified"] > now - timedelta(days=7)
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
        ):
            return None
    except (KeyError, ValueError, TypeError):
        return None
    response = storage.client.get_object(Bucket=storage.bucket, Key=key, VersionId=version)
    with response["Body"] as body:
        raw = body.read(storage.cap + 1)
    if len(raw) > storage.cap or hashlib.sha256(raw).hexdigest() != digest:
        return None
    return digest


def _lock(connection, project):
    try:
        with connection.begin_nested():
            connection.execute(
                text("LOCK TABLE ops.artifacts, ops.jobs IN SHARE ROW EXCLUSIVE MODE NOWAIT")
            )
    except DBAPIError:
        raise HTTPException(409) from None
    if connection.execute(
        text(
            "SELECT 1 FROM ops.jobs WHERE project_id=:p AND status IN ('queued','running') LIMIT 1"
        ),
        {"p": project},
    ).first():
        raise HTTPException(409)


def plan_cleanup(connection, identity, project, patient, storage, *, now=None):
    """Reserve at most 32 unreferenced fixture versions. Commit before apply."""
    authorize_project(identity, project, "admin")
    authorize_patient(connection, identity, project, patient, edit=True)
    now = now or datetime.now(timezone.utc)
    _lock(connection, project)
    plan, scanned = uuid4(), 0
    candidates: list[tuple[str, str, str]] = []
    for prefix in (f"quarantined/{project}/", f"verified/{project}/"):
        if scanned >= 128:
            break
        result = storage.client.list_object_versions(
            Bucket=storage.bucket, Prefix=prefix, MaxKeys=128 - scanned
        )
        scanned += len(result.get("DeleteMarkers", []))
        for item in result.get("Versions", []):
            scanned += 1
            digest = _eligible(connection, storage, project, item["Key"], item["VersionId"], now)
            reserved = connection.execute(
                text(
                    "SELECT 1 FROM imaging.cleanup_candidates WHERE object_key=:k AND object_version=:v"
                ),
                {"k": item["Key"], "v": item["VersionId"]},
            ).first()
            if digest and not reserved and len(candidates) < 32:
                candidates.append((item["Key"], item["VersionId"], digest))
    connection.execute(
        text(
            "INSERT INTO imaging.cleanup_plans(id,project_id,patient_id,actor_id,expires_at) VALUES(:id,:p,:u,:actor,:expiry)"
        ),
        {
            "id": plan,
            "p": project,
            "u": patient,
            "actor": identity.user_id,
            "expiry": now + timedelta(hours=1),
        },
    )
    for key, version, digest in candidates:
        connection.execute(
            text(
                "INSERT INTO imaging.cleanup_candidates(id,plan_id,object_key,object_version,sha256) VALUES(:id,:plan,:k,:v,:h)"
            ),
            {"id": uuid4(), "plan": plan, "k": key, "v": version, "h": digest},
        )
    return CleanupReport(plan_id=plan, candidate_count=len(candidates))


def apply_cleanup(connection, identity, project, patient, plan_id, storage, *, now=None):
    authorize_project(identity, project, "admin")
    authorize_patient(connection, identity, project, patient, edit=True)
    now = now or datetime.now(timezone.utc)
    _lock(connection, project)
    plan = (
        connection.execute(
            text(
                "SELECT *,created_xid=txid_current() AS uncommitted FROM imaging.cleanup_plans WHERE id=:id AND project_id=:p AND patient_id=:u"
            ),
            {"id": plan_id, "p": project, "u": patient},
        )
        .mappings()
        .one_or_none()
    )
    if not plan:
        raise HTTPException(404)
    if plan["uncommitted"] or plan["expires_at"] <= now:
        raise HTTPException(409)
    rows = (
        connection.execute(
            text("SELECT * FROM imaging.cleanup_candidates WHERE plan_id=:id ORDER BY id"),
            {"id": plan_id},
        )
        .mappings()
        .all()
    )
    counts = {"deleted": 0, "retained": 0, "retryable_failure": 0}
    for row in rows:
        done = connection.execute(
            text(
                "SELECT outcome FROM imaging.cleanup_outcomes WHERE candidate_id=:id AND outcome IN ('deleted','retained') LIMIT 1"
            ),
            {"id": row["id"]},
        ).scalar_one_or_none()
        if done:
            counts[done] += 1
            continue
        try:
            digest = _eligible(
                connection, storage, project, row["object_key"], row["object_version"], now
            )
            outcome = "retained"
            if digest == row["sha256"]:
                storage.client.delete_object(
                    Bucket=storage.bucket, Key=row["object_key"], VersionId=row["object_version"]
                )
                outcome = "deleted"
        except ClientError as error:
            outcome = (
                "deleted"
                if str(error.response.get("Error", {}).get("Code"))
                in {"NoSuchKey", "NoSuchVersion", "404"}
                else "retryable_failure"
            )
        connection.execute(
            text(
                "INSERT INTO imaging.cleanup_outcomes(id,candidate_id,actor_id,outcome) VALUES(:id,:candidate,:actor,:outcome)"
            ),
            {"id": uuid4(), "candidate": row["id"], "actor": identity.user_id, "outcome": outcome},
        )
        counts[outcome] += 1
    return CleanupReport(
        plan_id=plan_id,
        candidate_count=len(rows),
        deleted_count=counts["deleted"],
        retained_count=counts["retained"],
        retryable_failure_count=counts["retryable_failure"],
    )
