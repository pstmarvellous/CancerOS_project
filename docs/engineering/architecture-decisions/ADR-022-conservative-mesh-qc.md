# ADR-022: conservative exact convex display QC

Adopted engineering scope for COS-035, 2026-10-28. SPEC-005 §9, SPEC-009 §7/14,
SPEC-011 §5 and audit D06/C06 apply. This is neither a general clinical mesh
validator nor a substitute for authentic-case review. No source mask is altered.

`mesh-display/1` freezes finite vertices, bounded valid triangular indices, unique
positions/faces, nonzero area, used vertices, unit/recomputed normals, actual bounds,
identity invertible physical display transform, two opposed uses per edge, connected
cycle per vertex link and connected-component/Euler reporting. Small components are
counted and retained, never silently deleted.

Self-intersection exclusion is limited to one closed oriented genus-zero convex
shell. Exact cross/dot predicates operate on the binary64 coordinates represented
as integers on a common power-of-two lattice, with zero support slack. Confirm an
independent SciPy1.17.1 ConvexHull contains all positions using the same predicates,
and require exact signed six-volume equality to reject geometric multiple covering.
At most 500k face×point products per check. Nonconvex/compound/over-budget cases
retain artifacts but have no display approval or mesh-volume claim. A future robust
general intersection validator is an outstanding dependency, not a passed check.

The bounded simplifier retriangulates that same convex hull. Candidate vertices are
a subset of original positions; exact candidate support of all original positions
establishes equality of the convex body. Accepted geometric displacement is zero.
No smoothing or shape-changing decimation is enabled. Also freeze numerical display
limits: bounds and volume-centroid differences≤0.05mm, volume difference≤1%; these
are engineering comparisons, not clinical thresholds. Mask-vs-original volume
difference is reported separately and never overwrites authoritative voxel volume.
Vertex centroid is diagnostic; comparison uses enclosed-volume centroid.

LOD artifacts have separate immutable IDs and processing implementation hashes.
Choose the reduced certified LOD automatically, otherwise a certified original.
If triangle budget cannot be met, retain certified higher detail and return guidance;
if certification fails, select none and retain valid source measurements. All
annotation memberships, origin and physical coordinates remain. Publication/scientific
review stay draft/pending. SQL migration0027 binds immutable owned QC reports.
Both output and QC-report resource rights are rechecked at display asset access.

Shared CPU worker adds `mesh_qc`, with code/config/resources pinned and result lineage
including the QC report. GET mesh-qc-reports/{id} and /asset expose the contract;
OpenAPI/TypeScript regenerated. Tests include fold and double-cover defects actually
found during separate AI critical review, plus invalid/open/degenerate/nonmanifold,
compound objects, real private SQL/S3/Redis LOD and immutable measurement checks.
Evidence: mesh-quality.json and mesh-fixture-measurement.json. Target-device browser
load, peak memory, representative masks and qualified review remain unverified.
