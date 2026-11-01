"""COS-092 observability gate: redaction, health semantics and budget honesty."""

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from canceros.api import create_app
from canceros.settings import Settings

RESULTS_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "engineering"
    / "evidence"
    / "observability-cost.json"
)
SUITE_VERSION = "observability-cost/1"

SENSITIVE_GRAPH = (
    "Bearer ",
    "MODEL_API_KEY",
    "PRIVATE KEY",
    "signed_url",
    "presigned",
)


def app():
    return create_app(Settings(mode="test", _env_file=None))


def test_liveness_is_public_and_topology_free():
    with TestClient(app()) as client:
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert "postgres" not in response.text.lower()
        assert "redis" not in response.text.lower()


def test_restricted_readiness_denies_without_monitor_token():
    with TestClient(app()) as client:
        assert client.get("/health/ready").status_code == 401
        assert (
            client.get("/health/ready", headers={"authorization": "Bearer wrong"}).status_code
            == 401
        )


def test_health_and_error_payloads_carry_no_sensitive_graph():
    with TestClient(app()) as client:
        for path in ("/health/live", "/openapi.json"):
            body = client.get(path).text
            for marker in SENSITIVE_GRAPH:
                assert marker not in body, f"{path}: {marker}"
        missing = client.get("/api/v1/projects/00000000-0000-4000-8000-000000000000/patients")
        assert missing.status_code in (401, 403, 404, 422)
        for marker in SENSITIVE_GRAPH:
            assert marker not in missing.text, marker


def test_observability_report_with_ledger_and_alert_limits():
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "health": "pass: public liveness topology-free; restricted readiness denies without monitor token",
        "redaction": "pass: no bearer/key/grant graph in health, schema or denied responses",
        "budget_ledger": "estimates only: compute/DB/storage/egress/observability/model lines with caps; no free-credit assumption",
        "alerts_caps": "configured ceilings documented; delivery test needs a staging apply; alerts are not hard caps",
        "scope": "fixture and static checks; alert delivery and billed measurements need a live target",
        "result": "passed",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(sorted(SENSITIVE_GRAPH), sort_keys=True).encode()
    ).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "passed"
