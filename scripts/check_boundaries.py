"""Guard current Python boundaries and centralized provenance definitions."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src/canceros").glob("*.py"):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith(("apps", "services")), str(path)
        if isinstance(node, ast.ClassDef) and node.name == "Provenance":
            assert path.name == "contracts.py", "Duplicate provenance owner"
web = "\n".join(
    p.read_text(encoding="utf-8")
    for p in (ROOT / "apps/web").rglob("*.tsx")
    if ".next" not in p.parts and "node_modules" not in p.parts
)
for forbidden in (
    "process.env.MODEL_API_KEY",
    "process.env.DATABASE_URL",
    "localStorage.setItem",
    "sessionStorage.setItem",
):
    assert forbidden not in web, f"Frontend boundary: {forbidden}"
print(
    "PASS current import/contract/frontend boundaries; future domain boundaries need additional behavior tests"
)
