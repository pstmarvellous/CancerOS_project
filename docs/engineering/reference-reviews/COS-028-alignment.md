# COS-028 label alignment learning and fixture evidence

Scope: delegated pure label alignment contracts/functions and artificial geometry
tests. Read the exact prompt, [COS-028 context](COS-028.md), dual-map/repository
query outputs and SPEC-005 P-04/P-08, SPEC-008 spatial frames and SPEC-011 section 5.
IMG.PRE/IMG.MASK and mapped physical-grid/resampling behaviors constrain this task;
original map/specification sources remain unchanged. Parent owns patient/study
association, source rights, private persistence, previews, API and generated clients.
This engineering review is not qualified anatomical or clinical review.

## Actual sources and upstream inspection

- Mapped **A05**, ITK project online *Software Guide*, Book 2 chapter 2,
  [section 2.9.4 Resample Image Filter](https://itk.org/ITKSoftwareGuide/html/Book2/ITKSoftwareGuide-Book2ch2.html):
  read explicit input image/transform/interpolator/output-grid requirements, nearest
  neighbor example, outside background and output-to-input transform direction.
  The online page does not print an edition. Principle: choose physical output
  geometry deliberately and transform output samples back into the source;
  array dimensions alone do not define alignment. No wider chapter-reading claim.
- SimpleITK documentation labelled **2.4.0**,
  [Fundamental Concepts, Transforms](https://simpleitk.readthedocs.io/en/master/fundamentalConcepts.html):
  read spatial transform matrix/center/translation/offset distinction. Here the
  owned homogeneous matrix already contains the full offset and explicitly maps
  source RAS-mm world coordinates to target RAS-mm world coordinates.
- SciPy **1.17.1**, tagged
  [`ndimage/_interpolation.py`](https://github.com/scipy/scipy/blob/v1.17.1/scipy/ndimage/_interpolation.py),
  inspected `affine_transform` signature, homogeneous-matrix handling, pull mapping
  and interpolation/prefilter branches. The unversioned documentation now reports
  1.18.0; tagged source and installed 1.17.1 are the adoption basis. Public API used
  with `order=0`, `prefilter=False`, explicit target shape, `grid-constant`, background
  zero. Owned pull matrix is inverse(source affine) × inverse(source-to-target world)
  × target affine. No intensity interpolation followed by label rounding.
- SciPy **1.17.1**, tagged
  [`ndimage/_measurements.py`](https://github.com/scipy/scipy/blob/v1.17.1/scipy/ndimage/_measurements.py),
  inspected `label` structure/background/result semantics. Each label is measured
  separately with `generate_binary_structure(3,1)`, explicitly six-connected.
  Component changes flag review; connectivity is not inferred anatomical truth.
- Inspected tagged SciPy LICENSE.txt and interpolation/measurement file headers:
  BSD-3-Clause software conditions. No source code copied and no dataset, mask,
  annotation or checkpoint rights follow from this software license.

No genuine image/mask pair, independent Slicer overlay or empirical segmentation
paper was evaluated. Artificial expected locations/counts test representation
integrity only; they cannot establish biological or anatomical alignment.

## Three-source decision and numerical policy

Physical resampling principle → pinned SciPy nearest-neighbor pull sampler →
authentic cohort/reference-tool evidence unavailable → narrow explicit rigid-world
transform and target-grid service, with no guessed resize → independently calculated
translation, rotation, reflection-grid, anisotropy and clipping fixtures.

Original source arrays stay unchanged. Proper rigid world transforms are allowed;
world scaling/reflection/shear are rejected. Source/target grid affines may retain
reflection, anisotropy and shear because these describe sampling grids rather than
an invented biological transform. Exact mode accepts only identical effective grids;
different grids require explicit nearest-neighbor selection. No fitted registration
or reviewer acceptance is inferred from a numeric overlay.

Clipping checks the complete support of every foreground voxel cell. The exact
axis-aligned radius under an affine is half the row-wise sum of absolute linear
coefficients; comparing transformed centers plus/minus that radius with target
voxel faces catches partial clipping even when nearest-neighbor label counts do
not change. Coverage is the fraction of wholly contained source voxel cells, not
Dice, image intensity overlap or an anatomical score. Boundary tolerance is 1e-7
target index units, a versioned numerical bound. Iteration is chunked to limit
working memory. At most 32 distinct positive labels and the existing geometry
voxel bounds cap per-label component analysis.

Per-label before/after physical volume uses full affine absolute determinants
times counts, rounding only the totals to shared nine-place decimal strings.
This avoids accumulating a rounded single-voxel value. Allowed resampling error
is max(one source voxel, one target voxel, configured fraction of source volume),
with the configurable fraction capped at the frozen one-percent engineering
ceiling. This is not clinical acceptability or a guarantee of invariant volume.
Lost/new labels, changed component counts, excessive volume difference, clipping,
unknown labels and empty masks quarantine. Failed results expose no output pixels
or output hash; original sources and the report remain available to the parent.
An exact-grid mismatch has no candidate output: report output counts are zero.
Pass still states measurement readiness and anatomical review are not established.

## Actual checks and remaining gates

Executed `uv run pytest tests/test_mask_alignment.py -q`: **16 passed** using wholly
artificial labels. Cases cover exact immutable copies, known translations with
inverse direction, rotated/reflected grids, anisotropic physical-volume accounting,
partially clipped cells with unchanged label count, total nonoverlap, empty/unexpected
labels, nonintegral/negative/nonfinite/unsupported label values, proper-rigid policy,
phase/shape rejection, volume failure, component merging and label-count resource
bounds. Ruff check/format and focused mypy passed. Source metadata and patient data
were not inspected. Parent tests must establish ownership and persistence behavior;
qualified overlay review and independent real-source validation remain pending.

Hackathon compliance impact: deterministic private geometry only; no external
inference, source publication, model accuracy or scientific validation claimed.
