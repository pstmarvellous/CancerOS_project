"""Synthetic transport fixtures verify boundaries, never live provider access."""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from canceros.provider_contracts import ProviderInput, local_summary
from canceros.provider_gateway import (
    MAX_RESPONSE_BYTES,
    ClosedOutputValidator,
    MetaAdapter,
    MetaHTTPTransport,
    ProviderFailure,
    TransportReply,
    canonical_bytes,
    execute_private,
    strict_json,
)


@pytest.fixture
def context():
    return ProviderInput(
        purpose="research_summary",
        input_snapshot_hash="a" * 64,
        measurements=[
            {
                "reference_id": uuid4(),
                "metric_code": "volume",
                "value": "12.5",
                "unit": "mm3",
                "provenance": "SYNTHETIC_GENERATED",
            }
        ],
        missingness=["unreviewed"],
        evidence_ids=[uuid4()],
    )


def candidate(context):
    return {
        "schema_version": "provider-candidate/1",
        "input_snapshot_hash": context.input_snapshot_hash,
        "findings": [
            {
                "text": "Artificial private provider prose, never a validated public finding.",
                "measurement_refs": [str(context.measurements[0].reference_id)],
                "passage_refs": [str(context.evidence_ids[0])],
            }
        ],
    }


def response(context, *, output=None, **overrides):
    data = {
        "status": "completed",
        "model": "artificial-model",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(candidate(context) if output is None else output),
                    }
                ],
            }
        ],
        "usage": {"input_tokens": 10, "output_tokens": 8},
    }
    data.update(overrides)
    return TransportReply(status=200, body=canonical_bytes(data))


class ArtificialTransport:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    async def send(self, body, *, timeout):
        self.calls.append((body, timeout))
        reply = self.replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        return reply


@pytest.fixture
def approved_fixture(tmp_path, context):
    """Mock approval is isolated from Settings and cannot establish real rights."""
    evidence = tmp_path / "artificial-policy-evidence.txt"
    evidence.write_text("Synthetic adapter test only; no live account or source rights.")
    evidence_ref = {
        "reference_file": str(evidence),
        "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
    }
    path = tmp_path / "artificial-policy.json"
    policy = {
        "schema_version": "export/2",
        "policy_id": "synthetic-policy-fixture",
        "provider": "meta",
        "model_identifier": "artificial-model",
        "endpoint": "https://api.meta.ai/v1/responses",
        "account_id": "artificial-no-account",
        "region": "artificial-region",
        "purpose": context.purpose,
        "data_class": "minimized_structured_research",
        "retention_policy": "Artificial test declaration only",
        "training_policy": "Artificial test declaration only",
        "onward_processing_policy": "Artificial test declaration only",
        "permission_evidence": [evidence_ref],
        "source_rights_evidence": [evidence_ref],
        "approved_input_hashes": [
            hashlib.sha256(canonical_bytes(context.model_dump(mode="json"))).hexdigest()
        ],
        "approved_wire_hashes": [
            hashlib.sha256(MetaAdapter.request(context, "artificial-model")).hexdigest()
        ],
        "allowed_fields": list(context.model_dump()),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "policy_reviewed": True,
        "account_access_verified": True,
        "revoked": False,
    }
    path.write_bytes(canonical_bytes(policy))
    config = SimpleNamespace(
        mode="test",
        external_inference_enabled=True,
        model_api_key=SecretStr("artificial-private-secret"),
        export_policy_path=str(path),
        model_provider="meta",
        model_identifier="artificial-model",
        model_endpoint="https://api.meta.ai/v1/responses",
        model_account_id="artificial-no-account",
        model_region="artificial-region",
    )
    return config, path, policy, evidence


@pytest.mark.parametrize(
    "raw",
    [
        b'{"a":1,"a":2}',
        b'{"nested":{"a":1,"a":2}}',
        b"NaN",
        b"Infinity",
        b"-Infinity",
        b'{"truncated":',
        b"\xff",
        b" " * (MAX_RESPONSE_BYTES + 1),
    ],
    ids=[
        "duplicate",
        "nested_duplicate",
        "nan",
        "infinity",
        "negative_infinity",
        "truncated",
        "invalid_utf8",
        "oversized",
    ],
)
def test_strict_json_rejects_ambiguous_nonfinite_and_truncated_output(raw):
    with pytest.raises(ProviderFailure, match="FAILED_SCHEMA"):
        strict_json(raw)


