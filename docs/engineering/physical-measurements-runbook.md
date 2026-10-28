# Physical region measurements

Run technical QC for each selected imported annotation, then submit as a patient editor:

```text
POST /api/v1/projects/{project_id}/patients/{patient_id}/physical-measurements
Idempotency-Key: explicit-region-union-1
{"expected_revision":1,"segmentation_ids":["<owned-annotation-uuid>"],"definition":"numerical_region_volume"}
```

GET the returned Location for immutable quantities, exact calculation metadata,
centroid, support bounds, explicit selections, source time basis and provenance.
Multiple UUIDs explicitly request their union on the same study/grid; overlaps count
once. functional_region_volume requires functional annotations. Anatomical claims
stay unavailable where scientific review is missing. Unavailable values are null.
Standard nine-decimal quantities coexist with higher-precision exact_* calculation
metadata; neither implies that segmentation uncertainty was quantified.

```powershell
uv run python scripts/run_checks.py physical-measurements
```

Checks cover independently calculated cuboids, full affines, units, missing/absence,
zero denominators, masks with multiple labels, revision history, rights, QC withdrawal
and authenticated HTTP. No RECIST, diagnosis, response classification or real-case
validation is claimed. A mesh must retain these mask measurements as authoritative.
