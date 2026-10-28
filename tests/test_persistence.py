"""Real disposable PostgreSQL assertions, explicitly selected via environment."""

import os
from uuid import uuid4

import pytest
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from canceros.persistence import capture_revision, load_revision

pytestmark = pytest.mark.integration


@pytest.fixture
def connection():
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(".env").get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("Mandatory integration requires explicit disposable TEST_DATABASE_URL")
    engine = create_engine(url, hide_parameters=True)
    assert engine.url.database and "disposable" in engine.url.database, (
        "Refusing non-disposable test database"
    )
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()
    engine.dispose()


def identities(connection):
    project, other_project, patient, other_patient = [uuid4() for _ in range(4)]
    for p in (project, other_project):
        connection.execute(
            text("INSERT INTO access.projects(id,name) VALUES(:id,:name)"),
            {"id": p, "name": "Engineering-only project"},
        )
    for p, u in ((project, patient), (other_project, other_patient)):
        connection.execute(
            text(
                "INSERT INTO source.research_patients(id,project_id,display_code) VALUES(:u,:p,:code)"
            ),
            {"u": u, "p": p, "code": str(u)},
        )
    return project, other_project, patient, other_patient


def test_revision_n_survives_n_plus_one_and_is_append_only(connection):
    project, _, patient, _ = identities(connection)
    capture_revision(
        connection,
        project,
        patient,
        1,
        {"fixture_origin": "ENGINEERING_ONLY_NONCLINICAL", "members": ["original"]},
    )
    capture_revision(
        connection,
        project,
        patient,
        2,
        {"fixture_origin": "ENGINEERING_ONLY_NONCLINICAL", "members": ["correction"]},
    )
    assert load_revision(connection, project, patient, 1)["members"] == ["original"]
    assert load_revision(connection, project, patient, 2)["members"] == ["correction"]
    with pytest.raises(DBAPIError), connection.begin_nested():
        connection.execute(
            text(
                "UPDATE source.patient_revisions SET input_manifest='{}'::jsonb WHERE patient_id=:u"
            ),
            {"u": patient},
        )
    assert load_revision(connection, project, patient, 1)["members"] == ["original"]


def test_cross_patient_origin_denied_and_relative_root_has_no_date(connection):
    project, _, patient, foreign_patient = identities(connection)
    origin = uuid4()
    connection.execute(
        text(
            "INSERT INTO source.timeline_origins(id,project_id,patient_id,reference_meaning,time_domain) VALUES(:id,:p,:u,'Artificial source reference','source_relative')"
        ),
        {"id": origin, "p": project, "u": patient},
    )
    statement = text(
        "INSERT INTO clinical.time_references(id,project_id,patient_id,basis,time_domain,relative_day,timeline_origin_id) VALUES(:id,:p,:u,'relative_day','source_relative',0,:origin)"
    )
    connection.execute(statement, {"id": uuid4(), "p": project, "u": patient, "origin": origin})
    with pytest.raises(DBAPIError), connection.begin_nested():
        connection.execute(
            statement, {"id": uuid4(), "p": project, "u": foreign_patient, "origin": origin}
        )
    row = connection.execute(
        text(
            "SELECT date_value,timestamp_value FROM clinical.time_references WHERE timeline_origin_id=:id"
        ),
        {"id": origin},
    ).one()
    assert row.date_value is None and row.timestamp_value is None
    with pytest.raises(DBAPIError), connection.begin_nested():
        connection.execute(
            text(
                "INSERT INTO clinical.time_references(id,project_id,patient_id,basis,time_domain) VALUES(:id,:p,:u,'unknown','source_relative')"
            ),
            {"id": uuid4(), "p": project, "u": patient},
        )


def test_transaction_rollback_and_cross_project_revision(connection):
    project, other, patient, _ = identities(connection)
    with pytest.raises(DBAPIError), connection.begin_nested():
        capture_revision(connection, project, patient, 1, {"members": ["temporary"]})
        capture_revision(connection, other, patient, 2, {"members": ["wrong-project"]})
    assert (
        connection.execute(
            text("SELECT count(*) FROM source.patient_revisions WHERE patient_id=:u"),
            {"u": patient},
        ).scalar_one()
        == 0
    )


def test_artifact_provenance_and_byte_identity_cannot_be_rewritten(connection):
    project, other, patient, _ = identities(connection)
    identity = uuid4()
    insert = text(
        "INSERT INTO ops.artifacts(id,project_id,patient_id,object_key,object_version,byte_size,sha256,provenance,availability) VALUES(:id,:p,:u,:key,'artificial-version',1,:hash,'SYNTHETIC_GENERATED','quarantined')"
    )
    values = {
        "id": identity,
        "p": project,
        "u": patient,
        "key": "engineering-only-" + str(identity),
        "hash": "a" * 64,
    }
    connection.execute(insert, values)
    with pytest.raises(DBAPIError), connection.begin_nested():
        connection.execute(
            text("UPDATE ops.artifacts SET provenance='REAL_DERIVED' WHERE id=:id"),
            {"id": identity},
        )
    with pytest.raises(DBAPIError), connection.begin_nested():
        connection.execute(
            insert,
            {**values, "id": uuid4(), "p": other, "key": "engineering-other-" + str(uuid4())},
        )
    assert (
        connection.execute(
            text("SELECT provenance FROM ops.artifacts WHERE id=:id"), {"id": identity}
        ).scalar_one()
        == "SYNTHETIC_GENERATED"
    )