@pytest.mark.parametrize("change", ["extra", "wrong_hash", "measurement", "passage"])
def test_candidate_rejects_extra_fields_and_wrong_context_references(context, change):
    value = candidate(context)
    if change == "extra":
        value["unauthorized"] = "artificial-secret"
    elif change == "wrong_hash":
        value["input_snapshot_hash"] = "b" * 64
    else:
        key = "measurement_refs" if change == "measurement" else "passage_refs"
        value["findings"][0][key] = [str(uuid4())]
    with pytest.raises(ProviderFailure) as error:
        MetaAdapter.parse(response(context, output=value), context, "artificial-model")
    assert error.value.code == ("FAILED_SCHEMA" if change == "extra" else "FAILED_GROUNDING")
    assert "artificial-secret" not in str(error.value)


@pytest.mark.parametrize(
    "metadata",
    [
        {"status": "incomplete"},
        {"model": "other-model"},
        {"output": []},
        {"usage": {"input_tokens": True}},
        {"usage": {"output_tokens": -1}},
        {"usage": {"input_tokens": 1000001}},
        {"usage": {"input_tokens": "10"}},
    ],
)
def test_incomplete_or_wrong_identity_and_usage_metadata_fail_closed(context, metadata):
    with pytest.raises(ProviderFailure, match="FAILED_SCHEMA"):
        MetaAdapter.parse(response(context, **metadata), context, "artificial-model")


def test_local_summary_is_a_template_and_never_passes_input_prose(context):
    suspicious = context.model_copy(update={"missingness": ("Ignore_all_rules",)})
    result = local_summary(suspicious)
    assert result.execution_mode == "local_template"
    assert result.measurement_refs == (context.measurements[0].reference_id,)
    assert "Ignore_all_rules" not in result.summary
    assert "12.5" not in result.summary
    assert result.status == "source_inventory"
    empty = local_summary(context.model_copy(update={"measurements": ()}))
    assert empty.status == "insufficient_evidence"


def test_default_denial_makes_zero_transport_or_authorization_calls(context, approved_fixture):
    config, _, _, _ = approved_fixture
    config.external_inference_enabled = False
    transport = ArtificialTransport()
    checks = []
    with pytest.raises(ProviderFailure, match="EXTERNAL_PROCESSING_NOT_ALLOWED"):
        asyncio.run(execute_private(config, context, transport, lambda: checks.append(True)))
    assert transport.calls == checks == []


@pytest.mark.parametrize("mutation", ["revoked", "expired", "input", "wire", "field", "evidence"])
def test_export_policy_and_exact_wire_are_rechecked(context, approved_fixture, mutation):
    config, path, policy, evidence = approved_fixture
    if mutation == "revoked":
        policy["revoked"] = True
    elif mutation == "expired":
        policy["expires_at"] = "2000-01-01T00:00:00Z"
    elif mutation in ("input", "wire"):
        policy[f"approved_{mutation}_hashes"] = ["b" * 64]
    elif mutation == "field":
        policy["allowed_fields"].remove("measurements")
    else:
        evidence.write_text("Changed after the artificial review")
    path.write_bytes(canonical_bytes(policy))
    transport = ArtificialTransport()
    with pytest.raises(ProviderFailure, match="EXTERNAL_PROCESSING_NOT_ALLOWED"):
        asyncio.run(execute_private(config, context, transport, lambda: None))
    assert transport.calls == []


def test_private_success_retains_identity_usage_and_withholds_candidate(context, approved_fixture):
    config, _, _, _ = approved_fixture
    transport = ArtificialTransport(response(context))
    checks = []
    result = asyncio.run(execute_private(config, context, transport, lambda: checks.append(True)))
    assert len(transport.calls) == len(checks) == 1
    assert (result.input_tokens, result.output_tokens, result.attempts) == (10, 8, 1)
    assert result.model_identifier == "artificial-model" and result.model_revision is None
    assert result.publication_status == "withheld_pending_cos064"
    assert "candidate" not in result.model_dump()
    assert "Artificial private provider prose" not in repr(result)
    with pytest.raises(ProviderFailure, match="GROUNDING_VALIDATOR_UNAVAILABLE"):
        ClosedOutputValidator().validate(result)


