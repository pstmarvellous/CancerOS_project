"""Append-only owned lineage and inherited rights; no mutable historical relabeling."""

import hashlib
import json
import platform
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import AwareDatetime, Field
from sqlalchemy import text

from canceros.contracts import Contract, Hash, Provenance
from canceros.identity import authorize_project
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import science_hash
from canceros.source_registry import SourceAction, capability, get_source, lock_source_policy


class ProcessingSpec(Contract):
    algorithm: Annotated[str, Field(min_length=1, max_length=100)]
    code_version: Annotated[str, Field(min_length=1, max_length=100)]
    code_sha256: Hash
    config_version: Annotated[str, Field(min_length=1, max_length=100)]
    parameters: dict
    environment: dict[str, str]
    seed: int | None = None
    model_reference: str | None = None


class ParentSummary(Contract):
    id: UUID
    origin: Provenance
    content_hash: Hash
    relation: Literal["derived_from", "supersedes"]


class ResourceLineage(Contract):
    id: UUID
    kind: str
    origin: Provenance
    content_hash: Hash
    source_version_id: UUID | None
    manifest_hash: Hash
    processing: ProcessingSpec | None
    parents: list[ParentSummary]
    recorded_at: AwareDatetime
    restrictions: list[str]
    next_action: str


class WithdrawalInput(Contract):
    reason_code: Literal[
        "rights_withdrawn", "source_corrected", "scientific_review", "privacy_review"
    ]


class WithdrawalReceipt(Contract):
    id: UUID
    resource_id: UUID
    affected_descendant_ids: list[UUID]
    status: Literal["new_use_blocked"] = "new_use_blocked"
    next_action: str = "Review affected resources and applicable retention/deletion policy; history is not rewritten"


def processing_spec(module_file, algorithm, config_version, parameters, seed=None):
    package_root = Path(__file__).resolve().parent
    source_tree = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(package_root.glob("*.py"))
    }
    return ProcessingSpec(
        algorithm=algorithm,
        code_version="source-tree/1",
        code_sha256=hashlib.sha256(Path(module_file).read_bytes()).hexdigest(),
        config_version=config_version,
        parameters=parameters,
        environment={
            "python": platform.python_version(),
            "owned_source_tree_sha256": science_hash(source_tree),
            **{name: version(name) for name in ("pydantic", "sqlalchemy", "boto3")},
        },
        seed=seed,
    )


def get_resource(connection, identity, project, patient, resource_id):
    authorize_patient(connection, identity, project, patient)
    row = (
        connection.execute(
            text(
                "SELECT * FROM ops.resource_registry WHERE project_id=:p AND patient_id=:u AND id=:id"
            ),
            {"p": project, "u": patient, "id": resource_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404)
    if science_hash(row["manifest"]) != row["manifest_hash"]:
        raise HTTPException(409)
    return row


def register_root(
    connection, identity, project, patient, resource_id, kind, content_hash, source_version_id
):
    authorize_patient(connection, identity, project, patient, edit=True)
    source = get_source(connection, identity, project, source_version_id)
    if source.kind != "artifact_source":
        raise HTTPException(422)
    row = connection.execute(
        text("SELECT sha256 FROM ops.artifacts WHERE project_id=:p AND patient_id=:u AND id=:id"),
        {"p": project, "u": patient, "id": resource_id},
    ).one_or_none()
    if row is None or row.sha256 != content_hash or content_hash != source.manifest_sha256:
        raise HTTPException(422)
    origin = (
        Provenance.SYNTHETIC_GENERATED
        if source.origin == "synthetic_engineering_fixture"
        else Provenance.REAL_OBSERVED
    )
    manifest = {
        "schema_version": "lineage/1",
        "resource_id": str(resource_id),
        "kind": kind,
        "content_hash": content_hash,
        "source_version_id": str(source.id),
        "source_manifest_sha256": source.manifest_sha256,
        "origin": origin.value,
        "parents": [],
        "processing": None,
    }
    insert_resource(
        connection, project, patient, resource_id, kind, content_hash, origin, source.id, manifest
    )
    return resource_id


def inherited_origin(origins):
    if Provenance.SYNTHETIC_GENERATED in origins:
        return Provenance.SYNTHETIC_GENERATED
    if Provenance.MODEL_PREDICTED in origins:
        return Provenance.MODEL_PREDICTED
    if Provenance.INTERPOLATED in origins:
        return Provenance.INTERPOLATED
    return Provenance.REAL_DERIVED


def lock_lineage(connection, project, patient):
    connection.execute(
        text("SELECT id FROM source.research_patients WHERE project_id=:p AND id=:u FOR UPDATE"),
        {"p": project, "u": patient},
    ).one()
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:s,0))"),
        {"s": f"lineage:{project}:{patient}"},
    )


