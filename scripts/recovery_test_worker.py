"""Bounded real worker for the disposable synthetic product-browser fixture.

No API credentials or job identifiers are printed. This uses the existing outbox,
Redis transport, private storage adapter and imaging/simulation execution worker.
It refuses non-local dependencies, real-source provenance and foreign queued work.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import create_engine, text

from canceros.imaging_jobs import READY, dispatch_imaging, process_imaging_one
from canceros.jobs import queue_for
from canceros.settings import Settings
from canceros.storage import PrivateStorage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from product_browser_fixture import disposable_url  # noqa: E402


def _local_service(raw: str | None) -> bool:
    return bool(raw and urlparse(raw).hostname in ("127.0.0.1", "localhost", "::1"))


def _fixture_project() -> UUID:
    bundle = json.loads((ROOT / ".local/product-browser-fixture.json").read_text("utf-8"))
    if bundle.get("synthetic_only") is not True or not _local_service(bundle.get("api_url")):
        raise RuntimeError("Synthetic local product fixture required")
    return UUID(bundle["project_id"])


def _check_sources(engine, project: UUID) -> None:
    with engine.connect() as connection:
        total, unsafe = connection.execute(
            text(
                "SELECT count(*),count(*) FILTER (WHERE origin!='synthetic_engineering_fixture') "
                "FROM source.registry_versions WHERE project_id=:p"
            ),
            {"p": project},
        ).one()
        if not total or unsafe:
            raise RuntimeError("Only an explicitly synthetic fixture project may be processed")


def _check_ready_scope(engine, queue, project: UUID) -> None:
    # The canonical worker queue is shared; never consume another project's jobs.
    pending = queue.lrange(READY, 0, 1000)
    if len(pending) > 1000:
        raise RuntimeError("Fixture worker queue budget exceeded")
    with engine.connect() as connection:
        for raw in pending:
            job = connection.execute(
                text("SELECT project_id FROM ops.jobs WHERE id=:id"), {"id": UUID(raw)}
            ).scalar_one_or_none()
            if job != project:
                raise RuntimeError("Foreign queued work requires its owning worker")


def _work(seconds: int) -> None:
    engine = None
    queue = None
    try:
        project = _fixture_project()
        config = Settings(
            mode="test",
            database_url=disposable_url(),
            external_inference_enabled=False,
            model_api_key=None,
        )
        if not _local_service(config.storage_endpoint) or not _local_service(
            config.queue_url.get_secret_value() if config.queue_url else None
        ):
            raise RuntimeError("Only local fixture storage and queue are permitted")
        engine = create_engine(config.database_url.get_secret_value(), hide_parameters=True)
        _check_sources(engine, project)
        queue = queue_for(config)
        queue.ping()
        storage = PrivateStorage(config)
        deadline = time.monotonic() + seconds
        completed = 0
        print("Synthetic disposable worker ready; external inference disabled.", flush=True)
        while time.monotonic() < deadline:
            if _fixture_project() != project:
                raise RuntimeError("Fixture project changed; restart its owning worker")
            _check_sources(engine, project)
            _check_ready_scope(engine, queue, project)
            dispatch_imaging(engine, queue, project)
            _check_ready_scope(engine, queue, project)
            if process_imaging_one(engine, queue, storage, config) is not None:
                completed += 1
                print(f"Processed fixture deliveries: {completed}", flush=True)
            else:
                time.sleep(0.25)
        print("Synthetic disposable worker time budget reached.", flush=True)
    except Exception:
        # Dependency exceptions may contain credentials or private manifest text.
        print("Fixture worker stopped: dependency or synthetic-scope check failed.", flush=True)
        raise SystemExit(1) from None
    finally:
        if queue is not None:
            queue.close()
        if engine is not None:
            engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=900)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 900:
        parser.error("--seconds must be between 1 and 900")
    # A supervisor enforces the total wall limit even if a job/dependency hangs.
    child = multiprocessing.get_context("spawn").Process(target=_work, args=(args.seconds,))
    child.start()
    child.join(args.seconds)
    if child.is_alive():
        child.terminate()
        child.join(5)
        if child.is_alive():
            child.kill()
            child.join(5)
        print("Synthetic worker stopped at its hard wall limit.", flush=True)
        return 0
    return child.exitcode or 0


if __name__ == "__main__":
    raise SystemExit(main())
