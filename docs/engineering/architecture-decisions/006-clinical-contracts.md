# ADR-006: clinical/1 and local dictionaries

2026-10-27, COS-018 under SPEC-008; engineering self-review, scientific review pending.

Extend the existing frozen Pydantic contract base, decimal strings, time unions,
provenance and status enums. Do not fork those types. ClinicalRecord owns the
clinical/1 schema; generated JSON Schema and TypeScript round-trip the same fields.
Local vocabulary `canceros-local/1` supports visits, numeric labs/vitals, source
pathology, treatment exposure, symptoms and private note references. No external
terminology system/license or clinical instrument is claimed adopted.

Original source terms, numeric strings/units and locators remain explicit. Censoring
is comparator+threshold, not an exact result; missing is a distinct union variant.
Receptor positive/negative/equivocal/unknown/not-tested/not-recorded/invalid remain
different codes. A prescription/order cannot assert delivery. No reference ranges,
toxicity grades, stage inference or treatment recommendations are generated.
Only documented local units are accepted; supported conversions are COS-020 work.
The single engineering ordinal instrument is synthetic-fixture-only, not CTCAE.

ClinicalTime preserves source precision, timezone offset, shift basis and optional
uncertainty. Relative zero uses the independent persisted timeline origin. Graph
validation rejects cycles, unknown/unresolved/incomparable anchors in a caller-owned
graph; database services must additionally enforce patient/project ownership.
Unknown time carries no invented value. DCE phases are not visit concepts.

Dictionary GET is authenticated and project scoped; actual dictionary labels and
units are available to later import workflows. Schema-only safeguards do not verify
source records or authorize manual REAL_OBSERVED assertions: the ingestion service
derives provenance from an eligible private source. Publication is separate.

Evidence: clinical-contracts.json. Real terminology mapping, qualified review and
C06 scientific policy remain pending. Contract changes do not close D01–D06.
