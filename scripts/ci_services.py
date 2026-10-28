"""Linux CI counterpart: real isolated container services, no source/provider data."""

import os
import secrets
import subprocess
import time
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text

from canceros.jobs import queue_for
from canceros.persistence import engine_for
from canceros.settings import Settings
from canceros.storage import PrivateStorage

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
LOCAL.mkdir(exist_ok=True)
password = secrets.token_hex(24)
access = secrets.token_hex(20)
secret = secrets.token_hex(24)
queue_secret = secrets.token_hex(24)
env = {
    "MODE": "test",
    "DATABASE_URL": f"postgresql+psycopg://canceros:{password}@127.0.0.1:55432/canceros_disposable_ci",
    "TEST_DATABASE_URL": f"postgresql+psycopg://canceros:{password}@127.0.0.1:55432/canceros_disposable_ci",
    "QUEUE_URL": f"redis://:{queue_secret}@127.0.0.1:56379/0",
    "STORAGE_ENDPOINT": "http://127.0.0.1:58333",
    "STORAGE_BUCKET": "canceros-private",
    "STORAGE_ACCESS_KEY": access,
    "STORAGE_SECRET_KEY": secret,
    "MONITOR_TOKEN": secrets.token_hex(24),
    "EXTERNAL_INFERENCE_ENABLED": "false",
}
(ROOT / ".env").write_text("\n".join(f"{k}={v}" for k, v in env.items()) + "\n")
(LOCAL / "ci-postgres.env").write_text(
    f"POSTGRES_USER=canceros\nPOSTGRES_PASSWORD={password}\nPOSTGRES_DB=canceros_disposable_ci\n"
)
(LOCAL / "ci-storage.env").write_text(
    f"AWS_ACCESS_KEY_ID={access}\nAWS_SECRET_ACCESS_KEY={secret}\nS3_BUCKET=canceros-private\n"
)
(LOCAL / "redis-container.conf").write_text(
    f"bind 0.0.0.0\nport 56379\nrequirepass {queue_secret}\ndir /data\nappendonly yes\nmaxmemory 64mb\nmaxmemory-policy noeviction\n"
)
for filename in (
    ROOT / ".env",
    LOCAL / "ci-postgres.env",
    LOCAL / "ci-storage.env",
    LOCAL / "redis-container.conf",
):
    filename.chmod(0o600)
commands = [
    [
        "docker",
        "run",
        "-d",
        "--name",
        "canceros-ci-db",
        "--env-file",
        str(LOCAL / "ci-postgres.env"),
        "-p",
        "127.0.0.1:55432:5432",
        "postgres:15.4",
    ],
    [
        "docker",
        "run",
        "-d",
        "--name",
        "canceros-ci-queue",
        "-p",
        "127.0.0.1:56379:56379",
        "-v",
        f"{LOCAL}/redis-container.conf:/config/redis.conf:ro",
        "redis:8.2.1-alpine",
        "redis-server",
        "/config/redis.conf",
    ],
    [
        "docker",
        "run",
        "-d",
        "--name",
        "canceros-ci-storage",
        "--env-file",
        str(LOCAL / "ci-storage.env"),
        "-p",
        "127.0.0.1:58333:8333",
        "chrislusf/seaweedfs:4.51",
        "mini",
        "-dir=/data",
        "-ip=127.0.0.1",
        "-ip.bind=0.0.0.0",
        "-admin.ui=false",
        "-webdav=false",
        "-s3.port.iceberg=0",
        "-s3.port.lance=0",
    ],
]
for command in commands:
    subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
os.environ.update(env)
deadline = time.monotonic() + 60
while True:
    try:
        engine = engine_for(Settings())
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        storage = PrivateStorage(Settings())
        storage.initialize_development_bucket()
        project = uuid4()
        artifact = storage.write_verified(project, b"engineering-only CI readiness")
        assert storage.read(artifact, project) == b"engineering-only CI readiness"
        queue_for(Settings()).ping()
        break
    except Exception:
        if time.monotonic() > deadline:
            raise RuntimeError("CI private services unavailable") from None
        time.sleep(1)
print("CI ephemeral private services configured; no credentials displayed")
