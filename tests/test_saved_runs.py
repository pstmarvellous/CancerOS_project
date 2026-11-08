"""Exact-context reuse, idempotent persist, isolation and labeled fallback."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_context_runs import FIXTURE_PATIENT, SNAPSHOT_ID
from test_context_runs import build as build_context_fixture
from test_evidence_runs import evidence_db
from test_imaging_ingestion import http_session, imaging_db
from test_patient_linkage import keys
from test_source_registry import registry_db

from canceros.api import create_app
from canceros.context_contracts import ContextBuildInput
from canceros.identity import Identity
from canceros.interpretation_contracts import InterpretationInput
from canceros.interpretation_runs import build_interpretation
from canceros.saved_runs import fallback_label, persist_validated, read_saved, reuse_exact
from canceros.saved_runs_contracts import SavedResultQuery

__all__ = ["evidence_db", "imaging_db", "registry_db"]


def context(monkeypatch):
    return build_context_fixture(
        monkeypatch, ContextBuildInput(patient_id=FIXTURE_PATIENT, snapshot_id=SNAPSHOT_ID)
    )


def template(monkeypatch):
    built = context(monkeypatch)
    report = build_interpretation(
        built, InterpretationInput(context_snapshot_id=built.snapshot_id, mode="template")
    )
    return built, report


def ensure_patient(c, p, u):
    from sqlalchemy import text

    c.execute(
        text(
            "INSERT INTO source.research_patients(id,project_id,display_code) VALUES(:u,:p,:label)"
            " ON CONFLICT DO NOTHING"
        ),
        {"u": u, "p": p, "label": "Research-" + u.hex},
    )


def test_persist_is_idempotent_and_supersedes_prior_for_snapshot(evidence_db, monkeypatch):
    c, i, p = evidence_db[:3]
    built, report = template(monkeypatch)
    ensure_patient(c, p, built.patient_id)
    first = persist_validated(c, i, p, built, report, "k1")
    again = persist_validated(c, i, p, built, report, "k1")
    assert again.id == first.id and again.status == "validated_ready"
    assert again.model_identifier and again.prompt_version and again.validator_version
    assert again.model_revision == "unresolved"
    second = persist_validated(c, i, p, built, report, "k2")
    assert second.id != first.id
    assert read_saved(c, i, p, built.patient_id, first.id).status in ("validated_ready", "superseded")


def test_exact_context_reuse_revalidates_and_isolates_patients(evidence_db, monkeypatch):
    c, i, p = evidence_db[:3]
    built, report = template(monkeypatch)
    ensure_patient(c, p, built.patient_id)
    saved = persist_validated(c, i, p, built, report, "reuse-1")
    hit = reuse_exact(
        c, i, p, built, SavedResultQuery(context_snapshot_id=built.snapshot_id)
    )
    assert hit.id == saved.id and hit.context_hash == built.context_hash
    with pytest.raises(HTTPException) as wrong_hash:
        reuse_exact(
            c,
            i,
            p,
            built,
            SavedResultQuery(context_snapshot_id=built.snapshot_id, expected_context_hash="0" * 64),
        )
    assert wrong_hash.value.status_code == 409
    with pytest.raises(HTTPException) as unknown:
        reuse_exact(
            c, i, p, built, SavedResultQuery(context_snapshot_id=uuid4())
        )
    assert unknown.value.status_code == 409


def insert_saved(c, p, u, digest, key):
    identifier = uuid4()
    c.execute(
        text("""INSERT INTO intelligence.saved_interpretations(
          id,project_id,patient_id,context_snapshot_id,context_hash,execution_mode,visibility,
          model_identifier,model_revision,prompt_version,validator_version,corpus_manifest,
          finding_count,idempotency_key,status)
          VALUES(:id,:p,:u,:s,:h,'rule_based_summary','visible_template','local-template/1','unresolved',
          'interpretation-template/1','grounding-gate/1','postgres-curated-corpus/active-head',1,:k,'validated_ready')"""),
        {"id": identifier, "p": p, "u": u, "s": uuid4(), "h": digest, "k": key},
    )
    return identifier


def test_saved_retrieval_requires_patient_grant_and_binds_patient(registry_db):
    """REC-00: a valid project member with a grant for Patient A only must not
    read Patient B's saved interpretation; authorized retrieval still works."""
    c, i, p = registry_db
    viewer_id = uuid4()
    c.execute(
        text("INSERT INTO access.users(id,issuer,subject) VALUES(:id,'engineering',:s)"),
        {"id": viewer_id, "s": str(viewer_id)},
    )
    c.execute(
        text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:id,'viewer')"),
        {"p": p, "id": viewer_id},
    )
    patient_a, patient_b = uuid4(), uuid4()
    ensure_patient(c, p, patient_a)
    ensure_patient(c, p, patient_b)
    c.execute(
        text("INSERT INTO access.patient_grants(project_id,patient_id,user_id,permission) VALUES(:p,:u,:actor,'view')"),
        {"p": p, "u": patient_a, "actor": viewer_id},
    )
    saved_b = insert_saved(c, p, patient_b, "c" * 64, "rec00-b")
    saved_a = insert_saved(c, p, patient_a, "d" * 64, "rec00-a")
    viewer = Identity(viewer_id, {p: "viewer"})
    with pytest.raises(HTTPException) as denied:
        read_saved(c, viewer, p, patient_a, saved_b)
    assert denied.value.status_code in (403, 404)
    assert ("c" * 64) not in str(denied.value.detail)
    assert read_saved(c, viewer, p, patient_a, saved_a).id == saved_a
    assert read_saved(c, i, p, patient_b, saved_b).id == saved_b


