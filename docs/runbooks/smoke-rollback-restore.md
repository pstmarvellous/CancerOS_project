# COS-093 smoke, rollback and restore runbook: exact commands, safe stops.
# No deployed target exists in this scope, so this is a rehearsed procedure
# with local fixture validation. Never claim a deployed URL or recovery proof
# from these checks alone.

## 1. Freeze the candidate (no untracked hotfix, no latest-image promotion)
```powershell
git rev-parse HEAD
docker images --digests canceros-api canceros-web canceros-worker
uv run --python 3.12 python scripts/check_contract_drift.py
```
Record: commit hash, image digests, schema/config/corpus/model versions,
environment, source/demo manifests and evaluated scope. Compare with the
COS-087 candidate report; rerun affected checks for any drift.

## 2. Smoke journey (clean supported browser and account, isolated project)
1. Login with an authorized viewer; confirm judge reads need no admin rights.
2. Open case and source metadata; confirm restricted views stay blocked.
3. Load private mesh grant; verify bytes resolve and expiry renews by new grant.
4. Open exact state, chart, table and valid comparison if eligible.
5. Open published branch, approved summary with evidence, and evaluator report.
6. Editor writes run only in an isolated project with an authorized presenter.
STOP: any protected source leakage, role bypass or broken journey blocks
promotion. Record cold starts, slow trials and hardware limits.

## 3. Failed rollout rehearsal and rollback
```powershell
docker compose -f infrastructure/compose.staging.yaml --profile staging up -d
docker compose -f infrastructure/compose.staging.yaml ps
docker compose -f infrastructure/compose.staging.yaml --profile staging down
```
- Roll back to the pinned prior compatible app image and config; never blindly
  downgrade a destructive migration or restore over current writes.
- Use expand/contract migrations or an explicit compatible recovery plan.
- Verify: no duplicate jobs or publications, no historical rewrites, no
  unrecoverable new-schema writes. Preserve writes and object references.

## 4. Isolated restore (from COS-089 policy)
- Restore into an isolated environment, never over current data.
- Recover keys through the approved secret path; verify exact artifact bytes,
  hashes and versions, lineage, revision N after N+1, published run pointers
  and source grants.
- Measure achieved recovery time and loss against RPO<=24h and RTO<=4h.
  A backup job alone never passes this gate.

## 5. Disposition
- deployed-and-recovered: all smoke, rollback and isolated-restore checks pass
  on the named target with versioned evidence.
- deployment-only: staging serves smoke but restore stays open.
- blocked: no authorized target, so this task stays blocked with the exact
  remaining decision (account, target, spending authority, restore window).