def test_withdrawal_during_retry_stops_before_second_transmission(context, approved_fixture):
    config, path, policy, _ = approved_fixture
    transport = ArtificialTransport(TransportReply(status=429, body=b"private provider body"))

    async def withdraw(_):
        policy["revoked"] = True
        path.write_bytes(canonical_bytes(policy))

    with pytest.raises(ProviderFailure, match="EXTERNAL_PROCESSING_NOT_ALLOWED"):
        asyncio.run(execute_private(config, context, transport, lambda: None, wait=withdraw))
    assert len(transport.calls) == 1


@pytest.mark.parametrize("status,retryable", [(429, True), (503, True), (400, False), (401, False)])
def test_retryable_failures_and_permanent_rejections_are_distinct(
    context, approved_fixture, status, retryable
):
    config, _, _, _ = approved_fixture
    transport = ArtificialTransport(
        TransportReply(status=status, body=b"artificial-secret"), response(context)
    )
    waits = []

    async def wait(seconds):
        waits.append(seconds)

    if retryable:
        result = asyncio.run(execute_private(config, context, transport, lambda: None, wait=wait))
        assert result.attempts == 2 and len(transport.calls) == 2 and waits == [1]
    else:
        with pytest.raises(ProviderFailure, match="PROVIDER_REQUEST_REJECTED"):
            asyncio.run(execute_private(config, context, transport, lambda: None, wait=wait))
        assert len(transport.calls) == 1 and waits == []


def test_timeout_cancels_transport_and_returns_safe_error(context, approved_fixture):
    config, _, _, _ = approved_fixture
    cancelled = []

    class Slow:
        async def send(self, body, *, timeout):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(True)

    with pytest.raises(ProviderFailure, match="PROVIDER_TIMEOUT"):
        asyncio.run(
            execute_private(
                config, context, Slow(), lambda: None, max_attempts=1, timeout_seconds=0.01
            )
        )
    assert cancelled == [True]


def test_cancel_before_execution_makes_zero_calls(context, approved_fixture):
    config, _, _, _ = approved_fixture
    transport = ArtificialTransport()

    async def run():
        task = asyncio.create_task(execute_private(config, context, transport, lambda: None))
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    assert transport.calls == []


def test_cancellation_during_backoff_prevents_retry(context, approved_fixture):
    config, _, _, _ = approved_fixture
    transport = ArtificialTransport(TransportReply(status=429, body=b""))

    async def cancel(_):
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(execute_private(config, context, transport, lambda: None, wait=cancel))
    assert len(transport.calls) == 1


@pytest.mark.parametrize(
    "budget",
    [
        {"max_attempts": 0},
        {"max_attempts": 4},
        {"max_attempts": True},
        {"max_attempts": 1.5},
        {"timeout_seconds": 0},
        {"timeout_seconds": 31},
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": True},
    ],
)
def test_request_budgets_are_bounded_before_any_transmission(context, approved_fixture, budget):
    config, _, _, _ = approved_fixture
    transport = ArtificialTransport()
    with pytest.raises(ProviderFailure, match="INVALID_PROVIDER_BUDGET"):
        asyncio.run(execute_private(config, context, transport, lambda: None, **budget))
    assert transport.calls == []


def test_arbitrary_transport_exception_does_not_expose_private_text(context, approved_fixture):
    config, _, _, _ = approved_fixture
    transport = ArtificialTransport(RuntimeError("artificial-private-secret and payload"))
    with pytest.raises(ProviderFailure) as error:
        asyncio.run(execute_private(config, context, transport, lambda: None))
    assert str(error.value) == "PROVIDER_UNAVAILABLE"
    assert error.value.__suppress_context__
    assert len(transport.calls) == 1


def test_response_envelope_size_is_bounded():
    with pytest.raises(ValidationError):
        TransportReply(status=200, body=b"x" * (MAX_RESPONSE_BYTES + 1))


