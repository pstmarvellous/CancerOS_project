"""Policy fixtures do not establish real scientific-review evidence."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from canceros.annotation_contracts import (
    AnnotationInput,
    LabelDefinition,
    annotation_capabilities,
)


def annotation(**changes):
    value = dict(
        alignment_run_id=uuid4(),
        annotation_class="anatomical_tumor_contour",
        authorship="human",
        method_reference="manual_source_mask",
        labels=(
            LabelDefinition(label=1, meaning="tumor_region"),
            LabelDefinition(label=5, meaning="tumor_region"),
        ),
    )
    value.update(changes)
    return AnnotationInput(**value)


def test_multilabel_dictionary_retains_distinct_labels_and_unknown_evidence():
    value = annotation()
    assert [entry.label for entry in value.labels] == [1, 5]
    assert value.source_annotation_evidence_sha256 is None
    assert "scientific_review" not in value.model_dump()
    unknown = annotation(
        annotation_class="unknown",
        authorship="unknown",
        method_reference=None,
        labels=(LabelDefinition(label=1, meaning="unknown"),),
    )
    assert unknown.authorship == "unknown" and unknown.method_reference is None


def test_ambiguous_invalid_and_misclassified_dictionaries_reject():
    for entries in (
        [{"label": 1, "meaning": "tumor_region"}, {"label": 1, "meaning": "tumor_region"}],
        [{"label": 0, "meaning": "tumor_region"}],
        [{"label": 1.0, "meaning": "tumor_region"}],
        [{"label": 65536, "meaning": "tumor_region"}],
        [{"label": 1, "meaning": "functional_region"}],
        [],
    ):
        with pytest.raises(ValidationError):
            annotation(labels=entries)
    with pytest.raises(ValidationError):
        annotation(labels=[{"label": 1, "meaning": "tumor_region", "lesion_key": str(uuid4())}])


@pytest.mark.parametrize(
    "extra",
    [
        {"scientific_review": "qualified_reviewed"},
        {"reviewer_id": str(uuid4())},
        {"technical_qc_state": "pass"},
        {"publication": "published"},
    ],
)
def test_import_cannot_sign_off_review_qc_or_publication(extra):
    with pytest.raises(ValidationError):
        annotation(**extra)


def test_method_categories_are_controlled_and_model_proposal_is_not_human_authorship():
    proposal = annotation(
        annotation_class="model_proposal",
        authorship="algorithm",
        method_reference="external_algorithm_source_mask",
    )
    assert proposal.authorship == "algorithm"
    with pytest.raises(ValidationError):
        annotation(annotation_class="model_proposal")
    with pytest.raises(ValidationError):
        annotation(annotation_class="model_proposal", authorship="algorithm", method_reference=None)
    with pytest.raises(ValidationError):
        annotation(method_reference="https://private.example/patient-source")
    with pytest.raises(ValidationError):
        annotation(authorship="algorithm", method_reference="manual_source_mask")


def test_defaults_deny_uses_and_passing_alignment_enables_only_limited_preview():
    value = annotation_capabilities("anatomical_tumor_contour")
    assert not value.numerical_region_preview_allowed
    assert not value.technical_qc_allowed
    assert not value.anatomical_volume_allowed and not value.publication_allowed
    aligned = annotation_capabilities(
        "anatomical_tumor_contour", alignment_state="pass", source_rights_permitted=True
    )
    assert aligned.numerical_region_preview_allowed and aligned.technical_qc_allowed
    assert not aligned.numerical_region_volume_allowed
    assert not aligned.anatomical_volume_allowed


@pytest.mark.parametrize(
    "kind",
    [
        "functional_enhancement_region",
        "bounding_box",
        "approximate_illustrative",
        "model_proposal",
        "unknown",
    ],
)
def test_nonanatomical_classes_never_become_anatomical_under_any_review(kind):
    result = annotation_capabilities(
        kind,
        "qualified_reviewed",
        "pass",
        False,
        alignment_state="pass",
        source_rights_permitted=True,
        publication_approved=True,
    )
    assert not result.anatomical_volume_allowed
    assert not result.anatomical_mesh_allowed
    assert not result.publication_allowed
    assert result.numerical_region_volume_allowed == (kind != "unknown")


def test_hypothetical_reviewed_contour_can_enter_qc_without_fabricating_actual_review():
    # This pure truth-table input is not a persisted or asserted human review.
    pending_qc = annotation_capabilities(
        "anatomical_tumor_contour",
        "qualified_reviewed",
        "pending",
        False,
        alignment_state="pass",
        source_rights_permitted=True,
    )
    assert pending_qc.technical_qc_allowed
    assert not pending_qc.anatomical_volume_allowed
    passed = annotation_capabilities(
        "anatomical_tumor_contour",
        "qualified_reviewed",
        "pass",
        False,
        alignment_state="pass",
        source_rights_permitted=True,
    )
    assert passed.anatomical_volume_allowed and passed.anatomical_mesh_allowed
    assert not passed.publication_allowed
    fixture = annotation_capabilities(
        "anatomical_tumor_contour",
        "qualified_reviewed",
        "pass",
        True,
        alignment_state="pass",
        source_rights_permitted=True,
        publication_approved=True,
    )
    assert fixture.numerical_region_volume_allowed
    assert not fixture.anatomical_volume_allowed and not fixture.publication_allowed


def test_rights_revocation_alignment_failure_or_rejected_review_denies_downstream_claims():
    for extra in ({"source_rights_permitted": False}, {"alignment_state": "fail"}):
        options = dict(
            alignment_state="pass", source_rights_permitted=True, publication_approved=True
        )
        options.update(extra)
        result = annotation_capabilities(
            "anatomical_tumor_contour", "qualified_reviewed", "pass", False, **options
        )
        assert not result.technical_qc_allowed
        assert not result.anatomical_volume_allowed and not result.publication_allowed
    rejected = annotation_capabilities(
        "anatomical_tumor_contour",
        "rejected",
        "pass",
        False,
        alignment_state="pass",
        source_rights_permitted=True,
    )
    assert rejected.numerical_region_preview_allowed  # Preserved evidence for review.
    assert not rejected.technical_qc_allowed and not rejected.numerical_region_volume_allowed


def test_unknown_runtime_states_and_truthy_strings_do_not_enable_policy():
    with pytest.raises(ValueError):
        annotation_capabilities("arbitrary-class")
    with pytest.raises(ValueError):
        annotation_capabilities("anatomical_tumor_contour", "approved-by-agent")
    with pytest.raises(ValueError):
        annotation_capabilities("anatomical_tumor_contour", fixture_origin="false")
