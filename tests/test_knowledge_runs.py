"""Source-linked SQL relationships on synthetic note/private imaging fixtures."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from simulation_fixtures import setup_simulation_baseline
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_clinical_ingestion import clinical_db
from test_imaging_ingestion import http_session, imaging_db
from test_note_runs import make_extraction
from test_patient_linkage import keys
from test_source_registry import registry_db, review

from canceros.identity import Identity
from canceros.knowledge_contracts import EntityRef, RelationshipInput
from canceros.knowledge_runs import (
    ConceptInput,
    KnowledgeTraversal,
    RelationshipCommand,
    create_concept,
    create_relationship,
    read_concept,
    read_relationship,
    traverse_relationships,
)
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.source_registry import add_review
from canceros.twin_states import BranchInput, create_branch

__all__ = ["clinical_db", "imaging_db", "registry_db"]


def concept(data, code="pain", **changes):
    c, i, p = data[:3]
    return create_concept(c, i, p, ConceptInput(code=code, label=code.capitalize(), **changes))


def assertion(data, extracted, target, *, fact_index=0, **changes):
    c, i, p, patient = data[:4]
    fact = extracted.report.facts[fact_index]
    values = dict(
        relation="ABOUT_CONCEPT",
        source=EntityRef(kind="note_extraction", id=extracted.extraction_id),
        target=EntityRef(kind="clinical_concept", id=target.id),
        assertion_kind="extracted_assertion",
        supporting_resource_ids=[extracted.extraction_id],
        extraction_id=extracted.extraction_id,
        fact_id=fact.fact_id,
        time=fact.resolved_time,
    )
    values.update(changes)
    return create_relationship(
        c, i, p, patient.patient_id, RelationshipCommand(input=RelationshipInput(**values))
    )


def lexical(data, source, target, **changes):
    c, i, p = data[:3]
    return create_relationship(
        c,
        i,
        p,
        None,
        RelationshipCommand(
            input=RelationshipInput(
                relation="RELATED_TO",
                source=EntityRef(kind="clinical_concept", id=source.id),
                target=EntityRef(kind="clinical_concept", id=target.id),
                assertion_kind="model_proposal",
                **changes,
            )
        ),
    )


def test_concept_corrections_are_versioned_and_original_label_is_preserved(clinical_db):
    c, i, p = clinical_db[:3]
    original = concept(clinical_db)
    corrected = create_concept(
        c, i, p, ConceptInput(code="pain", label="Pain mention", supersedes_id=original.id)
    )
    assert corrected.id != original.id and corrected.version == 2
    assert corrected.input.supersedes_id == original.id
    assert corrected.status == "local_vocabulary_unreviewed"
    assert read_concept(c, i, p, original.id) == original
    with pytest.raises(HTTPException) as duplicate:
        concept(clinical_db)
    assert duplicate.value.status_code == 409
    with pytest.raises(HTTPException) as wrong_code:
        concept(clinical_db, "fatigue", supersedes_id=original.id)
    assert wrong_code.value.status_code == 422


def test_positive_and_negated_assertions_keep_exact_distinct_fact_support(clinical_db):
    c, i, p, patient = clinical_db[:4]
    _, extracted = make_extraction(clinical_db, "Patient reports pain. Patient denies pain.")
    target = concept(clinical_db)
    positive = assertion(clinical_db, extracted, target)
    negative = assertion(clinical_db, extracted, target, fact_index=1)
    assert positive.input.fact_id != negative.input.fact_id
    assert not extracted.report.facts[0].negated and extracted.report.facts[1].negated
    for edge in (positive, negative):
        assert edge.provenance == "SYNTHETIC_GENERATED"
        assert edge.validation_status == "unverified_extracted_assertion"
        assert edge.display_status == "Extracted assertion"
        assert read_relationship(c, i, p, patient.patient_id, edge.id) == edge
        assert edge.input.extraction_id == extracted.extraction_id
        assert "Patient reports pain" not in edge.model_dump_json()
    assert (
        c.execute(
            text("SELECT data_revision FROM source.research_patients WHERE id=:u"),
            {"u": patient.patient_id},
        ).scalar_one()
        == 1
    )
    assert (
        c.execute(
            text("SELECT count(*) FROM clinical.observations WHERE patient_id=:u"),
            {"u": patient.patient_id},
        ).scalar_one()
        == 0
    )
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


@pytest.mark.parametrize("wrong", ["fact", "concept", "support", "time"])
def test_assertion_requires_actual_fact_membership_concept_and_time(clinical_db, wrong):
    _, extracted = make_extraction(clinical_db)
    target = concept(clinical_db, "fatigue" if wrong == "concept" else "pain")
    changes = {
        "fact": {"fact_id": uuid4()},
        "support": {"supporting_resource_ids": [extracted.extraction_id, uuid4()]},
        "time": {
            "time": extracted.report.facts[0].resolved_time.model_copy(
                update={"uncertainty_days": "1"}
            )
        },
    }.get(wrong, {})
    with pytest.raises(HTTPException) as error:
        assertion(clinical_db, extracted, target, **changes)
    assert error.value.status_code in (404, 422)


def test_relationship_corrections_preserve_prior_events_and_current_traversal(clinical_db):
    c, i, p, patient = clinical_db[:4]
    _, extracted = make_extraction(clinical_db, "Patient reports pain. Patient denies pain.")
    target = concept(clinical_db)
    first = assertion(clinical_db, extracted, target)
    corrected = assertion(clinical_db, extracted, target, fact_index=1, supersedes_id=first.id)
    assert corrected.version == 2 and corrected.root_id == first.root_id
    assert corrected.input.supersedes_id == first.id
    assert read_relationship(c, i, p, patient.patient_id, first.id) == first
    page = traverse_relationships(
        c, i, p, patient.patient_id, KnowledgeTraversal(start=first.input.source)
    )
    assert page.items == (corrected,)
    with pytest.raises(HTTPException) as duplicate_correction:
        assertion(clinical_db, extracted, target, fact_index=1, supersedes_id=first.id)
    assert duplicate_correction.value.status_code == 409


def test_concept_cycles_bounded_depth_pagination_filters_and_snapshot_staleness(clinical_db):
    c, i, p = clinical_db[:3]
    a, b, d, e = (concept(clinical_db, code) for code in ("a", "b", "d", "e"))
    edges = [
        lexical(clinical_db, a, b),
        lexical(clinical_db, b, a),
        lexical(clinical_db, b, d),
        lexical(clinical_db, d, e),
    ]
    query = KnowledgeTraversal(start=EntityRef(kind="clinical_concept", id=a.id), depth=1, limit=1)
    page = traverse_relationships(c, i, p, None, query)
    assert len(page.items) == 1 and page.next_offset == 1
    following = traverse_relationships(
        c,
        i,
        p,
        None,
        query.model_copy(update={"offset": 1, "expected_snapshot_hash": page.snapshot_hash}),
    )
    assert {page.items[0].id, following.items[0].id} == {edges[0].id, edges[1].id}
    deeper = traverse_relationships(
        c, i, p, None, query.model_copy(update={"depth": 3, "limit": 100})
    )
    assert {edge.id for edge in deeper.items} == {edge.id for edge in edges}
    assert all(edge.validation_status == "unverified_proposal" for edge in deeper.items)
    filtered = traverse_relationships(
        c, i, p, None, query.model_copy(update={"relation_kinds": ("ABOUT_CONCEPT",)})
    )
    assert filtered.items == ()
    lexical(clinical_db, a, e)
    with pytest.raises(HTTPException) as stale:
        traverse_relationships(
            c, i, p, None, query.model_copy(update={"expected_snapshot_hash": page.snapshot_hash})
        )
    assert stale.value.status_code == 409


@pytest.mark.parametrize("scope", ["patient", "project", "branch"])
def test_relationship_reads_and_traversal_reject_foreign_scope(clinical_db, scope):
    c, i, p, patient = clinical_db[:4]
    _, extracted = make_extraction(clinical_db)
    edge = assertion(clinical_db, extracted, concept(clinical_db))
    if scope == "branch":
        with pytest.raises(HTTPException):
            create_relationship(
                c,
                i,
                p,
                patient.patient_id,
                RelationshipCommand(input=edge.input, branch_id=uuid4()),
            )
        return
    project, subject = (uuid4(), patient.patient_id) if scope == "project" else (p, uuid4())
    for operation in (
        lambda: read_relationship(c, i, project, subject, edge.id),
        lambda: traverse_relationships(
            c, i, project, subject, KnowledgeTraversal(start=edge.input.source)
        ),
    ):
        with pytest.raises(HTTPException) as error:
            operation()
        assert error.value.status_code == 404


@pytest.mark.parametrize("mode", ["withdrawal", "rights"])
def test_current_source_policy_and_withdrawal_recheck_relationship_reads(clinical_db, mode):
    c, i, p, patient, _, component, _ = clinical_db
    document, extracted = make_extraction(clinical_db)
    edge = assertion(clinical_db, extracted, concept(clinical_db))
    query = KnowledgeTraversal(start=edge.input.target)
    before = traverse_relationships(c, i, p, patient.patient_id, query)
    if mode == "withdrawal":
        withdraw_resource(
            c,
            i,
            p,
            patient.patient_id,
            document.artifact_id,
            WithdrawalInput(reason_code="rights_withdrawn"),
        )
    else:
        add_review(c, i, p, component, review(action="internal_processing", decision="denied"))
    with pytest.raises(HTTPException) as error:
        read_relationship(c, i, p, patient.patient_id, edge.id)
    assert error.value.status_code == 409
    # Starting from a still-visible concept cannot reveal a withdrawn patient edge.
    page = traverse_relationships(
        c, i, p, patient.patient_id, KnowledgeTraversal(start=edge.input.target)
    )
    assert page.items == ()
    with pytest.raises(HTTPException) as stale:
        traverse_relationships(
            c,
            i,
            p,
            patient.patient_id,
            query.model_copy(update={"expected_snapshot_hash": before.snapshot_hash}),
        )
    assert stale.value.status_code == 409


@pytest.mark.parametrize("role", ["viewer", "editor"])
def test_mutation_and_private_read_role_boundaries(clinical_db, role):
    c, i, p, patient = clinical_db[:4]
    _, extracted = make_extraction(clinical_db)
    edge = assertion(clinical_db, extracted, concept(clinical_db))
    c.execute(
        text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:u,:r)"),
        {"p": p, "u": i.user_id, "r": role},
    )
    c.execute(
        text(
            "INSERT INTO access.patient_grants(project_id,patient_id,user_id,permission) VALUES(:p,:u,:actor,'view')"
        ),
        {"p": p, "u": patient.patient_id, "actor": i.user_id},
    )
    restricted = Identity(i.user_id, {p: role})
    with pytest.raises(HTTPException) as denied:
        create_relationship(
            c, restricted, p, patient.patient_id, RelationshipCommand(input=edge.input)
        )
    assert denied.value.status_code == 403
    if role == "editor":
        assert read_relationship(c, restricted, p, patient.patient_id, edge.id) == edge
    else:
        with pytest.raises(HTTPException) as denied_read:
            read_relationship(c, restricted, p, patient.patient_id, edge.id)
        assert denied_read.value.status_code == 403


@pytest.mark.parametrize(
    "table", ["clinical_concepts", "relationship_events", "relationship_support"]
)
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_sql_relationship_data_is_append_only_and_support_fk_rejects_dangling(
    clinical_db, table, operation
):
    c, i, p, patient = clinical_db[:4]
    _, extracted = make_extraction(clinical_db)
    target = concept(clinical_db)
    edge = assertion(clinical_db, extracted, target)
    column = "relationship_id" if table == "relationship_support" else "id"
    identifier = target.id if table == "clinical_concepts" else edge.id
    with pytest.raises(DBAPIError), c.begin_nested():
        statement = (
            f"DELETE FROM intelligence.{table} WHERE {column}=:id"
            if operation == "DELETE"
            else f"UPDATE intelligence.{table} SET {column}={column} WHERE {column}=:id"
        )
        c.execute(text(statement), {"id": identifier})
    with pytest.raises(DBAPIError), c.begin_nested():
        c.execute(
            text(
                "INSERT INTO intelligence.relationship_support(project_id,patient_id,relationship_id,resource_id) VALUES(:p,:u,:r,:s)"
            ),
            {"p": p, "u": patient.patient_id, "r": edge.id, "s": uuid4()},
        )


def test_actual_branch_links_only_to_its_declared_physical_baseline(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    baseline, origin, _ = setup_simulation_baseline(imaging_db)
    branch = create_branch(
        c,
        i,
        p,
        patient.patient_id,
        BranchInput(baseline_measurement_id=baseline.id, timeline_origin_id=origin, run_id=uuid4()),
        storage,
        "knowledge-baseline-branch",
    )
    value = RelationshipInput(
        relation="GENERATED_FROM_BASELINE",
        source=EntityRef(kind="twin_branch", id=branch.id),
        target=EntityRef(kind="physical_measurement", id=baseline.id),
        assertion_kind="hypothetical_simulation",
        supporting_resource_ids=[branch.id, baseline.id],
    )
    edge = create_relationship(
        c, i, p, patient.patient_id, RelationshipCommand(input=value, branch_id=branch.id)
    )
    assert edge.display_status == "Simulated" and edge.provenance == "SYNTHETIC_GENERATED"
    assert read_relationship(c, i, p, patient.patient_id, edge.id) == edge
    with pytest.raises(HTTPException) as missing_context:
        create_relationship(c, i, p, patient.patient_id, RelationshipCommand(input=value))
    assert missing_context.value.status_code == 422
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_knowledge_http_scoped_replay_and_source_withdrawal(clinical_db):
    c, i, p, patient, _, component, storage = clinical_db
    document, extracted = make_extraction(clinical_db)
    target = concept(clinical_db)
    fact = extracted.report.facts[0]
    value = RelationshipCommand(
        input=RelationshipInput(
            relation="ABOUT_CONCEPT",
            source=EntityRef(kind="note_extraction", id=extracted.extraction_id),
            target=EntityRef(kind="clinical_concept", id=target.id),
            assertion_kind="extracted_assertion",
            supporting_resource_ids=[extracted.extraction_id],
            extraction_id=extracted.extraction_id,
            fact_id=fact.fact_id,
        )
    ).model_dump(mode="json")
    client, headers = http_session((c, i, p, patient, component, storage, keys()))
    root = f"/api/v1/projects/{p}/patients/{patient.patient_id}"
    command_headers = {**headers, "Idempotency-Key": "artificial-knowledge-edge"}
    with client:
        assert (
            client.post(
                root + "/relationships",
                json=value,
                headers={"Idempotency-Key": "artificial-unauthenticated"},
            ).status_code
            == 401
        )
        response = client.post(root + "/relationships", json=value, headers=command_headers)
        assert response.status_code == 201, response.text
        assert response.headers["cache-control"] == "private, no-store"
        result = response.json()
        assert client.get(response.headers["location"], headers=headers).json() == result
        assert (
            client.post(root + "/relationships", json=value, headers=command_headers).json()
            == result
        )
        query = {"start": value["input"]["source"]}
        page = client.post(root + "/relationship-queries", json=query, headers=headers)
        assert page.status_code == 200 and page.json()["items"][0]["id"] == result["id"]
        wrong_root = root.replace(str(patient.patient_id), str(uuid4()))
        assert (
            client.post(
                wrong_root + "/relationship-queries", json=query, headers=headers
            ).status_code
            == 404
        )
        assert (
            client.post(
                root + "/relationships",
                json={**value, "provenance": "REAL_OBSERVED"},
                headers=command_headers,
            ).status_code
            == 422
        )
        withdraw_resource(
            c,
            i,
            p,
            patient.patient_id,
            document.artifact_id,
            WithdrawalInput(reason_code="rights_withdrawn"),
        )
        c.commit()
        assert (
            client.post(root + "/relationships", json=value, headers=command_headers).status_code
            == 409
        )
        assert (
            client.post(root + "/relationship-queries", json=query, headers=headers).status_code
            == 409
        )
