# scikit-image: bounded mesh adapter audit

COS-034/035, 2026-10-28. Adopt pinned0.26.0 dependency, not copied upstream code.
Installed `skimage.measure.marching_cubes` wrapper inspected with Python inspect;
API and versioned LICENSE.txt read. Guessed raw wrapper URL404 was replaced by
actual installed source inspection. Default package BSD3; versioned license lists
exceptions for other files. No model/checkpoint/dataset or annotation license follows.

Owned adapter reconstructs binary XYZ masks, one zero pad, iso0.5, unit index spacing,
step1 and Lewiner method. Apply original RAS/mm affine once; reflect winding and
recompute world normals. Canonical source masks/measurements remain authoritative.
Separate selected annotation IDs become distinct objects. Private mesh JSON transport
is a scoped addition under ADR-021, not implemented GLB/glTF export.

Independent cuboid, affine/reflection/shear and empty/invalid tests plus actual
private SQL/S3/Redis worker tests passed in mesh-reconstruction.json. Mesh topology
certification is the separate bounded convex-only policy in ADR-022; no general
clinical nonconvex/compound acceptance or Slicer cohort validation is established.
Data rights, anatomical review, largestudy/device and publication remain open.
Runtime/method pins: pyproject.toml and uv.lock; no fabricated upstream SHA.
