"""Prove locked installation in a separate Python environment and clean Node tree."""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
environment = ROOT / ".local/locked-install-check"
assert environment.resolve().is_relative_to(ROOT.resolve())
records = []
commands = [
    (
        ["uv", "sync", "--locked", "--no-editable"],
        {**os.environ, "UV_PROJECT_ENVIRONMENT": str(environment)},
    ),
    (["npm.cmd" if os.name == "nt" else "npm", "ci"], os.environ.copy()),
]
for command, env in commands:
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    records.append(
        {
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    )
    if result.returncode:
        break
python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if all(r["exit_code"] == 0 for r in records):
    result = subprocess.run(
        [
            str(python),
            "-c",
            'import canceros; from canceros.api import create_app; from canceros.settings import Settings; assert create_app(Settings(mode="test",_env_file=None)).openapi()["openapi"]=="3.1.1"; print("PASS installed wheel import outside source working directory")',
        ],
        cwd=ROOT / ".local",
        capture_output=True,
        text=True,
    )
    records.append(
        {
            "command": ["isolated installed Python", "import outside source directory"],
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    )
record = {
    "result": "passed" if all(r["exit_code"] == 0 for r in records) else "failed",
    "scope": "Clean locked installation; isolated noneditable Python wheel, npm ci",
    "checks": records,
}
(ROOT / "docs/engineering/evidence/locked-install.json").write_text(
    json.dumps(record, indent=2) + "\n", encoding="utf-8"
)
for result in records:
    print(("PASS " if result["exit_code"] == 0 else "FAIL ") + " ".join(result["command"]))
if record["result"] == "failed":
    print(records[-1]["stdout"], records[-1]["stderr"])
    raise SystemExit(1)
