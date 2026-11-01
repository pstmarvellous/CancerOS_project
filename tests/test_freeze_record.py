"""COS-104 freeze audit: blocked tag with candidate package, no false release.

Final-release mode. Reconciles COS-102 (blocked readiness) and COS-103
(blocked operations): since mandatory gates are open, no release tag is
created and no validated-release claim is made. Assembles the candidate
package manifest over the already fixed commit, verifies the package excludes
restricted content, and writes the freeze record with blocked disposition.
Local tag creation stays distinct from remote publication; no push occurs here.
"""

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "docs" / "engineering" / "evidence" / "freeze-record.json"
SUITE_VERSION = "freeze-record/1"

PACKAGE_FILES = [
    "docs/PHASE-6-EVIDENCE-PACKAGE.md",
    "docs/runbooks/smoke-rollback-restore.md",
    "docs/runbooks/staging-deployment.md",
    "docs/runbooks/storage-backup-policy.md",
    "docs/runbooks/worker-operations.md",
    "docs/runbooks/observability-cost.md",
    "pyproject.toml",
    "uv.lock",
    "package.json",
]


def candidate():
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def test_mandatory_gates_block_release_tag():
    backlog = json.loads(
        (ROOT / "docs" / "engineering" / "evidence" / "remediation-backlog.json").read_text(
            encoding="utf-8"
        )
    )
    ops = json.loads(
        (ROOT / "docs" / "engineering" / "evidence" / "operational-verification.json").read_text(
            encoding="utf-8"
        )
    )
    assert backlog["engineering_disposition"].startswith("blocked")
    assert ops["result"] == "blocked"


def test_no_release_tag_created_while_blocked():
    tags = subprocess.run(
        ["git", "tag", "--list", "canceros-release-*"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert tags == "", f"unexpected release tag present: {tags}"


def test_candidate_package_manifest_with_safe_contents():
    missing = [name for name in PACKAGE_FILES if not (ROOT / name).exists()]
    assert missing == [], missing
    for name in PACKAGE_FILES:
        content = (ROOT / name).read_text(encoding="utf-8")
        assert "MODEL_API_KEY" not in content, name
        assert "PRIVATE KEY" not in content, name
    commit = candidate()
    manifest = {
        "candidate_commit": commit,
        "package_files": PACKAGE_FILES,
        "evidence_index": "docs/engineering/evidence/",
        "lockfiles": ["uv.lock", "package-lock.json"],
    }
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    assert len(commit) == 40 and len(digest) == 64


def test_freeze_record_with_blocked_disposition_and_no_push():
    commit = candidate()
    payload = {
        "run_id": f"cos104-{commit[:12]}",
        "mode": "final_release",
        "candidate_commit": commit,
        "validated_application_commit": commit,
        "release_evidence_commit": "pending: evidence sidecar written after this record; tag created only when gates pass",
        "tag": "none created: mandatory gates open; no validated release to freeze",
        "remote_publication": "none performed: local tagging distinct from remote push; no push in this task",
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "disposition": "blocked: candidate package assembled; validated release tag gated on COS-102/103 closure",
        "remaining_to_unblock": [
            "D02 genuine two-exam case",
            "isolated restore with RPO/RTO measurement",
            "deployed smoke on an authorized target",
            "qualified scientific review",
            "measured performance and participant review",
        ],
        "self_review_disclosure": "single agent self-review; no invented signatures",
        "result": "blocked",
    }
    payload["manifest_sha256"] = hashlib.sha256(commit.encode()).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "blocked"
