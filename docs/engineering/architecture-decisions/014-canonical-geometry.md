# ADR-014: immutable canonical RAS-mm voxel-center geometry

COS-026, 2026-10-28. SPEC-005 P-01–04, SPEC-008 section 7 and SPEC-011
section 5 govern the owned CanonicalGeometry/GeometryReport contracts.

Keep XYZ array indices and original source bytes. Canonical world coordinates are
RAS millimeters; integer indices locate voxel centers and support boundaries lie
half a voxel beyond the outer centers. Converting DICOM LPS to RAS left-multiplies
the world affine by diag(-1,-1,1,1). Record the original affine, source frame/units,
conversion matrix and direction. Orientation labels indicate nearest cardinal axes;
they do not claim resampling or anatomical registration.

Validate finite affine/units, invertibility, positive bounded column norms, numerical
conditioning, handedness and coordinate round trips. Preserve oblique/reflected and
uniformly sheared grids. Voxel volume is abs(det(A spatial)), never the product of
column lengths for a sheared matrix. Decimal-string derived quantities use a
documented nine-decimal-place representation; float64 matrices preserve transforms.
Bounds and 1e-5-mm round trips are versioned engineering fixtures, not clinical limits.
Irregular/missing/duplicate slice arrangements and conflicting coded NIfTI q/s
transforms are quarantined by the source parser, with no invented reconstruction.
Uniform missing slices cannot be discovered without trustworthy source evidence;
consistent spacing alone does not prove complete acquisition.

Confirmed imports can produce an immutable private float64 NPY array (no pickle),
geometry report and geometry/1 technical-validation event. The source association
manifest is a lineage parent, preserving all source rights and withdrawals. Replays
return the same validation, with current rights checked; reads of historical reports
remain possible, while actual array use verifies private bytes/current authorization.
Database foreign keys bind reports/imports/artifacts to the same patient.

POST/GET geometry-validations expose safe physical metadata and actionable status.
No image/header bytes or private source identifiers are returned. A technical pass
does not establish annotation meaning, anatomical accuracy, publication or alignment
between examinations. Real source rights and qualified review remain unestablished.
Storage limits may block large canonical arrays; no hidden limit increase is made.

Evidence: imaging-geometry.json, pure independently calculated geometry fixtures,
SQL/private-S3 persistence and actual authenticated in-process HTTP checks. Next:
COS-027 minimal versioned preprocessing. Optional models remain disabled.
