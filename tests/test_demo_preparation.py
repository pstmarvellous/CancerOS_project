"""Preparation must not skip fresh files that the serving boundary rejects."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from scripts import prepare_synthetic_demo as preparation


@pytest.mark.parametrize("expiry", [None, "2099-01-01T00:00:00", "not-a-date"])
def test_malformed_bundle_reports_invalid_without_traceback(tmp_path, expiry):
    target = tmp_path / "demo.json"
    target.write_text(json.dumps({"expiresAt": expiry}))
    assert preparation.bundle_status(target)[0] == "invalid"


def test_fresh_incomplete_bundle_is_rebuilt_not_skipped(tmp_path, monkeypatch):
    target = tmp_path / "demo.json"
    target.write_text(json.dumps({
        "version": "synthetic-demo/1", "syntheticOnly": False,
        "caseLabel": "wrong", "preparedAt": "invalid",
        "expiresAt": (datetime.now(timezone.utc) + timedelta(days=4)).isoformat(),
        "scenarios": dict.fromkeys(preparation.FAMILIES, {}),
    }))
    monkeypatch.setattr(preparation, "BUNDLE_PATH", target)
    before = target.read_bytes()

    def require_rebuild():
        raise RuntimeError("rebuild reached")

    monkeypatch.setattr(preparation, "registry_db", SimpleNamespace(__wrapped__=require_rebuild))
    assert preparation.bundle_status()[0] == "invalid"
    with pytest.raises(RuntimeError, match="rebuild reached"):
        preparation.prepare()
    assert target.read_bytes() == before


def test_missing_bundle_reports_actionable_status(tmp_path):
    state, message = preparation.bundle_status(tmp_path / "absent.json")
    assert state == "missing"
    assert "prepare again" in message


def test_expired_bundle_identifies_recovery(tmp_path):
    target = tmp_path / "expired.json"
    target.write_text(json.dumps({"expiresAt": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}))
    state, message = preparation.bundle_status(target)
    assert state == "expired"
    assert "refresh" in message
