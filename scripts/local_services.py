"""Start/stop only tracked local service processes; no data reset path."""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
STATE = LOCAL / "processes.json"


def load():
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def tracked(entry):
    try:
        process = psutil.Process(entry["pid"])
        return (
            process
            if abs(process.create_time() - entry["created"]) < 1
            and str(ROOT).lower() in " ".join(process.cmdline()).lower()
            else None
        )
    except psutil.Error:
        return None


def start(name):
    state = load()
    if name in state and tracked(state[name]):
        print(f"{name} already running as tracked local process")
        return
    config = json.loads((LOCAL / "development.json").read_text())
    env = os.environ.copy()
    # SeaweedFS binds generic DEBUG as a Boolean; the host uses DEBUG=release.
    env.pop("DEBUG", None)
    if name == "storage":
        executable = next((LOCAL / "tools/seaweedfs").rglob("weed.exe"), None)
        if executable is None:
            raise RuntimeError("Pinned SeaweedFS not installed; run bootstrap_tools.py")
        data = LOCAL / "objects"
        data.mkdir(exist_ok=True)
        command = [
            str(executable),
            "mini",
            f"-dir={data}",
            "-ip=127.0.0.1",
            "-ip.bind=127.0.0.1",
            "-master.port=19333",
            "-volume.port=18080",
            "-filer.port=18888",
            "-s3.port=58333",
            "-s3.port.grpc=18334",
            "-s3.port.iceberg=0",
            "-s3.port.lance=0",
            "-admin.ui=false",
            "-webdav=false",
            "-master.volumeSizeLimitMB=64",
        ]
        env.update(
            AWS_ACCESS_KEY_ID=config["storage_access_key"],
            AWS_SECRET_ACCESS_KEY=config["storage_secret_key"],
            S3_BUCKET="canceros-private",
        )
    elif name == "queue":
        executable = next((LOCAL / "tools/redis").rglob("redis-server.exe"), None)
        if executable is None:
            raise RuntimeError("Pinned Redis Windows port not installed")
        data = LOCAL / "redis"
        data.mkdir(exist_ok=True)
        config_file = LOCAL / "redis.conf"
        redis_data = (
            "/cygdrive/" + data.drive[0].lower() + data.as_posix()[2:]
            if os.name == "nt"
            else str(data)
        )
        config_file.write_text(
            f"bind 127.0.0.1\nport 56379\nprotected-mode yes\nrequirepass {config['queue_password']}\ndir {redis_data}\nappendonly yes\nappendfsync everysec\nmaxmemory 64mb\nmaxmemory-policy noeviction\n",
            encoding="utf-8",
        )
        (LOCAL / "redis-container.conf").write_text(
            config_file.read_text(encoding="utf-8")
            .replace(redis_data, "/data")
            .replace("bind 127.0.0.1", "bind 0.0.0.0"),
            encoding="utf-8",
        )
        command = [str(executable), ".local/redis.conf"]
    elif name == "api":
        command = [
            sys.executable,
            "-m",
            "uvicorn",
            "services.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--no-access-log",
        ]
    elif name == "web":
        node = shutil.which("node")
        if not node:
            raise RuntimeError("Node runtime required")
        command = [
            node,
            str(ROOT / "node_modules/next/dist/bin/next"),
            "start",
            str(ROOT / "apps/web"),
            "--hostname",
            "127.0.0.1",
            "--port",
            "3000",
        ]
    else:
        raise ValueError("Unknown service")
    with (LOCAL / f"{name}.log").open("ab") as stream:
        child = subprocess.Popen(
            command,
            cwd=ROOT,
            env=env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    state[name] = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
    STATE.write_text(json.dumps(state), encoding="utf-8")
    time.sleep(1)
    if child.poll() is not None:
        raise RuntimeError(f"{name} failed; inspect private .local/{name}.log")
    print(f"{name} started privately; logs/config/data remain ignored")


def stop(name):
    state = load()
    entry = state.get(name)
    process = tracked(entry) if entry else None
    if process:
        if name == "queue":
            from canceros.jobs import queue_for
            from canceros.settings import Settings

            queue_for(Settings()).shutdown(save=True)
        else:
            process.terminate()
        try:
            process.wait(10)
        except psutil.TimeoutExpired:
            raise RuntimeError("Tracked service did not stop; no broad process kill performed")
    state.pop(name, None)
    STATE.write_text(json.dumps(state), encoding="utf-8")
    print(f"{name} stopped if tracked; data retained")


if __name__ == "__main__":
    (stop if sys.argv[1] == "stop" else start)(sys.argv[2])
