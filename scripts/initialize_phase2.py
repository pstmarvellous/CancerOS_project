"""Extend existing governance records without changing original requirement sources."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "docs/engineering"


def initialize():
    prompt = (ROOT / "docs/agent_prompt/CancerOS_Phase_2_Prompt_Series.md").read_text(
        encoding="utf-8"
    )
    ledger = json.loads((E / "task-ledger.json").read_text(encoding="utf-8"))
    trace = json.loads((E / "requirements-traceability.json").read_text(encoding="utf-8"))
    template = next(r for r in trace["rows"] if r["requirement_id"] == "TASK-COS-015")
    for match in re.finditer(r"### (COS-\d+) — ([^\n]+)\n(.*?)(?=\n### |\Z)", prompt, re.S):
        identity, title, body = match.groups()
        if any(t["id"] == identity for t in ledger["tasks"]):
            continue
        dependencies = re.search(r"Prerequisites: ([^;\n]+)", body).group(1)
        ids = re.findall(r"COS-\d+", dependencies)
        scope = "Phase 2 assigned prompt; synthetic fixture verification distinct from real-data and qualified review gates"
        ledger["tasks"].append(
            {
                "id": identity,
                "purpose": title,
                "dependency_ids": ids,
                "requirement_links": ["TASK-" + identity],
                "allowed_scope": scope,
                "status": "planned",
                "status_history": ["planned"],
                "owner_responsibility": "Primary agent; specialist self-review only",
                "actual_touched_files": [],
                "decisions": [],
                "checks_evidence": [],
                "known_failures": [],
                "blocked_on": [],
                "next_action": "Execute in Phase 2 order; COS-030 optional and gated",
            }
        )
        trace["rows"].append(
            {
                **template,
                "requirement_id": "TASK-" + identity,
                "source_document": "PHASE2-PROMPTS",
                "source_locator": identity,
                "requirement": title,
                "phase": "2",
                "priority": "P1" if identity == "COS-030" else "P0",
                "implementation_task": identity,
                "owning_module": "Phase 2 domain modules",
                "acceptance_criterion": f"All acceptance checks in {identity}; distinguish fixture and real-data evidence",
                "planned_test_id": identity + "-ACCEPTANCE",
                "planned_test_type": "unit/integration/scientific review as applicable",
                "status": "planned",
                "evidence": [],
                "reference_review_record": "docs/engineering/phase-2-execution.md",
                "reference_empty_reason": "Task-specific map refresh pending before implementation",
            }
        )
    (E / "task-ledger.json").write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    (E / "requirements-traceability.json").write_text(
        json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    initialize()
