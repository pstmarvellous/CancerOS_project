"""Real disposable SQL and private storage with artificial research records only."""

from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_clinical_ingestion import clinical_db
from test_imaging_ingestion import http_session
from test_patient_linkage import keys
from test_source_registry import example, registry_db, review

from canceros.clinical_ingestion import read_record
from canceros.identity import Identity
from canceros.patient_runs import ObservationFilter, query_observations
from canceros.research_workspace import (
    ManualObservationInput,
    ResearchCaseInput,
    ResearchProfileUpdate,
    case_sources,
    create_case,
    manual_observation,
    research_cases,
    research_profile,
    update_profile,
    workspace,
)
from canceros.source_registry import add_review, add_source

__all__ = ["registry_db", "clinical_db"]


@pytest.fixture(autouse=True)
def stable_linkage_ring(monkeypatch):
    config = keys()
    monkeypatch.setitem(globals(), "keys", lambda: config)


def case_input(source, **changes):
    return ResearchCaseInput.model_validate(
        {
            "source_version_id": source,
            "case_identifier": "case-" + uuid4().hex[:10],
            "title": "Artificial engineering workspace",
            "pseudonym": "Participant-fixture-" + uuid4().hex[:10],
            "profile_source_reference": "Artificial local engineering source, no patient data",
            **changes,
        }
    )


def setup_case(data):
    c, i, p, patient, origin, component, storage = data
    result = create_case(c, i, p, case_input(patient.source_version_id), keys())
    return result


def manual_input(**changes):
    observation = {
        "kind": "laboratory",
        "concept": "hemoglobin",
        "original_term": "Fixture hemoglobin",
        "certainty": "documented",
        "negation": "affirmed",
        "time": {
            "reference": {
                "basis": "unknown",
                "time_domain": "simulation",
                "missing_reason": "not_recorded",
            },
            "precision": "unknown",
        },
        "result": {"form": "exact", "quantity": {"value": "12.5", "unit": "g/dL"}},
        "original_value": "12.5",
        "original_unit": "g/dL",
    }
    observation.update(changes)
    return ManualObservationInput(
        expected_revision=1,
        source_reference="Artificial worksheet observation",
        observation=observation,
    )


def test_profile_creation_revision_duplicate_search_and_ownership(clinical_db):
    c, i, p, patient, *_ = clinical_db
    profile = setup_case(clinical_db)
    assert profile.profile_revision == 1 and profile.sex == "not_recorded"
    assert profile.origin == "synthetic_engineering_fixture" and profile.observation_count == 0
    assert research_profile(c, i, p, profile.patient_id) == profile
    assert workspace(c, i).user_id == i.user_id
    assert p in {r.project_id for r in workspace(c, i).projects}
    assert any(
        r.source_version_id == patient.source_version_id and r.creation_permitted
        for r in case_sources(c, i, p, keys()).items
    )
    update = ResearchProfileUpdate(
        **profile.model_dump(
            include=set(ResearchProfileUpdate.model_fields) - {"expected_profile_revision"}
        ),
        expected_profile_revision=1,
    ).model_copy(update={"title": "Saved revised title"})
    saved = update_profile(c, i, p, profile.patient_id, update)
    assert saved.profile_revision == 2 and saved.title == "Saved revised title"
    assert saved.data_revision == profile.data_revision
    assert research_cases(c, i, p, "revised").items[0].patient_id == profile.patient_id
    assert research_cases(c, i, p, "absent-title").items == []
    with pytest.raises(HTTPException) as conflict:
        update_profile(c, i, p, profile.patient_id, update)
    assert conflict.value.status_code == 409
    with pytest.raises(HTTPException) as changed_source_alias:
        update_profile(
            c,
            i,
            p,
            profile.patient_id,
            update.model_copy(
                update={"expected_profile_revision": 2, "pseudonym": "Different-source-identity"}
            ),
        )
    assert changed_source_alias.value.status_code == 409
    with pytest.raises(HTTPException) as duplicate:
        create_case(
            c,
            i,
            p,
            ResearchCaseInput(**profile.model_dump(include=set(ResearchCaseInput.model_fields))),
            keys(),
        )
    assert duplicate.value.status_code == 409
    with pytest.raises(HTTPException) as alias_duplicate:
        create_case(
            c, i, p, case_input(patient.source_version_id, pseudonym=profile.pseudonym), keys()
        )
    assert alias_duplicate.value.status_code == 409
    viewer = Identity(i.user_id, {p: "viewer"})
    with pytest.raises(HTTPException) as private_profile:
        research_cases(c, viewer, p)
    assert private_profile.value.status_code == 403
    with pytest.raises(HTTPException) as denied:
        update_profile(c, viewer, p, profile.patient_id, update)
    assert denied.value.status_code == 403
    with pytest.raises(HTTPException):
        research_profile(c, i, uuid4(), profile.patient_id)
    with pytest.raises(DBAPIError), c.begin_nested():
        c.execute(
            text("UPDATE source.research_profile_revisions SET payload='{}' WHERE patient_id=:u"),
            {"u": profile.patient_id},
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"title": " "},
        {"age_at_observation": 30},
        {"age_at_observation": -1, "age_observed_on": date(2020, 1, 1)},
        {"sex": "assumed"},
        {"full_legal_name": "unused"},
    ],
)
def test_profile_rejects_unsupported_or_unsourced_fields(changes):
    with pytest.raises(ValidationError):
        case_input(uuid4(), **changes)