def derive_resource(
    connection,
    identity,
    project,
    patient,
    resource_id,
    kind,
    content_hash,
    parents: list[UUID],
    processing: ProcessingSpec,
    expected_origin=None,
):
    authorize_patient(connection, identity, project, patient, edit=True)
    if (
        not parents
        or len(parents) > 256
        or len(parents) != len(set(parents))
        or resource_id in parents
    ):
        raise HTTPException(422)
    lock_lineage(connection, project, patient)
    parent_rows = [
        get_resource(connection, identity, project, patient, parent) for parent in parents
    ]
    for parent in parents:
        require_resource_action(
            connection, identity, project, patient, parent, SourceAction.DERIVATIVE
        )
    origin = inherited_origin({Provenance(row["origin"]) for row in parent_rows})
    if expected_origin is not None and expected_origin != origin:
        raise HTTPException(422)
    manifest = {
        "schema_version": "lineage/1",
        "resource_id": str(resource_id),
        "kind": kind,
        "content_hash": content_hash,
        "source_version_id": None,
        "origin": origin.value,
        "parents": [
            {"id": str(row["id"]), "content_hash": row["content_hash"], "origin": row["origin"]}
            for row in parent_rows
        ],
        "processing": processing.model_dump(mode="json"),
    }
    # Serialize graph construction with withdrawals so eligibility cannot race insertion.
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:s,0))"),
        {"s": f"lineage:{project}:{patient}"},
    )
    insert_resource(
        connection, project, patient, resource_id, kind, content_hash, origin, None, manifest
    )
    for parent in parents:
        connection.execute(
            text(
                "INSERT INTO source.provenance_edges(project_id,patient_id,child_id,parent_id,relation) VALUES(:p,:u,:child,:parent,'derived_from')"
            ),
            {"p": project, "u": patient, "child": resource_id, "parent": parent},
        )
    return resource_id


def insert_resource(
    connection, project, patient, resource_id, kind, content_hash, origin, source_id, manifest
):
    connection.execute(
        text(
            "INSERT INTO ops.resource_registry(id,project_id,patient_id,kind,content_hash,origin,source_version_id,manifest,manifest_hash) VALUES(:id,:p,:u,:kind,:hash,:origin,:source,CAST(:manifest AS jsonb),:mh)"
        ),
        {
            "id": resource_id,
            "p": project,
            "u": patient,
            "kind": kind,
            "hash": content_hash,
            "origin": origin.value,
            "source": source_id,
            "manifest": json.dumps(manifest),
            "mh": science_hash(manifest),
        },
    )


def ancestors(connection, project, patient, resource_id):
    return (
        connection.execute(
            text(
                "WITH RECURSIVE chain(id) AS (SELECT CAST(:id AS uuid) UNION SELECT e.parent_id FROM source.provenance_edges e JOIN chain c ON e.child_id=c.id WHERE e.project_id=:p AND e.patient_id=:u) SELECT r.* FROM ops.resource_registry r JOIN chain c ON r.id=c.id WHERE r.project_id=:p AND r.patient_id=:u"
            ),
            {"id": resource_id, "p": project, "u": patient},
        )
        .mappings()
        .all()
    )


