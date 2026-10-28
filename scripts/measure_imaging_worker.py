"""Record actual disposable fixture-stage measurements without patient/secret metadata."""

import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text

root = Path(__file__).resolve().parents[1]
url = dotenv_values(root / ".env").get("TEST_DATABASE_URL")
assert url and "disposable" in url, "Explicit disposable test DB required"
engine = create_engine(url, hide_parameters=True)
try:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT e.wall_seconds,e.rss_peak_bytes FROM imaging.job_attempt_evidence e JOIN imaging.job_commands c ON c.job_id=e.job_id WHERE c.command_key='cli-cycle' AND e.outcome='completed' AND e.recorded_at>clock_timestamp()-interval '10 minutes' ORDER BY e.recorded_at DESC LIMIT 1"
            )
        ).one()
    assert row.wall_seconds is not None and row.rss_peak_bytes is not None
    report = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "scope": "One supervised artificial 3x4x2 segmentation-QC stage; no real MRI or general performance claim",
        "stage_wall_seconds": row.wall_seconds,
        "stage_sampled_peak_rss_bytes": row.rss_peak_bytes,
        "wall_limit_seconds": 120,
        "sampled_rss_limit_bytes": 512 * 1024 * 1024,
        "sampling_is_not_an_OS_memory_reservation": True,
    }
    (root / "docs/engineering/evidence/imaging-worker-measurement.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"PASS actual fixture stage measurement: {row.wall_seconds:.3f}s; sampled peak RSS {row.rss_peak_bytes} bytes"
    )
finally:
    engine.dispose()
