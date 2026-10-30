"""Owned PostgreSQL source links, immutable corrections and bounded authorized reads."""

import json
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import Field
from sqlalchemy import text

from canceros.clinical_ingestion import check_time, read_record
from canceros.contracts import Contract, Hash, Provenance
from canceros.identity import authorize_project
from canceros.knowledge_contracts import (
    EntityRef,
    RelationshipInput,
    ResolvedEntity,
    TraversalQuery,
    relationship_validation_status,
    validate_relationship,
)
from canceros.lesion_tracking import read_association, read_lesion
from canceros.lineage import get_resource, inherited_origin, lock_lineage, require_resource_action
from canceros.measurement_runs import read_measurement
from canceros.note_runs import read_extraction, read_note
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import science_hash
from canceros.source_registry import SourceAction
from canceros.twin_states import read_branch, read_state


class ConceptInput(Contract):
    code: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    label: str = Field(min_length=1, max_length=120)
    supersedes_id: UUID | None = None


class ConceptView(Contract):
    id: UUID
    project_id: UUID
    input: ConceptInput
    version: int
    status: str = "local_vocabulary_unreviewed"


class RelationshipCommand(Contract):
    input: RelationshipInput
    branch_id: UUID | None = None


class RelationshipView(Contract):
    id: UUID
    project_id: UUID
    patient_id: UUID | None
    branch_id: UUID | None
    root_id: UUID
    version: int
    input: RelationshipInput
    provenance: Provenance | None
    validation_status: str
    display_status: str
    statement: str
    limitations: tuple[str, ...] = (
        "A relationship is not causation or an accepted clinical finding.",
        "Scientific and source review remain separate from structural checks.",
    )


class KnowledgeTraversal(TraversalQuery):
    branch_id: UUID | None = None
    expected_snapshot_hash: Hash | None = None


class RelationshipPage(Contract):
    items: tuple[RelationshipView, ...]
    snapshot_hash: Hash
    next_offset: int | None
    budget_exhausted: bool = False


def _scope(c, i, p, u, *, write=False):
    authorize_project(i, p, "admin" if write else "editor")
    if u is not None:
        authorize_patient(c, i, p, u, edit=write)
        lock_lineage(c, p, u)
    c.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:s,0))"), {"s": f"knowledge:{p}:{u}"}
    )


def read_concept(c, i, p, identifier) -> ConceptView:
    authorize_project(i, p, "editor")
    row = c.execute(
        text(
            "SELECT payload,content_hash FROM intelligence.clinical_concepts WHERE project_id=:p AND id=:id"
        ),
        {"p": p, "id": identifier},
    ).first()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.payload) != row.content_hash:
        raise HTTPException(409)
    return ConceptView.model_validate(row.payload)


def create_concept(c, i, p, value: ConceptInput) -> ConceptView:
    _scope(c, i, p, None, write=True)
    prior = read_concept(c, i, p, value.supersedes_id) if value.supersedes_id else None
    if prior and prior.input.code != value.code:
        raise HTTPException(422)
    version = prior.version + 1 if prior else 1
    exists = c.execute(
        text(
            "SELECT id FROM intelligence.clinical_concepts WHERE project_id=:p AND code=:code AND version=:v"
        ),
        {"p": p, "code": value.code, "v": version},
    ).first()
    if exists:
        raise HTTPException(409)
    result = ConceptView(id=uuid4(), project_id=p, input=value, version=version)
    payload = result.model_dump(mode="json")
    c.execute(
        text(
            "INSERT INTO intelligence.clinical_concepts(id,project_id,code,version,supersedes_id,payload,content_hash) VALUES(:id,:p,:code,:v,:s,CAST(:payload AS jsonb),:h)"
        ),
        {
            "id": result.id,
            "p": p,
            "code": value.code,
            "v": version,
            "s": value.supersedes_id,
            "payload": json.dumps(payload),
            "h": science_hash(payload),
        },
    )
    audit(c, p, result.id, "LOCAL_CONCEPT_VERSION_ADDED")
    return result


def resolve_entity(c, i, p, u, ref: EntityRef) -> ResolvedEntity:
    if ref.kind == "clinical_concept":
        read_concept(c, i, p, ref.id)
        return ResolvedEntity(
            ref=ref, project_id=p, patient_id=None, branch_id=None, provenance=None
        )
    if u is None:
        raise HTTPException(404)
    authorize_patient(c, i, p, u)
    if ref.kind == "patient":
        if ref.id != u:
            raise HTTPException(404)
        return ResolvedEntity(ref=ref, project_id=p, patient_id=u, branch_id=None, provenance=None)
    readers = {
        "clinical_observation": read_record,
        "physical_measurement": read_measurement,
        "lesion_identity": read_lesion,
        "twin_branch": read_branch,
        "twin_snapshot": read_state,
        "note_document": read_note,
        "note_extraction": read_extraction,
    }
    reader = readers.get(ref.kind)
    if reader is None:
        raise HTTPException(409)
    resource = get_resource(c, i, p, u, ref.id)
    if resource["kind"] != ref.kind:
        raise HTTPException(422)
    report = reader(c, i, p, u, ref.id)
    require_resource_action(c, i, p, u, ref.id, SourceAction.INTERNAL)
    branch = ref.id if ref.kind == "twin_branch" else getattr(report, "branch_id", None)
    if ref.kind == "note_extraction":
        branch = report.report.branch_id
    if ref.kind == "twin_snapshot":
        branch = report.snapshot.branch_id
    return ResolvedEntity(
        ref=ref,
        project_id=p,
        patient_id=u,
        branch_id=branch,
        provenance=Provenance(resource["origin"]),
    )


