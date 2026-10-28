"""Restart owned development services and prove a tiny completed result survives."""

import json
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import psutil
from local_services import load, start, stop
from sqlalchemy import text

from canceros.jobs import queue_for
from canceros.persistence import engine_for
from canceros.settings import Settings
from canceros.storage import PrivateStorage

ROOT = Path(__file__).resolve().parents[1]
config = Settings()
storage = PrivateStorage(config)
project = uuid4()
artifact = storage.write_verified(project, b"engineering-only restart persistence")
engine = engine_for(config)
with engine.connect() as connection:
    before = connection.execute(
        text("SELECT count(*) FROM ops.jobs WHERE status='succeeded'")
    ).scalar_one()
assert before > 0
engine.dispose()
queue = queue_for(config)
key = "canceros:engineering:restart:" + str(uuid4())
queue.set(key, "engineering-only", ex=300)
for name in ("queue", "storage"):
    stop(name)
subprocess.run([sys.executable, "scripts/local_postgres.py", "stop"], cwd=ROOT, check=True)
subprocess.run([sys.executable, "scripts/local_postgres.py"], cwd=ROOT, check=True)
start("storage")
start("queue")
deadline = time.monotonic() + 45
while True:
    try:
        assert storage.read(artifact, project) == b"engineering-only restart persistence"
        assert queue.get(key) == "engineering-only"
        break
    except Exception:
        if time.monotonic() > deadline:
            raise RuntimeError("Restart persistence unavailable") from None
        time.sleep(0.5)
queue.delete(key)
engine = engine_for(config)
with engine.connect() as connection:
    assert (
        connection.execute(
            text("SELECT count(*) FROM ops.jobs WHERE status='succeeded'")
        ).scalar_one()
        == before
    )
engine.dispose()
memory = {}
for name, entry in load().items():
    try:
        memory[name] = round(psutil.Process(entry["pid"]).memory_info().rss / 1024**2, 2)
    except psutil.Error:
        memory[name] = "unavailable"
record = {
    "result": "passed",
    "command": "uv run python scripts/restart_smoke.py",
    "scope": "Owned local services and nonclinical byte/job/queue markers; not production backup/restore",
    "completed_jobs_retained": before,
    "tracked_process_rss_mib": memory,
    "host_total_ram_gib": round(psutil.virtual_memory().total / 1024**3, 2),
    "limitations": "Point-in-time process RSS, not peak workload or full8GB scientific pipeline benchmark",
}
(ROOT / "docs/engineering/evidence/restart-smoke.json").write_text(
    json.dumps(record, indent=2) + "\n", encoding="utf-8"
)
print(
    "PASS owned-service restart retains SQL result, private object version and queue marker; memory measured"
)
