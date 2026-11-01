# COS-AUDIT-002 Clean-Code Audit (highest priority)

**Run:** `cos-audit-002-arch-001` · **Candidate:** `bd7b2c2`
**Standard:** the codebase must be maintainable, testable and extendable without accumulating complexity. Subjective style preferences are not findings.

## CC-01 — Oversized modules and functions (MEDIUM)

- **Location:** `src/canceros/imaging_api.py` (`imaging_routes`, 576 lines), `src/canceros/clinical_api.py` (`clinical_routes`, 470 lines), `src/canceros/twin_states.py` (41,394 bytes), `src/canceros/imaging_jobs.py` (`_process_locked`, 285 lines); 42 backend functions exceed 100 lines.
- **Evidence:** AST line-span scan, 2026-11-01.
- **Consequence:** route assembly and job-processing paths are harder to review and test in isolation.
- **Remedy:** extract per-resource route builders and split `_process_locked` by stage; no behavior change.
- **Effort:** M. **Regression risk:** low with contract tests. **Rule:** engineering maintainability.

## CC-02 — Route-handler duplication across API modules (MEDIUM)

- **Location:** repeated `session`-style dependency helpers across `clinical_api.py`, `context_api.py`, `evaluation_api.py`, `evidence_api.py`, `grounding_api.py`, `imaging_api.py`, `interpretation_api.py`, `knowledge_api.py`, `patient_api.py` (83 duplicate local function names repo-wide, mostly narrow helpers such as `session`, `detail`, `execute`).
- **Evidence:** name-collision scan; most are small module-local helpers, not shared domain logic.
- **Consequence:** low direct risk, but onboarding cost and drift surface for auth/session handling.
- **Remedy:** consolidate shared FastAPI dependencies into one tested helper module; keep domain handlers local.
- **Effort:** S–M. **Regression risk:** low. **Related:** COS-102 backlog (accepted, not yet scheduled).

## CC-03 — Unformatted files (LOW)

- **Location:** 20 files fail `ruff format --check` (formatter-only diffs, e.g. `src/canceros/context_runs.py:67`).
- **Evidence:** `ruff format --check src tests scripts workers migrations`, 2026-11-01.
- **Consequence:** diff noise; no behavior risk.
- **Remedy:** run `ruff format` on the listed files in a remediation task.
- **Effort:** S. **Regression risk:** none.

## CC-04 — Broad exception handlers (MEDIUM)

- **Location:** 17 `except Exception` sites, including `src/canceros/api.py:64`, `src/canceros/export.py:56`, `src/canceros/imaging_formats.py:185,431`, `src/canceros/imaging_geometry.py:69,248`, `src/canceros/imaging_jobs.py:758,906`, `src/canceros/jobs.py:227`, `src/canceros/readiness.py:20`, `src/canceros/provider_gateway.py:132,278,340`.
- **Evidence:** grep, 2026-11-01. Most convert to stable safe failures (`ProviderFailure`, `GeometryError`, HTTP statuses) rather than leaking internals.
- **Consequence:** correct fail-closed behavior today, but broad catches can mask new error modes.
- **Remedy:** narrow to documented exception types per call site with a regression test per change.
- **Effort:** M. **Regression risk:** low–medium; cover with existing negative tests.

## CC-05 — Large frontend components (LOW–MEDIUM)

- **Location:** `case-workspace.tsx` (596 lines), `state-timeline-explorer.tsx` (420), `lesion-viewer.tsx` (401), `clinical-charts-explorer.tsx` (350); largest backend modules listed in CC-01.
- **Evidence:** line counts, 2026-11-01. Components are single-concern explorers with bounded state, not god objects.
- **Consequence:** review cost; no duplicated scientific calculation found in the browser (volumes, centroids and comparisons come from server contracts).
- **Remedy:** extract sub-panels per concern when touching these files next; do not rename public routes for style.
- **Effort:** M. **Regression risk:** low with component tests.

## CC-06 — No duplicated scientific or provider logic found (strength)

- Single volume path (`exact_voxel_volume` in `physical_measurements.py` reusing the stored-affine determinant, cross-checked by `imaging_geometry.py` validators), single mesh reconstruction entry, single simulation registry, single provider adapter. No competing tumor-volume, provenance, or Meta-API implementations found.

## CC-07 — Dependency hygiene (LOW, monitor)

- Lockfiles present (`uv.lock`, `package-lock.json`); no unpinned critical-path additions found in this pass. No dependency upgrade performed by this audit. Known-vulnerability scan with reliable advisory data not run — recorded as a remediation backlog item, not a finding of a specific CVE.