def test_fallback_labels_distinguish_saved_rule_based_and_refusal(monkeypatch):
    built = context(monkeypatch)
    assert fallback_label(built, "exact_reuse")["label"] == "Saved result for this snapshot"
    assert fallback_label(built, "outage")["label"] == "Rule-based fallback"
    refused = fallback_label(built, "policy_refusal")
    assert refused["status"] == 403
    assert "measurements" in " ".join(
        [fallback_label(built, "outage")["next_action"]]
    )


def test_saved_http_persist_reuse_and_auth_boundary(imaging_db, monkeypatch):
    c, i, p, patient, _, _, _ = imaging_db
    monkeypatch.setattr("canceros.saved_api.build_context", lambda *a, **k: object())
    monkeypatch.setattr(
        "canceros.saved_api.build_interpretation", lambda *a, **k: object()
    )
    from canceros.saved_runs_contracts import PersistedInterpretation as P

    fake = P.model_validate(
        {
            "id": uuid4(),
            "project_id": p,
            "patient_id": patient.patient_id,
            "context_snapshot_id": uuid4(),
            "context_hash": "b" * 64,
            "execution_mode": "rule_based_summary",
            "visibility": "visible_template",
            "model_identifier": "local-template/1",
            "prompt_version": "interpretation-template/1",
            "validator_version": "grounding-gate/1",
            "corpus_manifest": "postgres-curated-corpus/active-head",
            "finding_count": 2,
            "status": "validated_ready",
            "next_action": "fixture",
        }
    )
    monkeypatch.setattr("canceros.saved_api.persist_validated", lambda *a, **k: fake)
    monkeypatch.setattr("canceros.saved_api.read_saved", lambda *a, **k: fake)
    monkeypatch.setattr("canceros.saved_api.reuse_exact", lambda *a, **k: fake)
    client, headers = http_session((c, i, p, patient, None, None, keys()))
    state_id, interpretation_id = uuid4(), uuid4()
    create = f"/api/v1/projects/{p}/patients/{patient.patient_id}/states/{state_id}/interpretations/{interpretation_id}/saved-results"
    body = {"interpretation_snapshot_id": str(interpretation_id), "idempotency_key": "k-http"}
    with client:
        assert client.post(create, json=body, headers={"Idempotency-Key": "k-http"}).status_code == 401
        response = client.post(
            create, json=body, headers={**headers, "Idempotency-Key": "k-http"}
        )
        assert response.status_code == 201, response.text
        got = client.get(response.headers["location"], headers=headers)
        assert got.status_code == 200 and got.json()["status"] == "validated_ready"
        assert got.headers["cache-control"] == "private, no-store"
        reuse = client.post(
            f"/api/v1/projects/{p}/patients/{patient.patient_id}/states/{state_id}/saved-result-queries",
            json={"context_snapshot_id": str(state_id)},
            headers=headers,
        )
        assert reuse.status_code == 200, reuse.text
        denied = client.post(create, json=body, headers={"Authorization": "Bearer invalid"})
        assert denied.status_code in (401, 403, 404, 422)

def test_saved_http_detail_denies_cross_patient_without_content(imaging_db):
    """REC-00 HTTP proof: URL patient A + Patient-B saved id denies; Patient-A
    saved id still returns 200. Uses the real read_saved (no mock)."""
    from datetime import datetime, timedelta, timezone

    import jwt
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    c, i, p, patient, _, _, _ = imaging_db
    other_id = uuid4()
    c.execute(
        text("INSERT INTO source.research_patients(id,project_id,display_code) VALUES(:u,:p,:label)"),
        {"u": other_id, "p": p, "label": "Research-" + other_id.hex},
    )
    saved_other = insert_saved(c, p, other_id, "e" * 64, "rec00-http-other")
    saved_own = insert_saved(c, p, patient.patient_id, "f" * 64, "rec00-http-own")
    viewer_id = uuid4()
    c.execute(
        text("INSERT INTO access.users(id,issuer,subject) VALUES(:id,'engineering',:s)"),
        {"id": viewer_id, "s": str(viewer_id)},
    )
    c.execute(
        text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:id,'viewer')"),
        {"p": p, "id": viewer_id},
    )
    c.execute(
        text("INSERT INTO access.patient_grants(project_id,patient_id,user_id,permission) VALUES(:p,:u,:actor,'view')"),
        {"p": p, "u": patient.patient_id, "actor": viewer_id},
    )
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        private.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    from canceros.settings import Settings

    # The HTTP app opens independent connections, so commit this artificial
    # setup first (same precedent as imaging_db/http_session); the disposable
    # fixture transaction still rolls back the remainder at teardown.
    c.commit()
    service = Settings(
        mode="test",
        identity_issuer="engineering",
        identity_public_key=public,
        database_url=c.engine.url.render_as_string(hide_password=False),
        linkage_active_key="k1",
        linkage_keys=keys().linkage_keys,
        _env_file=None,
    )
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(viewer_id),
            "iss": service.identity_issuer,
            "aud": service.identity_audience,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=5),
        },
        private,
        algorithm="RS256",
    )
    headers = {"Authorization": "Bearer " + token}
    own_path = f"/api/v1/projects/{p}/patients/{patient.patient_id}/saved-interpretations/{saved_own}"
    cross_path = f"/api/v1/projects/{p}/patients/{patient.patient_id}/saved-interpretations/{saved_other}"
    with TestClient(create_app(service)) as client:
        ok = client.get(own_path, headers=headers)
        assert ok.status_code == 200, ok.text
        assert ok.json()["patient_id"] == str(patient.patient_id)
        denied = client.get(cross_path, headers=headers)
        assert denied.status_code in (403, 404), denied.text
        assert ("e" * 64) not in denied.text
        assert str(saved_other) not in denied.text
