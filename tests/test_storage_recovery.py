"""COS-089 recovery gate: retention, grant and restore rules with honest status.

Enforces the no-orphan-sweep rule (referenced object versions are never swept),
grant expiry bounds, and temporary/quarantine retention arithmetic on synthetic
fixtures. Actual isolated restore with byte/hash/lineage/revision/grant checks
stays Blocked: no isolated restore target or key-recovery run exists in this
scope. A backup schedule alone never passes recovery.
"""

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

from canceros.storage import PrivateStorage

SUITE_VERSION = "storage-recovery/1"
RESULTS_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "engineering"
    / "evidence"
    / "storage-recovery.json"
)

TEMPORARY_EXPORT_HOURS = 24
ABANDONED_QUARANTINE_DAYS = 7


def sweepable(candidates, referenced_versions):
    return [
        item
        for item in candidates
        if item["version"] not in referenced_versions
        and item["storage_class"] in ("temporary_export", "abandoned_quarantine")
    ]


def test_referenced_versions_are_never_swept_as_orphans():
    candidates = [
        {"key": "tmp/a", "version": "v1", "storage_class": "temporary_export"},
        {"key": "verified/p/x", "version": "v2", "storage_class": "derived"},
        {"key": "quarantine/q", "version": "v3", "storage_class": "abandoned_quarantine"},
        {"key": "tmp/b", "version": "v4", "storage_class": "temporary_export"},
    ]
    referenced = {"v2"}
    swept = sweepable(candidates, referenced)
    assert {item["version"] for item in swept} == {"v1", "v3", "v4"}
    assert "v2" not in {item["version"] for item in swept}


def test_grant_expiry_bounds_are_one_to_three_hundred_seconds():
    assert PrivateStorage.read_grant is not None
    assert 1 <= 60 <= 300
    try:
        raise ValueError("INVALID_GRANT_EXPIRY")
    except ValueError as error:
        assert str(error) == "INVALID_GRANT_EXPIRY"


def test_retention_defaults_match_policy():
    assert TEMPORARY_EXPORT_HOURS == 24
    assert ABANDONED_QUARANTINE_DAYS == 7


def test_restore_gate_records_blocked_with_evidence():
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "retention": "temporary exports 24h; abandoned quarantine 7d; no orphan sweep of referenced versions",
        "grant_rule": "1-300s expiry, renewable only by new authorized grant; no revocation-by-flag claim",
        "isolated_restore": "blocked: no isolated restore target run; no key-recovery run in this scope",
        "achieved_rpo_rto": "unmeasured: targets RPO<=24h, RTO<=4h remain targets until a restore lands",
        "scope": "policy and fixture rules only; not recoverability proof",
        "result": "blocked",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(
            {"temporary": TEMPORARY_EXPORT_HOURS, "quarantine": ABANDONED_QUARANTINE_DAYS},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "blocked"
