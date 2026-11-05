"""Immutable source versions and action-specific rights; metadata never fetches URLs."""

import ipaddress
import json
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import AwareDatetime, Field, field_validator, model_validator
from sqlalchemy import text

from canceros.contracts import Contract, Hash
from canceros.identity import Identity, authorize_project
from canceros.persistence import science_hash

Text = Annotated[str, Field(min_length=1, max_length=2000)]


class SourceAction(StrEnum):
    INTERNAL = "internal_processing"
    EXTERNAL = "external_inference"
    DERIVATIVE = "derivative_creation"
    PUBLIC = "public_demo_redistribution"
    PATIENT = "patient_linkage_privacy"


class SourceVersionInput(Contract):
    record_key: Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}$")]
    version: Annotated[int, Field(strict=True, ge=1)]
    kind: Literal["collection", "release", "component", "artifact_source"]
    parent_version_id: UUID | None = None
    title: Text
    source_url: Annotated[str, Field(max_length=2000)]
    citation: Text
    accession: Text
    retrieved_on: date
    manifest_sha256: Hash
    license_reference: Text
    attribution: Text
    access_conditions: Text
    retention_policy: Text
    availability: Literal["available", "unavailable", "unknown"]
    origin: Literal["real_source", "synthetic_engineering_fixture"]

    @field_validator("source_url")
    @classmethod
    def metadata_url(cls, value):
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.port not in (None, 443)
        ):
            raise ValueError("Public HTTPS citation URL without credentials or query required")
        host = parsed.hostname.lower()
        if host == "localhost" or "." not in host or host.endswith((".local", ".internal")):
            raise ValueError("Public citation host required")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            if not address.is_global:
                raise ValueError("Private citation address rejected")
        return value

    @model_validator(mode="after")
    def hierarchy(self):
        if (self.kind == "collection") != (self.parent_version_id is None):
            raise ValueError("Only a collection has no parent")
        if self.retrieved_on > datetime.now(timezone.utc).date():
            raise ValueError("Retrieval cannot be future dated")
        return self


class SourceVersion(SourceVersionInput):
    id: UUID
    project_id: UUID
    created_by: UUID
    recorded_at: AwareDatetime


class RightsReviewInput(Contract):
    action: SourceAction
    decision: Literal["allowed", "denied", "unknown"]
    basis: Literal["documented_rights_review", "engineering_fixture_example"]
    evidence_reference: Text
    evidence_sha256: Hash
    valid_until: AwareDatetime


class RightsReview(RightsReviewInput):
    id: UUID
    source_version_id: UUID
    reviewed_by: UUID
    reviewed_at: AwareDatetime


class SourceCapability(Contract):
    source_version_id: UUID
    action: SourceAction
    permitted: bool
    verification_scope: Literal["engineering_fixture_only", "documented_review", "not_approved"]
    reason: Literal["allowed", "missing_review", "denied", "unknown", "expired", "unavailable"]
    next_action: str
    attribution: str
    review_id: UUID | None = None


def get_source(connection, identity: Identity, project_id: UUID, source_id: UUID):
    authorize_project(identity, project_id)
    row = (
        connection.execute(
            text("SELECT * FROM source.registry_versions WHERE project_id=:p AND id=:id"),
            {"p": project_id, "id": source_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404)
    if row["record_key"].startswith("manual-"):
        # Generated entry sources contain patient-specific content digests. Their
        # metadata follows the owning clinical resource's access boundary too.
        authorize_project(identity, project_id, "editor")
        if identity.memberships[project_id] != "admin":
            from canceros.patient_linkage import authorize_patient

            owners = connection.execute(
                text(
                    "SELECT DISTINCT patient_id FROM ops.resource_registry WHERE project_id=:p AND source_version_id=:id"
                ),
                {"p": project_id, "id": source_id},
            ).all()
            if not owners:
                raise HTTPException(404)
            for owner in owners:
                authorize_patient(connection, identity, project_id, owner.patient_id)
    return SourceVersion.model_validate(
        {**row["payload"], **{k: row[k] for k in ("id", "project_id", "created_by", "recorded_at")}}
    )


def add_source(connection, identity: Identity, project_id: UUID, value: SourceVersionInput):
    authorize_project(identity, project_id, "admin")
    # Serialize revisions by logical key, including concurrent initial creations.
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
        {"key": str(project_id) + ":" + value.record_key},
    )
    previous = connection.execute(
        text(
            "SELECT version,kind,origin FROM source.registry_versions WHERE project_id=:p AND record_key=:k ORDER BY version DESC LIMIT 1"
        ),
        {"p": project_id, "k": value.record_key},
    ).one_or_none()
    if value.version != (previous.version + 1 if previous else 1):
        raise HTTPException(409)
    if previous and (previous.kind != value.kind or previous.origin != value.origin):
        raise HTTPException(409)
    if value.parent_version_id:
        parent = get_source(connection, identity, project_id, value.parent_version_id)
        expected = {"release": "collection", "component": "release", "artifact_source": "component"}
        if parent.kind != expected.get(value.kind) or parent.origin != value.origin:
            raise HTTPException(422)
    source_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO source.registry_versions(id,project_id,record_key,version,kind,origin,parent_version_id,payload,created_by) VALUES(:id,:p,:k,:v,:kind,:origin,:parent,CAST(:payload AS jsonb),:actor)"
        ),
        {
            "id": source_id,
            "p": project_id,
            "k": value.record_key,
            "v": value.version,
            "kind": value.kind,
            "origin": value.origin,
            "parent": value.parent_version_id,
            "payload": value.model_dump_json(),
            "actor": identity.user_id,
        },
    )
    return get_source(connection, identity, project_id, source_id)


