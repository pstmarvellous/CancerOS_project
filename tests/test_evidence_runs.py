"""Disposable SQL/private S3 integration with artificial evidence, never NCI text."""

import hashlib
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_evidence_contracts import manifest as evidence_manifest
from test_imaging_ingestion import http_session
from test_patient_linkage import keys
from test_source_registry import example, hierarchy, registry_db, review

from canceros.evidence_contracts import CorpusBuildInput, EvidenceTextInput
from canceros.evidence_runs import (
    CorpusActivationInput,
    EvidenceStatusInput,
    activate_corpus,
    build_corpus,
    import_document,
    read_corpus,
    read_document,
    restrict_document,
)
from canceros.identity import Identity
from canceros.settings import Settings
from canceros.source_registry import add_review, add_source
from canceros.storage import PrivateStorage, StoredObject

__all__ = ["registry_db"]


@pytest.fixture
def evidence_db(registry_db):
    c, i, p = registry_db
    _, _, component, _ = hierarchy(c, i, p)
    for action in ("internal_processing", "derivative_creation", "public_demo_redistribution"):
        add_review(c, i, p, component.id, review(action=action))
    return c, i, p, component, PrivateStorage(Settings(mode="test"))


def staged(
    data,
    raw="Artificial paragraph about fixture measurements.\n\nSecond fixture paragraph.",
    *,
    digest=None,
    **changes,
):
    c, i, p, component, _ = data
    changes.setdefault("retraction_status", "clear")
    source = add_source(
        c,
        i,
        p,
        example(
            kind="artifact_source",
            parent_version_id=component.id,
            manifest_sha256=digest or hashlib.sha256(raw.encode()).hexdigest(),
        ),
    )
    metadata = evidence_manifest(source_version_id=source.id, **changes)
    content = (
        EvidenceTextInput(manifest=metadata, text=raw)
        if metadata.content_mode == "approved_excerpt"
        else None
    )
    return metadata, content


def imported(data, **changes):
    c, i, p, _, storage = data
    metadata, content = staged(data, **changes)
    return import_document(c, i, p, metadata, content, storage)


def corpus(data):
    c, i, p = data[:3]
    document = imported(data)
    built = build_corpus(c, i, p, CorpusBuildInput(document_ids=[document.id]))
    return document, built


def test_private_original_bytes_nfc_hash_passage_locators_and_english_fts(evidence_db):
    c, i, p, _, storage = evidence_db
    raw = "🧪 Cafe\u0301 fixture measurement 12.50 mm3.\n\nSecond complete fixture paragraph."
    metadata, content = staged(evidence_db, raw)
    document = import_document(c, i, p, metadata, content, storage)
    assert read_document(c, i, p, document.id) == document
    assert import_document(c, i, p, metadata, content, storage) == document
    assert len(document.passage_ids) == 2
    assert document.original_sha256 == hashlib.sha256(raw.encode()).hexdigest()
    assert document.original_sha256 != document.normalized_sha256
    assert raw not in document.model_dump_json() and "12.50" not in document.model_dump_json()
    artifact = (
        c.execute(
            text("SELECT * FROM ops.artifacts WHERE project_id=:p AND id=:id"),
            {"p": p, "id": document.artifact_id},
        )
        .mappings()
        .one()
    )
    assert artifact["patient_id"] is None
    assert (
        storage.read(
            StoredObject(
                p,
                artifact["object_key"],
                artifact["object_version"],
                artifact["sha256"],
                artifact["byte_size"],
            ),
            p,
        )
        == raw.encode()
    )
    passages = c.execute(
        text(
            "SELECT m.id,m.payload,t.text_content,t.text_sha256 FROM intelligence.evidence_passages m "
            "JOIN intelligence.evidence_passage_content t ON(t.project_id,t.passage_id)=(m.project_id,m.id) "
            "WHERE m.project_id=:p AND m.document_id=:d ORDER BY (m.payload->'span'->>'start')::int"
        ),
        {"p": p, "d": document.id},
    ).all()
    assert passages[0].text_content == "🧪 Café fixture measurement 12.50 mm3."
    assert passages[0].payload["span"]["start"] == 0
    assert passages[0].payload["span"]["end"] == len(passages[0].text_content)
    assert all(
        hashlib.sha256(row.text_content.encode()).hexdigest() == row.text_sha256 for row in passages
    )
    matches = c.execute(
        text(
            "SELECT passage_id FROM intelligence.evidence_passage_content WHERE project_id=:p "
            "AND search_vector @@ plainto_tsquery('english','measurement')"
        ),
        {"p": p},
    ).all()
    assert matches == [(passages[0].id,)]
    index = c.execute(
        text(
            "SELECT indexdef FROM pg_indexes WHERE schemaname='intelligence' AND indexname='evidence_english_search'"
        )
    ).scalar_one()
    assert "USING gin (search_vector)" in index
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_metadata_only_stores_no_bytes_passages_or_index_entries(evidence_db):
    c, i, p = evidence_db[:3]
    document = imported(evidence_db, content_mode="metadata_only")
    assert document.artifact_id is None and document.passage_ids == ()
    assert document.original_sha256 is None and document.normalized_sha256 is None
    assert read_document(c, i, p, document.id) == document
    assert (
        c.execute(
            text("SELECT count(*) FROM intelligence.evidence_passage_content WHERE project_id=:p"),
            {"p": p},
        ).scalar_one()
        == 0
    )
    with pytest.raises(HTTPException) as blocked:
        build_corpus(c, i, p, CorpusBuildInput(document_ids=[document.id]))
    assert blocked.value.status_code == 409


