"""Check original map packages without duplicating or modifying them."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/Agent_knowledge_map"
FILES = [
    BASE / "Knowlage_map_1/canceros-knowledge-graph.json",
    BASE / "Knowlage_map_2/knowledge-map.json",
    BASE / "Knowlage_map_2/academic-source-register.json",
    BASE / "Knowlage_map_2/behavior-index.json",
]
for path in FILES:
    json.loads(path.read_text(encoding="utf-8"))
reference = BASE / "CancerOS_Repository_and_Scientific_Knowledge_Maps/reference-maps"


def load(name):
    return json.loads((reference / name).read_text(encoding="utf-8"))


repositories = load("repository-map/behavior-to-repository.json")
scientific = load("scientific-map/behavior-to-evidence.json")
assert {b["id"] for b in repositories} == {b["id"] for b in scientific}, "Behavior map mismatch"
registered_repos = {x["id"] for x in load("repository-map/repository-register.json")}
registered_academic = {x["id"] for x in load("scientific-map/academic-source-register.json")}
registered_papers = {x["id"] for x in load("scientific-map/research-paper-register.json")}
for behavior in scientific:
    assert set(behavior["academic_sources"]) <= registered_academic, behavior["id"]
    assert set(behavior["papers"]) <= registered_papers, behavior["id"]
    assert set(behavior["implementations"]) <= registered_repos, behavior["id"]
for behavior in repositories:
    assert set(behavior["repositories"]) <= registered_repos, behavior["id"]
print(
    f"PASS {len(scientific)} matched reference behavior IDs and all local source/repository/paper references"
)
scripts = [
    BASE / "Knowlage_map_1/query_map.py",
    BASE / "Knowlage_map_2/query_academic_map.py",
    BASE
    / "CancerOS_Repository_and_Scientific_Knowledge_Maps/reference-maps/shared/query_references.py",
]
for script in scripts:
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(script), "provenance"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0 and result.stdout.strip(), f"Map query failed: {script.name}"
    assert "No matching" not in result.stdout and "No mapped" not in result.stdout
    print(f"PASS original map lookup: {script.relative_to(ROOT).as_posix()}")
print(
    "PASS readable original maps/registry/index; external URLs and source contents not verified by this check"
)
