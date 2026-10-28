# Canonical geometry verification

After staging, previewing and confirming an artificial import as in
[import runbook](imaging-import-runbook.md):

```text
POST /api/v1/projects/{project_id}/patients/{patient_id}/geometry-validations
{"import_id":"<confirmed-import-uuid>","rule_version":"geometry/1"}
```

An authorized patient editor can run this operation; initial source staging and
association confirmation require administrator access. Read the returned Location
with GET. Repeated validation is stable. Reports show RAS/mm, voxel-center convention,
full affine, original source transform, physical spacing, handedness, determinant
voxel volume and measured numerical round-trip error. A valid result remains draft,
scientific-review pending and longitudinal-alignment not established.

```powershell
uv run python scripts/run_checks.py imaging-geometry
```

This runs guarded disposable migrations, pure geometry fixtures, private array and
ownership/rights tests plus authenticated HTTP, type checks and generated-client
drift checks. It does not establish authentic MRI performance. Canonical arrays use
the existing private storage cap; too-large arrays return 413 and preserve original
staged sources. No public read grant or publication action is created.

`index_to_world(geometry, points)` and `world_to_index(geometry, points)` use the full
affine, without applying spacing a second time. `convert_frame` explicitly converts
world coordinates while retaining index axes. The independent shear fixture checks
that spacing-product and determinant volume differ. Source parsing rejects unknown
units/qform-sform disagreement/irregular slices before confirmation. Supply verified
metadata or a separately reviewed reconstruction; never repair by guessing.