def _support(c, i, p, u, value: RelationshipInput):
    if u is None:
        if value.supporting_resource_ids:
            # No generic corpus resources exist before COS060; never read a patient ID here.
            raise HTTPException(422)
        return
    for identifier in value.supporting_resource_ids:
        resource = get_resource(c, i, p, u, identifier)
        if identifier not in (value.source.id, value.target.id):
            if value.relation != "HAS_MEASUREMENT" or resource["kind"] != "lesion_association":
                raise HTTPException(422)
        require_resource_action(c, i, p, u, identifier, SourceAction.INTERNAL)
    if value.assertion_kind == "extracted_assertion":
        extracted = read_extraction(c, i, p, u, value.extraction_id)
        fact = next((f for f in extracted.report.facts if f.fact_id == value.fact_id), None)
        if fact is None:
            raise HTTPException(404)
        if value.relation == "ABOUT_CONCEPT":
            concept = read_concept(c, i, p, value.target.id)
            if concept.input.code != fact.concept:
                raise HTTPException(422)
        if value.time is not None and value.time != fact.resolved_time:
            raise HTTPException(422)


def _validate(c, i, p, u, command: RelationshipCommand):
    value, branch_id = command.input, command.branch_id
    source = resolve_entity(c, i, p, u, value.source)
    target = resolve_entity(c, i, p, u, value.target)
    baseline_verified = False
    if branch_id:
        branch = read_branch(c, i, p, u, branch_id)
        require_resource_action(c, i, p, u, branch_id, SourceAction.INTERNAL)
        baseline_verified = (
            value.source.kind == "twin_branch"
            and value.source.id == branch_id
            and value.target.id == branch.input.baseline_measurement_id
        )
    _support(c, i, p, u, value)
    if value.time:
        if u is None:
            raise HTTPException(422)
        check_time(c, p, u, value.time)
    try:
        validate_relationship(
            value,
            source,
            target,
            project_id=p,
            patient_id=u,
            branch_id=branch_id,
            baseline_link_verified=baseline_verified,
        )
    except ValueError:
        raise HTTPException(422) from None
    # Structural identity links have canonical backing; no arbitrary claims by UUID.
    if value.relation == "HAS_MEASUREMENT":
        backed = False
        for support in value.supporting_resource_ids:
            resource = get_resource(c, i, p, u, support)
            if resource["kind"] == "lesion_association":
                event = read_association(c, i, p, u, support)
                backed = backed or (
                    event.input.lesion_id == value.source.id
                    and event.input.measurement_id == value.target.id
                    and event.input.status == "matched"
                )
        if not backed:
            raise HTTPException(409)
    origins = {x.provenance for x in (source, target) if x.provenance is not None}
    for identifier in value.supporting_resource_ids:
        origins.add(Provenance(get_resource(c, i, p, u, identifier)["origin"]))
    return inherited_origin(origins) if origins else None


def read_relationship(c, i, p, u, identifier) -> RelationshipView:
    _scope(c, i, p, u)
    row = c.execute(
        text(
            "SELECT payload,content_hash FROM intelligence.relationship_events WHERE project_id=:p AND patient_id IS NOT DISTINCT FROM CAST(:u AS uuid) AND id=:id"
        ),
        {"p": p, "u": u, "id": identifier},
    ).first()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.payload) != row.content_hash:
        raise HTTPException(409)
    view = RelationshipView.model_validate(row.payload)
    _validate(c, i, p, u, RelationshipCommand(input=view.input, branch_id=view.branch_id))
    return view


