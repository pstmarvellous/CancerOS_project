# ADR-026: immutable engineering states and explicit private publication

COS-039, 2026-10-28. Adopted C02/C03/C04 exact-membership/1 is implemented for the
authorized synthetic engineering slice. SPEC-004/005/008/009/010 retain scientific
authority. Genuine observed baseline and scientific acceptance remain blocked.

Synthetic states require an owned immutable branch. Enabled branches explicitly
pin an engineering baseline measurement/optional mesh-QC report hash, simulation
timeline origin and run UUID. observed_baseline_verified=false and baseline_state_id
is null; this is not the specified authentic published baseline or a simulation
engine. OBSERVED requests fail closed. No branch silently rebases.

Worker input selects target_revision and association_head explicitly. Clinical IDs
must belong to that exact immutable revision manifest. Associations must be latest
for their annotation at the supplied historical head, not today's head. Rebuilds
may use old revision/head; current-use/publication eligibility then reports staleness.
The shared worker captures resource/code pins and never substitutes mutable heads.
Typed snapshot members preserve original clinical record, measurement, annotation,
time, origin, units, source hashes and optional mesh QC. Provenance parameters carry
request hash rather than duplicating raw clinical values into lineage metadata.

Current member time equals the state anchor exactly. Historical context needs a
reason and retains its actual source time; known future members cannot be historical.
Unknown/private image time cannot become current. Same-time concept conflicts are
retained and block readiness rather than resolved by ID order. Missing modalities
stay explicit. Lab-only states reuse historical geometry without new mesh jobs.
No imputation, carry-forward, source date invention or clinical causality is added.

Build, technical readiness, administrator engineering review and private fixture
publication are separate. A successful job does not publish. Explicit publication
locks the patient/lineage and verifies snapshot hash, current patient revision,
association head, latest accepted review ID and current inherited rights/QC. A unique
publication row plus idempotent receipts protects repeat/concurrent commands. Later
corrections, rejected reviews or withdrawals affect eligibility views, never stored
snapshot values/publication history. Scientific review remains pending even when
scope=private_engineering_fixture is published. This is unrelated to publishing
the repository, dataset or a public site; none is authorized or performed here.

The earlier signed-cursor design is narrowed to server-backed opaque random tokens
for this implementation. Store only token hash, scope hash and immutable list manifest;
bind actor/project/patient/branch/filter/limit, revision and expiry. First page freezes
ordered snapshot IDs, subsequent pages use that exact list. No arbitrary client cursor
fields or new signing secret. Current authorization still applies on every read.
This is a documented transport decision, not a durable-history claim based on MVCC.

Migration0030 adds immutable branches/snapshots/membership/review/publication plus
scoped cursor records. Thin state API and generated contracts accompany the existing
shared CPU worker command state_assembly; no new service/queue. Evidence is in
twin-states.json, including N-after-N+1, frozen association history, exact time/no
carry/conflicts, historical mesh reuse, rights/QC, explicit publication and cursor
checks. Real baseline, longitudinal proof and qualified review remain open gates.
