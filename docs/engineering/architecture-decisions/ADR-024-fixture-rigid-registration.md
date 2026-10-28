# ADR-024: explicit rigid landmark registration, genuine-pair gate open

COS-037, 2026-10-28. SPEC-005 §10, SPEC-010 privacy/provenance, SPEC-011 genuine
longitudinal evaluation and audit D02 apply. No permitted real two-exam pair exists.
Implement fixture-tested infrastructure; genuine-pair acceptance and anatomical
overlay remain false for every enabled report, even a successful numerical fit.

The starting method is paired physical landmark rigid Kabsch, not an intensity
optimizer or deformable registration. SciPy1.17.1 aligns centered moving b to fixed a;
translation restores the centroids. Store moving_RAS_mm→fixed_RAS_mm and inverse
explicitly. This differs from SimpleITK's fixed→moving resampling convention; mask
adapter constructs its own inverse pull transform and nearest-neighbor labels.
Original image, masks and physical measures remain immutable. No image interpolation
is claimed. Optional mask preview is separate private pending-review output.

Four to32 unique full-rank fit points and1–32 held-out points (not reused within
1e-6mm) are required. Held-out numerical checks are not qualified anatomical review.
Freeze engineering limits: RMS≤1mm, max residual≤2mm (fit and holdout), rotation≤60°,
matrix translation norm at declared RAS origin≤150mm, roundtrip≤1e-5mm. Reject
singular/reflected/scaled/nonfinite transforms and degenerate geometry; these limits
are not clinical thresholds. World-axis-aligned image-bound overlap≥0.1 is only a
numerical guard, not anatomical overlap, correspondence or scientific acceptance.

Only administrator engineering attestations are enabled. Owned images must be
synthetic, three-dimensional selected acquisitions, distinct study IDs of the same
patient and same known sequence. Same-exam phases and reversed/equal relative time
fail. Relative days are explicitly engineering assumptions, never observed exam
dates. Real-source reviewed identity/time/sequence and overlay review remain missing.

Optional selected annotation must belong to moving image and have current QC. Its
exact QC report UUID is paired in input and frozen into job resource pins. A later QC
attempt causes a stale request to fail closed, rather than selecting the latest head.
QC withdrawal propagates to preview/report/result lineage. Reports preserve history.
Poor registration blocks spatial use but does not invalidate independently valid
scalar measures; temporal lesion identity/comparability remain separate (COS-038).

Raw landmarks live only in the private job input manifest. Exposed provenance gets
request hash, method/policy, input IDs, pinned QC ID, revision and evidence hash;
never raw fit/holdout coordinates. Numerical report exposes transforms and residuals.
Migration0028 adds immutable owned reports. Shared worker command `registration`
and GET registrations/{id} are generated into OpenAPI/TypeScript. No publication.
Evidence: registration.json and known-transform, failed/inverted/low-quality,
same-exam, ownership, unchanged measurement, QC pin/withdrawal and HTTP/worker tests.
