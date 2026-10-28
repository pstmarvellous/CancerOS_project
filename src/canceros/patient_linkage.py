"""Opaque patient identity with authenticated encryption and keyed private lookups."""

import base64
import hashlib
import hmac
import os
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID, uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException
from pydantic import AwareDatetime, Field, SecretStr, model_validator
from sqlalchemy import text

from canceros.contracts import Contract, DecimalString, Hash
from canceros.identity import Identity, authorize_project
from canceros.persistence import capture_revision, load_revision
from canceros.source_registry import SourceAction, get_source, require_source_action


class LinkageInput(Contract):
    source_version_id: UUID
    source_patient_key: SecretStr = Field(
        min_length=1, max_length=256, json_schema_extra={"writeOnly": True}
    )


class PatientIdentity(Contract):
    patient_id: UUID
    display_code: str
    mapping_id: UUID
    source_version_id: UUID
    release_version_id: UUID
    origin: Literal["real_source", "synthetic_engineering_fixture"]


class LinkageStatus(Contract):
    enabled: bool
    real_source_processing: Literal["blocked_pending_privacy_linkage_review"] = (
        "blocked_pending_privacy_linkage_review"
    )
    next_action: str


class PersonLinkInput(Contract):
    left_patient_id: UUID
    right_patient_id: UUID
    supersedes_id: UUID | None = None
    status: Literal["uncertain", "confirmed", "rejected", "withdrawn"]
    confidence: DecimalString
    evidence_reference: Annotated[str, Field(min_length=1, max_length=500)]
    evidence_sha256: Hash

    @model_validator(mode="after")
    def valid_link(self):
        if self.left_patient_id == self.right_patient_id or not 0 <= Decimal(self.confidence) <= 1:
            raise ValueError("Distinct patients and bounded review confidence required")
        return self


class PersonLinkEvent(PersonLinkInput):
    id: UUID
    reviewed_by: UUID
    reviewed_at: AwareDatetime
    downstream_status: Literal["identity_review_changed"] = "identity_review_changed"


