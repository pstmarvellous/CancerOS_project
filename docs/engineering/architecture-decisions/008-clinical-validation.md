# ADR-008: exact numeric normalization and source-specific warnings

COS-020; clinical-structural/1 + local-units/1, 2026-10-27. Scientific review pending.

Only explicitly enumerated local units are supported. Use finite Decimal strings and
exact dimensional scaling; hemoglobin g/L → g/dL multiplies by 0.1. Other current
units use identity conversion. No creatinine molar conversion, Fahrenheit conversion,
unverified external code mapping or learned normalization is enabled.

Retain original text/unit and typed source result. Store canonical result separately
with conversion-rule version, including qualifier+threshold for censored results.
Reject disagreement between original text and typed result. Missing stays missing.
Negative counts/concentrations/mass and zero mass are structural errors. No universal
normal ranges or automatic toxicity, treatment safety or eligibility grades exist.

Source-provided reference bounds retain provenance description, context, version and
unit. An exact out-of-interval value creates a review warning; the original remains
accepted with warning status. Censored thresholds are not treated as exact observations.
Blood pressure uses separate concepts and a component group. Missing partners produce
a warning; duplicate components error. No absent component is invented.

The only scored symptom instrument is an explicitly synthetic engineering ordinal
fixture, version 1, bounded 0–10. Unknown instruments are quarantined; reporter and
negation remain explicit. This is not CTCAE or a clinical scale validation.

Rules run during validate-first staging and acceptance. Canonical numeric SQL subtype
columns and API payload agree; source intervals remain in immutable typed rows.
Rules and report versions are persisted rather than inferred from installed code.
Evidence: clinical-validation.json; clinical-fixture.json; boundary/conversion tests.
C06 qualified terminology, source restrictions and scientific review remain open.
