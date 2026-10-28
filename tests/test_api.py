from fastapi.testclient import TestClient

from canceros.api import create_app
from canceros.settings import Settings


def test_health_and_restricted_readiness():
    app = create_app(Settings(mode="test", _env_file=None))
    with TestClient(app) as client:
        response = client.get("/health/live")
        assert response.json() == {"status": "ok"}
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["x-request-id"]
        assert client.get("/health/ready").status_code == 401
        assert client.get("/api/v1/projects/no-patient").status_code == 404


def test_ready_is_not_fake_success():
    app = create_app(
        Settings(mode="test", monitor_token="artificial-monitor-token", _env_file=None)
    )
    with TestClient(app) as client:
        assert (
            client.get(
                "/health/ready", headers={"Authorization": "Bearer artificial-monitor-token"}
            ).status_code
            == 503
        )


def test_internal_error_does_not_leak_secret():
    app = create_app(Settings(mode="test", _env_file=None))

    @app.get("/engineering-failure")
    def fail():
        raise RuntimeError("artificial-secret-never-render")

    with TestClient(app) as client:
        response = client.get("/engineering-failure")
        assert response.status_code == 500
        assert "artificial-secret" not in response.text
        assert response.headers["content-type"] == "application/problem+json"
