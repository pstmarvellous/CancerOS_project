"""Default-denied external export policy; no network/provider adapter in Phase1."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import Field

from canceros.contracts import Contract, Hash


class PermissionEvidence(Contract):
    reference_file: str
    sha256: Hash


class ExportPolicy(Contract):
    schema_version: Literal["export/1"]
    policy_id: str = Field(min_length=1)
    provider: str
    model_identifier: str
    permission_evidence: list[PermissionEvidence] = Field(min_length=1)
    approved_input_hashes: list[Hash] = Field(min_length=1)
    allowed_fields: list[
        Literal["research_context", "measurements", "missingness", "provenance", "evidence_ids"]
    ]


def verified_policy(config):
    if (
        not config.external_inference_enabled
        or not config.model_api_key
        or not config.export_policy_path
    ):
        raise PermissionError("EXTERNAL_EXPORT_DENIED")
    try:
        policy = ExportPolicy.model_validate_json(
            Path(config.export_policy_path).read_text(encoding="utf-8")
        )
        if (
            policy.provider != config.model_provider
            or policy.model_identifier != config.model_identifier
        ):
            raise ValueError("Policy/provider mismatch")
        for evidence in policy.permission_evidence:
            if (
                hashlib.sha256(Path(evidence.reference_file).read_bytes()).hexdigest()
                != evidence.sha256
            ):
                raise ValueError("Permission evidence mismatch")
        return policy
    except Exception:
        raise PermissionError("EXTERNAL_EXPORT_DENIED") from None


def prepare_export(config, payload):
    policy = verified_policy(config)
    if set(payload) - set(policy.allowed_fields):
        raise PermissionError("EXTERNAL_EXPORT_DENIED")
    content = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(content).hexdigest() not in policy.approved_input_hashes:
        raise PermissionError("EXTERNAL_EXPORT_DENIED")
    return content


def invoke_provider(config, payload):
    prepare_export(config, payload)
    # Configuration does not establish an evaluated registered provider integration.
    raise PermissionError("NO_VERIFIED_PROVIDER_ADAPTER")
