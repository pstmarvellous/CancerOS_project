# ADR-027: bounded hypothetical volume geometry

Adopted for the isolated engineering implementation on 2026-10-28. This does not
approve scientific behavior, real source rights or the external simulation engine.

Each frozen test run pins a branch baseline hash, patient revision, association
head, explicit ordered relative times, targets and deterministic configuration.
Run authorization and execution require test mode. Development/production deny
generation until the authorized simulation engine contract is integrated.

The CPU algorithm scales a binary region isotropically about its physical RAS/mm
centroid. It pulls into the unchanged original grid with nearest-neighbor sampling
using the full affine. It checks cell-boundary clipping before sampling and measures
the resulting mask independently. Acceptance tolerance is the greater of one voxel
volume or 1% of target: an engineering bound, not a clinical accuracy threshold.
Unsupported geometry or failed mesh QC produces a blocked result, never a fallback
bounding box. Masks remain authoritative; mesh volume is not the requested metric.

Configured zero has no surface and uses `configured_simulated_absent`, distinct from
observed absence, cure or surgery. Every descendant remains SYNTHETIC_GENERATED
and displays Simulated. No follow-up study, scan, date or observed record is created.
Generated geometry is a separate typed state member, at most one per branch/time.
Ready or zero outputs create draft immutable states; review and private publication
remain separate explicit operations. Actual follow-up imaging remains unavailable.

Adding default generated-member lists preserves old persisted state hashes: the
provided snapshot hash refers to verified stored JSON, before later DTO defaults.
Consumers must use that server hash for review/publication rather than hashing a
reserialized expanded response. Legacy empty-member requests remain replayable.

This component does not implement the five scenario families, anatomical
containment, trained forecasting or independent scientific validation. Those require
the authentic baseline and later simulation policy/integration gates.