def test_manual_canonical_records_corrections_and_no_synthetic_promotion(clinical_db):
    c, i, p, _, _, _, storage = clinical_db
    profile = setup_case(clinical_db)
    entered = manual_observation(c, i, p, profile.patient_id, manual_input(), "manual-one", storage)
    assert entered.status == "accepted", entered
    assert entered.result_revision == 2
    record = read_record(c, i, p, profile.patient_id, entered.record_ids[0])
    assert record.origin == "SYNTHETIC_GENERATED" and record.context == "SYNTHETIC"
    assert record.source_reference == "Artificial worksheet observation"
    assert (
        c.execute(
            text("SELECT source_reference FROM source.source_locators WHERE id=:id"),
            {"id": record.item.source_locator_id},
        ).scalar_one()
        == record.source_reference
    )
    assert record.numeric_normalization.canonical_result.quantity.value == "12.5"
    corrected = manual_input(
        original_value="13", result={"form": "exact", "quantity": {"value": "13", "unit": "g/dL"}}
    ).model_copy(update={"expected_revision": 2, "corrects_record_id": record.id})
    revised = manual_observation(c, i, p, profile.patient_id, corrected, "manual-two", storage)
    assert revised.status == "accepted" and revised.result_revision == 3
    assert read_record(c, i, p, profile.patient_id, record.id).item.original_value == "12.5"
    replacement_id = revised.record_ids[0]
    assert read_record(c, i, p, profile.patient_id, replacement_id).item.original_value == "13"
    history = {
        item.record_id: item
        for item in query_observations(c, i, p, profile.patient_id, ObservationFilter()).items
    }
    assert history[record.id].superseded is True
    assert history[replacement_id].superseded is False
    assert research_profile(c, i, p, profile.patient_id).data_revision == 3
    assert (
        c.execute(
            text("SELECT count(*) FROM clinical.observations WHERE patient_id=:u"),
            {"u": profile.patient_id},
        ).scalar_one()
        == 2
    )
    with pytest.raises(HTTPException):
        manual_observation(c, i, p, profile.patient_id, manual_input(), "stale-revision", storage)