def test_duplicate_doi_version_is_conflict_and_new_version_preserves_prior(evidence_db):
    c, i, p = evidence_db[:3]
    first = imported(evidence_db, doi="DOI:10.1234/ARTIFICIAL")
    with pytest.raises(HTTPException) as duplicate:
        imported(evidence_db, doi="https://doi.org/10.1234/artificial")
    assert duplicate.value.status_code == 409
    second = imported(evidence_db, doi="10.1234/artificial", document_version="fixture-2")
    assert first.id != second.id and read_document(c, i, p, first.id) == first
    assert set(first.passage_ids).isdisjoint(second.passage_ids)


@pytest.mark.parametrize(
    "gate", ["source_hash", "internal", "derivative", "public", "fixture_basis"]
)
def test_rights_and_exact_source_hash_fail_before_private_storage_write(
    evidence_db, monkeypatch, gate
):
    c, i, p, component, storage = evidence_db
    metadata, content = staged(
        evidence_db,
        digest="b" * 64 if gate == "source_hash" else None,
        review_basis="documented_review" if gate == "fixture_basis" else "synthetic_fixture",
    )
    if gate in ("internal", "derivative", "public"):
        action = {
            "internal": "internal_processing",
            "derivative": "derivative_creation",
            "public": "public_demo_redistribution",
        }[gate]
        add_review(c, i, p, component.id, review(action=action, decision="denied"))
    writes = []
    monkeypatch.setattr(storage, "write_verified", lambda *args: writes.append(True))
    with pytest.raises(HTTPException) as error:
        import_document(c, i, p, metadata, content, storage)
    assert error.value.status_code in (409, 422)
    assert writes == []


def test_fixture_review_cannot_enable_content_labeled_as_real_source(evidence_db):
    c, i, p, _, storage = evidence_db
    collection = add_source(c, i, p, example(origin="real_source"))
    release = add_source(
        c, i, p, example(kind="release", parent_version_id=collection.id, origin="real_source")
    )
    component = add_source(
        c, i, p, example(kind="component", parent_version_id=release.id, origin="real_source")
    )
    source = add_source(
        c,
        i,
        p,
        example(kind="artifact_source", parent_version_id=component.id, origin="real_source"),
    )
    metadata = evidence_manifest(
        source_version_id=source.id, content_mode="metadata_only", review_basis="synthetic_fixture"
    )
    with pytest.raises(HTTPException) as blocked:
        import_document(c, i, p, metadata, None, storage)
    assert blocked.value.status_code == 422


