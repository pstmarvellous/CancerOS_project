"""Check public/browser assets for known local secrets without printing values."""

import argparse
import json
import re
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--evidence-dir", default="docs/engineering/testing/rec00-reverify")
options = parser.parse_args()
directory = (ROOT / options.evidence_dir).resolve()
directory.relative_to(ROOT)
OUTPUT = directory / "artifact-scan.json"
roots = [
    ROOT / "apps/web/public",
    ROOT / "apps/web/.next/static",
    OUTPUT.parent,
]
secrets = []
sources = [dict(dotenv_values(ROOT / ".env"))]
for relative in (".local/development.json", ".local/product-browser-fixture.json"):
    path = ROOT / relative
    if path.exists():
        sources.append(json.loads(path.read_text(encoding="utf-8")))
for source in sources:
    for key, value in source.items():
        if isinstance(value, str) and len(value) > 15 and any(
            term in key.lower()
            for term in ("key", "password", "secret", "token", "database_url", "queue_url")
        ):
            secrets.append(value.encode())
assert secrets, "Configure local development credentials before running this check"
files = [p for root in roots if root.exists() for p in root.rglob("*") if p.is_file()]
failures = []
for path in files:
    content = path.read_bytes()
    if any(secret in content for secret in secrets) or re.search(
        rb"-----BEGIN (?:RSA )?PRIVATE KEY-----", content
    ):
        failures.append(path.relative_to(ROOT).as_posix())
payload = {
    "scope": "Known local configured secrets and private-key markers in public assets, browser static output and fresh artificial browser evidence",
    "files_scanned": len(files),
    "failures": failures,
    "result": "FAIL" if failures else "PASS",
    "limitations": "Not a general patient-data classifier, historical Git scan, dependency audit or deployment review",
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
assert not failures, "Secret marker detected; inspect the affected artifact privately"
print(f"PASS {len(files)} public/browser/evidence artifacts; known-secret scan only")
