"""Regenerate in memory/on disk and reject unexplained generated client drift."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, "scripts/generate_contracts.py", "--check"], cwd=ROOT, check=True)
paths = [
    ROOT / f"packages/contracts/generated/{name}.ts" for name in ("api", "foundation", "clinical")
]
before = {p: p.read_bytes() for p in paths}
try:
    subprocess.run(
        ["npm.cmd" if os.name == "nt" else "npm", "run", "contracts:types"], cwd=ROOT, check=True
    )
    assert all(p.read_bytes() == before[p] for p in paths), (
        "Generated TypeScript drift; regenerate/review contracts"
    )
finally:
    for p, content in before.items():
        p.write_bytes(content)
print("PASS runtime OpenAPI, foundation schemas and generated TypeScript drift check")