def authorize_patient(connection, identity: Identity, project_id, patient_id, edit=False):
    authorize_project(identity, project_id, "editor" if edit else "viewer")
    row = connection.execute(
        text("SELECT id FROM source.research_patients WHERE project_id=:p AND id=:u"),
        {"p": project_id, "u": patient_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if identity.memberships[project_id] == "admin":
        return
    grant = connection.execute(
        text(
            "SELECT permission FROM access.patient_grants WHERE project_id=:p AND patient_id=:u AND user_id=:actor"
        ),
        {"p": project_id, "u": patient_id, "actor": identity.user_id},
    ).scalar_one_or_none()
    if grant is None or (edit and grant != "edit"):
        raise HTTPException(404)


class LinkageKeys:
    def __init__(self, settings):
        if not settings.linkage_active_key:
            raise HTTPException(409)
        self.active = settings.linkage_active_key
        self.keys = {
            v: base64.b64decode(s.get_secret_value(), validate=True)
            for v, s in settings.linkage_keys.items()
        }

    def key(self, version, purpose):
        if version not in self.keys:
            raise HTTPException(409)
        return hmac.digest(self.keys[version], b"canceros-linkage/1/" + purpose, "sha256")

    def digest(self, version, project, release, source_key):
        namespace = f"{project}:{release}:".encode()
        return hmac.new(
            self.key(version, b"lookup"), namespace + source_key.encode(), hashlib.sha256
        ).hexdigest()

    def encrypt(self, version, project, release, mapping, source_key):
        nonce = os.urandom(12)
        aad = f"linkage/1:{project}:{release}:{mapping}:{version}".encode()
        return nonce, AESGCM(self.key(version, b"encryption")).encrypt(
            nonce, source_key.encode(), aad
        )

    def decrypt(self, version, project, release, mapping, nonce, ciphertext):
        aad = f"linkage/1:{project}:{release}:{mapping}:{version}".encode()
        return (
            AESGCM(self.key(version, b"encryption"))
            .decrypt(bytes(nonce), bytes(ciphertext), aad)
            .decode()
        )


def audit(connection, project, target, event):
    connection.execute(
        text(
            "INSERT INTO ops.audit_events(id,project_id,event_code,target_id) VALUES(:id,:p,:event,:target)"
        ),
        {"id": uuid4(), "p": project, "target": target, "event": event},
    )


def release_for(connection, identity, project, source_id):
    source = get_source(connection, identity, project, source_id)
    if source.kind != "artifact_source":
        raise HTTPException(422)
    current = source
    while current.kind != "release":
        current = get_source(connection, identity, project, current.parent_version_id)
    return source, current.id


def mapping_summary(connection, identity, project, mapping_id):
    authorize_project(identity, project, "admin")
    row = (
        connection.execute(
            text(
                "SELECT m.*,p.display_code FROM source.patient_mappings m JOIN source.research_patients p ON (p.project_id,p.id)=(m.project_id,m.patient_id) WHERE m.project_id=:p AND m.id=:id"
            ),
            {"p": project, "id": mapping_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404)
    source = get_source(connection, identity, project, row["source_version_id"])
    return PatientIdentity(
        patient_id=row["patient_id"],
        display_code=row["display_code"],
        mapping_id=mapping_id,
        source_version_id=source.id,
        release_version_id=row["release_version_id"],
        origin=source.origin,
    )


def resolve_mapping(connection, identity, project, value: LinkageInput, settings):
    authorize_project(identity, project, "admin")
    require_source_action(
        connection, identity, project, value.source_version_id, SourceAction.INTERNAL
    )
    source, release = release_for(connection, identity, project, value.source_version_id)
    if source.origin != "synthetic_engineering_fixture":
        raise HTTPException(409)
    keys = LinkageKeys(settings)
    raw = value.source_patient_key.get_secret_value()
    if not raw.strip() or raw != raw.strip() or any(ord(c) < 32 for c in raw):
        raise HTTPException(422)
    # Namespace lock prevents duplicate creation across concurrent workers/key rotations.
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:s,0))"),
        {"s": f"linkage:{project}:{release}"},
    )
    existing = set()
    for version in keys.keys:
        match = connection.execute(
            text(
                "SELECT mapping_id FROM source.mapping_secrets WHERE project_id=:p AND release_version_id=:r AND key_version=:v AND lookup_digest=:d"
            ),
            {
                "p": project,
                "r": release,
                "v": version,
                "d": keys.digest(version, project, release, raw),
            },
        ).scalar_one_or_none()
        if match:
            existing.add(match)
    if len(existing) > 1:
        raise HTTPException(409)
    if existing:
        mapping_id = existing.pop()
        audit(connection, project, mapping_id, "LINKAGE_LOOKUP")
        return mapping_summary(connection, identity, project, mapping_id)
    # An incomplete ring must not silently turn an unsearchable identity into a new person.
    unmapped_keys = connection.execute(
        text(
            "SELECT m.id FROM source.patient_mappings m WHERE m.project_id=:p AND m.release_version_id=:r AND NOT EXISTS (SELECT 1 FROM source.mapping_secrets s WHERE s.project_id=m.project_id AND s.mapping_id=m.id AND s.key_version=ANY(:versions)) LIMIT 1"
        ),
        {"p": project, "r": release, "versions": list(keys.keys)},
    ).first()
    if unmapped_keys:
        raise HTTPException(409)
    patient, mapping_id = uuid4(), uuid4()
    connection.execute(
        text(
            "INSERT INTO source.research_patients(id,project_id,display_code) VALUES(:id,:p,:label)"
        ),
        {"id": patient, "p": project, "label": "Research-" + patient.hex},
    )
    connection.execute(
        text(
            "INSERT INTO source.patient_mappings(id,project_id,patient_id,release_version_id,source_version_id,recorded_by) VALUES(:id,:p,:u,:r,:s,:actor)"
        ),
        {
            "id": mapping_id,
            "p": project,
            "u": patient,
            "r": release,
            "s": source.id,
            "actor": identity.user_id,
        },
    )
    nonce, ciphertext = keys.encrypt(keys.active, project, release, mapping_id, raw)
    connection.execute(
        text(
            "INSERT INTO source.mapping_secrets(project_id,release_version_id,mapping_id,key_version,lookup_digest,nonce,ciphertext) VALUES(:p,:r,:id,:v,:d,:nonce,:cipher)"
        ),
        {
            "p": project,
            "r": release,
            "id": mapping_id,
            "v": keys.active,
            "d": keys.digest(keys.active, project, release, raw),
            "nonce": nonce,
            "cipher": ciphertext,
        },
    )
    audit(connection, project, mapping_id, "LINKAGE_CREATED")
    capture_revision(
        connection,
        project,
        patient,
        1,
        {
            "members": [],
            "retractions": [],
            "identity_review_events": [],
            "mapping_id": str(mapping_id),
        },
    )
    return mapping_summary(connection, identity, project, mapping_id)


def rotate_mapping(connection, identity, project, mapping_id, settings):
    summary = mapping_summary(connection, identity, project, mapping_id)
    keys = LinkageKeys(settings)
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:s,0))"),
        {"s": f"linkage:{project}:{summary.release_version_id}"},
    )
    rows = (
        connection.execute(
            text("SELECT * FROM source.mapping_secrets WHERE project_id=:p AND mapping_id=:id"),
            {"p": project, "id": mapping_id},
        )
        .mappings()
        .all()
    )
    if any(r["key_version"] == keys.active for r in rows):
        return summary
    old = next((r for r in rows if r["key_version"] in keys.keys), None)
    if old is None:
        raise HTTPException(409)
    raw = keys.decrypt(
        old["key_version"],
        project,
        summary.release_version_id,
        mapping_id,
        old["nonce"],
        old["ciphertext"],
    )
    nonce, ciphertext = keys.encrypt(
        keys.active, project, summary.release_version_id, mapping_id, raw
    )
    connection.execute(
        text(
            "INSERT INTO source.mapping_secrets(project_id,release_version_id,mapping_id,key_version,lookup_digest,nonce,ciphertext) VALUES(:p,:r,:id,:v,:d,:nonce,:cipher)"
        ),
        {
            "p": project,
            "r": summary.release_version_id,
            "id": mapping_id,
            "v": keys.active,
            "d": keys.digest(keys.active, project, summary.release_version_id, raw),
            "nonce": nonce,
            "cipher": ciphertext,
        },
    )
    audit(connection, project, mapping_id, "LINKAGE_KEY_ROTATED")
    return summary


