"""One CPU imaging job per supervised child; no data, exception or signed URL output."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID

import psutil

ROOT = Path(__file__).resolve().parents[1]
MAX_WALL_SECONDS = 120
MAX_RSS_BYTES = 512 * 1024 * 1024


def supervise(command, *, env=None, max_wall_seconds=MAX_WALL_SECONDS, max_rss_bytes=MAX_RSS_BYTES):
    """Only caller-owned children are monitored/killed; never serialize their output."""
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    monitor = psutil.Process(process.pid)
    peak, outcome = 0, "completed"
    try:
        while process.poll() is None:
            try:
                peak = max(peak, monitor.memory_info().rss)
            except psutil.NoSuchProcess:
                break
            if time.monotonic() - started > max_wall_seconds:
                outcome = "wall_limit"
            elif peak > max_rss_bytes:
                outcome = "rss_limit"
            if outcome != "completed":
                process.kill()
                break
            time.sleep(0.05)
        code = process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
    if outcome == "completed" and code:
        outcome = "worker_error"
    return {
        "outcome": outcome,
        "exit_code": code,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "sampled_peak_rss_bytes": peak,
        "scope": "bounded_CPU_engineering_worker_not_scientific_validation",
    }


def child_once(project_id):
    from canceros import imaging_jobs
    from canceros.jobs import queue_for
    from canceros.persistence import engine_for
    from canceros.settings import Settings
    from canceros.storage import PrivateStorage

    settings = Settings()
    if settings.mode == "test":
        for name in ("READY", "PROCESSING"):
            value = os.environ.get("CANCEROS_IMAGING_" + name)
            if value:
                if not value.startswith("canceros:tests:"):
                    raise ValueError("Invalid isolated test transport")
                setattr(imaging_jobs, name, value)
    engine = engine_for(settings)
    try:
        queue = queue_for(settings)
        imaging_jobs.recover_imaging(engine, queue, project_id)
        imaging_jobs.dispatch_imaging(engine, queue, project_id)
        imaging_jobs.process_imaging_one(engine, queue, PrivateStorage(settings), settings)
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once", action="store_true", help="Run one bounded CPU worker cycle (the default)"
    )
    parser.add_argument("--project-id", type=UUID)
    parser.add_argument("--child-once", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child_once:
        try:
            child_once(args.project_id)
        except Exception:
            raise SystemExit(1) from None
        return
    command = [sys.executable, str(Path(__file__).resolve()), "--child-once"]
    if args.project_id:
        command.extend(["--project-id", str(args.project_id)])
    result = supervise(command)
    print(json.dumps(result, sort_keys=True))
    if result["outcome"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
