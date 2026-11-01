# COS-088 staging runbook: reviewable plan, guarded execution, honest status.
# No cloud account, credentials or spending authority are assumed. Complete the
# manifests and local validation below; record the remaining decision if the
# target is missing. Never invent a deployed URL.

## 0. Prerequisites (owner/evidence needed if absent)
- Authorized hosting account, region and budget cap for staging.
- Private `.env.staging` (never committed): MODE=staging, isolated postgres/redis/
  storage credentials, private loopback or VPC endpoints, CORS origins, and either
  EXTERNAL_INFERENCE_ENABLED=false or a verified export policy path.
- Pinned image digests recorded after build (immutable digest/config, not `latest`).

## 1. Build reproducible images (no secrets or patient data in images)
```powershell
docker build -f infrastructure/Dockerfile.api -t canceros-api:cos088 .
docker images --digests canceros-api
docker build -f infrastructure/Dockerfile.web -t canceros-web:cos088 .
docker images --digests canceros-web
docker build -f infrastructure/Dockerfile.worker -t canceros-worker:cos088 .
docker images --digests canceros-worker
```

## 2. Validate configuration before any cost-bearing apply
```powershell
uv run --python 3.12 python scripts/check_deployment_config.py --env-file .env.staging --topology staging
```
Expected: typed missing-config diagnostics with exact variable names; non-zero exit
lists every gap and names the owning decision. A local pass is configuration
validation, not cloud-deployed evidence.

## 3. Guarded staging start (only with an authorized target)
```powershell
docker compose -f infrastructure/compose.staging.yaml --profile staging up -d
docker compose -f infrastructure/compose.staging.yaml ps
curl http://127.0.0.1:8000/health/live
docker compose -f infrastructure/compose.staging.yaml --profile staging down
```
Record: image digests, chosen CPU/memory, startup status and health outcomes.
Startup alone never authorizes public promotion; COS-089 through COS-093 gates
stay closed until their evidence lands.

## 4. Environment separation matrix
| Concern | Development (.env) | Staging (.env.staging) |
|---|---|---|
| Identity/secrets | local loopback only | isolated staging credentials, never copied |
| Database/schema | canceros_dev | separate staging database; guarded one-time migrations |
| Buckets/prefixes | canceros-private dev prefixes | isolated staging bucket/prefix with deny-by-default policy |
| Queue namespace | local redis DB | isolated staging namespace |
| Allowed origins | http://127.0.0.1:3000 | staging origin allowlist only |
| Seed data | safe local fixtures | explicit safe fixtures or permitted curated manifests only |
| Inference | EXTERNAL_INFERENCE_ENABLED=false | false unless verified export policy and budget exist |

Bounded staging estimate: ~4 vCPU / ~6 GiB across six services before object data;
measure actuals on the chosen host. No GPU, Kubernetes or paid tier is required by
this topology. If Docker is absent, this task remains a reviewable plan with the
exact remaining decision: authorized account/target/spending authority.
