# ADR-018: technical segmentation QC and explicitly eligible accuracy metrics

COS-031, 2026-10-28. SPEC-005 7.5–7.7, SPEC-010 scientific integrity and
SPEC-011 sections 5–7 govern segmentation-qc/1.

Technical QC reuses owned geometry and label-specific mask readers. Check finite
legal labels, physical grid, extent, empty semantics, components and boundary contact.
Disconnected/multifocal regions are visible warnings, not silently deleted lesions.
Missing annotation, processing failure and documented absence are distinct. The API
does not accept an unsupported assertion of confirmed absence or qualified review.

The pure metric implementation supports independently suitable binary references:
Dice, absolute/relative physical volume error and symmetric HD95. Freeze HD95 as
the linear 95th percentile of concatenated bidirectional nearest-neighbor distances
between six-connected boundary voxel centers, transformed by the full RAS-mm affine.
Use pinned SciPy cKDTree/NumPy with single-worker exact queries and bounded surface
points. This definition differs from a continuous triangulated surface distance.
Both-empty and one-empty cases have explicit counts; undefined distance/zero-reference
relative error are null, never NaN or fabricated zero. No universal clinical cutoff.

Server checks reference eligibility independently from technical checks. Imported
fixture objects have no qualified authentic-reference review. Actual API requests
therefore report independent accuracy not_evaluated; self/shared-mask comparisons
are explicitly excluded. Different IDs do not prove independence. Pure known-distance
fixtures verify formulas, not model accuracy or authentic breast MRI performance.

Each command key binds actor/patient/input hash atomically. Replays check current
source/output restrictions; a new command key creates a new retained attempt. Store
technical failures and per-case attempt/failure counts. Append a server-generated
technical-validation event and immutable QC report/lineage. Current annotation reads
derive technical status/capabilities from these events plus current rights; historical
metadata remains immutable. A technical pass can enable labeled numerical region
arithmetic, while anatomical/publication claims remain denied for fixtures.

POST/GET segmentation-qc-reports require patient edit authority. This API creates
draft research reports, not public publication. Source review, qualified annotation
acceptance and actual independent accuracy remain blocked by D01/D05. Evidence:
segmentation-qc.json. Optional COS-030 is not required. Next: COS-032 durable jobs.
