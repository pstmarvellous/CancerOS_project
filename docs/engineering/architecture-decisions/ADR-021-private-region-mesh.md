# ADR-021: private CPU region surfaces

Adopted for the authorized COS-034 engineering slice, 2026-10-28. SPEC-005 §9,
SPEC-008 §7, SPEC-009 §7/14 and SPEC-011 §5 govern scientific meaning, access and
measurement authority. This decision adds a bounded internal transport; it does
not claim the specified GLB/glTF export or full viewer acceptance is implemented.

Use pinned scikit-image 0.26.0 Lewiner marching cubes (BSD-3-Clause package default;
license file separately lists exceptions). Use the installed wrapper inspected at
this release, not a copied implementation. VTK/glTF export adds integration weight
unnecessary for the current small private engineering preview and is deferred.

Owned `canceros-mesh-json/1` has objects keyed by annotation UUID, retained label,
annotation class and exact source mask hash. Separate objects are never silently
merged. Membership is annotation identity, not a reviewed longitudinal lesion ID.
Vertices and recalculated normals are in RAS millimetres. Identity display↔patient
matrices are explicit inverses. No unit conversion, per-object normalization or
scientific measurement is performed by the browser transport.

Pad binary XYZ mask with one zero sample; iso-level 0.5, unit index spacing, step1,
Lewiner, no degenerate faces. Subtract padding and apply full source affine once.
Reflection reverses winding. Reject unsupported orientation/normals/resource size;
never substitute a box. Isosurfaces are approximations, especially for tiny masks;
canonical voxel measurements remain authoritative and unchanged.

Worker `mesh` input pins an available measurement and its immutable QC/mask lineage.
The manifest hashes both mesh modules and measurements; artifact lineage includes
implementation/lock hashes and configuration. Existing SQL idempotency, ownership,
leases, retry/cancel/resource limits apply. Migration0026 adds immutable owned mesh
runs. No automatic publication. Metadata history remains readable after withdrawal;
asset access rechecks current inherited rights. Authenticated `/mesh-runs/{id}/asset`
returns typed private content with no-store and no private storage key or signed URL.

50k vertices/100k triangles per combined asset and existing private byte cap are
engineering bounds, not representative clinical acceptance. Output is pending mesh
QC (COS-035), pending scientific review and synthetic origin. D01/C06 remain open.
Affected contracts: imaging command union, MeshInput/Report/Asset/Surface; runtime
OpenAPI and TypeScript regenerated. Tests: mesh reconstruction, mesh runs, existing
worker regressions. See mesh-reconstruction.json for actual results.
