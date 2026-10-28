"""Versioned structural/unit rules; no universal clinical ranges, toxicity or treatment grades."""

import re
from decimal import Decimal
from uuid import UUID

from canceros.clinical_contracts import NumericInput, NumericNormalization

RULE_VERSION = "clinical-structural/1"
UNITS = {
    "hemoglobin": {"g/dL": ("g/dL", Decimal(1)), "g/L": ("g/dL", Decimal("0.1"))},
    "wbc": {"10[9]/L": ("10[9]/L", Decimal(1))},
    "anc": {"10[9]/L": ("10[9]/L", Decimal(1))},
    "platelets": {"10[9]/L": ("10[9]/L", Decimal(1))},
    "creatinine": {"mg/dL": ("mg/dL", Decimal(1))},
    "alt": {"U/L": ("U/L", Decimal(1))},
    "ast": {"U/L": ("U/L", Decimal(1))},
    "heart_rate": {"/min": ("/min", Decimal(1))},
    "temperature": {"Cel": ("Cel", Decimal(1))},
    "weight": {"kg": ("kg", Decimal(1))},
    "systolic_bp": {"mmHg": ("mmHg", Decimal(1))},
    "diastolic_bp": {"mmHg": ("mmHg", Decimal(1))},
}


def decimal_text(number):
    result = format(number, "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return "0" if number == 0 else result


def semantic_validation(item, path):
    """Return canonical numeric derivation + safe rule findings; never echo protected input."""
    findings = []

    def issue(
        code, reason, field="", severity="error", action="Review the source value, unit and mapping"
    ):
        findings.append(
            {
                "rule_id": code,
                "severity": severity,
                "path": path + field,
                "reason": reason,
                "next_action": action,
            }
        )

    if item.kind in ("laboratory", "vital"):
        result = item.result
        if item.concept in ("systolic_bp", "diastolic_bp") and item.component_group is None:
            issue(
                "BP-COMPONENT-GROUP-1",
                "Blood pressure requires a declared component group",
                "/component_group",
            )
        if result.form == "missing":
            return NumericNormalization(
                original_value=item.original_value,
                original_unit=item.original_unit,
                canonical_result=result,
            ), findings
        quantity = result.quantity if result.form == "exact" else result.threshold
        # Exact finite decimal/qualified source syntax only; never treat a qualifier as equality.
        original = item.original_value or ""
        match = re.fullmatch(r"\s*(<=|>=|<|>)?\s*(-?(?:0|[1-9]\d*)(?:\.\d{1,9})?)\s*", original)
        if match is None:
            issue(
                "ORIGINAL-NUMERIC-SYNTAX-1",
                "Original numeric text requires an explicit supported qualifier",
                "/original_value",
            )
            return None, findings
        qualifier, original_number = match.groups()
        if (result.form == "exact" and qualifier) or (
            result.form == "censored" and qualifier != result.comparator
        ):
            issue("CENSOR-SEMANTICS-1", "Original qualifier and typed result disagree", "/result")
        original_unit = item.original_unit
        rules = UNITS[item.concept]
        if original_unit not in rules or quantity.unit not in rules:
            issue("UNIT-DIMENSION-1", "Unsupported unit or measurement dimension", "/original_unit")
            return None, findings
        canonical_unit, factor = rules[original_unit]
        canonical = Decimal(original_number) * factor
        declared_unit, declared_factor = rules[quantity.unit]
        if (
            declared_unit != canonical_unit
            or Decimal(quantity.value) * declared_factor != canonical
        ):
            issue(
                "SOURCE-NUMERIC-MISMATCH-1",
                "Typed result does not equal its original source measurement",
                "/result",
            )
        if canonical < 0 and item.concept != "temperature":
            issue(
                "NONNEGATIVE-STRUCTURE-1",
                "This count, mass or concentration cannot be negative",
                "/result",
            )
        if item.concept == "weight" and canonical == 0:
            issue("POSITIVE-MASS-1", "Recorded mass cannot be zero", "/result")
        canonical_value = decimal_text(canonical)
        # Canonical fixed-decimal range is checked by the existing shared quantity type.
        try:
            normalized = NumericNormalization.model_validate(
                {
                    "original_value": original,
                    "original_unit": original_unit,
                    "canonical_result": {
                        "form": "exact",
                        "quantity": {"value": canonical_value, "unit": canonical_unit},
                    }
                    if result.form == "exact"
                    else {
                        "form": "censored",
                        "comparator": result.comparator,
                        "threshold": {"value": canonical_value, "unit": canonical_unit},
                    },
                }
            )
        except ValueError:
            issue(
                "CANONICAL-DECIMAL-RANGE-1",
                "Canonical value exceeds supported exact decimal precision",
                "/result",
            )
            return None, findings
        interval = item.reference_interval
        if interval:
            if interval.unit not in rules:
                issue(
                    "REFERENCE-UNIT-1",
                    "Source interval has an incompatible unit",
                    "/reference_interval/unit",
                )
            elif result.form == "exact":
                multiplier = rules[interval.unit][1]
                outside = (
                    interval.low is not None and canonical < Decimal(interval.low) * multiplier
                ) or (interval.high is not None and canonical > Decimal(interval.high) * multiplier)
                if outside:
                    issue(
                        "SOURCE-INTERVAL-REVIEW-1",
                        "Value lies outside this source-provided interval; the original is preserved",
                        "/result",
                        "warning",
                        "Review the supplied population/context; this is not a treatment decision",
                    )
        return normalized, findings
    if item.kind == "symptom":
        if item.severity is not None:
            if (item.instrument, item.instrument_version) != ("engineering_ordinal", "1"):
                issue(
                    "SYMPTOM-INSTRUMENT-1",
                    "Unsupported named instrument/version",
                    "/instrument",
                    action="Review the instrument mapping; do not guess a scale",
                )
            elif not 0 <= Decimal(item.severity) <= 10:
                issue(
                    "SYMPTOM-BOUNDS-1",
                    "Score exceeds the declared engineering scale bounds",
                    "/severity",
                )
        if (item.presence == "present" and item.negation == "negated") or (
            item.presence == "absent" and item.negation == "affirmed"
        ):
            issue("SYMPTOM-NEGATION-1", "Presence and source negation conflict", "/presence")
    return None, findings


def component_validation(items):
    groups: dict[UUID, list[tuple[int, NumericInput]]] = {}
    findings = []
    for index, item in items:
        if (
            item.kind == "vital"
            and item.concept in ("systolic_bp", "diastolic_bp")
            and item.component_group
        ):
            groups.setdefault(item.component_group, []).append((index, item))
    for group in groups.values():
        concepts = [item.concept for _, item in group]
        severity = (
            "warning"
            if len(group) == 1
            else "error"
            if len(concepts) != len(set(concepts))
            else None
        )
        if severity:
            findings.append(
                {
                    "rule_id": "BP-COMPONENT-STRUCTURE-1",
                    "severity": severity,
                    "path": f"/records/{group[0][0]}/component_group",
                    "reason": "Blood pressure has missing or duplicate components",
                    "next_action": "Review the grouped source reading; do not invent a missing component",
                }
            )
    return findings
