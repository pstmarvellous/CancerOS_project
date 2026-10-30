"""SLRE context checks; software eligibility does not establish clinical appropriateness."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from canceros.contracts import Contract, Hash, Provenance
from canceros.simulation_contracts import TreatmentAssumptions

RULESET_VERSION: Literal["simulation-eligibility/1"] = "simulation-eligibility/1"
ExposureConfig = TreatmentAssumptions
Capability = Literal["measurement", "anatomical_mesh"]
PathologyField = Literal["er", "pr", "her2", "subtype"]
StrictBoolean = Annotated[bool, Field(strict=True)]


class PathologyFact(Contract):
    source_id: UUID
    field: PathologyField
    status: Literal[
        "positive",
        "negative",
        "equivocal",
        "unknown",
        "not_recorded",
        "not_tested",
        "invalid",
        "documented",
    ]
    value: Annotated[str, Field(strict=True, min_length=1, max_length=100)] | None = None
    origin: Provenance
    record_status: Literal["current", "retracted", "superseded"] = "current"

    @model_validator(mode="after")
    def pathology_type(self):
        if self.field != "subtype" and (self.value is not None or self.status == "documented"):
            raise ValueError("Receptor facts require categorical status, without subtype text")
        if self.field == "subtype" and self.status == "documented" and self.value is None:
            raise ValueError("Documented subtype requires its explicit source value")
        if self.field == "subtype" and self.status in ("positive", "negative", "equivocal"):
            raise ValueError(
                "Subtype requires an explicit documented source value or missing status"
            )
        if self.field == "subtype" and self.status != "documented" and self.value is not None:
            raise ValueError("Undocumented subtype cannot supply a compatible source value")
        return self


class PureBaselineFacts(Contract):
    """Trusted server-derived facts; this model is never an eligibility API input."""

    baseline_hash: Hash
    observed_baseline_verified: StrictBoolean
    published_baseline_verified: StrictBoolean
    source_rights_allowed: StrictBoolean
    patient_ownership_verified: StrictBoolean
    revision_current: StrictBoolean
    metric_valid: StrictBoolean
    annotation_numeric_eligible: StrictBoolean
    anatomy_eligible: StrictBoolean
    pathology: Annotated[list[PathologyFact], Field(max_length=128)] = []
    evidence_ids: Annotated[list[UUID], Field(max_length=256)] = []


class CompatibilityRule(Contract):
    category: str
    receptor_any_positive: tuple[PathologyField, ...] = ()
    receptor_all_positive: tuple[PathologyField, ...] = ()
    requires_subtype: bool = False
    requires_setting_intent: bool = False
    review_status: Literal["descriptive_only", "qualified_review_missing", "unsupported_transition"]
    evidence: tuple[str, ...]


_CONTEXT_SOURCES = (
    "COS-SPEC-004:6",
    "https://www.cancer.gov/types/breast/hp/breast-treatment-pdq",
)
COMPATIBILITY_MATRIX = (
    CompatibilityRule(
        category="no_specific_assumption",
        review_status="descriptive_only",
        evidence=("COS-SPEC-004:1.2,5,8",),
    ),
    CompatibilityRule(
        category="chemotherapy",
        review_status="qualified_review_missing",
        evidence=("COS-SPEC-004:6.1,6.7",),
    ),
    CompatibilityRule(
        category="endocrine",
        receptor_any_positive=("er", "pr"),
        review_status="qualified_review_missing",
        evidence=_CONTEXT_SOURCES,
    ),
    CompatibilityRule(
        category="her2_targeted",
        receptor_all_positive=("her2",),
        requires_setting_intent=True,
        review_status="qualified_review_missing",
        evidence=_CONTEXT_SOURCES,
    ),
    CompatibilityRule(
        category="immunotherapy",
        requires_subtype=True,
        requires_setting_intent=True,
        review_status="qualified_review_missing",
        evidence=("COS-SPEC-004:6.4,6.7",),
    ),
    CompatibilityRule(
        category="surgery", review_status="unsupported_transition", evidence=("COS-SPEC-004:6.5",)
    ),
    CompatibilityRule(
        category="radiotherapy",
        review_status="qualified_review_missing",
        evidence=("COS-SPEC-004:6.5,6.7",),
    ),
)


class EligibilityReason(Contract):
    code: str
    disposition: Literal["ineligible", "insufficient_data", "information"]
    fields: list[str] = []


class EligibilityResult(Contract):
    status: Literal["eligible", "ineligible", "insufficient_data"]
    ruleset_version: Literal["simulation-eligibility/1"] = RULESET_VERSION
    baseline_hash: Hash
    requested_capability: Capability
    permitted_capabilities: list[Capability]
    missing_fields: list[str]
    evidence_ids: list[UUID]
    reasons: list[EligibilityReason]
    next_actions: list[str]
    clinical_appropriateness_established: Literal[False] = False
    review_status: Literal["unreviewed_demo"] = "unreviewed_demo"


def evaluate(
    facts: PureBaselineFacts, exposure: ExposureConfig, capability: Capability = "measurement"
) -> EligibilityResult:
    """Evaluate supplied server evidence; never impute optional labs or compatible pathology."""
    if capability not in ("measurement", "anatomical_mesh"):
        raise ValueError("Unknown eligibility capability")
    facts = PureBaselineFacts.model_validate_json(facts.model_dump_json())
    exposure = ExposureConfig.model_validate_json(exposure.model_dump_json())
    reasons: list[EligibilityReason] = []
    missing: set[str] = set()
    actions: set[str] = set()

    def issue(code, disposition, fields=(), action="Review the recorded source evidence"):
        reasons.append(EligibilityReason(code=code, disposition=disposition, fields=list(fields)))
        if disposition == "insufficient_data":
            missing.update(fields)
        actions.add(action)

    for field in (
        "source_rights_allowed",
        "patient_ownership_verified",
        "revision_current",
        "metric_valid",
        "annotation_numeric_eligible",
    ):
        if not getattr(facts, field):
            issue("baseline_" + field + "_failed", "ineligible", (field,))
    for field in ("observed_baseline_verified", "published_baseline_verified"):
        if not getattr(facts, field):
            issue(
                "baseline_" + field + "_missing",
                "insufficient_data",
                (field,),
                "Obtain verified observed baseline and authorized publication evidence",
            )
    if capability == "anatomical_mesh" and not facts.anatomy_eligible:
        issue(
            "anatomical_annotation_not_eligible",
            "ineligible",
            ("anatomy_eligible",),
            "Use a measurement-only workflow or obtain qualified anatomical annotation evidence",
        )
    rule = next(item for item in COMPATIBILITY_MATRIX if item.category == exposure.category)
    source_facts = [
        item
        for item in facts.pathology
        if item.origin == Provenance.REAL_OBSERVED and item.record_status == "current"
    ]

    def status(field):
        candidates = [item for item in source_facts if item.field == field]
        known = {item.status for item in candidates if item.status in ("positive", "negative")}
        if len(known) > 1:
            issue(
                "conflicting_observed_pathology",
                "insufficient_data",
                (field,),
                "Resolve conflicting source pathology without rewriting historical observations",
            )
            return "unknown"
        return next(iter(known)) if known else "unknown"

    if rule.receptor_any_positive:
        statuses = [status(field) for field in rule.receptor_any_positive]
        if "positive" not in statuses:
            if all(item == "negative" for item in statuses):
                issue("required_hormone_receptors_negative", "ineligible", ("er", "pr"))
            else:
                fields = [
                    field
                    for field, result in zip(rule.receptor_any_positive, statuses)
                    if result == "unknown"
                ]
                issue(
                    "required_hormone_receptor_status_unknown",
                    "insufficient_data",
                    fields,
                    "Obtain documented source ER/PR status; do not substitute synthetic results",
                )
    for field in rule.receptor_all_positive:
        result = status(field)
        if result == "negative":
            issue("required_" + field + "_negative", "ineligible", (field,))
        elif result != "positive":
            issue(
                "required_" + field + "_status_unknown",
                "insufficient_data",
                (field,),
                "Obtain documented source receptor status; do not impute a favorable status",
            )
    if rule.requires_subtype:
        subtypes = {
            item.value
            for item in source_facts
            if item.field == "subtype" and item.status == "documented"
        }
        if len(subtypes) != 1:
            issue("documented_subtype_missing_or_conflicting", "insufficient_data", ("subtype",))
        issue(
            "reviewed_compatible_subtype_matrix_missing",
            "insufficient_data",
            ("reviewed_subtype_matrix",),
            "Obtain qualified review of the supported subtype and treatment-setting matrix",
        )
    if rule.requires_setting_intent:
        for field in ("setting", "intent"):
            if getattr(exposure, field) == "not_recorded":
                issue(
                    "required_treatment_" + field + "_missing",
                    "insufficient_data",
                    (field,),
                    "Record the explicit hypothetical research treatment context",
                )
    if rule.review_status == "qualified_review_missing":
        issue(
            "specific_exposure_rules_unreviewed",
            "insufficient_data",
            ("qualified_rule_review",),
            "Obtain qualified scientific rule review or select no particular treatment assumption",
        )
    elif rule.review_status == "unsupported_transition":
        issue(
            "discrete_surgery_transition_unsupported",
            "ineligible",
            (),
            "Implement and review discrete residual/removed-lesion semantics before enabling surgery",
        )
    blocked = {reason.disposition for reason in reasons}
    result_status: Literal["eligible", "ineligible", "insufficient_data"] = (
        "ineligible"
        if "ineligible" in blocked
        else "insufficient_data"
        if "insufficient_data" in blocked
        else "eligible"
    )
    if result_status == "eligible":
        reasons.append(
            EligibilityReason(code="descriptive_software_checks_passed", disposition="information")
        )
        actions.add("Continue the explicitly hypothetical descriptive workflow")
    return EligibilityResult(
        status=result_status,
        baseline_hash=facts.baseline_hash,
        requested_capability=capability,
        permitted_capabilities=[capability] if result_status == "eligible" else [],
        missing_fields=sorted(missing),
        evidence_ids=sorted(
            {*facts.evidence_ids, *(item.source_id for item in facts.pathology)}, key=str
        ),
        reasons=reasons,
        next_actions=sorted(actions),
    )