def test_corpus_membership_is_reproducible_and_activation_is_atomic_compare_and_swap(evidence_db):
    c, i, p = evidence_db[:3]
    document, built = corpus(evidence_db)
    assert built == build_corpus(c, i, p, CorpusBuildInput(document_ids=[document.id]))
    assert read_corpus(c, i, p, built.id) == built
    assert {identifier for identifier, _ in built.passage_hashes} == set(document.passage_ids)
    first = activate_corpus(c, i, p, CorpusActivationInput(corpus_id=built.id))
    with pytest.raises(HTTPException) as stale:
        activate_corpus(c, i, p, CorpusActivationInput(corpus_id=built.id))
    assert stale.value.status_code == 412
    assert (
        c.execute(
            text(
                "SELECT activation_id FROM intelligence.evidence_corpus_heads WHERE project_id=:p"
            ),
            {"p": p},
        ).scalar_one()
        == first.id
    )
    second = activate_corpus(
        c, i, p, CorpusActivationInput(corpus_id=built.id, expected_activation_id=first.id)
    )
    assert second.prior_activation_id == first.id
    assert (
        c.execute(
            text("SELECT count(*) FROM intelligence.evidence_activations WHERE project_id=:p"),
            {"p": p},
        ).scalar_one()
        == 2
    )


@pytest.mark.parametrize("action", ["withdrawn", "retracted", "retention_review_required"])
def test_restrictions_remove_search_content_and_block_reads_build_and_reactivation(
    evidence_db, action
):
    c, i, p, _, storage = evidence_db
    metadata, content = staged(evidence_db)
    document = import_document(c, i, p, metadata, content, storage)
    built = build_corpus(c, i, p, CorpusBuildInput(document_ids=[document.id]))
    active = activate_corpus(c, i, p, CorpusActivationInput(corpus_id=built.id))
    receipt = restrict_document(
        c, i, p, document.id, EvidenceStatusInput(action=action, reason="curator_review")
    )
    assert receipt.search_content_removed
    assert receipt.original_private_object_retention == "review_required_no_complete_deletion_claim"
    assert (
        c.execute(
            text("SELECT count(*) FROM intelligence.evidence_passage_content WHERE project_id=:p"),
            {"p": p},
        ).scalar_one()
        == 0
    )
    assert c.execute(
        text("SELECT count(*) FROM intelligence.evidence_passages WHERE document_id=:d"),
        {"d": document.id},
    ).scalar_one() == len(document.passage_ids)
    operations = [
        lambda: read_document(c, i, p, document.id),
        lambda: read_corpus(c, i, p, built.id),
        lambda: build_corpus(c, i, p, CorpusBuildInput(document_ids=[document.id])),
        lambda: activate_corpus(
            c, i, p, CorpusActivationInput(corpus_id=built.id, expected_activation_id=active.id)
        ),
        lambda: import_document(c, i, p, metadata, content, storage),
    ]
    for operation in operations:
        with pytest.raises(HTTPException) as blocked:
            operation()
        assert blocked.value.status_code == 409


@pytest.mark.parametrize("action", ["internal_processing", "public_demo_redistribution"])
def test_current_source_rights_withdrawal_blocks_previously_built_corpus(evidence_db, action):
    c, i, p, component, _ = evidence_db
    document, built = corpus(evidence_db)
    add_review(c, i, p, component.id, review(action=action, decision="denied"))
    for operation in (
        lambda: read_document(c, i, p, document.id),
        lambda: read_corpus(c, i, p, built.id),
        lambda: activate_corpus(c, i, p, CorpusActivationInput(corpus_id=built.id)),
    ):
        with pytest.raises(HTTPException) as blocked:
            operation()
        assert blocked.value.status_code == 409


