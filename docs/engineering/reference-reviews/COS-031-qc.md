# COS-031 mask QC and independent metric learning

Scope: delegated pure technical mask QC and per-case binary metrics. Read the
exact prompt, [COS-031 context](COS-031.md), original map outputs and SPEC-011
sections 5/7, plus SPEC-005 segmentation postprocessing/evaluation. EVAL.SEG,
IMG.MASK and mapped R05/MONAI pointers constrain separate technical validity,
reference suitability and measured model performance. Original maps/specifications
remain unchanged. This is AI engineering review, not qualified scientific review.

## Actual learning and inspection

- SPEC-011 section 7 explicitly defines overlap/volume metrics, undefined zero-
  reference relative error, empty-label handling, failed-attempt denominators and
  absence of universal clinical Dice/HD95 thresholds. These are implementation
  protocol requirements, not achieved research results.
- Mapped R05 **MONAI 1.5.1**, inspected tagged
  [`metrics/hausdorff_distance.py`](https://github.com/Project-MONAI/MONAI/blob/1.5.1/monai/metrics/hausdorff_distance.py):
  read input binarization, spacing treatment, directed/symmetric choices, reduction
  and empty-distance behavior. Its symmetric implementation takes the maximum
  directional percentile; the CancerOS protocol below deliberately chooses the
  percentile of concatenated directions instead and labels that exact definition.
  No equivalence claimed, no MONAI/Torch dependency installed, no code copied.
  Inspected file header declares Apache-2.0; no checkpoint/dataset rights inferred.
- SciPy **1.17.1**, inspected tagged
  [`spatial/_ckdtree.pyx`](https://github.com/scipy/scipy/blob/v1.17.1/scipy/spatial/_ckdtree.pyx),
  cKDTree/query public interface and nearest-neighbor parameters. Versioned 1.17.1
  generated-document URLs were inaccessible; **1.17.0** query documentation was
  accessible and separately labelled as such. Exact public calls use k=1, Euclidean
  p=2, eps=0 and workers=1. Tagged source plus executed installed 1.17.1 fixtures
  establish the actual interface used, not the inaccessible documentation.
- NumPy **2.4**, [percentile documentation](https://numpy.org/doc/2.4/reference/generated/numpy.percentile.html):
  read explicit `method='linear'`, percent range, equal sample weights and default
  nonmutating behavior. Installed **2.4.6** is pinned. Fixture `[0,0,1,...,9]`
  independently gives a 95th percentile of 8.5 under this definition.
- Existing SciPy 1.17.1 label/binary morphology and software-license inspection
  from COS-028 applies: six-connectivity is explicit, not anatomical truth.
  The attempted primary metric-review article PMC4533825 and MONAI stable web
  documentation were inaccessible/browser-challenged; no article reading claimed.
  Mapped textbook/lecture metric chapters were not newly read. No authentic reference
  cohort, independent Slicer result or model effectiveness was evaluated.

## Three-source decision and pinned protocol

Protocol separation of validity/accuracy → public pinned morphology and exact
world-point nearest-neighbor interfaces → no genuine independent reference available →
enable technical QC while leaving real accuracy eligibility blocked by parent policy →
verify hand-counted overlaps, physical distances and explicit failures on artificial data.

`inspect_mask` validates a bounded, finite, integral, nonnegative mask against a
revalidated 3D canonical geometry. At most 32 positive labels, values at most 65535.
Counts, six-connected components and source image-face boundary counts are reported.
Multiple components remain intact and warn of possible multifocal regions; boundary
contact warns of uncertain extent, not automatic anatomical failure. No anatomical
size threshold, automatic component removal or clinical acceptance threshold exists.
Source association and anatomical review are not established by this pure function.

Empty masks distinguish unrecorded meaning, missing annotation, processing failure
and caller-evidenced confirmed absence. Confirmed absence can pass only technical
empty-label policy with an explicit evidence warning; the parent must independently
verify any actual absence review and currently supplies no such human signoff.
Nonempty pixels conflict with a declared absence/failure. Invalid inputs return
failed QC with unknown counts rather than fabricated zeros.

`evaluate_masks` accepts two selected-label binary masks already on one validated
grid. Reference suitability/independence are server-owned gates. Missing reference,
unestablished independence and declared/same-object self-comparison are excluded.
Equal-valued independently annotated masks are not automatically declared fraudulent;
the parent must verify their provenance and independence, not infer it from bytes.

Metric version **segmentation-metrics/1** defines:

- Dice = 2×intersection/(candidate count+reference count).
- HD95 uses six-connected boundary **voxel centers**, not voxel faces or mesh
  surfaces. Map centers through the full RAS-mm affine, find exact nearest distances
  in both directions, concatenate samples and take the linear 95th percentile.
  Full affine treatment preserves shear; axis-spacing-only distance transforms do not.
  No surface-area weighting or equivalence to MONAI's directional maximum is implied.
- Physical volume error uses count difference times the absolute spatial determinant,
  with final nine-place decimal-string rounding. Relative error divides by positive
  reference count only; zero reference is null.
- Both-empty Dice/distance are null and correct absence is counted separately.
  One-empty Dice is zero, distance null and failure count one. Invalid/resource
  failures remain in eligible attempted-case counts. No NaN-based silent reduction.
  Surface sets are capped at 100,000 points each; exceeding this records a failure
  and no score. Large physical totals beyond shared quantity range fail explicitly.

Every result carries one attempted case, eligible attempted/scored/failed/correct-
absence counts, exclusions and software/metric definition. Scored cases count only
nonempty valid pairs; absent/invalid cases remain visible. No cohort aggregation or
model enablement is inferred from these per-case arithmetic results.

## Actual checks and remaining work

Executed `uv run pytest tests/test_segmentation_qc.py -q`: **20 passed**. Covered
hand-counted Dice=0.5, 24 mm3 volume error, anisotropic 2 mm distance, sheared
sqrt(18) mm distance, concat-percentile 8.5 fixture, all empty cases, no-NaN
serialization, missing/self/nonindependent reference guards, malformed geometry,
invalid labels, absent metadata, constant masks and counted resource failures.
Ruff check/format and focused mypy passed. Parent owns persisted attempts/QC events,
current source/annotation rights, reference ownership/evidence and API contracts.
Independent real accuracy evaluation and qualified anatomical review remain missing.

Hackathon impact: deterministic local QC only; no model inference, clinical advice,
source publication, accuracy claim or competition eligibility established.
