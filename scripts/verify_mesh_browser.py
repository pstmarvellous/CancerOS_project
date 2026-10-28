"""Mandatory browser check: missing private fixture is a failure, never a skip."""

import json
import subprocess
from pathlib import Path
from urllib.request import urlopen

root = Path(__file__).resolve().parents[1]
bundle_path = root / ".local/mesh-browser-fixture.json"
assert bundle_path.is_file(), "Start the explicitly disposable mesh_browser_fixture.py first"
bundle = json.loads(bundle_path.read_text())
assert bundle["api_url"] == "http://127.0.0.1:8000"
with urlopen(bundle["api_url"] + "/health/live", timeout=3) as response:
    assert response.status == 200
result = subprocess.run(
    ["npx.cmd", "playwright", "test", "tests/browser/mesh-preview.spec.ts", "--reporter=line"],
    cwd=root,
    check=False,
)
raise SystemExit(result.returncode)
