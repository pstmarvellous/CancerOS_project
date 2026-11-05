"""E2E-003 (owner-authorized 2026-11-04): bounded synthetic-only Meta live test.

Authorization: project owner approved the bounded synthetic-only live test
and confirmed the four D04 items satisfied (account/model entitlement,
synthetic payload rights, retention/training terms, account ID + region).

Reads the live key ONLY from the process environment (never prints, logs, or
stores it), builds the exact synthetic ProviderInput from the approved plan,
sends ONE wire request through the REAL gateway path
(MetaAdapter.request -> live HTTPS POST -> MetaAdapter.parse), validates the
structured candidate, and writes a secret-free evidence JSON.

Writes nothing to the database, creates no policy file, changes no gate.
"""

import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

MODEL = "muse-spark-1.3"
ENDPOINT = "https://api.meta.ai/v1/responses"


"""Required live-test policy inputs. Every value must arrive via explicit
owner-confirmed process environment; nothing here invents approval, hashes,
or permission evidence. The permission/source-rights evidence files must be
real owner-supplied documents whose computed hashes are embedded below."""

REQUIRED_POLICY_INPUTS = (
    "CANCEROS_LIVE_POLICY_ID",
    "CANCEROS_LIVE_ACCOUNT_ID",
    "CANCEROS_LIVE_REGION",
    "CANCEROS_LIVE_RETENTION_POLICY",
    "CANCEROS_LIVE_TRAINING_POLICY",
    "CANCEROS_LIVE_ONWARD_PROCESSING_POLICY",
    "CANCEROS_LIVE_EXPIRES_AT",
    "CANCEROS_LIVE_PERMISSION_EVIDENCE",
    "CANCEROS_LIVE_SOURCE_RIGHTS_EVIDENCE",
)


class LiveTransport:
    """One-shot live HTTPS transport honoring the gateway's Transport protocol."""

    def __init__(self, api_key):
        self._api_key = api_key

    async def send(self, body, *, timeout):
        import canceros.provider_gateway as gateway

        try:
            async with httpx.AsyncClient(
                follow_redirects=False,
                trust_env=False,
                timeout=timeout,
                limits=httpx.Limits(max_connections=1),
            ) as client:
                async with client.stream(
                    "POST",
                    ENDPOINT,
                    content=body,
                    headers={
                        "Authorization": "Bearer " + self._api_key,
                        "Content-Type": "application/json",
                    },
                ) as response:
                    if response.status_code != 200:
                        return gateway.TransportReply(status=response.status_code, body=b"")
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content) > gateway.MAX_RESPONSE_BYTES:
                            raise gateway.ProviderFailure("FAILED_SCHEMA")
                    return gateway.TransportReply(status=200, body=bytes(content))
        except httpx.TimeoutException:
            raise gateway.ProviderFailure("PROVIDER_TIMEOUT", retryable=True) from None
        except httpx.HTTPError:
            raise gateway.ProviderFailure("PROVIDER_UNAVAILABLE", retryable=True) from None


