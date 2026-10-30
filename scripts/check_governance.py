"""Validate real sources, traceability, map references, ledger and local links."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "docs/engineering"
STATES = {"not_started", "planned", "in_progress", "blocked", "implemented_unverified", "verified"}


def validate_rows(rows, documents):
    seen = set()
    for row in rows:
        for key in (
            "requirement_id",
            "source_document",
            "source_locator",
            "requirement",
            "domain",
            "priority",
            "phase",
            "authority_reference",
            "applicability",
            "implementation_task",
            "owning_module",
            "acceptance_criterion",
            "planned_test_id",
            "planned_test_type",
            "status",
            "reference_review_record",
            "reference_empty_reason",
        ):
            assert row.get(key), f"Missing {key}"
        identity = row["requirement_id"]
        assert identity not in seen, f"Duplicate requirement {identity}"
        seen.add(identity)
        assert row["source_document"] in documents | {
            "PHASE1-PROMPTS",
            "PHASE2-PROMPTS",
            "PHASE3-PROMPTS",
        }, identity
        assert row["status"] in STATES, identity
        assert row["status"] != "verified" or row["evidence"], f"No evidence: {identity}"
        assert (ROOT / row["reference_review_record"]).is_file(), identity


def validate_ledger(tasks):
    index = {t["id"]: t for t in tasks}
    assert len(index) == len(tasks), "Duplicate task"
    visited = set()

    def visit(identity, stack):
        assert identity in index, f"Missing dependency {identity}"
        assert identity not in stack, "Dependency cycle"
        if identity in visited:
            return
        for dependency in index[identity]["dependency_ids"]:
            visit(dependency, stack | {identity})
        visited.add(identity)

    allowed = {
        "planned": {"in_progress"},
        "in_progress": {"blocked", "implemented_unverified", "verified"},
        "blocked": {"in_progress"},
        "implemented_unverified": {"in_progress", "verified", "blocked"},
        "verified": {"in_progress"},
    }
    for task in tasks:
        visit(task["id"], set())
        assert task["status"] in STATES - {"not_started"}
        assert task["status"] != "verified" or task["checks_evidence"], "Verified without evidence"
        for old, new in zip(task.get("status_history", []), task.get("status_history", [])[1:]):
            assert new in allowed.get(old, set()), f"Invalid transition {old}->{new}"


def run(write_csv=False, self_test=False):
    manifest = json.loads(
        (ROOT / "docs/specifications/source-manifest.json").read_text(encoding="utf-8")
    )
    documents = {d["document_id"] for d in manifest["documents"]}
    for doc in manifest["documents"]:
        assert hashlib.sha256((ROOT / doc["path"]).read_bytes()).hexdigest() == doc["sha256"], doc[
            "path"
        ]
    trace = json.loads((E / "requirements-traceability.json").read_text(encoding="utf-8"))
    rows = trace["rows"]
    validate_rows(rows, documents)
    csv_path = E / "requirements-traceability.csv"
    if write_csv:
        with csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                        for k, v in row.items()
                    }
                )
    else:
        with csv_path.open(encoding="utf-8", newline="") as stream:
            data = list(csv.DictReader(stream))
        assert [r["requirement_id"] for r in data] == [r["requirement_id"] for r in rows], (
            "CSV drift"
        )
        for actual, row in zip(data, rows):
            for k, v in row.items():
                expected = (
                    json.dumps(v, ensure_ascii=False)
                    if isinstance(v, (list, dict))
                    else ("" if v is None else str(v))
                )
                assert actual[k] == expected, f"CSV drift {row['requirement_id']}/{k}"
    ledger = E / "task-ledger.json"
    if ledger.exists():
        validate_ledger(json.loads(ledger.read_text(encoding="utf-8"))["tasks"])
    if self_test:
        for invalid in (rows + [rows[0]], [{**rows[0], "owning_module": ""}]):
            try:
                validate_rows(invalid, documents)
            except AssertionError:
                pass
            else:
                raise AssertionError("Negative traceability fixture accepted")
        base = [{"id": "one", "dependency_ids": [], "status": "planned"}]
        for invalid in (
            [{**base[0], "dependency_ids": ["missing"]}],
            [{**base[0], "dependency_ids": ["one"]}],
            [{**base[0], "status_history": ["planned", "verified"]}],
        ):
            try:
                validate_ledger(invalid)
            except AssertionError:
                pass
            else:
                raise AssertionError("Negative ledger fixture accepted")
    print(
        f"PASS source hashes, {len(rows)} trace rows, CSV synchronization, ledger if present; negative fixtures={self_test}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-csv", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    run(args.write_csv, args.self_test)