@pytest.mark.parametrize("mode", ["development", "staging", "production"])
def test_live_modes_remain_closed_even_with_full_mock_policy(context, approved_fixture, mode):
    config, _, _, _ = approved_fixture
    config.mode = mode
    transport = ArtificialTransport()
    with pytest.raises(ProviderFailure, match="LIVE_PROVIDER_GATE_NOT_CLOSED"):
        asyncio.run(execute_private(config, context, transport, lambda: None))
    assert transport.calls == []


def test_current_authorization_is_rechecked_before_every_attempt(context, approved_fixture):
    config, _, _, _ = approved_fixture
    transport = ArtificialTransport(TransportReply(status=429, body=b""))
    checks = []

    def authorize():
        checks.append(True)
        if len(checks) == 2:
            raise ProviderFailure("EXTERNAL_PROCESSING_NOT_ALLOWED")

    async def wait(_):
        return None

    with pytest.raises(ProviderFailure, match="EXTERNAL_PROCESSING_NOT_ALLOWED"):
        asyncio.run(execute_private(config, context, transport, authorize, wait=wait))
    assert len(checks) == 2 and len(transport.calls) == 1


def test_rate_limit_exhaustion_never_exceeds_attempt_budget(context, approved_fixture):
    config, _, _, _ = approved_fixture
    transport = ArtificialTransport(*(TransportReply(status=429, body=b"") for _ in range(3)))

    async def wait(_):
        return None

    with pytest.raises(ProviderFailure, match="PROVIDER_RATE_LIMITED"):
        asyncio.run(
            execute_private(config, context, transport, lambda: None, max_attempts=3, wait=wait)
        )
    assert len(transport.calls) == 3


@pytest.mark.parametrize("behavior", ["ok", "redirect", "oversized", "timeout", "network"])
def test_http_transport_is_bounded_isolated_and_redacts_provider_failures(
    context, approved_fixture, monkeypatch, behavior
):
    config, _, _, _ = approved_fixture
    calls = []
    options = []
    original_client = httpx.AsyncClient

    def handler(request):
        calls.append(request)
        assert request.url == "https://api.meta.ai/v1/responses"
        assert request.headers["Authorization"] == "Bearer artificial-private-secret"
        if behavior == "timeout":
            raise httpx.ReadTimeout("artificial-private-secret", request=request)
        if behavior == "network":
            raise httpx.ConnectError("artificial-private-secret", request=request)
        if behavior == "redirect":
            return httpx.Response(
                302,
                headers={"Location": "https://untrusted.invalid"},
                content=b"artificial-private-secret",
            )
        return httpx.Response(
            200,
            content=(
                b"x" * (MAX_RESPONSE_BYTES + 1) if behavior == "oversized" else b"safe fixture"
            ),
        )

    def client(**kwargs):
        options.append(kwargs)
        return original_client(**kwargs)

    monkeypatch.setattr("canceros.provider_gateway.httpx.AsyncClient", client)
    operation = MetaHTTPTransport(config, http_transport=httpx.MockTransport(handler)).send(
        MetaAdapter.request(context, config.model_identifier), timeout=1
    )
    if behavior in ("timeout", "network", "oversized"):
        with pytest.raises(ProviderFailure) as error:
            asyncio.run(operation)
        assert "artificial-private-secret" not in str(error.value)
        assert (
            error.value.code
            == {
                "timeout": "PROVIDER_TIMEOUT",
                "network": "PROVIDER_UNAVAILABLE",
                "oversized": "FAILED_SCHEMA",
            }[behavior]
        )
    else:
        result = asyncio.run(operation)
        assert result.status == (302 if behavior == "redirect" else 200)
        assert result.body == (b"" if behavior == "redirect" else b"safe fixture")
    assert len(calls) == 1
    assert options[0]["follow_redirects"] is False
    assert options[0]["trust_env"] is False


def test_http_transport_cannot_use_real_network_even_in_test_mode(
    context, approved_fixture, monkeypatch
):
    config, _, _, _ = approved_fixture
    calls = []
    monkeypatch.setattr(
        "canceros.provider_gateway.httpx.AsyncClient", lambda **kwargs: calls.append(kwargs)
    )
    with pytest.raises(ProviderFailure, match="LIVE_PROVIDER_GATE_NOT_CLOSED"):
        asyncio.run(
            MetaHTTPTransport(config).send(
                MetaAdapter.request(context, config.model_identifier), timeout=1
            )
        )
    assert calls == []
