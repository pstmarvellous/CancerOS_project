# ADR-005: restricted patient linkage

2026-10-27; SPEC-003/008/010, COS-017. Engineering self-review only.

Patient UUIDs and random Research display codes carry no source identifiers.
Private lookup namespace is project + pinned release UUID. Matching source strings
in distinct releases create distinct patient identities until an explicit review.
No demographic/date matching or destructive patient merges are performed.

Versioned 256-bit keys are injected through private Settings SecretStr values.
Domain-separated HMAC-SHA256 keys protect exact lookups and AES-GCM encryption.
Each encryption uses a fresh random 96-bit nonce; authenticated associated data
binds project, release, mapping and key version. Ciphertexts and aliases are immutable.
Namespace advisory locks and unique digest constraints prevent concurrent duplicates.
An incomplete searchable key ring blocks new mappings; key loss is not a new patient.
No plaintext mapping export/decrypt endpoint exists. Logs contain method/status only.

Source-patient resolution, map summaries, rotation and identity review commands are
administrator only. Editor/viewer membership alone grants no patient data: explicit
patient grants are required. Later import commands must check patient grant plus
the pinned source action; they must not expose generic mapping access.

Same-person reviews are append-only events with confidence, evidence and server
actor/time. Corrections require the current predecessor; old events and patient IDs
remain intact. Each review increments both patient revisions and writes an audit
invalidation event. Downstream consumers must not treat stale identity evidence as
current. Confirmation is a reviewer assertion, not independent biological proof.

Rotation: install old+new private keys, select new active version, POST each mapping's
key-rotations command, verify all mappings have new aliases, then retire old keys
from the running service. Historical ciphertext/backup recovery still needs old keys.
Back up encrypted DB and separately protected key ring; losing both old and rotated
keys makes linkage unrecoverable. Never store keys alongside database exports.
Restoration and production key-custodian procedures need deployment review.

No runtime key is generated or logged by this feature. Missing keys disable linkage
with a typed status/action. Tests use ephemeral artificial keys/identifiers only.
No real de-identification, anonymity or external review is claimed.
