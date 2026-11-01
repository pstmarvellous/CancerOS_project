# COS-092 observability and cost runbook: visible failures, redacted telemetry.
# Liveness never restarts a healthy process for an optional provider outage.
# Readiness checks essential dependencies without revealing topology.

## Endpoints
- `GET /health/live` — public liveness, no auth, no dependency checks.
- `GET /health/ready` — restricted readiness, monitor token required; 503 when
  any essential dependency (PostgreSQL, queue, versioned bucket) is down.
- `GET /api/health` (web proxy) — operator check used by the home page.

## Correlation and redaction
- Correlate by request/job/attempt with environment, release/version, safe
  resource IDs (project/branch/state/run hashes and UUID prefixes), stage,
  error code and retry outcome.
- Audit events (`ops.audit_events`) stay separate from operational logs.
- Redact at source and exporter: no raw notes, prompts, model payloads,
  mappings, auth headers, secrets, signed URLs or unreviewed patient attributes
  in logs, traces or error screenshots. Patient-facing errors carry only a
  support/request ID, never a stack trace.

## Signals
- Request latency and error rates; queue age and depth; failed, retried and
  cancelled jobs; lease health; worker memory/CPU/disk; storage and DB growth;
  artifact misses; inference usage and grounding rejection counts.
- Accepted jobs stay distinct from completed, validated and published outputs;
  every denominator is named before a rate is reported.

## Budget ledger (estimates until billed measurements land)
| Line | Basis | Cap |
|---|---|---|
| Compute uptime/CPU time | staging host hours | authorized budget cap only |
| DB/storage/versions/backups | object bytes and version count | artifact limit 1MiB; growth alert |
| Network egress | grant bytes served | deny-by-default; grants 1-300s |
| Observability | log/trace bytes retained | bounded retention per data policy |
| Model calls | input/output tokens per accepted result incl. failures | token/rate/run ceilings; provider disable preserves reads |
- Verify current rates at implementation; record estimates versus billed or
  usage-based measurements. No assumed free credits. Budget alerts are not hard
  spending caps: enforced admission, concurrency, token and run ceilings plus a
  safe pause, scale-down and provider-disable path preserve published reads,
  immutable data and recoverability.
