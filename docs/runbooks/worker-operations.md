# COS-090 worker runbook: bounded CPU execution with durable job semantics.
# Imported-mask and deterministic paths stay usable without GPU or live inference.

## Entrypoints and kinds
- Digest (engineering queue batch): `uv run python -m workers.digest` — at most
  25 transport entries per invocation; SQL records authoritative status.
- Imaging (one job per supervised child): `uv run python workers/imaging.py --help`
  — wall limit 120s, RSS limit 512MiB; only caller-owned children monitored.
- Resource classes stay distinct (ingestion, imaging, simulation,
  interpretation) even when one process handles multiple kinds.

## Limits (starting bounds on the 8GB target)
| Kind | Concurrency | CPU/RAM/time/disk | Queue/admission |
|---|---|---|---|
| Digest | 1 process, 25/batch | OS scheduling; bounded batch | redis list; noeviction 64MB |
| Imaging child | 1 job per child | 120s wall, 512MiB RSS kill, no stdout capture | explicit job record required |
| Simulation/interpretation | via API outbox dispatch | job_max_attempts 1-3; bounded payloads | frozen manifests pin inputs/revision |

## Durability rules
- Transactional outbox dispatch; at-least-once handling with idempotent
  artifact finalization; stale-lease rejection; cancellation and
  dead-letter/quarantine diagnosis.
- Frozen job manifests pin exact inputs, config and data revision; no retry
  against mutable heads. A worker completes ready outputs; publication stays
  separately guarded in COS-064/COS-068 flows.
- Graceful shutdown: finish the current entry, drain, then exit. Rolling
  deployment requires compatible app/schema versions; never start workers on an
  incompatible schema.
- Abandoned leases recover safely; prior successful output is preserved; no
  duplicate publication or duplicate provider billing where controllable.

## Inference gating
- Egress and policy checks run immediately before inference and every retry.
- Token, rate and budget caps plus circuit breakers configured per deployment.
- Disabled or unavailable models use the permitted honest local mode or return a
  clear failure. No automatic expensive fallback, model download or local neural
  training on the 8GB target.
- Residual uncertainty: an external call that times out after transmission may
  have executed remotely; never promise exactly-once provider execution.

## Operator visibility
- Stage, attempt, queue/lease status and safe retry/cancel actions surface in
  existing Activity and operator tools. Unknown progress stays indeterminate;
  leaving a page never cancels the durable job.
