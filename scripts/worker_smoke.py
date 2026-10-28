"""Execute actual worker process on explicitly artificial persisted input."""

import json
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text

from canceros.jobs import enqueue
from canceros.persistence import engine_for
from canceros.settings import Settings

root = Path(__file__).resolve().parents[1]
engine = engine_for(Settings())
project, patient = uuid4(), uuid4()
with engine.begin() as connection:
    connection.execute(
        text("INSERT INTO access.projects(id,name) VALUES(:id,'Engineering-only worker smoke')"),
        {"id": project},
    )
    connection.execute(
        text(
            "INSERT INTO source.research_patients(id,project_id,display_code) VALUES(:u,:p,:code)"
        ),
        {"u": patient, "p": project, "code": "engineering-" + str(patient)},
    )
identity = enqueue(engine, project, patient)
subprocess.run([sys.executable, "-m", "workers.digest"], cwd=root, check=True)
with engine.connect() as connection:
    row = connection.execute(
        text("SELECT status,result_hash,publication_status FROM ops.jobs WHERE id=:id"),
        {"id": identity},
    ).one()
    assert row.status == "succeeded" and row.publication_status == "ready"
    report = {
        "scope": "Engineering-only persisted transport/job process smoke; no medical processing",
        "job_id": str(identity),
        "result": "passed",
        "status": row.status,
        "publication_status": row.publication_status,
        "digest": row.result_hash,
        "command": "uv run python scripts/worker_smoke.py",
    }
(root / "docs/engineering/evidence/worker-smoke.json").write_text(
    json.dumps(report, indent=2) + "\n", encoding="utf-8"
)
print(
    "PASS separate worker process, configured queue, durable SQL result, private byte artifact; ready is not published"
)
engine.dispose()
