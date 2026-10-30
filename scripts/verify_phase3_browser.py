"""Require an explicitly disposable fixture and real Chromium/WebGL assertions."""

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

root = Path(__file__).resolve().parents[1]
bundle_path = root / ".local/phase3-browser-fixture.json"
assert bundle_path.is_file(), "Start phase3_browser_fixture.py; missing fixture is not a pass"
bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
assert bundle["api_url"] == "http://127.0.0.1:8000"
try:
    with urlopen(bundle["api_url"] + "/health/live", timeout=3) as response:
        assert response.status == 200
    result = subprocess.run(
        [
            "npx.cmd",
            "playwright",
            "test",
            "tests/browser/phase3-timeline.spec.ts",
            "--reporter=line",
        ],
        cwd=root,
        check=False,
    )
finally:
    # Playwright failure context can include password input values even with traces
    # disabled. Scrub only this fixture's text artifacts before returning diagnostics.
    for directory in (root / "test-results").glob("phase3-timeline*"):
        for artifact in directory.rglob("*"):
            if artifact.is_file() and artifact.suffix in (".md", ".json", ".txt", ".log"):
                value = artifact.read_text(encoding="utf-8")
                artifact.write_text(
                    re.sub(
                        r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[REDACTED]", value
                    ),
                    encoding="utf-8",
                )
    subprocess.run(
        [sys.executable, "scripts/phase3_browser_fixture.py", "--stop"], cwd=root, check=True
    )
raise SystemExit(result.returncode)
