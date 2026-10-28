# COS-027 numerical preprocessing learning and evidence

Scope: delegated pure single-acquisition preprocessing and artificial-array tests.
Read the exact prompt, [task-local context](COS-027.md), original dual-map and
repository/scientific results, and SPEC-005 P-01–08/optional-processing/output
sections. IMG.PRE and IMG.03 constrain versioned intensity processing without
changing geometry; preceding ingestion/geometry and later mask/QC work remain
separate. Original source maps/specifications are untouched. AI engineering review
does not establish qualified MRI or clinical review.

## Actual source learning

- NumPy **2.4** official [mean](https://numpy.org/doc/2.4/reference/generated/numpy.mean.html)
  and [standard deviation](https://numpy.org/doc/2.4/reference/generated/numpy.std.html)
  documentation: read accumulator precision, full-array reduction and divisor
  `N-ddof` semantics. Explicit float64 calculations with `ddof=0` define this
  pipeline's population standard deviation; all selected-volume voxels, including
  background, participate. This is not foreground-aware or model-specific processing.
- Inspected pinned **NumPy 2.4.6**
  [`_core/_methods.py`](https://github.com/numpy/numpy/blob/v2.4.6/numpy/_core/_methods.py),
  `_mean`, variance reduction and standard deviation implementation. Reproduced
  the four-value `[1,2,3,4]` example independently: mean 2.5, population variance
  1.25 and normalized residuals. This small example establishes arithmetic only.
  BSD-3-Clause software license was inspected in COS-025; no dataset/model rights
  follow from the software license.
- ITK online documentation labelled **5.4.0**,
  [`NormalizeImageFilter` detailed description](https://docs.itk.org/projects/doxygen/en/stable/classitk_1_1NormalizeImageFilter.html):
  read shift/scale behavior and the warning that integral output cannot preserve
  unit variance. This informs float64 output selection; ITK is not installed/adopted
  by this task and equivalence to its statistics implementation is not claimed.
- Mapped **A05**, ITK project online *Software Guide*, Book 2 chapter 2,
  [section 2.3.1 Linear Mappings](https://itk.org/ITKSoftwareGuide/html/Book2/ITKSoftwareGuide-Book2ch2.html):
  read casting versus rescale versus shift/scale versus statistical normalization,
  the normalized residual formula and float-output example. The inspected online
  chapter does not print an edition; no invented edition is attributed. It separates
  mere type conversion from intensity correction, which informs the explicit method
  field and retention of source values. No broader chapter-reading claim is made.
- SimpleITK **2.4.0** [Fundamental Concepts](https://simpleitk.readthedocs.io/en/master/fundamentalConcepts.html),
  Images and Channels: reread physical grids and scalar/vector distinction.
  Sequence selection retains the spatial frame; multiple acquisitions are not
  automatically equivalent channels. No toolkit defaults supply missing units,
  phase identities or motion alignment.

MIT MRI lectures, Toennies textbook, MONAI/MAMA-MIA preprocessing and empirical
breast-MRI studies were not evaluated. No claim that generic z-scoring is optimal
for a particular scanner, tissue, lesion, model or endpoint. Identity is the default
for the imported-mask pathway; optional normalization requires explicit selection.

## Three-source decision and owned interface

Physical-grid and floating-point principles → public pinned NumPy reductions with
full original affine retained → no qualified cohort/scanner evidence → enable only
identity and explicit selected-volume population z-score → verify deterministic
pixel bytes, independent small-array arithmetic and unchanged source/geometry.
No resampling, crop, bias correction, model, GPU, learned/cohort-fitted parameters,
missing-channel fabrication or voxelwise phase fusion is enabled by this config.

`preprocess(array, geometry, config, source_sequence)` returns immutable copied
float64 pixels, three-dimensional geometry and a typed `PreprocessingReport`.
Source and output pixel hashes use C-order little-endian float64 bytes, explicitly
distinct from the parent's serialized artifact byte hashes. Method/version, sequence,
selected source phase, ordering evidence hash, exact float64 mean/std and software
version are recorded. Numerical statistics are metadata in arbitrary image units,
not clinical quantity estimates or calibrated perfusion measurements.

For a 4D DCE source, require an explicit selected index plus one source-relative
acquisition offset per phase, strictly increasing in source array order. Misordered,
equal-time, absent or mismatched evidence blocks this narrow implementation; no
automatic reorder fabricates phase chronology. Role may remain unknown for selecting
one independent acquisition and is visibly labelled unknown. The evidence is an
administrator-provided source attestation, not specialist review. No operation assumes
voxelwise correspondence or within-exam motion correction. Phase selection yields
one 3D grid, preserves original LPS/RAS conversion exactly once and creates no visits.

Constant or numerically constant images retain their true values under identity
with a warning. Z-score processing blocks when standard deviation is at most 1e-12;
it never substitutes invented contrast. Nonfinite values are rejected, never imputed.
Absolute image intensity above 1e12 is unsupported by this bounded numerical policy.
These limits are versioned engineering support bounds, not clinical validity limits.

## Critical review and actual checks

Self-review covered source mutation, aliasing, zero/constant data, source/expected
sequence mismatch, phase-order ambiguity, source-frame double conversion, numerical
versus medical interpretation, unsupported cohort fitting and missing channels.
Config forbids unknown fields/methods, so held-out inputs cannot enter any enabled
cohort-fit operation; none exists. Parent evaluation tests separately exercise its
existing training-partition guard and own authorization/lineage enforcement.

Executed `uv run pytest tests/test_imaging_preprocessing.py -q`: **16 passed** on
artificial arrays. Executed Ruff check/format and focused mypy successfully.
No real MRI was inspected, no scanner/model compatibility measured, and no clinical
or scientific normalization effectiveness claimed. Parent owns persisted private
artifacts, current source rights, API contracts and generated-client checks.

Hackathon impact: local deterministic numerical processing only. External inference,
source publication, validated response predictions and competition eligibility
remain outside this verified scope. Next action: run parent processing integration
while retaining real-source and qualified-review evidence gaps.
