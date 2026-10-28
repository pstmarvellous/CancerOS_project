"""Upgrade only an explicitly named disposable PostgreSQL test database."""

import os
import subprocess
import sys

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(".env").get("TEST_DATABASE_URL")
if not url or "disposable" not in (make_url(url).database or ""):
    raise SystemExit("Explicit disposable TEST_DATABASE_URL required")
env = {**os.environ, "DATABASE_URL": url}
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env, check=True)
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env, check=True)
print("PASS disposable PostgreSQL migrations and repeated upgrade; no reset/drop performed")
