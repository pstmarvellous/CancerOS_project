"""Controlled software-fact fixtures, without claiming authentic baseline approval."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from canceros.contracts import Provenance
from canceros.simulation_eligibility import (
    COMPATIBILITY_MATRIX,
    ExposureConfig,
    PathologyFact,
    PureBaselineFacts,
    evaluate,
)


def baseline(**changes):
    fields = {
        field: True
        for field in (
            "observed_baseline_verified",
            "published_baseline_verified",
            "source_rights_allowed",
            "patient_ownership_verified",
            "revision_current",
            "metric_valid",
            "annotation_numeric_eligible",
            "anatomy_eligible",
        )
    }
    return PureBaselineFacts(baseline_hash="a" * 64, **{**fields, **changes})


def exposure(category="no_specific_assumption", **changes):
    data = {"exposure": "none"}
    if category != "no_specific_assumption":
        data = {
            "exposure": "hypothetical",
            "category": category,
            "events": [
                {
                    "event_id": "start",
                    "relative_day": "0",
                    "category": "hypothetical_exposure_start",
                }
            ],
        }
    return ExposureConfig.model_validate({**data, **changes})


def fact(field, status, origin=Provenance.REAL_OBSERVED, **changes):
    return PathologyFact(
        source_id=UUID(int={"er": 1, "pr": 2, "her2": 3, "subtype": 4}[field]),
        field=field,
        status=status,
        origin=origin,
        **changes,
    )


def codes(result):
    return {reason.code for reason in result.reasons}


def test_descriptive_measurement_without_optional_labs_or_pathology():
    result = evaluate(baseline(anatomy_eligible=False), exposure())
    assert result.status == "eligible"
    assert result.permitted_capabilities == ["measurement"]
    assert not result.clinical_appropriateness_established
    assert result.missing_fields == []
    assert (
        evaluate(baseline(anatomy_eligible=False), exposure(), "anatomical_mesh").status
        == "ineligible"
    )


@pytest.mark.parametrize(
    "field",
    [
        "source_rights_allowed",
        "patient_ownership_verified",
        "revision_current",
        "metric_valid",
        "annotation_numeric_eligible",
    ],
)
def test_hard_baseline_failures(field):
    result = evaluate(baseline(**{field: False}), exposure())
    assert result.status == "ineligible"
    assert result.permitted_capabilities == []
    assert "baseline_" + field + "_failed" in codes(result)


@pytest.mark.parametrize("field", ["observed_baseline_verified", "published_baseline_verified"])
def test_missing_baseline_approval_is_not_imputed(field):
    result = evaluate(baseline(**{field: False}), exposure())
    assert result.status == "insufficient_data"
    assert field in result.missing_fields


def test_unknown_is_distinct_from_explicit_negative_hormone_receptors():
    unknown = evaluate(baseline(), exposure("endocrine"))
    negative = evaluate(
        baseline(pathology=[fact("er", "negative"), fact("pr", "negative")]), exposure("endocrine")
    )
    positive = evaluate(baseline(pathology=[fact("er", "positive")]), exposure("endocrine"))
    assert unknown.status == "insufficient_data"
    assert {"er", "pr"} <= set(unknown.missing_fields)
    assert negative.status == "ineligible"
    assert "required_hormone_receptors_negative" in codes(negative)
    assert positive.status == "insufficient_data"
    assert positive.missing_fields == ["qualified_rule_review"]


@pytest.mark.parametrize(
    "origin",
    [
        Provenance.SYNTHETIC_GENERATED,
        Provenance.MODEL_PREDICTED,
        Provenance.INTERPOLATED,
        Provenance.REAL_DERIVED,
    ],
)
def test_non_observed_pathology_cannot_satisfy_required_receptor(origin):
    result = evaluate(
        baseline(pathology=[fact("her2", "positive", origin)]),
        exposure("her2_targeted", setting="neoadjuvant", intent="research_hypothetical"),
    )
    assert "her2" in result.missing_fields
    assert "required_her2_status_unknown" in codes(result)


def test_her2_negative_incompatible_and_context_missing_is_explicit():
    result = evaluate(baseline(pathology=[fact("her2", "negative")]), exposure("her2_targeted"))
    assert result.status == "ineligible"
    assert "required_her2_negative" in codes(result)
    assert {"setting", "intent"} <= set(result.missing_fields)


def test_conflicting_or_retracted_observations_do_not_pick_favorable_value():
    conflict = evaluate(
        baseline(pathology=[fact("her2", "positive"), fact("her2", "negative")]),
        exposure("her2_targeted"),
    )
    assert "conflicting_observed_pathology" in codes(conflict)
    retracted = evaluate(
        baseline(pathology=[fact("her2", "positive", record_status="retracted")]),
        exposure("her2_targeted"),
    )
    assert "her2" in retracted.missing_fields


@pytest.mark.parametrize("category", ["chemotherapy", "radiotherapy", "endocrine", "her2_targeted"])
def test_specific_rules_stay_unreviewed(category):
    result = evaluate(
        baseline(pathology=[fact("er", "positive"), fact("her2", "positive")]),
        exposure(category, setting="adjuvant", intent="research_hypothetical"),
    )
    assert result.status == "insufficient_data"
    assert "specific_exposure_rules_unreviewed" in codes(result)
    assert not result.clinical_appropriateness_established


def test_immunotherapy_does_not_invent_compatible_subtype_list():
    result = evaluate(
        baseline(pathology=[fact("subtype", "documented", value="source-described-subtype")]),
        exposure("immunotherapy", setting="neoadjuvant", intent="research_hypothetical"),
    )
    assert result.status == "insufficient_data"
    assert "reviewed_compatible_subtype_matrix_missing" in codes(result)


def test_surgery_disabled_as_discrete_transition_and_rules_serializable():
    result = evaluate(baseline(), exposure("surgery"))
    assert result.status == "ineligible"
    assert "discrete_surgery_transition_unsupported" in codes(result)
    assert len({rule.category for rule in COMPATIBILITY_MATRIX}) == 7
    assert all(rule.model_dump(mode="json")["evidence"] for rule in COMPATIBILITY_MATRIX)


def test_strict_facts_no_clinical_review_toggle():
    with pytest.raises(ValidationError):
        PureBaselineFacts.model_validate({**baseline().model_dump(), "source_rights_allowed": 1})
    with pytest.raises(ValidationError):
        ExposureConfig.model_validate({"exposure": "none", "reviewed": True})
    with pytest.raises(ValidationError):
        ExposureConfig.model_validate({"exposure": "none", "category": "endocrine"})


def test_evidence_ids_include_structural_and_pathology_sources_once():
    structural = UUID(int=90)
    result = evaluate(
        baseline(evidence_ids=[structural, structural], pathology=[fact("er", "positive")]),
        exposure("endocrine"),
    )
    assert result.evidence_ids == [UUID(int=1), structural]
    assert result.baseline_hash == "a" * 64
