"""Check scoped governance artifacts without claiming application verification."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
files = [
    ROOT / "AGENTS.md",
    ROOT / "IMPLEMENTATION_GUIDE.md",
    *ROOT.glob("docs/engineering/**/*.md"),
]
for path in files:
    content = path.read_text(encoding="utf-8")
    assert content.strip(), f"Empty {path}"
    for target in re.findall(r"\]\(([^)]+)\)", content):
        if "://" not in target and not target.startswith("#"):
            assert (path.parent / target.split("#")[0]).exists(), f"Broken link {path}: {target}"
for path in ROOT.glob("docs/engineering/**/*.json"):
    json.loads(path.read_text(encoding="utf-8"))
for name in (
    "authority-and-scope",
    "reference-consultation-policy",
    "specification-audit",
    "reference-map-integrity",
    "traceability-maintenance",
    "coding-standards",
    "module-boundaries",
    "data-and-ai-safety-rules",
    "checkpoint-template",
    "change-control",
):
    assert (ROOT / f"docs/engineering/{name}.md").is_file(), name
invariants = json.loads(
    (ROOT / "docs/engineering/safety-invariants.json").read_text(encoding="utf-8")
)["invariants"]
assert {x["id"] for x in invariants} == {f"SAFE-{i:02}" for i in range(1, 26)}
decisions = json.loads(
    (ROOT / "docs/engineering/decision-register.json").read_text(encoding="utf-8")
)["decisions"]
assert {f"{kind}{i:02}" for kind in "ACD" for i in range(1, 7)} <= {x["id"] for x in decisions}
print(
    f"PASS {len(files)} governance Markdown files/links, readable JSON, 25 SAFE controls and 18 audit findings; no clinical/runtime verification implied"
)