def resource_restrictions(connection, identity, project, patient, resource_id, action):
    get_resource(connection, identity, project, patient, resource_id)
    rows = ancestors(connection, project, patient, resource_id)
    restrictions = []
    for row in rows:
        if science_hash(row["manifest"]) != row["manifest_hash"]:
            restrictions.append("lineage_integrity_failed")
        if row["source_version_id"]:
            rights = capability(connection, identity, project, row["source_version_id"], action)
            if not rights.permitted:
                restrictions.append("source_permission_" + rights.reason)
        withdrawn = connection.execute(
            text(
                "SELECT id FROM source.withdrawal_events WHERE project_id=:p AND patient_id=:u AND resource_id=:id LIMIT 1"
            ),
            {"p": project, "u": patient, "id": row["id"]},
        ).first()
        if withdrawn:
            restrictions.append("ancestor_withdrawn")
    return sorted(set(restrictions))


def require_resource_action(connection, identity, project, patient, resource_id, action):
    lock_lineage(connection, project, patient)
    components = set()
    for row in ancestors(connection, project, patient, resource_id):
        if row["source_version_id"]:
            source = get_source(connection, identity, project, row["source_version_id"])
            components.add(
                source.parent_version_id if source.kind == "artifact_source" else source.id
            )
    for component_id in sorted(components, key=str):
        lock_source_policy(connection, identity, project, component_id)
    if resource_restrictions(connection, identity, project, patient, resource_id, action):
        raise HTTPException(409)


def lineage_detail(connection, identity, project, patient, resource_id):
    authorize_project(identity, project, "editor")
    row = get_resource(connection, identity, project, patient, resource_id)
    parents = (
        connection.execute(
            text(
                "SELECT r.id,r.origin,r.content_hash,e.relation FROM source.provenance_edges e JOIN ops.resource_registry r ON r.id=e.parent_id WHERE e.project_id=:p AND e.patient_id=:u AND e.child_id=:id ORDER BY r.id"
            ),
            {"p": project, "u": patient, "id": resource_id},
        )
        .mappings()
        .all()
    )
    restrictions = resource_restrictions(
        connection, identity, project, patient, resource_id, SourceAction.INTERNAL
    )
    return ResourceLineage(
        id=resource_id,
        kind=row["kind"],
        origin=row["origin"],
        content_hash=row["content_hash"],
        source_version_id=row["source_version_id"],
        manifest_hash=row["manifest_hash"],
        processing=ProcessingSpec.model_validate(row["manifest"]["processing"])
        if row["manifest"]["processing"]
        else None,
        parents=[ParentSummary.model_validate(p) for p in parents],
        recorded_at=row["recorded_at"],
        restrictions=restrictions,
        next_action="Review the blocked ancestor/source evidence"
        if restrictions
        else "Inspect the pinned source and processing evidence; scientific approval remains separate",
    )


def withdraw_resource(connection, identity, project, patient, resource_id, value):
    authorize_project(identity, project, "admin")
    get_resource(connection, identity, project, patient, resource_id)
    lock_lineage(connection, project, patient)
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:s,0))"),
        {"s": f"lineage:{project}:{patient}"},
    )
    event_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO source.withdrawal_events(id,project_id,patient_id,resource_id,reason_code,actor_id) VALUES(:id,:p,:u,:r,:reason,:actor)"
        ),
        {
            "id": event_id,
            "p": project,
            "u": patient,
            "r": resource_id,
            "reason": value.reason_code,
            "actor": identity.user_id,
        },
    )
    children = (
        connection.execute(
            text(
                "WITH RECURSIVE descendants(id) AS (SELECT CAST(:id AS uuid) UNION SELECT e.child_id FROM source.provenance_edges e JOIN descendants d ON e.parent_id=d.id WHERE e.project_id=:p AND e.patient_id=:u) SELECT id FROM descendants WHERE id<>:id ORDER BY id"
            ),
            {"p": project, "u": patient, "id": resource_id},
        )
        .scalars()
        .all()
    )
    audit(connection, project, resource_id, "RESOURCE_WITHDRAWN")
    return WithdrawalReceipt(
        id=event_id, resource_id=resource_id, affected_descendant_ids=list(children)
    )
