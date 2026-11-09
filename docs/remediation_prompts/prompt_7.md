# COS-REC-06 — Imaging Import and 3D Reconstruction Workflow

**Role:** Medical Imaging Engineer, Backend Engineer, Data Engineer and UX Engineer

**Mission:** Connect authorized imaging input to the existing processing, segmentation/QC, measurement and 3D visualization services.

Do not replace the established scientific imaging architecture.

## Initial investigation

Identify:

- Current accepted imaging formats.
- Existing import endpoints and schema restrictions.
- Existing image and mask association logic.
- Source-rights requirements.
- De-identification controls.
- Spatial metadata requirements.
- Existing segmentation and geometry services.
- Background-job dependencies.
- File-size and resource limitations.

Determine which capabilities are implemented, which are fixture-only and which are missing.

## Required workflow

Within a selected research case, provide:

**Imaging → Add Imaging Study**

The user should be able to:

1. Select a supported file or study.
2. Associate it with the current case.
3. Select an appropriate authorized segmentation mask, where necessary.
4. Review source and provenance information.
5. Submit the import.
6. See processing progress.
7. View QC results.
8. Open the resulting 3D model.
9. Inspect deterministic measurements.

Do not silently create segmentation masks when none are available.

Do not assume that every uploaded MRI includes a verified tumor annotation.

## Example user experience

The researcher selects an eligible sample.

The application shows:

**Study uploaded — preparing image**

Then:

**Checking image geometry**

Then:

**Segmentation and measurements available**

Finally:

**Open 3D Model**

Use actual backend processing status, not simulated progress presented as real computation.

If a required mask is absent, display:

"This imaging study has no compatible verified region mask. A 3D tumor measurement is not yet available."

Offer the appropriate next action.

## Restrictions

Never modify original medical data simply to make it pass QC.

Never guess voxel spacing or spatial units.

Never treat DCE contrast phases as separate longitudinal visits.

Do not relax source-rights or patient-identity checks.

Use an entirely synthetic imaging fixture for unrestricted pipeline tests; use authentic data only when its rights, de-identification, geometry and annotation status have been verified.

## Acceptance gate

PASS requires evidence that:

- Authorized input reaches private storage.
- Image and mask alignment checks execute.
- Physical geometry is derived from verified metadata.
- The existing measurement engine produces its outputs.
- A supported 3D mesh renders in the browser.
- The case retains the study association after refresh.
- Invalid or mismatched inputs fail safely.
- No cross-patient access is possible.

If authentic-data permissions remain unavailable, distinguish a passed synthetic pipeline test from the blocked authentic MRI acceptance gate.

Do not report authentic medical imaging as verified based solely on synthetic fixtures.
