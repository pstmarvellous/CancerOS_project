"""E2E-003: authorized synthetic smoke-test input fixture (unsigned draft).

Created for owner review under COS-E2E-003. Contains NO patient data, NO
identifiers, NO clinical records, NO note text, NO dataset content. All UUIDs
are freshly generated and unrelated to any stored record; the single
measurement is an explicitly artificial constant. This file is the proposed
test input described in the owner authorization draft; it becomes the
approved input ONLY after the owner signs the authorization document.
"""

import hashlib
import json
from pathlib import Path
from uuid import uuid4

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main():
    from canceros.provider_contracts import ProviderInput
    from canceros.provider_gateway import MetaAdapter, canonical_bytes

    measurement_id = uuid4()
    evidence_id = uuid4()
    context = ProviderInput(
        purpose="research_summary",
        input_snapshot_hash="0" * 64,
        measurements=[
            {
                "reference_id": measurement_id,
                "metric_code": "synthetic_region_volume",
                "value": "216",
                "unit": "mm3",
                "provenance": "SYNTHETIC_GENERATED",
            }
        ],
        missingness=["laboratory_values_not_supplied"],
        evidence_ids=[evidence_id],
    )
    snapshot = hashlib.sha256(canonical_bytes(context.model_dump(mode="json"))).hexdigest()
    context = context.model_copy(update={"input_snapshot_hash": snapshot})
    wire = MetaAdapter.request(context, "muse-spark-1.3")
    record = {
        "fixture": "COS-META-SMOKE-2026-11-04-v1/synthetic-input/1",
        "status": "UNSIGNED_DRAFT_FOR_OWNER_REVIEW",
        "created_for_policy": "COS-META-SMOKE-2026-11-04-v1",
        "provider_input": context.model_dump(mode="json"),
        "input_bytes": len(canonical_bytes(context.model_dump(mode="json"))),
        "input_sha256": hashlib.sha256(
            canonical_bytes(context.model_dump(mode="json"))
        ).hexdigest(),
        "wire_bytes": len(wire),
        "wire_sha256": hashlib.sha256(wire).hexdigest(),
        "content_declaration": "One artificial measurement "
        "(synthetic_region_volume = 216 mm3, SYNTHETIC_GENERATED), one "
        "missingness code (laboratory_values_not_supplied), two freshly "
        "generated UUID references. No MRI, no clinical records, no patient "
        "identifiers, no note text, no dataset content.",
    }
    out = ROOT / ".local" / "e2e-003-synthetic-input.json"
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print("wrote %s" % out)
    print("input_sha256=%s" % record["input_sha256"])
    print("wire_sha256=%s" % record["wire_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
