# ADR-020: mask-authoritative, revision-pinned physical region measurements

COS-033, 2026-10-28. SPEC-005 section 8, SPEC-008 section 7 and SPEC-011
section 5 govern physical-measurements/1. Numerical regions and anatomical claims
have different eligibility requirements; fixture contours cannot establish anatomy.

Explicit annotation UUID selection forms a voxel union without double counting.
All members require the same owned study/image/grid and current source permissions.
Known annotation meaning and current passing QC enable numerical region arithmetic.
Functional-region requests require that class. Anatomical tumor requests remain
unavailable without qualified authentic anatomical review. Missing/unverified empty
masks never become zero; only an independently verified absence can use the pure
absence calculation, and no API assertion of that evidence exists.

Use the absolute 3×3 affine determinant, not rounded spacings, times selected voxel
count. Decimal precision 80 operates on stored affine coefficient strings; divide
by 1000 for cm3. Preserve these calculation decimal strings separately from existing
numeric(24,9)-compatible quantity fields. The latter round half-even at the output
boundary, after multiplication, while exact_* metadata preserves the higher-precision
calculation. This additive calculation metadata does not redefine the shared Quantity
contract or claim anatomical accuracy at those digits. Display rounding is separate.

Centroid is the mean voxel-center position. Bounds are the world-axis-aligned union
of selected voxel-cell support, using the full affine, including shear/reflection.
Box extents are explicitly not RECIST or maximal lesion diameters. Registration,
response, prognosis and measurement uncertainty are not inferred. Unknown uncertainty
and acquisition-time availability remain explicit; private dates are not exposed.

Immutable JSONB reports bind patient revision, annotation IDs, labels, mask hashes,
QC validation/report IDs, geometry hash and method. Source masks remain authoritative
for later mesh display. A new request checks expected current revision; an idempotent
historical replay retains its original revision and rechecks use restrictions.
Unavailable reports replay consistently. Reads retain history; actual downstream use
must call load_usable_measurement rather than treating a historical DTO as permission.

QC evidence is a provenance parent. Its withdrawal blocks measurement use, makes
current annotation QC pending and stales capability reports, without rewriting old
technical results or numbers. This closes a dependency gap found during self-review.
No measurement automatically publishes a state or increments observed source history.

POST/GET physical-measurements and generated contracts expose definition, selections,
units and repair guidance. Evidence: physical-measurements.json, independent cuboids/
anisotropy/obliquity/reflection/shear/multilabel arithmetic and actual private SQL/S3/
HTTP history, ownership, rights and QC-withdrawal checks. Real measurements and qualified
review remain blocked by D01/C06. Next: COS-034 mask-to-mesh reconstruction.
