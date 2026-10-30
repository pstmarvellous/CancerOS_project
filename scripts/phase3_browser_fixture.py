"""Serve an isolated Phase 3 browser fixture; never overwrite development settings.

Only the explicitly disposable test database is used. The ignored bundle contains
an ephemeral JWT and must never be printed, attached to evidence, or committed.
"""

import argparse
import json
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import psutil
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / ".local/phase3-browser-fixture.json"
OWNER = ROOT / ".local/phase3-browser-process.json"


def occupied():
    with socket.socket() as probe:
        return probe.connect_ex(("127.0.0.1", 8000)) == 0


def serve():
    # Refuse to replace any existing API. Uvicorn also atomically binds the port.
    if occupied():
        raise RuntimeError("Loopback API port already occupied")
    sys.path.insert(0, str(ROOT / "tests"))
    import uvicorn
    from test_imaging_ingestion import imaging_db
    from test_simulation_execution import publication_value
    from test_simulation_runs import TEST
    from test_source_registry import registry_db
    from test_timeline_runs import prepared

    from canceros.api import create_app
    from canceros.settings import Settings
    from canceros.simulation_execution import publish_completion

    fixture = registry_db.__wrapped__()
    try:
        data = imaging_db.__wrapped__(next(fixture))
        connection, identity, project, patient, _, storage, config = data
        measurement, origin, branch, run, completion, query = prepared(data, geometry=True)
        publish_completion(
            connection,
            identity,
            project,
            patient.patient_id,
            completion.id,
            publication_value(run),
            storage,
            "phase3-browser-publish",
            TEST,
        )
        connection.execute(
            text(
                "INSERT INTO access.memberships(project_id,user_id,role) "
                "VALUES(:p,:u,'admin') ON CONFLICT DO NOTHING"
            ),
            {"p": project, "u": identity.user_id},
        )
        connection.commit()
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = (
            private.public_key()
            .public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
            )
            .decode()
        )
        service = Settings(
            mode="test",
            database_url=connection.engine.url.render_as_string(hide_password=False),
            identity_issuer="engineering",
            identity_public_key=public,
            linkage_active_key="k1",
            linkage_keys=config.linkage_keys,
        )
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": str(identity.user_id),
                "iss": service.identity_issuer,
                "aud": service.identity_audience,
                "iat": now,
                "nbf": now,
                "exp": now + timedelta(minutes=45),
            },
            private,
            algorithm="RS256",
        )
        BUNDLE.parent.mkdir(exist_ok=True)
        BUNDLE.write_text(
            json.dumps(
                {
                    "api_url": "http://127.0.0.1:8000",
                    "project_id": str(project),
                    "patient_id": str(patient.patient_id),
                    "branch_id": str(branch.id),
                    "run_id": str(run.id),
                    "config_id": str(run.config_id),
                    "completion_id": str(completion.id),
                    "timeline_origin_id": str(origin),
                    "data_revision": run.input_revision,
                    "knowledge_as_of": query.window.knowledge_as_of.isoformat(),
                    "expected_followup_values": ["64", "8", "1"],
                    "token": token,
                    "expected_volume_mm3": measurement.values.volume_mm3,
                    "scope": "Synthetic engineering fixture; no authentic patient or clinical validation",
                }
            ),
            encoding="utf-8",
        )
        process = psutil.Process()
        OWNER.write_text(json.dumps({"pid": process.pid, "create_time": process.create_time()}))
        uvicorn.run(
            create_app(service), host="127.0.0.1", port=8000, access_log=False, log_level="critical"
        )
    finally:
        fixture.close()


def start():
    if occupied():
        raise RuntimeError("API port occupied; existing API was left unchanged")
    BUNDLE.unlink(missing_ok=True)
    OWNER.unlink(missing_ok=True)
    child = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--serve"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise RuntimeError("Synthetic Phase 3 API fixture failed; no credentials were logged")
        if BUNDLE.exists() and occupied():
            print("PASS synthetic browser API running on loopback; private bundle is ignored")
            return
        time.sleep(0.2)
    raise RuntimeError("Fixture startup timed out; inspect owned process before cleanup")


def stop():
    if not OWNER.exists():
        print("No owned synthetic browser API process recorded")
        return
    owner = json.loads(OWNER.read_text())
    try:
        process = psutil.Process(owner["pid"])
        command = process.cmdline()
        if (
            abs(process.create_time() - owner["create_time"]) > 0.01
            or str(Path(__file__).resolve()) not in command
            or "--serve" not in command
        ):
            raise RuntimeError("Process ownership mismatch; no process was stopped")
        process.terminate()
        process.wait(timeout=10)
    except psutil.NoSuchProcess:
        pass
    BUNDLE.unlink(missing_ok=True)
    OWNER.unlink(missing_ok=True)
    print("Stopped owned synthetic browser API; private JWT bundle removed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--stop", action="store_true")
    options = parser.parse_args()
    if options.serve:
        serve()
    elif options.stop:
        stop()
    else:
        start()