@pytest.mark.parametrize("role", ["viewer", "editor"])
def test_ordinary_roles_can_read_eligible_metadata_but_cannot_mutate_corpus(evidence_db, role):
    c, i, p = evidence_db[:3]
    document, built = corpus(evidence_db)
    reader = Identity(i.user_id, {p: role})
    assert read_document(c, reader, p, document.id) == document
    for operation in (
        lambda: build_corpus(c, reader, p, CorpusBuildInput(document_ids=[document.id])),
        lambda: activate_corpus(c, reader, p, CorpusActivationInput(corpus_id=built.id)),
        lambda: restrict_document(
            c,
            reader,
            p,
            document.id,
            EvidenceStatusInput(action="withdrawn", reason="source_rights"),
        ),
    ):
        with pytest.raises(HTTPException) as blocked:
            operation()
        assert blocked.value.status_code == 403


def test_cross_project_and_unknown_documents_cannot_be_read_or_linked(evidence_db):
    c, i, p = evidence_db[:3]
    document, built = corpus(evidence_db)
    for operation in (
        lambda: read_document(c, i, uuid4(), document.id),
        lambda: read_corpus(c, i, uuid4(), built.id),
        lambda: build_corpus(c, i, p, CorpusBuildInput(document_ids=[uuid4()])),
    ):
        with pytest.raises(HTTPException) as blocked:
            operation()
        assert blocked.value.status_code == 404
    with pytest.raises(DBAPIError), c.begin_nested():
        c.execute(
            text(
                "INSERT INTO intelligence.evidence_corpus_members(project_id,corpus_id,document_id) VALUES(:p,:c,:d)"
            ),
            {"p": p, "c": built.id, "d": uuid4()},
        )


@pytest.mark.parametrize(
    "table",
    [
        "evidence_documents",
        "evidence_passages",
        "evidence_corpora",
        "evidence_corpus_members",
        "evidence_activations",
        "evidence_document_events",
    ],
)
def test_scientific_evidence_metadata_is_append_only(evidence_db, table):
    c, i, p = evidence_db[:3]
    document, built = corpus(evidence_db)
    activate_corpus(c, i, p, CorpusActivationInput(corpus_id=built.id))
    if table == "evidence_document_events":
        restrict_document(
            c, i, p, document.id, EvidenceStatusInput(action="withdrawn", reason="source_rights")
        )
    for operation in ("UPDATE", "DELETE"):
        statement = (
            f"UPDATE intelligence.{table} SET project_id=project_id WHERE project_id=:p"
            if operation == "UPDATE"
            else f"DELETE FROM intelligence.{table} WHERE project_id=:p"
        )
        with pytest.raises(DBAPIError), c.begin_nested():
            c.execute(text(statement), {"p": p})


def test_corrupt_search_projection_cannot_be_activated(evidence_db):
    c, i, p = evidence_db[:3]
    document, built = corpus(evidence_db)
    c.execute(
        text(
            "UPDATE intelligence.evidence_passage_content SET text_content='changed untrusted text' WHERE project_id=:p"
        ),
        {"p": p},
    )
    with pytest.raises(HTTPException) as blocked:
        activate_corpus(c, i, p, CorpusActivationInput(corpus_id=built.id))
    assert blocked.value.status_code == 409
    assert document.id == built.document_ids[0]


def test_same_normalized_text_cannot_replay_different_original_source_bytes(evidence_db):
    c, i, p, _, storage = evidence_db
    metadata, content = staged(evidence_db, "Café artificial fixture.")
    import_document(c, i, p, metadata, content, storage)
    different_source = EvidenceTextInput(manifest=metadata, text="Cafe\u0301 artificial fixture.")
    with pytest.raises(HTTPException) as blocked:
        import_document(c, i, p, metadata, different_source, storage)
    assert blocked.value.status_code == 422


def test_unknown_retraction_status_cannot_enter_active_corpus(evidence_db):
    c, i, p = evidence_db[:3]
    document = imported(evidence_db, retraction_status="unknown")
    with pytest.raises(HTTPException) as blocked:
        build_corpus(c, i, p, CorpusBuildInput(document_ids=[document.id]))
    assert blocked.value.status_code == 409


