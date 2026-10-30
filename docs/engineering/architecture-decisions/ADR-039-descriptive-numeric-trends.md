# ADR-039: deterministic descriptive comparisons and trends

COS-052. Compare only exact owned observations selected through the canonical
revision/knowledge/event window. The API accepts point identities and tolerance,
never replacement clinical values. Preserve source/state/measurement IDs, context,
lesion/metric/method, units and explicit comparability reasons. Full input windows
are used even when the timeline table is paginated.

Use existing versioned unit conversions and exact Decimal quantities. Actual time
intervals determine endpoint/adjacent slopes. Zero-baseline percentages are null,
censored quantities are not equal to their thresholds, and duplicate or unknown
time denominators cannot produce a slope. Retain extra exact physical quantities
alongside bounded display arithmetic so a rounded display zero is not a true zero.

Ordinal symptom instruments support ordered descriptive direction only; no ratio
percentage or interval slope is established. Missing/conflicted values remain gaps.
Engineering tolerance describes numeric equality only, not clinical significance.
Charts use actual elapsed positions and exact tables; connecting segments are
visual guides, not additional observations or interpolation. No RECIST/CTCAE,
resistance, treatment efficacy, confidence interval or LLM dependency is introduced.