def add_review(
    connection, identity: Identity, project_id: UUID, source_id: UUID, value: RightsReviewInput
):
    authorize_project(identity, project_id, "admin")
    if value.valid_until <= datetime.now(timezone.utc):
        raise HTTPException(422)
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:s,0))"),
        {"s": f"source-policy:{project_id}:{source_id}"},
    )
    source = get_source(connection, identity, project_id, source_id)
    if source.kind != "component" or (
        (source.origin == "synthetic_engineering_fixture")
        != (value.basis == "engineering_fixture_example")
    ):
        raise HTTPException(422)
    review_id = uuid4()
    row = connection.execute(
        text(
            "INSERT INTO source.rights_reviews(id,project_id,source_version_id,action,decision,basis,evidence_reference,evidence_sha256,valid_until,reviewed_by) VALUES(:id,:p,:source,:action,:decision,:basis,:reference,:hash,:until,:actor) RETURNING reviewed_at"
        ),
        {
            "id": review_id,
            "p": project_id,
            "source": source_id,
            "action": value.action.value,
            "decision": value.decision,
            "basis": value.basis,
            "reference": value.evidence_reference,
            "hash": value.evidence_sha256,
            "until": value.valid_until,
            "actor": identity.user_id,
        },
    ).one()
    return RightsReview(
        **value.model_dump(),
        id=review_id,
        source_version_id=source_id,
        reviewed_by=identity.user_id,
        reviewed_at=row.reviewed_at,
    )


def capability(
    connection, identity: Identity, project_id: UUID, source_id: UUID, action: SourceAction
):
    source = get_source(connection, identity, project_id, source_id)
    component = source
    if source.kind == "artifact_source":
        component = get_source(connection, identity, project_id, source.parent_version_id)
    if component.kind != "component":
        raise HTTPException(422)
    review = (
        connection.execute(
            text(
                "SELECT * FROM source.rights_reviews WHERE project_id=:p AND source_version_id=:id AND action=:action ORDER BY sequence DESC LIMIT 1"
            ),
            {"p": project_id, "id": component.id, "action": action.value},
        )
        .mappings()
        .one_or_none()
    )
    reason = "missing_review"
    if review:
        reason = review["decision"]
        if review["valid_until"] <= datetime.now(timezone.utc):
            reason = "expired"
    # Availability never supplies rights; unavailable ancestry independently blocks use.
    current = source
    while True:
        if current.availability != "available":
            reason = "unavailable"
        if current.parent_version_id is None:
            break
        current = get_source(connection, identity, project_id, current.parent_version_id)
    permitted = reason == "allowed"
    scope = "not_approved"
    if permitted:
        scope = (
            "engineering_fixture_only"
            if source.origin == "synthetic_engineering_fixture"
            else "documented_review"
        )
    return SourceCapability.model_validate(
        dict(
            source_version_id=source_id,
            action=action,
            permitted=permitted,
            verification_scope=scope,
            reason=reason,
            next_action="Use only within the recorded scope"
            if permitted
            else "Add current license evidence and an administrator rights review",
            attribution=source.attribution,
            review_id=review["id"] if review else None,
        )
    )


def registry_command(
    connection, identity, project_id, operation, key, value, execute, minimum="admin"
):
    """Atomic idempotency; authorization is always checked before replay."""
    authorize_project(identity, project_id, minimum)
    digest = science_hash(value.model_dump(mode="json"))
    scope = f"{project_id}:{identity.user_id}:{operation}:{key}"
    connection.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:s,0))"), {"s": scope})
    previous = connection.execute(
        text(
            "SELECT input_hash,response FROM source.registry_commands WHERE project_id=:p AND actor_id=:u AND operation=:op AND key=:key"
        ),
        {"p": project_id, "u": identity.user_id, "op": operation, "key": key},
    ).one_or_none()
    if previous:
        if previous.input_hash != digest:
            raise HTTPException(409)
        return previous.response
    result = execute().model_dump(mode="json")
    connection.execute(
        text(
            "INSERT INTO source.registry_commands(project_id,actor_id,operation,key,input_hash,response) VALUES(:p,:u,:op,:key,:hash,CAST(:response AS jsonb))"
        ),
        {
            "p": project_id,
            "u": identity.user_id,
            "op": operation,
            "key": key,
            "hash": digest,
            "response": json.dumps(result),
        },
    )
    return result


def require_source_action(connection, identity, project_id, source_id, action, *, real_data=False):
    lock_source_policy(connection, identity, project_id, source_id)
    result = capability(connection, identity, project_id, source_id, action)
    if not result.permitted or (real_data and result.verification_scope != "documented_review"):
        raise HTTPException(409)
    return result


def lock_source_policy(connection, identity, project, source_id):
    source = get_source(connection, identity, project, source_id)
    component_id = source.parent_version_id if source.kind == "artifact_source" else source.id
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:s,0))"),
        {"s": f"source-policy:{project}:{component_id}"},
    )
