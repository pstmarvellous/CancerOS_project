# COS-AUDIT-002 Pre-Testing Readiness Decision

**Run:** `cos-audit-002-arch-001` · **Candidate:** `bd7b2c2` · **Date (UTC):** 2026-11-01

## Decision: READY_WITH_RESTRICTIONS

Formal testing may proceed **only** within the restricted scope below. This is a permission to test, not a product pass and not clinical validation.

### In scope for formal testing now

- Backend contract, persistence (with a running disposable PostgreSQL), worker, and frontend component suites on synthetic fixtures.
- Geometry, regression, plausibility, NLP, safety, and Phase 7 audit suites (19/19 + 20/20 verified in this audit).
- Static gates: boundaries, hygiene, ruff check, typecheck, lint.

### Restrictions (out of scope until their gates close)

- Real-data validation, qualified scientific review, and participant sessions.
- Live deployment, isolated restore with RPO/RTO, billed costs, declared-device trials.
- Live Model API calls (require explicit authorization + verified export policy).
- Any claim of clinical validity, certification, finalist status, or publication.

## Why not READY (unrestricted)

- No genuine two-exam longitudinal case (D02) — mandatory for full P0 readiness.
- No deployed target, isolated restore run, or measured recovery.
- One DB-backed identity test cannot pass without a local PostgreSQL instance (environmental, recorded).

## Why not NOT_READY

- No critical defect found: no secret exposure, identity corruption, false provenance, destructive path, or broken core workflow in the sampled paths.
- Architecture, isolation, provenance, grounding, and denial controls verified on fixtures with evidence.
- All open gates are honestly recorded as blocked with owners, not hidden.

## Evidence

- `ARCHITECTURE-INTEGRATION-AUDIT.md`, `SEVEN-PHASE-REVIEW.md`, `CLEAN-CODE-AUDIT.md`, `KNOWLEDGE-MAP-COMPLIANCE.md`, `META-API-SECURITY-AUDIT.md`, `REMEDIATION-BACKLOG.md` (this package).
- Phase 6/7 evidence indices and the task ledger (`implemented_unverified: 78`, `verified: 15`, `blocked: 9`, `planned: 2`).

## Next actions

1. Stand up disposable PostgreSQL and rerun the full DB-backed suites before any release claim.
2. Work the remediation backlog in risk order (CC-01/02/04 first).
3. Close D02, restore, deployment, review, performance, and participant gates through COS-103/104 with a new candidate fingerprint.
