# COS-REC-04 — Scenarios, Timeline and Plain-Language Data Presentation

**Role:** UX Researcher, Data Visualization Engineer, Clinical Informatics Specialist and Frontend Engineer

**Mission:** Make the existing simulation and clinical-data presentation understandable to a visitor with no medical background.

Reuse the existing five-family simulation results, authoritative measurements and observation provenance.

## Tasks

1. Review all scenario names, descriptions, controls, charts and clinical-data tables.
2. Provide clear human-readable scenario names.
3. Explain each scenario in one or two simple sentences.
4. Display a visible timeline connected to the 3D viewer.
5. Present changes in volume with explicit units and source labels.
6. Explain clinical observations in plain language while retaining exact data values.
7. Add simple contextual help for unfamiliar terms.
8. Clearly distinguish synthetic observations, authentic records and derived measurements.
9. Ensure observations do not silently carry forward to timepoints where they were not measured.
10. Preserve the existing five families without inventing new clinical claims.

## Example scenario selection

Replace technical identifiers such as SC-01 through SC-05 in primary controls with:

- **Continuous shrinkage**
- **Little or no size change**
- **Continued growth**
- **Shrinks, then grows again**
- **Stable size with worsening symptoms**

Keep the original scenario identifiers in metadata.

The descriptions must accurately reflect the corresponding generated trajectories.

Example:

**Shrinks, then grows again**

"In this hypothetical example, the modeled region becomes smaller before increasing in size at a later point."

Do not describe that outcome as a validated prediction.

## Expected output presentation

A selected Day 37 state could display:

**Modeled region volume: 64 mm³**

"Compared with this scenario's 216 mm³ synthetic baseline, the selected region is smaller."

If showing a percentage, calculate it deterministically from verified values and identify the comparison baseline.

For a laboratory value, show the readable name, recorded value, unit and observation date.

Example:

**Hemoglobin: 12.4 g/dL**

"Artificial example recorded on 1 November 2026."

Do not add health interpretations or normal/abnormal classifications without appropriate evidence.

## Acceptance gate

A visitor must be able to:

1. Select each of the five scenarios.
2. Understand the chosen scenario's meaning.
3. Change the selected timepoint.
4. See the 3D model, chart and selected-state measurements update consistently.
5. Open the associated observations.
6. Distinguish observed, derived and synthetic information.

Run all five families in Playwright.

Include tests for missing observations, changing scenarios, navigating back and restoring state after refresh.

Do not mark this stage complete if explanatory text is polished but data selection is inconsistent.