def append_person_link(connection, identity, project, value: PersonLinkInput):
    authorize_project(identity, project, "admin")
    for patient in (value.left_patient_id, value.right_patient_id):
        authorize_patient(connection, identity, project, patient)
    pair = sorted((str(value.left_patient_id), str(value.right_patient_id)))
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:s,0))"),
        {"s": f"person-link:{project}:{pair}"},
    )
    previous = connection.execute(
        text(
            "SELECT id,left_patient_id,right_patient_id FROM source.person_link_events WHERE project_id=:p AND ((left_patient_id=:l AND right_patient_id=:r) OR (left_patient_id=:r AND right_patient_id=:l)) ORDER BY sequence DESC LIMIT 1"
        ),
        {"p": project, "l": value.left_patient_id, "r": value.right_patient_id},
    ).one_or_none()
    if (previous.id if previous else None) != value.supersedes_id:
        raise HTTPException(409)
    event_id = uuid4()
    row = connection.execute(
        text(
            "INSERT INTO source.person_link_events(id,project_id,left_patient_id,right_patient_id,supersedes_id,status,confidence,evidence_reference,evidence_sha256,reviewed_by) VALUES(:id,:p,:l,:r,:prior,:status,:confidence,:evidence,:hash,:actor) RETURNING reviewed_at"
        ),
        {
            "id": event_id,
            "p": project,
            "l": value.left_patient_id,
            "r": value.right_patient_id,
            "prior": value.supersedes_id,
            "status": value.status,
            "confidence": Decimal(value.confidence),
            "evidence": value.evidence_reference,
            "hash": value.evidence_sha256,
            "actor": identity.user_id,
        },
    ).one()
    for patient_id in sorted((value.left_patient_id, value.right_patient_id), key=str):
        revision = connection.execute(
            text(
                "SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:id FOR UPDATE"
            ),
            {"p": project, "id": patient_id},
        ).scalar_one()
        manifest = load_revision(connection, project, patient_id, revision)
        manifest = {
            **manifest,
            "identity_review_events": manifest.get("identity_review_events", []) + [str(event_id)],
        }
        capture_revision(connection, project, patient_id, revision + 1, manifest)
        connection.execute(
            text(
                "UPDATE source.research_patients SET data_revision=:rev WHERE project_id=:p AND id=:id"
            ),
            {"rev": revision + 1, "p": project, "id": patient_id},
        )
    audit(connection, project, event_id, "PATIENT_IDENTITY_REVIEW_CHANGED")
    return PersonLinkEvent(
        **value.model_dump(), id=event_id, reviewed_by=identity.user_id, reviewed_at=row.reviewed_at
    )