@pytest.mark.parametrize(
    "kind,fields",
    [
        (
            "vital",
            {
                "concept": "heart_rate",
                "result": {"form": "missing", "missing_reason": "not_recorded"},
            },
        ),
        ("symptom", {"concept": "pain", "presence": "unknown", "reporter": "unknown"}),
        (
            "treatment",
            {
                "concept": "other",
                "event_type": "reported_exposure",
                "exposure_status": "reported",
                "regimen_text": "Artificial documented exposure",
            },
        ),
        (
            "diagnosis",
            {
                "concept": "source_pathology",
                "side": "unknown",
                "er_status": "not_recorded",
                "pr_status": "not_recorded",
                "her2_status": "not_recorded",
            },
        ),
        ("visit", {"concept": "imaging_exam", "label": "Artificial examination metadata"}),
        ("note", {"text": "Artificial medical history source note. No patient data."}),
    ],
)
def test_supported_manual_kinds_use_existing_clinical_tables(clinical_db, kind, fields):
    c, i, p, _, _, _, storage = clinical_db
    profile = setup_case(clinical_db)
    base = {
        "kind": kind,
        "original_term": "Artificial source entry",
        "certainty": "documented",
        "negation": "affirmed",
        "time": {
            "reference": {
                "basis": "unknown",
                "time_domain": "simulation",
                "missing_reason": "not_recorded",
            },
            "precision": "unknown",
        },
        **fields,
    }
    entered = manual_observation(
        c,
        i,
        p,
        profile.patient_id,
        ManualObservationInput(
            expected_revision=1, source_reference="Artificial input", observation=base
        ),
        "manual-" + kind,
        storage,
    )
    assert entered.status == "accepted", entered
    record = read_record(c, i, p, profile.patient_id, entered.record_ids[0])
    assert record.item.kind == kind and record.context == "SYNTHETIC"
    if kind == "note":
        assert record.item.note_document_id is not None


def test_real_source_privacy_review_default_deny_and_canonical_provenance(clinical_db):
    c, i, p, _, _, _, storage = clinical_db
    parent = None
    for kind in ("collection", "release", "component", "artifact_source"):
        source = add_source(
            c, i, p, example(kind=kind, parent_version_id=parent, origin="real_source")
        )
        parent = source.id
        if kind == "component":
            component = source.id
    add_review(c, i, p, component, review(basis="documented_rights_review"))
    add_review(
        c, i, p, component, review(action="derivative_creation", basis="documented_rights_review")
    )
    with pytest.raises(HTTPException) as blocked:
        create_case(c, i, p, case_input(source.id), keys())
    assert blocked.value.status_code == 409
    assert not next(
        r for r in case_sources(c, i, p, keys()).items if r.source_version_id == source.id
    ).creation_permitted
    add_review(
        c,
        i,
        p,
        component,
        review(action="patient_linkage_privacy", basis="documented_rights_review"),
    )
    profile = create_case(c, i, p, case_input(source.id), keys())
    raw = manual_input().model_dump(mode="json")
    raw["observation"]["time"] = {
        "reference": {"basis": "date", "value": "2020-01-01", "time_domain": "source_calendar"},
        "precision": "day",
    }
    entered = manual_observation(
        c,
        i,
        p,
        profile.patient_id,
        ManualObservationInput.model_validate(raw),
        "real-labelled-fixture",
        storage,
    )
    assert entered.status == "accepted", entered
    record = read_record(c, i, p, profile.patient_id, entered.record_ids[0])
    assert record.context == "OBSERVED" and record.origin == "REAL_DERIVED"
    assert entered.verification_scope == "documented_source_structural_only"
    note = ManualObservationInput(
        expected_revision=2,
        source_reference="Artificial history note, real-labelled gate test only",
        observation={
            "kind": "note",
            "time": raw["observation"]["time"],
            "original_term": "Source medical history",
            "certainty": "documented",
            "negation": "affirmed",
            "text": "Artificial gate test. No genuine clinical content.",
        },
    )
    note_report = manual_observation(
        c, i, p, profile.patient_id, note, "real-labelled-note-fixture", storage
    )
    assert note_report.status == "accepted", note_report
    note_record = read_record(c, i, p, profile.patient_id, note_report.record_ids[0])
    assert note_record.origin == "REAL_DERIVED" and note_record.context == "OBSERVED"
    # These are deliberately artificial bytes; no clinical or privacy review is claimed.
    add_review(
        c,
        i,
        p,
        component,
        review(
            action="patient_linkage_privacy", decision="denied", basis="documented_rights_review"
        ),
    )
    with pytest.raises(HTTPException):
        create_case(c, i, p, case_input(source.id), keys())