def create_relationship(c, i, p, u, command: RelationshipCommand) -> RelationshipView:
    _scope(c, i, p, u, write=True)
    provenance = _validate(c, i, p, u, command)
    value = command.input
    prior = read_relationship(c, i, p, u, value.supersedes_id) if value.supersedes_id else None
    if prior and prior.branch_id != command.branch_id:
        raise HTTPException(422)
    if prior:
        successor = c.execute(
            text(
                "SELECT id FROM intelligence.relationship_events WHERE project_id=:p AND supersedes_id=:id"
            ),
            {"p": p, "id": prior.id},
        ).first()
        if successor:
            raise HTTPException(409)
    identifier = uuid4()
    display = {
        "extracted_assertion": "Extracted assertion",
        "hypothetical_simulation": "Simulated",
    }.get(value.assertion_kind, "Unreviewed association")
    result = RelationshipView(
        id=identifier,
        project_id=p,
        patient_id=u,
        branch_id=command.branch_id,
        root_id=prior.root_id if prior else identifier,
        version=prior.version + 1 if prior else 1,
        input=value,
        provenance=provenance,
        validation_status=relationship_validation_status(value.assertion_kind),
        display_status=display,
        statement=f"{value.source.kind.replace('_', ' ').capitalize()} — {value.relation.lower().replace('_', ' ')} — {value.target.kind.replace('_', ' ')}",
    )
    payload = result.model_dump(mode="json")

    def resource(ref):
        return ref.id if ref.kind not in ("patient", "clinical_concept") else None

    c.execute(
        text("""INSERT INTO intelligence.relationship_events(id,project_id,patient_id,branch_id,root_id,version,supersedes_id,
      source_kind,target_kind,source_resource_id,target_resource_id,source_concept_id,target_concept_id,payload,content_hash)
      VALUES(:id,:p,:u,:b,:root,:v,:prior,:sk,:tk,:sr,:tr,:sc,:tc,CAST(:payload AS jsonb),:h)"""),
        {
            "id": identifier,
            "p": p,
            "u": u,
            "b": command.branch_id,
            "root": result.root_id,
            "v": result.version,
            "prior": value.supersedes_id,
            "sk": value.source.kind,
            "tk": value.target.kind,
            "sr": resource(value.source),
            "tr": resource(value.target),
            "sc": value.source.id if value.source.kind == "clinical_concept" else None,
            "tc": value.target.id if value.target.kind == "clinical_concept" else None,
            "payload": json.dumps(payload),
            "h": science_hash(payload),
        },
    )
    for support in value.supporting_resource_ids:
        c.execute(
            text(
                "INSERT INTO intelligence.relationship_support(project_id,patient_id,relationship_id,resource_id) VALUES(:p,:u,:r,:s)"
            ),
            {"p": p, "u": u, "r": identifier, "s": support},
        )
    audit(c, p, identifier, "SOURCE_RELATIONSHIP_APPENDED")
    return result


def traverse_relationships(c, i, p, u, query: KnowledgeTraversal) -> RelationshipPage:
    _scope(c, i, p, u)
    resolve_entity(c, i, p, u, query.start)
    if query.branch_id:
        if u is None:
            raise HTTPException(422)
        read_branch(c, i, p, u, query.branch_id)
        require_resource_action(c, i, p, u, query.branch_id, SourceAction.INTERNAL)
    rows = c.execute(
        text("""SELECT r.id,r.content_hash FROM intelligence.relationship_events r
      WHERE r.project_id=:p AND r.patient_id IS NOT DISTINCT FROM CAST(:u AS uuid)
      AND r.branch_id IS NOT DISTINCT FROM CAST(:b AS uuid)
      AND NOT EXISTS(SELECT 1 FROM intelligence.relationship_events n WHERE n.project_id=r.project_id AND n.supersedes_id=r.id)
      ORDER BY r.id LIMIT 501"""),
        {"p": p, "u": u, "b": query.branch_id},
    ).all()
    if len(rows) > 500:
        return RelationshipPage(
            items=(),
            snapshot_hash=science_hash({"scope_budget": 500}),
            next_offset=None,
            budget_exhausted=True,
        )
    usable = []
    for row in rows:
        try:
            usable.append(read_relationship(c, i, p, u, row.id))
        except HTTPException as exc:
            if exc.status_code not in (403, 404, 409):
                raise
    snapshot = science_hash(
        {
            "eligible_events": [edge.model_dump(mode="json") for edge in usable],
            "query": query.model_dump(
                mode="json", exclude={"offset", "limit", "expected_snapshot_hash"}
            ),
        }
    )
    if query.expected_snapshot_hash and query.expected_snapshot_hash != snapshot:
        raise HTTPException(409)
    frontier = {(query.start.kind, query.start.id)}
    seen = set(frontier)
    selected = {}
    for _ in range(query.depth):
        following = set()
        for edge in usable:
            if query.relation_kinds and edge.input.relation not in query.relation_kinds:
                continue
            left, right = edge.input.source, edge.input.target
            pair = {(left.kind, left.id), (right.kind, right.id)}
            if pair & frontier:
                selected[edge.id] = edge
                following.update(pair - seen)
        seen.update(following)
        frontier = following
    ordered = sorted(selected.values(), key=lambda edge: str(edge.id))
    end = query.offset + query.limit
    return RelationshipPage(
        items=tuple(ordered[query.offset : end]),
        snapshot_hash=snapshot,
        next_offset=end if end < len(ordered) else None,
    )
