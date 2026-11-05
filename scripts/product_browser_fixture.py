"""Owned loopback API for product browser tests using artificial records only.

Uses TEST_DATABASE_URL only after requiring a local, explicitly disposable database.
The ignored bundle contains ephemeral credentials: never print or attach it to evidence.
No patient is created by setup; the browser creates its own artificial research case.
This fixture seeds test identities and source reviews, not real source permissions.
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4

import jwt
import psutil
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
BUNDLE = ROOT / ".local/product-browser-fixture.json"
OWNER = ROOT / ".local/product-browser-process.json"
HOST = "127.0.0.1"
PORT = int(os.environ.get("CANCEROS_PRODUCT_FIXTURE_PORT", "8001"))
if not 1024 <= PORT <= 65535:
    raise RuntimeError("Product fixture port must be an unprivileged local TCP port")


def occupied():
    with socket.socket() as probe:
        return probe.connect_ex((HOST, PORT)) == 0


def private_json(path, value, *, exclusive=False):
    target = path if exclusive else path.with_suffix(path.suffix + ".tmp")
    with target.open("x" if exclusive else "w", encoding="utf-8") as stream:
        json.dump(value, stream)
    if os.name != "nt":
        target.chmod(0o600)
    if not exclusive:
        target.replace(path)


def read_owner():
    if not OWNER.exists():
        return None
    try:
        value = json.loads(OWNER.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or set(value) != {"pid", "create_time", "run_id"}:
            raise ValueError()
        return value
    except (OSError, ValueError):
        raise RuntimeError(
            "Fixture ownership record is unreadable; no process was stopped"
        ) from None


def owned_process(owner):
    try:
        process = psutil.Process(owner["pid"])
        if abs(process.create_time() - owner["create_time"]) > 0.01:
            return None  # PID has been reused; never stop the new process.
        command = process.cmdline()
        if (
            str(SCRIPT) not in command
            or "--serve" not in command
            or "--run-id" not in command
            or owner["run_id"] not in command
        ):
            raise RuntimeError("Fixture process ownership mismatch; no process was stopped")
        return process
    except psutil.NoSuchProcess:
        return None


def disposable_url():
    raw = os.environ.get("TEST_DATABASE_URL") or dotenv_values(ROOT / ".env").get(
        "TEST_DATABASE_URL"
    )
    if not raw:
        raise RuntimeError("An explicit disposable TEST_DATABASE_URL is required")
    url = make_url(raw)
    if (
        url.drivername not in ("postgresql", "postgresql+psycopg")
        or url.host not in ("127.0.0.1", "localhost", "::1")
        or not url.database
        or "disposable" not in url.database.casefold()
    ):
        raise RuntimeError("Only a local explicitly disposable test database is permitted")
    engine = create_engine(raw, hide_parameters=True)
    try:
        with engine.connect() as connection:
            if connection.execute(text("SELECT current_database()")).scalar_one() != url.database:
                raise RuntimeError("Disposable database identity did not match")
    finally:
        engine.dispose()
    return raw


def migrate_test_database(url):
    environment = {**os.environ, "DATABASE_URL": url, "EXTERNAL_INFERENCE_ENABLED": "false"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Disposable database migration failed; no credentials were logged")


def serve(run_id):
    if occupied():
        raise RuntimeError("Loopback API port occupied; existing API was left unchanged")
    BUNDLE.parent.mkdir(exist_ok=True)
    process = psutil.Process()
    owner = {"pid": process.pid, "create_time": process.create_time(), "run_id": run_id}
    private_json(OWNER, owner, exclusive=True)
    fixture = None
    try:
        os.environ["EXTERNAL_INFERENCE_ENABLED"] = "false"
        url = disposable_url()
        os.environ["TEST_DATABASE_URL"] = url
        migrate_test_database(url)
        sys.path.insert(0, str(ROOT / "tests"))
        import uvicorn
        from test_patient_linkage import keys, setup_mapping
        from test_source_registry import registry_db, review

        from canceros.api import create_app
        from canceros.settings import Settings
        from canceros.source_registry import add_review, get_source
        from canceros.storage import PrivateStorage

        fixture = registry_db.__wrapped__()
        connection, identity, project, mapping = setup_mapping(next(fixture))
        source = get_source(connection, identity, project, mapping.source_version_id)
        if source.origin != "synthetic_engineering_fixture":
            raise RuntimeError("Browser setup requires explicitly artificial source provenance")
        add_review(
            connection,
            identity,
            project,
            source.parent_version_id,
            review(action="derivative_creation"),
        )
        viewer, outsider = uuid4(), uuid4()
        for user in (viewer, outsider):
            connection.execute(
                text("INSERT INTO access.users(id,issuer,subject) VALUES(:u,'engineering',:s)"),
                {"u": user, "s": str(user)},
            )
        for user, role in ((identity.user_id, "admin"), (viewer, "viewer")):
            connection.execute(
                text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:u,:r)"),
                {"p": project, "u": user, "r": role},
            )
        # The test source hierarchy is committed so independent real API requests
        # can see it. There are deliberately no research-patient/profile rows yet.
        connection.commit()

        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = (
            private.public_key()
            .public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
            )
            .decode()
        )
        configured = Settings(mode="test", external_inference_enabled=False)
        ring = keys()
        service = Settings(
            mode="test",
            database_url=url,
            identity_issuer="engineering",
            identity_public_key=public,
            identity_public_key_file=None,
            linkage_active_key=ring.linkage_active_key,
            linkage_keys=ring.linkage_keys,
            storage_endpoint=configured.storage_endpoint,
            storage_access_key=configured.storage_access_key,
            storage_secret_key=configured.storage_secret_key,
            storage_bucket=configured.storage_bucket,
            queue_url=configured.queue_url,
            external_inference_enabled=False,
            model_api_key=None,
            _env_file=None,
        )
        # Validate the existing private storage dependency before issuing tokens.
        # This does not initialize a new bucket or upload an artifact.
        storage = PrivateStorage(service)
        storage.client.head_bucket(Bucket=storage.bucket)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=45)

        def credential(user):
            return jwt.encode(
                {
                    "sub": str(user),
                    "iss": service.identity_issuer,
                    "aud": service.identity_audience,
                    "iat": now,
                    "nbf": now,
                    "exp": expires,
                },
                private,
                algorithm="RS256",
            )

        private_json(
            BUNDLE,
            {
                "api_url": f"http://{HOST}:{PORT}",
                "project_id": str(project),
                "source_version_id": str(mapping.source_version_id),
                "admin_token": credential(identity.user_id),
                "viewer_token": credential(viewer),
                "outsider_token": credential(outsider),
                "expires_at": expires.isoformat(),
                "run_id": run_id,
                "synthetic_only": True,
                "scope": "Artificial engineering records in disposable SQL; no authentic patient, rights or clinical validation",
            },
        )
        uvicorn.run(
            create_app(service),
            host=HOST,
            port=PORT,
            access_log=False,
            log_level="critical",
        )
    finally:
        if fixture is not None:
            fixture.close()
        if read_owner() == owner:
            BUNDLE.unlink(missing_ok=True)
            OWNER.unlink(missing_ok=True)


def start():
    if occupied():
        raise RuntimeError("API port occupied; existing API was left unchanged")
    owner = read_owner()
    if owner is not None:
        if owned_process(owner) is not None:
            raise RuntimeError("Owned browser fixture is already starting or running")
        # Only stale ownership metadata is removed. No database is reset or cleared.
        OWNER.unlink(missing_ok=True)
    BUNDLE.unlink(missing_ok=True)
    run_id = str(uuid4())
    child = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--serve", "--run-id", run_id],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise RuntimeError("Artificial product API fixture failed; credentials were not logged")
        if BUNDLE.exists() and occupied():
            bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
            if bundle.get("run_id") == run_id:
                try:
                    with urlopen(f"http://{HOST}:{PORT}/health/live", timeout=2) as response:
                        if response.status == 200:
                            print(
                                "PASS artificial product API running on loopback; credential bundle is ignored"
                            )
                            return
                except OSError:
                    pass  # The listening socket may precede HTTP readiness.
        time.sleep(0.2)
    owner = read_owner()
    if owner is not None and owner.get("run_id") == run_id:
        stop()
    raise RuntimeError("Fixture startup timed out; only its owned process was stopped")


def stop():
    owner = read_owner()
    if owner is None:
        print("No owned product browser API process recorded")
        return
    process = owned_process(owner)
    if process is not None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except psutil.TimeoutExpired:
            # Recheck before the stronger fallback; never target a reused PID.
            checked = owned_process(owner)
            if checked is not None:
                checked.kill()
                checked.wait(timeout=5)
    if read_owner() == owner:
        BUNDLE.unlink(missing_ok=True)
        OWNER.unlink(missing_ok=True)
    print("Stopped owned artificial product API; private credential bundle removed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--serve", action="store_true")
    actions.add_argument("--stop", action="store_true")
    parser.add_argument("--run-id", help=argparse.SUPPRESS)
    options = parser.parse_args()
    try:
        if options.serve:
            if not options.run_id:
                raise RuntimeError("Serve must be launched by this fixture's owned startup command")
            serve(options.run_id)
        elif options.stop:
            stop()
        else:
            start()
    except Exception:
        # Do not serialize SQL parameters, private URLs, JWTs or settings in errors.
        print(
            "Product browser fixture could not complete safely; no credentials were logged",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
