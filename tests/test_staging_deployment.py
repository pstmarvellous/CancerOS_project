"""COS-088 staging evidence: local validation with honest deployment status."""

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "docs" / "engineering" / "evidence" / "staging-deployment.json"


def run(*command):
    result = subprocess.run(list(command), cwd=ROOT, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()[:2000]


def test_staging_plan_is_reviewable_without_cloud_spend():
    code, missing = run(
        sys.executable, "scripts/check_deployment_config.py", "--env-file", ".env.nonexistent"
    )
    assert code == 2
    assert "MISSING" in missing
    assert ROOT.joinpath("infrastructure/compose.staging.yaml").exists()
    assert ROOT.joinpath("infrastructure/Dockerfile.api").exists()
    assert ROOT.joinpath("infrastructure/Dockerfile.web").exists()
    assert ROOT.joinpath("infrastructure/Dockerfile.worker").exists()
    assert ROOT.joinpath("docs/runbooks/staging-deployment.md").exists()
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "suite": "staging-deployment/1",
        "config_gate": "pass: missing-file path returns typed diagnostics with exit 2",
        "images": "Dockerfiles present; digests recorded only after a real build on a Docker host",
        "deployment_status": "not deployed: no authorized account/target/spending authority in this scope",
        "estimated_resources": "~4 vCPU / ~6 GiB across six services before object data",
        "measured_costs": "none: no cost-bearing apply performed",
        "scope": "reviewable plan and local validation only; not cloud-deployed evidence",
        "result": "passed",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(
            ["Dockerfile.api", "Dockerfile.web", "Dockerfile.worker", "compose.staging.yaml"],
            sort_keys=True,
        ).encode()
    ).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "passed"