def test_optional_corpus_build_precondition_rejects_wrong_activation(evidence_db):
    c, i, p = evidence_db[:3]
    document = imported(evidence_db)
    with pytest.raises(HTTPException) as blocked:
        build_corpus(
            c, i, p, CorpusBuildInput(document_ids=[document.id], expected_activation_id=uuid4())
        )
    assert blocked.value.status_code == 412


def test_evidence_http_import_activation_replay_and_withheld_passage(evidence_db):
    c, i, p = evidence_db[:3]
    metadata, content = staged(evidence_db)
    body = {**content.model_dump(mode="json"), "text": content.text.get_secret_value()}
    client, headers = http_session((c, i, p, None, None, None, keys()))
    root = f"/api/v1/projects/{p}"
    with client:
        assert client.get(root + "/evidence-corpus-current").status_code == 401
        command_headers = {**headers, "Idempotency-Key": "artificial-evidence-import"}
        response = client.post(
            root + "/evidence-document-excerpts", json=body, headers=command_headers
        )
        assert response.status_code == 201, response.text
        document = response.json()
        assert body["text"] not in response.text
        assert (
            client.post(
                root + "/evidence-document-excerpts", json=body, headers=command_headers
            ).json()
            == document
        )
        assert (
            client.post(
                root + "/evidence-document-excerpts",
                json={**body, "text": "Different fixture bytes"},
                headers=command_headers,
            ).status_code
            == 409
        )
        response = client.post(
            root + "/evidence-corpora",
            json={"document_ids": [document["id"]]},
            headers={**headers, "Idempotency-Key": "artificial-corpus-build"},
        )
        assert response.status_code == 201, response.text
        corpus = response.json()
        head = client.get(root + "/evidence-corpus-current", headers=headers)
        assert head.json()["status"] == "unconfigured" and head.headers["etag"] == '"empty"'
        activation_body = {"corpus_id": corpus["id"]}
        activation_headers = {**headers, "Idempotency-Key": "artificial-corpus-activate"}
        assert (
            client.post(
                root + "/evidence-corpus-activations",
                json=activation_body,
                headers=activation_headers,
            ).status_code
            == 428
        )
        activation_headers["If-Match"] = head.headers["etag"]
        response = client.post(
            root + "/evidence-corpus-activations", json=activation_body, headers=activation_headers
        )
        assert response.status_code == 201, response.text
        receipt = response.json()
        assert (
            client.post(
                root + "/evidence-corpus-activations",
                json=activation_body,
                headers=activation_headers,
            ).json()
            == receipt
        )
        current = client.get(root + "/evidence-corpus-current", headers=headers)
        assert (
            current.json()["status"] == "active" and current.headers["etag"] == f'"{receipt["id"]}"'
        )
        passage_url = (
            root + f"/evidence-corpora/{corpus['id']}/passages/{document['passage_ids'][0]}"
        )
        passage = client.get(passage_url, headers=headers)
        assert (
            passage.status_code == 200
            and passage.json()["support_status"]
            == "citation_resolves_meaningful_support_unreviewed"
        )
        assert passage.headers["cache-control"] == "private, no-store"
        assert (
            client.get(passage_url.replace(str(p), str(uuid4())), headers=headers).status_code
            == 404
        )
        preflight = client.options(
            root + "/evidence-corpus-activations",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "If-Match,Idempotency-Key,Authorization",
            },
        )
        assert preflight.status_code == 200
        response = client.post(
            root + f"/evidence-documents/{document['id']}/restrictions",
            json={"action": "withdrawn", "reason": "source_rights"},
            headers={**headers, "Idempotency-Key": "artificial-evidence-withdraw"},
        )
        assert response.status_code == 201, response.text
        assert response.json()["search_content_removed"] is True
        assert client.get(passage_url, headers=headers).status_code == 409
        assert (
            client.get(root + "/evidence-corpus-current", headers=headers).json()["status"]
            == "unavailable"
        )
        assert (
            client.post(
                root + "/evidence-corpus-activations",
                json=activation_body,
                headers=activation_headers,
            ).status_code
            == 409
        )
