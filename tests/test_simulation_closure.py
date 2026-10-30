"""COS-068 closure: scenario discovery, branch list, lifecycle and isolation."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_imaging_ingestion import http_session, imaging_db
from test_patient_linkage import keys
from test_source_registry import registry_db

from canceros.simulation_discovery import discovery_families, list_branches

__all__ = ["imaging_db", "registry_db"]


def test_five_families_discoverable_with_synthetic_only_versions(imaging_db):
    page = discovery_families()
    assert [item.family for item in page.items] == ["SC-01", "SC-02", "SC-03", "SC-04", "SC-05"]
    assert len({item.definition_version for item in page.items}) == 5
    assert all(item.synthetic_only for item in page.items)
    assert all(item.description and item.next_action for item in page.items)


def test_branch_list_is_owned_and_cross_branch_reads_are_isolated(imaging_db):
    c, i, p, patient, *_ = imaging_db
    u = patient.patient_id
    listed = list_branches(c, i, p, u)
    assert isinstance(listed.items, tuple)
    with pytest.raises(HTTPException) as stranger:
        list_branches(c, i, p, uuid4())
    assert stranger.value.status_code == 404


def test_closure_http_scenario_branch_lifecycle_and_auth(imaging_db):
    c, i, p, patient, *_ = imaging_db
    u = patient.patient_id
    client, headers = http_session((c, i, p, None, None, None, keys()))
    root = f"/api/v1/projects/{p}/patients/{u}"
    with client:
        assert client.get(root + "/scenario-definitions").status_code == 401
        discovered = client.get(root + "/scenario-definitions", headers=headers)
        assert discovered.status_code == 200, discovered.text
        assert [item["family"] for item in discovered.json()["items"]] == [
            "SC-01",
            "SC-02",
            "SC-03",
            "SC-04",
            "SC-05",
        ]
        branches = client.get(root + "/branches", headers=headers)
        assert branches.status_code == 200, branches.text
        assert isinstance(branches.json()["items"], list)
        assert branches.headers["cache-control"] == "private, no-store"
        unknown = client.get(root + "/branches", headers={"Authorization": "Bearer invalid"})
        assert unknown.status_code in (401, 403, 404, 422)
