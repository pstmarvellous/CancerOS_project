# COS-089 storage, backup and restore policy: enforceable rules, honest status.
# No irreversible retention lock is applied without an approved deletion-duty
# review. Withdrawal, access denial and deletion are distinct operations.

## Roles and access
- App/worker/backup use isolated credentials with least privilege: read/write
  only their environment bucket and prefix; no bucket listing, no delete of
  versioned source objects, no cross-project reads.
- Storage credentials live in the private environment file only, never in
  images, logs, reports or bundles.

## Immutability and versioning
- Bucket versioning required; every artifact resolves by (key, version, sha256,
  byte size). A restored SQL row must resolve its exact object version.
- Source overwrite is denied by versioned keys plus server-side checks, not by
  checksums alone. Historical revisions and branch baselines stay reconstructable.

## Grants
- Reads use manifest-backed grants scoped to one artifact version and project,
  expiry 1-300 seconds, renewable only through a new authorized grant.
- No public listing, no raw object-key exposure. An issued signed URL may work
  until expiry; immediate revocation needs a tested authenticated proxy or
  provider feature, never a database flag alone.

## Retention (proposed operational defaults, not statutory periods)
| Class | Default | Rights reference |
|---|---|---|
| Accepted raw source data | retain while rights permit | source registry permission evidence |
| Derivatives (meshes, previews, sampled observations) | retain while parent retained | lineage parent hash |
| Quarantined uploads, abandoned | sweep after 7 days | ingestion quarantine record |
| Temporary exports | sweep after 24 hours | export manifest and grant expiry |
| Audit records | retain per review policy | governance evidence |
| Backups | per backup schedule below | backup manifest and key-recovery record |
- Withdrawal removes future access but keeps audit history; deletion removes data
  including caches, descendants and expired backups per approved duty; access
  denial blocks reads without deleting. Never sweep a referenced object version
  as an orphan: sweep only unreferenced temporary/quarantine classes.

## Backup and recovery targets
- Nightly database backup plus referenced object-version/manifest protection.
- RPO <= 24h, RTO <= 4h for staging; owner: platform; key recovery through the
  approved secret path only.
- A successful backup job is not proof of restore: recovery stays Blocked until
  an isolated restore with byte/hash, lineage, revision and grant checks lands.
