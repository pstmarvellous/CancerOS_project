"""E2E-003: authorized synthetic-only live-test planner (no network, no secrets).

Reads the committed .env for key NAMES ONLY (never values), builds a minimal
synthetic ProviderInput, computes the exact canonical input bytes, snapshot
hash and wire body the gateway would send, and prints the bounded test plan
for owner authorization. Exits non-zero while any D04 approval item is
unresolved, so it can never be mistaken for an authorized live call.
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def env_names(path):
    names = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            names.append(line.split("=", 1)[0])
    return names


def main():
    from canceros.provider_contracts import ProviderInput
    from canceros.provider_gateway import MetaAdapter, canonical_bytes

    names = env_names(ROOT / ".env")
    measurement_id = uuid4()
    evidence_id = uuid4()
    snapshot = hashlib.sha256(canonical_bytes({"synthetic": "baseline"})).hexdigest()
    context = ProviderInput(
        purpose="research_summary",
        input_snapshot_hash=snapshot,
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
    snapshot = context.input_snapshot_hash
    wire = MetaAdapter.request(context, "muse-spark-1.3")
    plan = {
        "scope": "synthetic-only connectivity + structured research interpretation",
        "model": "muse-spark-1.3",
        "endpoint": "https://api.meta.ai/v1/responses",
        "env_keys_present": [n for n in ("MODEL_API_KEY", "EXTERNAL_INFERENCE_ENABLED") if n in names],
        "env_keys_absent": [
            n
            for n in ("EXPORT_POLICY_PATH", "MODEL_ACCOUNT_ID", "MODEL_REGION")
            if n not in names
        ],
        "transmitted_input_bytes": len(canonical_bytes(context.model_dump(mode="json"))),
        "transmitted_wire_bytes": len(wire),
        "input_snapshot_hash": snapshot,
        "wire_sha256": hashlib.sha256(wire).hexdigest(),
        "measurements": [
            {
                "metric_code": "synthetic_region_volume",
                "value": "216",
                "unit": "mm3",
                "provenance": "SYNTHETIC_GENERATED",
            }
        ],
        "missingness": ["laboratory_values_not_supplied"],
        "note": "No patient data, no identifiers, no note text. UUIDs above are "
        "freshly generated synthetic references, unrelated to any stored record.",
        "approval_required_from": "project/AI owner (D04)",
        "approval_items": [
            "genuine Meta account/model entitlement for muse-spark-1.3",
            "minimized synthetic payload rights for this exact input hash",
            "retention/training/onward-processing terms for the account",
            "account ID + region binding for the export/2 policy",
        ],
        "live_call_authorized": False,
    }
    print(json.dumps(plan, indent=2))
    return 3


if __name__ == "__main__":
    sys.exit(main())
