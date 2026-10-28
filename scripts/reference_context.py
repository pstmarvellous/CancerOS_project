"""Refresh original maps and write a task-local, auditable reading record."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAP = ROOT / "docs/Agent_knowledge_map/Knowlage_map_1"
ACA = ROOT / "docs/Agent_knowledge_map/Knowlage_map_2"
REF = (
    ROOT
    / "docs/Agent_knowledge_map/CancerOS_Repository_and_Scientific_Knowledge_Maps/reference-maps"
)


def refresh(task, terms, sections):
    graph = json.loads((CAP / "canceros-knowledge-graph.json").read_text(encoding="utf-8"))
    academic = json.loads((ACA / "knowledge-map.json").read_text(encoding="utf-8"))
    matches = [
        n for n in graph["nodes"] if any(t.casefold() in json.dumps(n).casefold() for t in terms)
    ]
    ids = {n["id"] for n in matches}
    edges = [e for e in graph["edges"] if e["from_id"] in ids or e["to_id"] in ids]
    behaviors = [
        n
        for n in academic["nodes"]
        if n["type"] == "behavior" and any(t.casefold() in json.dumps(n).casefold() for t in terms)
    ]
    logs = []
    for term in terms:
        for script in (
            CAP / "query_map.py",
            ACA / "query_academic_map.py",
            REF / "shared/query_references.py",
        ):
            cmd = [sys.executable, "-X", "utf8", str(script), term]
            result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            logs.append(
                {
                    "script": script.relative_to(ROOT).as_posix(),
                    "query": term,
                    "returncode": result.returncode,
                    "output": result.stdout,
                    "error": result.stderr,
                }
            )
    directory = ROOT / "docs/engineering/reference-reviews"
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "task": task,
        "queries": logs,
        "capability_node_ids": sorted(ids),
        "academic_behavior_ids": [n["id"] for n in behaviors],
        "edges": edges,
        "mapped_source_ids": sorted(
            {
                s
                for n in behaviors
                for k in ("academic_sources", "repository_references", "paper_references")
                for s in n.get(k, [])
            }
        ),
        "source_sections_inspected": sections,
    }
    (directory / f"{task}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    note = f"""# {task} reference context

Scope: assigned implementation task; specialist self-review through architecture,
data-integrity/security and verification perspectives; no independent clinical review.

Queries executed: {", ".join(terms)} against capability, academic and repository/scientific maps.
Exact commands, output, IDs and incoming/outgoing dependency/guard/verification edges:
[{task}.json]({task}.json). Unmatched queries are gaps, not successful source reviews.

Original specification sections inspected: {sections}.
Agent guidance: COS-000 sections 3–8/11; repository instructions sections 2–8;
COS-REF-001 sections 2–3/15–23; COS-HACK-001 sections 2–3/9/11/17.

## Source Learning Record and Three-Source Decision Note

Map source IDs are retrieved pointers only. Academic text, upstream interfaces and
empirical papers are NOT claimed read or reproduced by this refresh. Append actual
source learning, pinned interface inspection and empirical scope below before
enabling consequential scientific or security behavior. Medical reading exemptions
must be justified for the actual task; this refresh grants no exemption.
Missing academic/repository/empirical categories remain unverified for future domain
enablement. No weights, datasets or upstream code are adopted by a lookup.

Decision: preserve scoped specifications and keep unsupported capabilities disabled.
Verification: task-specific evidence and ledger, not map
existence. Failure fallback: disable affected domain/provider capability. Map drift
is recorded separately; original maps are unchanged.

## Hackathon Compliance Impact

Applies to preservation, source privacy and truthful contribution records. No external
model request is authorized by this task record. Models/rules/access remain unverified.
Architecture is preserved; refer to the task ledger for changed files and actual checks.
"""
    (directory / f"{task}.md").write_text(note, encoding="utf-8")
    print(
        f"{task}: {len(ids)} capability nodes, {len(behaviors)} academic behaviors, {len(edges)} adjacent edges; query results saved"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task")
    parser.add_argument("terms", nargs="+")
    parser.add_argument("--sections", required=True)
    args = parser.parse_args()
    refresh(args.task, args.terms, args.sections)
