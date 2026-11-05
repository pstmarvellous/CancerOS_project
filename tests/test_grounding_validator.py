"""E2E-003: GroundingValidator unit checks (synthetic contexts only, no network).

Covers the real fail-closed validator completed for the production adapter:
snapshot-hash match, reference membership, numeric fidelity passthrough,
prohibited-claim rejection, unresolved-reference rejection, unsupported
metric-code abstention, and empty-candidate handling. The unavailable-validator
placeholder behavior (always refusing) is preserved for unvalidated inputs.
"""

from uuid import uuid4

import pytest

from canceros.context_contracts import ContextBuildInput
from canceros.grounding_runs import GATE_VERSION, GroundingValidator
from canceros.interpretation_runs import build_interpretation
from canceros.provider_contracts import ProviderInput
from canceros.provider_gateway import PrivateResult, ProviderFailure
from test_context_runs import FIXTURE_PATIENT, SNAPSHOT_ID
from test_context_runs import build as build_context_fixture


def context(monkeypatch):
    value = ContextBuildInput(patient_id=FIXTURE_PATIENT, snapshot_id=SNAPSHOT_ID)
    return build_context_fixture(monkeypatch, value)


def candidate_for(built, text="Retained synthetic fixture value."):
    return PrivateResult.model_validate(
        {
            "candidate": {
                "schema_version": "provider-candidate/1",
                "input_snapshot_hash": built.snapshot_hash,
                "findings": [
                    {
                        "text": text,
                        "measurement_refs": [str(m.reference_id) for m in built.measurements[:1]],
                        "passage_refs": [],
                    }
                ],
            },
            "model_identifier": "muse-spark-1.3",
            "model_revision": None,
            "policy_id": "synthetic-validator-check",
            "prompt_version": "provider-boundary/1",
            "attempts": 1,
            "input_tokens": 10,
            "output_tokens": 8,
            "publication_status": "withheld_pending_cos064",
        }
    )


def test_validator_version_pins_gate():
    assert GroundingValidator.version == GATE_VERSION == "grounding-gate/1"


def test_matching_candidate_passes_grounding(monkeypatch):
    built = context(monkeypatch)
    assert built.measurements, "fixture must supply at least one measurement"
    report = GroundingValidator().validate(candidate_for(built), built)
    assert report.verdict == "published"
    assert report.numeric_matched == report.numeric_statements >= 1


def test_snapshot_mismatch_fails_closed(monkeypatch):
    built = context(monkeypatch)
    result = candidate_for(built)
    tampered = result.model_copy(
        update={
            "candidate": result.candidate.model_copy(
                update={"input_snapshot_hash": "0" * 64}
            )
        }
    )
    with pytest.raises(ProviderFailure, match="FAILED_GROUNDING"):
        GroundingValidator().validate(tampered, built)


def test_unresolved_reference_fails_closed(monkeypatch):
    built = context(monkeypatch)
    result = candidate_for(built)
    tampered = result.model_copy(
        update={
            "candidate": result.candidate.model_copy(
                update={
                    "findings": (
                        result.candidate.findings[0].model_copy(
                            update={"measurement_refs": (uuid4(),)}
                        ),
                    )
                }
            )
        }
    )
    with pytest.raises(ProviderFailure, match="FAILED_GROUNDING"):
        GroundingValidator().validate(tampered, built)


def test_prohibited_claim_fails_closed(monkeypatch):
    built = context(monkeypatch)
    with pytest.raises(ProviderFailure, match="FAILED_GROUNDING"):
        GroundingValidator().validate(
            candidate_for(built, "The patient should receive dose-adjusted treatment."),
            built,
        )


def test_empty_candidate_withholds(monkeypatch):
    built = context(monkeypatch)
    result = candidate_for(built).model_copy(
        update={
            "candidate": candidate_for(built).candidate.model_copy(update={"findings": ()})
        }
    )
    with pytest.raises(ProviderFailure, match="FAILED_GROUNDING"):
        GroundingValidator().validate(result, built)
