"""Own isolated loopback PostgreSQL cluster; never reset existing services/databases."""

import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
CLUSTER = LOCAL / "postgres"
BIN = Path(os.environ.get("POSTGRES_BIN", "C:/Program Files/PostgreSQL/15/bin"))
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def call(arguments):
    with (LOCAL / "postgres-bootstrap.log").open("a", encoding="utf-8") as log:
        result = subprocess.run(arguments, stdout=log, stderr=log, text=True, creationflags=FLAGS)
    if result.returncode:
        # This command does not contain connection URLs or passwords.
        raise RuntimeError(
            "Local PostgreSQL command failed; inspect private postgres-bootstrap.log"
        )


def start():
    LOCAL.mkdir(exist_ok=True)
    private = LOCAL / "development.json"
    if private.exists():
        config = json.loads(private.read_text())
    else:
        config = {
            k: secrets.token_hex(24)
            for k in (
                "database_password",
                "storage_access_key",
                "storage_secret_key",
                "queue_password",
                "monitor_token",
            )
        }
        private.write_text(json.dumps(config), encoding="utf-8")
        if os.name != "nt":
            private.chmod(0o600)
    if not (CLUSTER / "PG_VERSION").exists():
        password_file = LOCAL / "postgres-init-password"
        password_file.write_text(config["database_password"], encoding="utf-8")
        try:
            call(
                [
                    str(BIN / "initdb.exe"),
                    "-D",
                    str(CLUSTER),
                    "-U",
                    "canceros",
                    "-A",
                    "scram-sha-256",
                    "--pwfile",
                    str(password_file),
                    "--encoding=UTF8",
                    "--locale=C",
                ]
            )
        finally:
            password_file.unlink(missing_ok=True)
        with (CLUSTER / "postgresql.conf").open("a") as stream:
            stream.write(
                "\nlisten_addresses='127.0.0.1'\nport=55432\nshared_buffers='64MB'\nmax_connections=20\n"
            )
    status = subprocess.run(
        [str(BIN / "pg_ctl.exe"), "-D", str(CLUSTER), "status"],
        capture_output=True,
        creationflags=FLAGS,
    )
    if status.returncode:
        call(
            [
                str(BIN / "pg_ctl.exe"),
                "-D",
                str(CLUSTER),
                "-l",
                str(LOCAL / "postgres.log"),
                "-w",
                "start",
            ]
        )
    import psycopg
    from psycopg import sql

    with psycopg.connect(
        host="127.0.0.1",
        port=55432,
        user="canceros",
        password=config["database_password"],
        dbname="postgres",
        autocommit=True,
    ) as connection:
        for name in ("canceros_dev", "canceros_disposable_test"):
            if (
                connection.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,)).fetchone()
                is None
            ):
                connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    env = ROOT / ".env"
    if not env.exists():
        values = {
            "MODE": "development",
            "DATABASE_URL": f"postgresql+psycopg://canceros:{config['database_password']}@127.0.0.1:55432/canceros_dev",
            "TEST_DATABASE_URL": f"postgresql+psycopg://canceros:{config['database_password']}@127.0.0.1:55432/canceros_disposable_test",
            "QUEUE_URL": f"redis://:{config['queue_password']}@127.0.0.1:56379/0",
            "STORAGE_ENDPOINT": "http://127.0.0.1:58333",
            "STORAGE_BUCKET": "canceros-private",
            "STORAGE_ACCESS_KEY": config["storage_access_key"],
            "STORAGE_SECRET_KEY": config["storage_secret_key"],
            "MONITOR_TOKEN": config["monitor_token"],
            "EXTERNAL_INFERENCE_ENABLED": "false",
        }
        env.write_text("\n".join(f"{k}={v}" for k, v in values.items()) + "\n", encoding="utf-8")
        if os.name != "nt":
            env.chmod(0o600)
    print(
        "PASS isolated PostgreSQL ready on loopback:55432; private credentials saved without display"
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        assert CLUSTER.resolve().is_relative_to(ROOT.resolve())
        call([str(BIN / "pg_ctl.exe"), "-D", str(CLUSTER), "-m", "fast", "-w", "stop"])
        print("Stopped only CancerOS isolated cluster; data retained")
    else:
        start()
