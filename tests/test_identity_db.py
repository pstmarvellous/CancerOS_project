import os
from uuid import uuid4

import pytest
from dotenv import dotenv_values
from fastapi import HTTPException
from sqlalchemy import create_engine, text

from canceros.identity import SQLMemberships, authorize_project
from canceros.settings import Settings

pytestmark = pytest.mark.integration


def test_actual_sql_membership_and_role_denial():
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(".env").get("TEST_DATABASE_URL")
    assert url and "disposable" in url
    engine = create_engine(url, hide_parameters=True)
    project, user = uuid4(), uuid4()
    subject = "engineering-" + str(user)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO access.projects(id,name) VALUES(:id,'Engineering identity fixture')"),
            {"id": project},
        )
        connection.execute(
            text("INSERT INTO access.users(id,issuer,subject) VALUES(:id,'canceros-local',:sub)"),
            {"id": user, "sub": subject},
        )
        connection.execute(
            text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:u,'viewer')"),
            {"p": project, "u": user},
        )
    repository = SQLMemberships(Settings(mode="test", database_url=url, _env_file=None))
    identity = repository.resolve("canceros-local", subject)
    authorize_project(identity, project)
    with pytest.raises(HTTPException) as denied:
        authorize_project(identity, project, "admin")
    assert denied.value.status_code == 403
    with pytest.raises(HTTPException) as hidden:
        authorize_project(identity, uuid4())
    assert hidden.value.status_code == 404
    engine.dispose()
