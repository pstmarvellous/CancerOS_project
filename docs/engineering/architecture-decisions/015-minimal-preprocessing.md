# ADR-015: source-preserving, single-volume CPU preprocessing

COS-027, 2026-10-28. SPEC-005 P-01–08, SPEC-003 sequence meaning and SPEC-011
reproducibility/leakage govern this bounded preprocessing/1 adapter.

Start with identity preprocessing, preserving every original voxel and affine.
An optional per-volume z-score uses all voxels of one selected acquisition, population
standard deviation (ddof=0), float64 parameters and a pinned NumPy environment.
These numerical intensities have no calibrated perfusion or biological meaning.
No crop, resampling, bias correction, model, channel fabrication or cohort fit is
enabled. A requested missing/unknown sequence blocks rather than substitutes.

T1/T2/other-MR process independently. Explicit DCE phase selection requires an index,
ordered acquisition offsets, source evidence hash and a declared role, which may
remain unknown. These are source assertions, not motion/alignment approval. Select
one phase only; voxelwise combination, subtraction or temporal perfusion is disabled
until within-exam correspondence is actually reviewed. DCE phases never create visits.
Constant/all-zero volumes remain representable under identity with warnings; z-score
blocks if variance is unsupported. Nonfinite or excessive numerical intensity fails.

Input arrays are read-only, private, hash-verified and source-authorized. Persist a
new immutable private output plus full config, numerical parameters, input/output
hashes, spatial frame and code/environment lineage. A blocked run retains a safe
report and no usable output. Replays check current rights. Owned composite foreign
keys bind both artifacts to the same patient. No report is a scientific approval.

There is no cohort-fitted operation to bypass a split guard. Existing COS-024
require_fit_access remains mandatory for a future learned fit; held-out leakage
tests run with this task's checks. Extra unsupported config fields are rejected.
Real-source/sequence validation, representative normalization evaluation and qualified
review remain blocked by D01/D05. Minimal imported-mask processing needs no GPU.

API: POST/GET patient preprocessing-runs. Evidence: imaging-preprocessing.json,
artificial numerical fixtures and actual PostgreSQL/S3/authenticated HTTP checks.
No public bytes, publication or inference were added. Next: COS-028 mask alignment.