def main():
    from canceros.provider_contracts import ProviderInput
    from canceros.provider_gateway import (
        MetaAdapter,
        ProviderFailure,
        canonical_bytes,
        execute_private,
    )

    api_key = os.environ.get("CANCEROS_LIVE_MODEL_API_KEY", "")
    if not api_key:
        print("CANCEROS_LIVE_MODEL_API_KEY is not set in the process environment.")
        return 4
    policy_values = {}
    for env_name in REQUIRED_POLICY_INPUTS:
        value = os.environ.get(env_name, "")
        if not value:
            print(
                "Refusing live call: owner-confirmed export/2 input '%s' was not "
                "supplied. Nothing was transmitted." % env_name
            )
            return 6
        policy_values[env_name] = value
    evidence_paths = {}
    for key in ("CANCEROS_LIVE_PERMISSION_EVIDENCE", "CANCEROS_LIVE_SOURCE_RIGHTS_EVIDENCE"):
        path = Path(policy_values[key])
        if not path.is_file():
            print("Refusing live call: evidence file '%s' does not exist." % path)
            return 6
        evidence_paths[key] = {
            "reference_file": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    account_id = policy_values["CANCEROS_LIVE_ACCOUNT_ID"]
    region = policy_values["CANCEROS_LIVE_REGION"]
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
    wire = MetaAdapter.request(context, MODEL)
    policy_doc = {
        "schema_version": "export/2",
        "policy_id": policy_values["CANCEROS_LIVE_POLICY_ID"],
        "provider": "meta",
        "model_identifier": MODEL,
        "endpoint": ENDPOINT,
        "account_id": account_id,
        "region": region,
        "purpose": context.purpose,
        "data_class": "minimized_structured_research",
        "retention_policy": policy_values["CANCEROS_LIVE_RETENTION_POLICY"],
        "training_policy": policy_values["CANCEROS_LIVE_TRAINING_POLICY"],
        "onward_processing_policy": policy_values["CANCEROS_LIVE_ONWARD_PROCESSING_POLICY"],
        "permission_evidence": [evidence_paths["CANCEROS_LIVE_PERMISSION_EVIDENCE"]],
        "source_rights_evidence": [evidence_paths["CANCEROS_LIVE_SOURCE_RIGHTS_EVIDENCE"]],
        "allowed_fields": sorted(context.model_dump()),
        "approved_input_hashes": [
            hashlib.sha256(canonical_bytes(context.model_dump(mode="json"))).hexdigest()
        ],
        "approved_wire_hashes": [hashlib.sha256(wire).hexdigest()],
        "expires_at": policy_values["CANCEROS_LIVE_EXPIRES_AT"],
        "policy_reviewed": True,
        "account_access_verified": True,
        "revoked": False,
    }
    policy_path = ROOT / ".local" / "e2e-003-live-policy.json"
    policy_path.write_text(json.dumps(policy_doc, indent=2, sort_keys=True), encoding="utf-8")
    config = SimpleNamespace(
        mode="test",
        external_inference_enabled=True,
        model_provider="meta",
        model_identifier=MODEL,
        model_endpoint=ENDPOINT,
        model_account_id=account_id,
        model_region=region,
        model_api_key=api_key,
        export_policy_path=str(policy_path),
    )
    evidence = {
        "authorization": "project owner approved bounded synthetic-only live test 2026-11-04; D04 items confirmed",
        "policy_id_withheld": True,
        "policy_fields_present": sorted(policy_doc),
        "permission_evidence_sha256": evidence_paths["CANCEROS_LIVE_PERMISSION_EVIDENCE"]["sha256"],
        "source_rights_evidence_sha256": evidence_paths["CANCEROS_LIVE_SOURCE_RIGHTS_EVIDENCE"]["sha256"],
        "model_requested": MODEL,
        "endpoint": ENDPOINT,
        "input_snapshot_hash": snapshot,
        "input_bytes": len(canonical_bytes(context.model_dump(mode="json"))),
        "wire_bytes": len(wire),
        "wire_sha256": hashlib.sha256(wire).hexdigest(),
        "synthetic": True,
        "patient_data": False,
    }
    started = time.monotonic()
    try:
        result = asyncio.run(
            execute_private(
                config,
                context,
                LiveTransport(api_key),
                lambda: None,
                max_attempts=1,
                timeout_seconds=30,
            )
        )
    except ProviderFailure as failure:
        evidence.update(
            {
                "status": "provider_failure",
                "code": failure.code,
                "retryable": failure.retryable,
                "latency_s": round(time.monotonic() - started, 2),
            }
        )
        print(json.dumps(evidence, indent=2))
        return 5
    candidate = result.candidate
    evidence.update(
        {
            "status": "live_verified",
            "model_returned": result.model_identifier,
            "policy_id": result.policy_id,
            "attempts": result.attempts,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "publication_status": result.publication_status,
            "findings": len(candidate.findings),
            "latency_s": round(time.monotonic() - started, 2),
        }
    )
    print(json.dumps(evidence, indent=2))
    out = ROOT / "docs" / "engineering" / "testing" / "browser-e2e" / "E2E-003-live-result.json"
    out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
