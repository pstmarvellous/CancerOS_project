"""Exact server-side scalar comparisons after separately established lesion identity.

Registration is deliberately absent: failed spatial alignment does not invalidate
otherwise comparable scalar volumes. This arithmetic cannot establish identity,
anatomical review, clinical response, or treatment causation.
"""

from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from canceros.contracts import Contract, DecimalString, Provenance

POLICY = "temporal-volume-comparison/1"
UNKNOWN = {"", "unknown", "not_recorded", "unavailable", "not_established", "unspecified"}
ANNOTATION_CLASSES = {
    "anatomical_tumor_contour",
    "model_proposal",
    "functional_enhancement_region",
    "bounding_box",
    "approximate_illustrative",
}
DEFINITIONS = {"numerical_region_volume", "functional_region_volume", "anatomical_tumor_volume"}


class ComparisonError(ValueError):
    """Static numerical error without supplied source values."""


class ScalarPoint(Contract):
    event_id: UUID
    measurement_id: UUID | None
    study_id: UUID
    annotation_class: Annotated[str, Field(strict=True, max_length=160)]
    definition: Annotated[str, Field(strict=True, max_length=160)]
    method: Annotated[str, Field(strict=True, max_length=160)]
    origin: Provenance
    unit: Literal["mm3"] = "mm3"
    volume_mm3: DecimalString | None
    time_group_id: UUID | None
    relative_day: DecimalString | None
    eligible: Annotated[bool, Field(strict=True)]


class ScalarChange(Contract):
    absolute_mm3: DecimalString | None
    percent_change: DecimalString | None
    eligibility: bool
    reasons: list[str]
    policy: Literal["temporal-volume-comparison/1"] = "temporal-volume-comparison/1"
    meaning: Literal["scalar_volume_change_not_RECIST_clinical_response_or_treatment_causation"] = (
        "scalar_volume_change_not_RECIST_clinical_response_or_treatment_causation"
    )


def _number(value):
    if value is None:
        return None
    try:
        number = Decimal(value)
        if not number.is_finite() or abs(number) >= Decimal("1e15"):
            raise ComparisonError("finite_bounded_scalar_quantity_required")
        return number
    except (InvalidOperation, TypeError, ValueError):
        raise ComparisonError("finite_bounded_scalar_quantity_required") from None


def _quantity(value):
    if not value.is_finite() or abs(value) >= Decimal("1e15"):
        raise ComparisonError("computed_change_outside_quantity_bounds")
    value = value.quantize(Decimal("0.000000001"), rounding=ROUND_HALF_EVEN)
    if abs(value) >= Decimal("1e15"):
        raise ComparisonError("computed_change_outside_quantity_bounds")
    return "0" if not value else format(value, "f").rstrip("0").rstrip(".")


def compare_points(left: ScalarPoint, right: ScalarPoint) -> ScalarChange:
    """Compute later-minus-earlier values only for the declared comparable context."""
    reasons = []
    if left.measurement_id is None or right.measurement_id is None:
        reasons.append("measurement_reference_missing")
    if left.study_id == right.study_id:
        reasons.append("distinct_examinations_required")
    if not left.eligible or not right.eligible:
        reasons.append("point_not_eligible")
    for name in ("annotation_class", "definition", "method", "origin", "unit"):
        if getattr(left, name) != getattr(right, name):
            reasons.append(name + "_mismatch")
    if (
        left.annotation_class not in ANNOTATION_CLASSES
        or right.annotation_class not in ANNOTATION_CLASSES
    ):
        reasons.append("annotation_class_unknown")
    if left.definition not in DEFINITIONS or right.definition not in DEFINITIONS:
        reasons.append("measurement_definition_unknown")
    if left.method.strip().lower() in UNKNOWN or right.method.strip().lower() in UNKNOWN:
        reasons.append("measurement_method_unknown")
    if left.unit != "mm3" or right.unit != "mm3":
        reasons.append("unsupported_unit")
    if left.origin not in set(Provenance) or right.origin not in set(Provenance):
        reasons.append("origin_unknown")
    if left.time_group_id is None or right.time_group_id is None:
        reasons.append("time_group_unknown")
    elif left.time_group_id != right.time_group_id:
        reasons.append("time_group_mismatch")
    with localcontext() as context:
        context.prec = 80
        before, after = _number(left.volume_mm3), _number(right.volume_mm3)
        left_day, right_day = _number(left.relative_day), _number(right.relative_day)
        if before is None or after is None:
            reasons.append("measurement_missing")
        elif before < 0 or after < 0:
            reasons.append("negative_volume_invalid")
        if left_day is None or right_day is None:
            reasons.append("relative_time_unknown")
        elif right_day <= left_day:
            reasons.append("strictly_later_comparable_time_required")
        if reasons:
            return ScalarChange(
                absolute_mm3=None, percent_change=None, eligibility=False, reasons=reasons
            )
        assert before is not None and after is not None
        absolute = _quantity(after - before)
        if before == 0:
            return ScalarChange(
                absolute_mm3=absolute,
                percent_change=None,
                eligibility=True,
                reasons=["zero_baseline_percentage_undefined"],
            )
        percent = _quantity((after - before) / before * Decimal(100))
        return ScalarChange(
            absolute_mm3=absolute, percent_change=percent, eligibility=True, reasons=[]
        )
