"""COS-091 hardening gate: boundaries, secrets hygiene and denied-by-default export.

Runs the existing boundary and hygiene gates, asserts no frontend secret or
storage APIs, no committed env or restricted assets, and verifies the export
gateway denies by default with zero transport calls (reusing the COS-086
denial path pattern). Deployed ingress/TLS/session review and scanner audit
stay open: no deployed target exists in this scope.
"""

import asyncio
import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from canceros.provider_contracts import ProviderInput
from canceros.provider_gateway import ProviderFailure, execute_private

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "docs" / "engineering" / "evidence" / "security-hardening.json"
SUITE_VERSION = "security-hardening/1"

FORBIDDEN_WEB = (
    "process.env.MODEL_API_KEY",
    "process.env.DATABASE_URL",
    "localStorage.setItem",
    "sessionStorage.setItem",
)


def web_sources():
    return [
        p
        for p in (ROOT / "apps" / "web").rglob("*")
        if p.suffix in (".ts", ".tsx") and ".test." not in p.name
        if ".next" not in p.parts and "node_modules" not in p.parts
    ]


def test_frontend_boundary_holds_no_secrets_or_storage():
    for path in web_sources():
        content = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_WEB:
            assert forbidden not in content, f"{path.name}: {forbidden}"


def test_no_committed_env_or_restricted_assets():
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    files = [p.decode("utf-8") for p in result.stdout.split(b"\0") if p]
    assert ".env" not in files
    assert not any(f.startswith(".env.") and f != ".env.example" for f in files)
    for relative in files:
        assert not relative.startswith(("Data_folder/", ".local/", ".venv/", "node_modules/")), (
            relative
        )
        assert not re.search(r"\.(dcm|nii|nii\.gz|pth|ckpt|pem|key)$", relative, re.I), relative


def test_denied_export_makes_zero_transport_calls():
    context = ProviderInput(
        purpose="research_summary",
        input_snapshot_hash="a" * 64,
        measurements=[],
        missingness=["unreviewed"],
        evidence_ids=[uuid4()],
    )
    config = SimpleNamespace(
        mode="test",
        external_inference_enabled=False,
        export_policy_path=None,
        model_provider="meta",
        model_identifier="artificial-model",
        model_endpoint="https://api.meta.ai/v1/responses",
        model_account_id="artificial-no-account",
        model_region="artificial-region",
    )

    class DeniedTransport:
        def __init__(self):
            self.calls = []

        async def post(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            raise AssertionError("network egress attempted while denied")

    transport = DeniedTransport()
    with pytest.raises(ProviderFailure, match="EXTERNAL_PROCESSING_NOT_ALLOWED"):
        asyncio.run(execute_private(config, context, transport, lambda: None))
    assert transport.calls == []


def test_security_hardening_report_with_open_deployment_review():
    # A report-only invocation must not publish success without running its gates.
    test_frontend_boundary_holds_no_secrets_or_storage()
    test_no_committed_env_or_restricted_assets()
    test_denied_export_makes_zero_transport_calls()
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "frontend_boundary": f"pass: none of {len(FORBIDDEN_WEB)} forbidden patterns in web sources",
        "committed_secrets": "pass: no .env or restricted assets in git-visible files",
        "denied_egress": "pass: zero transport calls when export disabled",
        "deployed_review": "open: no deployed target; ingress/TLS/session/CSRF/origin and scanner audit need a staging apply",
        "demo_manifest_rights": "open: source rights reconciled against the demo manifest at curation time (COS-094/095)",
        "scope": "fixture and static gates; not a complete security audit",
        "result": "passed",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(sorted(FORBIDDEN_WEB), sort_keys=True).encode()
    ).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "passed"
    assert sys.version_info >= (3, 12)