def test_http_session_case_create_retry_manual_idempotency_and_access(clinical_db, caplog):
    caplog.set_level("INFO", logger="canceros.requests")
    c, i, p, patient, *_ = clinical_db
    client, headers = http_session((c, i, p, None, None, None, keys()))
    root = f"/api/v1/projects/{p}"
    value = case_input(patient.source_version_id).model_dump(mode="json")
    headers = {**headers, "Idempotency-Key": "case-create-1"}
    with client:
        assert client.get("/api/v1/workspace").status_code == 401
        assert client.get("/api/v1/workspace", headers=headers).status_code == 200
        assert (
            client.post(
                root + "/research-cases", json=value, headers={"Idempotency-Key": "unauthorized"}
            ).status_code
            == 401
        )
        created = client.post(root + "/research-cases", json=value, headers=headers)
        assert created.status_code == 201, created.text
        u = created.json()["patient_id"]
        assert (
            client.post(root + "/research-cases", json=value, headers=headers).json()["patient_id"]
            == u
        )
        assert (
            client.post(
                root + "/research-cases",
                json=value,
                headers={**headers, "Idempotency-Key": "duplicate-new-key"},
            ).status_code
            == 409
        )
        manual_path = root + f"/patients/{u}/manual-observations"
        mixed_time = manual_input().model_dump(mode="json")
        mixed_time["observation"]["time"]["reference"]["time_domain"] = "source_calendar"
        assert (
            client.post(
                manual_path,
                json=mixed_time,
                headers={**headers, "Idempotency-Key": "mixed-source-time"},
            ).status_code
            == 422
        )
        entered = client.post(
            manual_path,
            json=manual_input().model_dump(mode="json"),
            headers={**headers, "Idempotency-Key": "clinical-one"},
        )
        assert entered.status_code == 201, entered.text
        assert entered.json()["status"] == "accepted", entered.text
        again = client.post(
            manual_path,
            json=manual_input().model_dump(mode="json"),
            headers={**headers, "Idempotency-Key": "clinical-one"},
        )
        assert again.json()["record_ids"] == entered.json()["record_ids"]
        assert (
            client.get(root + f"/patients/{u}/research-profile", headers=headers).json()[
                "data_revision"
            ]
            == 2
        )
        queried = client.post(root + f"/patients/{u}/observation-queries", json={}, headers=headers)
        assert queried.status_code == 200 and queried.json()["items"]
        assert client.get(root + "/research-cases?search=engineering", headers=headers).json()[
            "items"
        ]

        invalid = manual_input().model_dump(mode="json")
        invalid["expected_revision"] = 2
        invalid["observation"]["source_locator_id"] = str(uuid4())
        assert (
            client.post(
                manual_path, json=invalid, headers={**headers, "Idempotency-Key": "forged-locator"}
            ).status_code
            == 422
        )
        invalid["observation"].pop("source_locator_id")
        invalid["observation"]["original_unit"] = "unsupported_unit"
        invalid["observation"]["result"]["quantity"]["unit"] = "unsupported_unit"
        quarantined = client.post(
            manual_path, json=invalid, headers={**headers, "Idempotency-Key": "invalid-unit"}
        )
        assert quarantined.status_code == 201 and quarantined.json()["status"] == "quarantined"
        assert quarantined.json()["record_ids"] == []
        assert (
            client.get(root + f"/patients/{u}/research-profile", headers=headers).json()[
                "data_revision"
            ]
            == 2
        )

        note = manual_input().model_dump(mode="json")
        note["expected_revision"] = 2
        note["observation"] = {
            k: v
            for k, v in note["observation"].items()
            if k in {"time", "original_term", "certainty", "negation"}
        }
        note["observation"].update(kind="note", text="Artificial restricted source note one.")
        note_headers = {**headers, "Idempotency-Key": "note-content-key"}
        first_note = client.post(manual_path, json=note, headers=note_headers)
        assert first_note.status_code == 201 and first_note.json()["status"] == "accepted", (
            first_note.text
        )
        note["observation"]["text"] = "Artificial restricted source note two."
        assert client.post(manual_path, json=note, headers=note_headers).status_code == 409
        commands = c.execute(
            text("SELECT response::text FROM source.registry_commands WHERE project_id=:p"),
            {"p": p},
        ).all()
        assert all("Artificial restricted source note" not in str(row) for row in commands)
        assert "Artificial restricted source note" not in caplog.text
        generated = c.execute(
            text(
                "SELECT id,payload FROM source.registry_versions WHERE project_id=:p AND record_key LIKE 'manual-%'"
            ),
            {"p": p},
        ).all()
        assert generated
        assert all("Artificial worksheet observation" not in str(r.payload) for r in generated)

        c.execute(
            text("UPDATE access.memberships SET role='viewer' WHERE project_id=:p AND user_id=:u"),
            {"p": p, "u": i.user_id},
        )
        c.commit()
        assert client.get(root + "/research-cases", headers=headers).status_code == 403
        assert client.get(root + f"/sources/{generated[0].id}", headers=headers).status_code == 403
        assert (
            client.get(root + f"/patients/{u}/research-profile", headers=headers).status_code == 403
        )
        assert (
            client.post(
                manual_path,
                json=manual_input().model_dump(mode="json"),
                headers={**headers, "Idempotency-Key": "viewer-denied"},
            ).status_code
            == 403
        )


