"""Annotation meaning and fail-closed capabilities, separate from review evidence."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from canceros.contracts import Contract, Hash

AnnotationClass = Literal[
    "anatomical_tumor_contour",
    "model_proposal",
    "functional_enhancement_region",
    "bounding_box",
    "approximate_illustrative",
    "unknown",
]
Authorship = Literal["human", "algorithm", "unknown"]
ScientificReviewState = Literal["pending", "qualified_reviewed", "rejected", "not_available"]
TechnicalQCState = Literal["pending", "pass", "fail"]
Meaning = Literal["tumor_region", "functional_region", "region", "bounding_region", "unknown"]
MethodReference = Literal[
    "manual_source_mask", "external_algorithm_source_mask", "engineering_fixture_mask"
]
_MEANINGS = {
    "anatomical_tumor_contour": "tumor_region",
    "model_proposal": "tumor_region",
    "functional_enhancement_region": "functional_region",
    "bounding_box": "bounding_region",
    "approximate_illustrative": "region",
    "unknown": "unknown",
}


class LabelDefinition(Contract):
    label: Annotated[int, Field(strict=True, ge=1, le=65535)]
    meaning: Meaning


class AnnotationInput(Contract):
    alignment_run_id: UUID
    annotation_class: AnnotationClass
    authorship: Authorship
    method_reference: MethodReference | None = None
    labels: Annotated[tuple[LabelDefinition, ...], Field(min_length=1, max_length=32)]
    source_annotation_evidence_sha256: Hash | None = None

    @model_validator(mode="after")
    def unambiguous_class_and_dictionary(self):
        if len({item.label for item in self.labels}) != len(self.labels):
            raise ValueError(
                "Each positive label requires a separate unambiguous annotation definition"
            )
        if any(item.meaning != _MEANINGS[self.annotation_class] for item in self.labels):
            raise ValueError("Label meanings disagree with the declared annotation class")
        if self.annotation_class == "model_proposal" and (
            self.authorship != "algorithm"
            or self.method_reference
            not in ("external_algorithm_source_mask", "engineering_fixture_mask")
        ):
            raise ValueError(
                "Model proposals require algorithmic authorship and an explicit source-method category"
            )
        if self.authorship == "algorithm" and self.method_reference == "manual_source_mask":
            raise ValueError("Algorithmic authorship cannot assert a manual source method")
        if self.authorship == "human" and self.method_reference == "external_algorithm_source_mask":
            raise ValueError("Human authorship cannot assert an unreviewed algorithm source method")
        return self


class AnnotationCapabilities(Contract):
    annotation_class: AnnotationClass
    numerical_region_preview_allowed: bool
    technical_qc_allowed: bool
    numerical_region_volume_allowed: bool
    anatomical_volume_allowed: bool
    anatomical_mesh_allowed: bool
    publication_allowed: bool
    scientific_review_state: ScientificReviewState
    technical_qc_state: TechnicalQCState
    fixture_origin: bool
    blocked_reasons: tuple[str, ...]
    interpretation: Literal[
        "region_geometry_alone_is_not_anatomical_tumor_or_clinical_response"
    ] = "region_geometry_alone_is_not_anatomical_tumor_or_clinical_response"
    policy_version: Literal["annotation-capabilities/1"] = "annotation-capabilities/1"


def annotation_capabilities(
    annotation_class: AnnotationClass,
    scientific_review_state: ScientificReviewState = "pending",
    technical_qc_state: TechnicalQCState = "pending",
    fixture_origin: bool = True,
    *,
    alignment_state: TechnicalQCState = "pending",
    source_rights_permitted: bool = False,
    publication_approved: bool = False,
) -> AnnotationCapabilities:
    """Evaluate server-owned evidence states; never accept review assertions from import.

    A caller must independently verify qualified review records, current inherited
    source permissions and publication authority. Pure policy tests do not create
    any such evidence. Preview and raw region arithmetic preserve class meaning.
    """
    if (
        annotation_class not in _MEANINGS
        or scientific_review_state
        not in ("pending", "qualified_reviewed", "rejected", "not_available")
        or technical_qc_state not in ("pending", "pass", "fail")
        or alignment_state not in ("pending", "pass", "fail")
    ):
        raise ValueError("Unsupported annotation evidence state; capabilities remain denied")
    if any(
        type(value) is not bool
        for value in (fixture_origin, source_rights_permitted, publication_approved)
    ):
        raise ValueError("Explicit server-owned boolean evidence states required")
    aligned = alignment_state == "pass" and source_rights_permitted
    technical_pass = aligned and technical_qc_state == "pass"
    reviewed = scientific_review_state == "qualified_reviewed"
    anatomical = annotation_class == "anatomical_tumor_contour"
    rejected = scientific_review_state == "rejected"
    anatomical_allowed = technical_pass and reviewed and anatomical and not fixture_origin
    reasons = []
    if not source_rights_permitted:
        reasons.append("CURRENT_INHERITED_SOURCE_PERMISSION_REQUIRED")
    if alignment_state != "pass":
        reasons.append("PASSING_EXPLICIT_IMAGE_MASK_ALIGNMENT_REQUIRED")
    if technical_qc_state != "pass":
        reasons.append("TECHNICAL_ANNOTATION_QC_REQUIRED")
    if not reviewed:
        reasons.append("QUALIFIED_SCIENTIFIC_REVIEW_EVIDENCE_REQUIRED_FOR_ANATOMICAL_CLAIMS")
    if not anatomical:
        reasons.append("ANNOTATION_CLASS_DOES_NOT_ESTABLISH_ANATOMICAL_TUMOR_CONTOUR")
    if fixture_origin:
        reasons.append("ENGINEERING_FIXTURE_CANNOT_ESTABLISH_AUTHENTIC_ANATOMICAL_CLAIMS")
    if not publication_approved:
        reasons.append("EXPLICIT_PUBLICATION_AUTHORITY_AND_REVIEW_REQUIRED")
    if rejected:
        reasons.append("SCIENTIFIC_REVIEW_REJECTED_ANNOTATION")
    return AnnotationCapabilities(
        annotation_class=annotation_class,
        numerical_region_preview_allowed=aligned,
        technical_qc_allowed=aligned and not rejected,
        numerical_region_volume_allowed=technical_pass
        and not rejected
        and annotation_class != "unknown",
        anatomical_volume_allowed=anatomical_allowed,
        anatomical_mesh_allowed=anatomical_allowed,
        publication_allowed=anatomical_allowed and publication_approved,
        scientific_review_state=scientific_review_state,
        technical_qc_state=technical_qc_state,
        fixture_origin=fixture_origin,
        blocked_reasons=tuple(reasons),
    )
