"""Canonical Windows-native service profiles. No reset, remote upload or hidden worker."""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4

from local_services import start, stop

from canceros.readiness import dependencies_ready
from canceros.settings import Settings
from canceros.storage import PrivateStorage

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def wait(predicate, label, deadline=45):
    end = time.monotonic() + deadline
    while time.monotonic() < end:
        try:
            if predicate():
                print(label + " ready")
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(
        label + " unavailable; inspect private logs, configuration and occupied ports"
    )


def http_ready(url):
    with urlopen(url, timeout=2) as response:
        return response.status == 200


def start_profile(profile):
    if profile in ("data", "foundation"):
        run("scripts/local_postgres.py")
        run("-m", "alembic", "upgrade", "head")
        start("storage")
        start("queue")
        settings = Settings()
        storage = PrivateStorage(settings)

        def ready_object():
            storage.initialize_development_bucket()
            artifact = storage.write_verified(uuid4(), b"engineering-only startup byte probe")
            return (
                storage.read(artifact, artifact.project_id)
                == b"engineering-only startup byte probe"
            )

        wait(ready_object, "Private versioned object store")
        wait(lambda: dependencies_ready(settings), "PostgreSQL/storage/queue dependencies")
        # Demo launch is part of normal startup: ensure a valid synthetic bundle
        # while services are up, so the homepage never advertises a missing demo.
        run("scripts/migrate_test.py")
        run("scripts/prepare_synthetic_demo.py")
    if profile in ("shell", "foundation"):
        start("api")
        start("web")
        wait(lambda: http_ready("http://127.0.0.1:8000/health/live"), "API process")
        wait(lambda: http_ready("http://127.0.0.1:3000"), "Research shell")
    print("Profile started; workers run only on explicit command. No medical capability asserted.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "status"])
    parser.add_argument(
        "profile", choices=["shell", "data", "foundation"], default="foundation", nargs="?"
    )
    args = parser.parse_args()
    if args.action == "start":
        start_profile(args.profile)
    elif args.action == "stop":
        names = (
            ["web", "api"]
            if args.profile == "shell"
            else ["queue", "storage"]
            if args.profile == "data"
            else ["web", "api", "queue", "storage"]
        )
        for name in names:
            stop(name)
        if args.profile != "shell":
            run("scripts/local_postgres.py", "stop")
    else:
        print("Required private dependencies ready:", dependencies_ready(Settings()))
        for name, url in [
            ("API", "http://127.0.0.1:8000/health/live"),
            ("Web", "http://127.0.0.1:3000"),
        ]:
            try:
                print(name, "reachable" if http_ready(url) else "unavailable")
            except Exception:
                print(name, "unavailable")


if __name__ == "__main__":
    main()