def test_case_pagination_is_explicit_and_grants_stay_patient_scoped(clinical_db):
    c, i, p, patient, *_ = clinical_db
    ids = {
        create_case(c, i, p, case_input(patient.source_version_id), keys()).patient_id
        for _ in range(3)
    }
    first = research_cases(c, i, p, limit=2)
    assert len(first.items) == 2 and first.next_cursor is not None
    last = research_cases(c, i, p, limit=2, cursor=first.next_cursor)
    assert len(last.items) == 1 and last.next_cursor is None
    assert {r.patient_id for r in first.items + last.items} == ids
    viewer_id = uuid4()
    c.execute(
        text("INSERT INTO access.users(id,issuer,subject) VALUES(:id,'engineering',:s)"),
        {"id": viewer_id, "s": str(viewer_id)},
    )
    c.execute(
        text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:id,'editor')"),
        {"p": p, "id": viewer_id},
    )
    allowed = next(iter(ids))
    c.execute(
        text(
            "INSERT INTO access.patient_grants(project_id,patient_id,user_id,permission) VALUES(:p,:u,:actor,'view')"
        ),
        {"p": p, "u": allowed, "actor": viewer_id},
    )
    viewer = Identity(viewer_id, {p: "editor"})
    assert [r.patient_id for r in research_cases(c, viewer, p).items] == [allowed]
    assert research_profile(c, viewer, p, allowed).patient_id == allowed
    with pytest.raises(HTTPException):
        research_profile(c, viewer, p, next(u for u in ids if u != allowed))


@pytest.mark.parametrize("reference", [" ", "source\nreference"])
def test_manual_requires_a_meaningful_source_reference(reference):
    data = manual_input().model_dump(mode="json")
    data["source_reference"] = reference
    with pytest.raises(ValidationError):
        ManualObservationInput.model_validate(data)
