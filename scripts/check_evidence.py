"""Validate evidence examples and executed check records; fail on known failed records."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
directory = ROOT / "docs/engineering"
schema = json.loads((directory / "evidence-record.schema.json").read_text(encoding="utf-8"))
example = json.loads((directory / "evidence-record.example.json").read_text(encoding="utf-8"))
validator = Draft202012Validator(schema)
validator.validate(example)
invalid = {**example, "result": "pretend-passed"}
assert list(validator.iter_errors(invalid)), "Invalid evidence result accepted"
for path in (directory / "evidence").glob("*.json"):
    if path.name == "governance.json":
        # The active fail-fast governance runner writes this aggregate after these checks.
        continue
    record = json.loads(path.read_text(encoding="utf-8"))
    if "checks" in record:
        assert record.get("result") == "passed", f"Failed/incomplete recorded checks: {path.name}"
        assert record["checks"], path.name
        if all(isinstance(x, dict) for x in record["checks"]):
            assert all(x.get("exit_code") == 0 for x in record["checks"]), path.name
        else:
            assert path.name == "final-startup.json" and all(
                isinstance(x, str) for x in record["checks"]
            ), path.name
print(
    "PASS evidence schema/example and recorded check exit codes; future/skipped science is not passed"
)
