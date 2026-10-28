# ADR-025: curated fixture lesion history and comparable scalar series

COS-038, 2026-10-28. SPEC-005 §10.7, SPEC-008 ownership/history, SPEC-009 comparisons
and SPEC-010 provenance govern this engineering slice. D02 genuine longitudinal
identity/time and qualified correspondence review remain open.

Stable patient-owned lesion UUIDs derive from an explicit baseline annotation, not
label value, centroid proximity or registration score. Administrator fixture review
appends per-annotation association versions. Superseding requires the latest event;
candidate/matched/unresolved/rejected/withdrawn and explicit related-lesion split/
merge relations retain evidence hashes, server actor/time and history. `matched`
means engineering attestation only; scientific review stays pending. No clinical
reviewer credential or biological identity is inferred from an authenticated role.

Enabled data are synthetic. Association times must be explicit simulation-relative
references to an owned timeline origin, or explicit unknown simulation time. They
are labelled engineering hypotheses, never observed source examination dates.
No date is inferred from revision, processing time or DCE phase. Current source
rights and single exact annotation measurements/QC are checked; unrelated-label
union measures cannot silently become a single lesion's volume.

Series capture latest per-annotation events across the patient before filtering by
lesion, preserving correction/movement between lesions. Freeze at most64 points;
retain unknown times and missing measurement references without fake UUIDs/zeros.
Each point keeps study, mask/hash, class, definition, annotation/measurement method,
units, origin and time group. Scalar arithmetic requires distinct exams, matched
same-lesion relation, compatible class/definition/method/origin/mm3 and strictly
ordered known times in the same group. Zero baseline permits absolute change but
no percentage. Unsupported numerical ranges are explicit gaps. No carry-forward,
RECIST, treatment causation or response classification is computed. Registration
does not gate otherwise comparable scalar arithmetic.

Snapshots are immutable. Read views separately report staleness from changed patient
event head, revision, rights or QC. Mapping corrections invalidate current use without
rewriting past numbers. Command replay retains old snapshots under current rights;
head/revision changes alone do not replace them. Future state assembly must call
load_usable_series for current use. Migration0029 enforces patient-owned FKs and
immutable records/relations. Publication remains separate and absent here.

Canonical lesion/association/series POST/GET routes, OpenAPI and generated TypeScript
are added together. Evidence: lesion-tracking.json; real private SQL/S3/HTTP fixtures
and Decimal comparison tests. Genuine source-time trajectories and scientific
correspondence acceptance are not established. Next: immutable state assembly.
