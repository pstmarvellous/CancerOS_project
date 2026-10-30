"""Capability discovery is authenticated and cannot enable external processing."""

# ruff: noqa: F811

from uuid import uuid4

import jwt
from fastapi.testclient import TestClient
from test_identity_export import identity_runtime  # noqa: F401

from canceros.api import create_app
from canceros.provider_gateway import ProviderFailure


def test_capabilities_require_membership_and_disclose_no_configuration(identity_runtime):
    private, project, config, memberships, claims = identity_runtime
    token = jwt.encode(claims, private, algorithm="RS256")
    headers = {"Authorization": "Bearer " + token}
    with TestClient(create_app(config, memberships)) as client:
        path = f"/api/v1/projects/{project}/ai/capabilities"
        assert client.get(path).status_code == 401
        assert (
            client.get(f"/api/v1/projects/{uuid4()}/ai/capabilities", headers=headers).status_code
            == 404
        )
        response = client.get(path, headers=headers)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "private, no-store"
        assert response.json() == {
            "schema_version": "provider-capabilities/1",
            "local_summary_available": True,
            "external_model_available": False,
            "external_status": "policy_access_and_grounding_review_required",
            "candidate_publication_available": False,
            "note_extraction_available": False,
            "local_note_extraction_available": True,
            "local_note_extraction_scope": "four_symptom_templates_synthetic_fixture_only",
            "next_action": "use_local_mode",
        }


def test_policy_denial_has_safe_specific_error_and_no_provider_text(identity_runtime):
    _, _, config, memberships, _ = identity_runtime
    app = create_app(config, memberships)

    # Test-only route exercises the global typed handler, not a shipped model proxy.
    @app.get("/test-denied")
    def denied():
        raise ProviderFailure("EXTERNAL_PROCESSING_NOT_ALLOWED")

    @app.get("/test-unknown")
    def unknown():
        raise ProviderFailure("artificial-private-provider-message")

    with TestClient(app) as client:
        response = client.get("/test-denied")
        assert response.status_code == 403
        assert response.json()["code"] == "EXTERNAL_PROCESSING_NOT_ALLOWED"
        response = client.get("/test-unknown")
        assert response.status_code == 503
        assert "artificial-private-provider-message" not in response.text
        assert response.json()["code"] == "PROVIDER_UNAVAILABLE"
