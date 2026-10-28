# ADR-010: immutable lineage and inherited restrictions

COS-022, 2026-10-27. The owned resource registry stores content hash, item origin,
source version or processing manifest, exact parent IDs/hashes/origins, config,
environment, seed/model reference when applicable and actual source-code hashes.
Private S3 object versions remain authoritative byte identity. No graph database or
cross-patient aggregate is introduced; multi-input same-patient outputs retain every
parent origin. All synthetic descendants remain synthetic. Predicted/interpolated
origins remain distinct when later enabled; no prediction capability is implied.

Current clinical uploads, CSV raw/derived artifacts and accepted observations register
lineage in their existing transaction. Graph FKs/immutability/cycle guard and service
ownership checks reject dangling, cyclic or foreign links. The service derives origin;
requested synthetic-to-real promotion fails. Earlier disposable test rows are not
silently backfilled as reviewed scientific sources and cannot enter new processing
without complete lineage. Engineering.digest remains an isolated nonclinical fixture.

New use checks all ancestor component rights and withdrawal events. Processing and
rights writes take bounded transaction locks in a consistent patient/lineage/policy
order. Source-version changes do not rewrite old manifests. Withdrawal appends an
audited event, returns affected descendants and blocks subsequent processing/export/
publication through the shared eligibility service. Existing audit/history stays
readable to authorized operators; no old source result is silently relabeled.

Patient-scoped provenance GET and administrator withdrawal POST are real handlers.
They expose opaque source/processing references, never private object keys or mapping
ciphertexts. Idempotency replay rechecks role. Future publishing/export services must
call require_resource_action in their transaction; no such service is enabled here.

Source/processing hashes identify the current uncommitted implementation, not a
fabricated Git SHA. One deterministic adapter fixture is rebuilt from its pinned input.
Long-term archived code/environment restoration, qualified data review, lawful removal
of source/mappings/derivatives and backup-expiry handling remain deployment/retention
work. Append-only application history is not a promise to override required deletion.
Evidence: lineage.json and inherited storage/tamper/clinical revision tests.
