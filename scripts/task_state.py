"""Record truthful sequential task progress and evidence; no automatic success."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/engineering/task-ledger.json"


def transition(identity, status, evidence=None, files=None, blocked=None, verification_scope=None):
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    task = next(t for t in data["tasks"] if t["id"] == identity)
    if task["status"] != status:
        task["status_history"].append(status)
    task["status"] = status
    context_file = ROOT / f"docs/engineering/reference-reviews/{identity}.json"
    if context_file.exists():
        context = json.loads(context_file.read_text(encoding="utf-8"))
        task["map_queries"] = context["queries"]
        task["graph_neighbors"] = context["edges"]
        task["sections_read"] = context["source_sections_inspected"]
    task["actual_touched_files"] = sorted(set(task["actual_touched_files"] + (files or [])))
    if evidence:
        task["checks_evidence"].append(evidence)
    task["blocked_on"] = blocked or []
    if verification_scope:
        task["verification_scope"] = verification_scope
    task["next_action"] = (
        "Proceed to next authorized prompt"
        if status == "verified"
        else "Complete remaining acceptance checks; continue independent authorized foundation work"
    )
    if status == "verified":
        assert task["checks_evidence"], "Cannot verify without evidence"
        for reference in (evidence or "").split(";"):
            reference = reference.strip()
            assert (ROOT / reference).is_file(), f"Evidence file missing: {reference}"
            if reference.endswith(".json"):
                record = json.loads((ROOT / reference).read_text(encoding="utf-8"))
                assert record.get("result") != "failed", f"Failed evidence: {reference}"
        task["completion_timestamp"] = datetime.now(timezone.utc).isoformat()
    else:
        task.pop("completion_timestamp", None)
    LEDGER.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    trace_path = ROOT / "docs/engineering/requirements-traceability.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    for row in trace["rows"]:
        if row["requirement_id"] == "TASK-" + identity:
            row["status"] = status
            row["evidence"] = task["checks_evidence"]
    trace_path.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    from check_governance import run

    run(write_csv=True)
    checkpoint = ROOT / "docs/engineering/checkpoint.md"
    checkpoint.write_text(
        f"# Execution checkpoint\n\n{identity}: {status}.\nEvidence: {evidence or 'see ledger'}.\nNext: {task['next_action']}.\nRead task ledger, both maps, relevant specifications and hackathon guide before resuming.\nUser authorizes sequential execution of the current phase without routine approval.\n",
        encoding="utf-8",
    )
    print(identity, status)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("task")
    parser.add_argument("status")
    parser.add_argument("--evidence")
    parser.add_argument("--files", nargs="*")
    parser.add_argument("--blocked", nargs="*")
    parser.add_argument(
        "--verification-scope",
        choices=[
            "fixture_verified_real_data_review_pending",
            "real_data_verified",
            "review_pending",
        ],
    )
    args = parser.parse_args()
    transition(
        args.task, args.status, args.evidence, args.files, args.blocked, args.verification_scope
    )
