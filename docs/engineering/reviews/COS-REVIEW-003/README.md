# COS-REVIEW-003 — Independent Product & UI/UX Review Package

**Review ID:** COS-REVIEW-003  
**Date:** 2026-11-05  
**Reviewer:** Single-agent multidisciplinary (COS-000 persona)  
**Authority:** Original specs (PRD, SPEC-003–012, audit COS-AUD-001 as reconciliation where adopted), knowledge maps, academic map

## Deliverables (7 docs)

- `EXECUTIVE-PRODUCT-REVIEW.md` — intended vs delivered, verdicts, top 10 gaps, critical UX, recovery high-level
- `UI-UX-DEEP-REVIEW.md` — primary (40%) — first-time UX, IA, case management, intake, 3D viewer, simulation, AI, visual design, journey testing
- `SPECIFICATION-COMPLIANCE-MATRIX.md` — status taxonomy mapping: FULLY_IMPLEMENTED, IMPLEMENTED_BUT_NOT_ACCESSIBLE, PARTIALLY, BACKEND_ONLY, etc with files, entry points, evidence, UX impact
- `SEVEN-PHASE-PRODUCT-GAP-REVIEW.md` — what each phase delivered vs what became usable product
- `ARCHITECTURE-AND-INTEGRATION-REVIEW.md` — backend/frontend integration, contracts, DB, imaging, simulation, AI, auth, workers, provenance, error, complexity classification + minimal changes
- `USER-JOURNEY-FAILURE-MAP.md` — 9 journeys (first-time, token holder no case, clinical entry, imaging/3D, real scenario gen, demo success, charts/timeline, insights, guided demo) with repro, severity
- `PRIORITIZED-PRODUCT-RECOVERY-PLAN.md` — P0/P1/P2 ordered fixes with files, dependency order, verification criteria

## Method

Pass1: restored persona (`agent-persona.md`), read authority-and-scope, impl guide, KMAP COS-KMAP-001 (121 nodes), task ledger (106 tasks, 78 implemented_unverified, 15 verified), routes (18 pages), components (~30), backend modules (~90), global css, demo-workspace, research cases, lesion viewer, mesh renderer, simulation workflow, onboarding.

Pass2: inspected actual implementation: apps/web/app/page.tsx (home), cases, case-detail/workspace, twin, charts, simulation, insights, evaluation, activity, admin, demo, guided-demo; components case-creator, case-library, research-session, research-profile, observation-intake, clinical-charts-explorer, insights-explorer, lesion-viewer, mesh-renderer, simulation-workflow, demo-workspace, guided-demo; src/canceros modules imaging, persistence, patient, simulation, interpretation etc.

Pass3: UI/UX deep review with code-level reasoning (no live browser in this env but full code evidence). First-time session assumed fresh (no cookies/UUIDs).

Pass4–5: compliance matrix and architecture integration.

Pass6: root cause analysis via phase execution stubs (phase-4, phase-5) and task ledger.

Pass7: recovery plan.

## Key Conclusions

- **Overall:** Engineering substantial but product delivery fails first-time researcher journey; synthetic `/demo` is only coherent end-to-end (EVI) product path.
- **Safety/Scientific integrity:** PASS — provenance five kinds, immutable history, missing stays missing, physical mm correctness, no invented values, DCE≠visits respected, publication gates present.
- **Engineering quality:** PASS with complexity debt — 90 modules, idempotency, optimistic concurrency, secure transport checks, abort signal handling, role gating correct, but many run tables duplicate pattern, proxy inconsistency, session in-memory.
- **UI/UX:** FAIL — UUID leak, manual URL param dependence, dense forms, insufficient viewer prominence, engineering-private simulation, fragmented navigation, weak design system.
- **Most critical P0 blockers:** onboarding (token source unknown, no project creation guide), no unified case-centered workspace, manual UUID/token entry for twin and simulation, 3D viewer <40% viewport, no scenario builder (JSON handwrite), error states not actionable.

## Restrictions Compliance

- No source code modified during assessment — only docs under `docs/engineering/reviews/COS-REVIEW-003/` created.
- No specifications rewritten.
- No knowledge maps regenerated.
- No new requirements invented to justify implementation.
- Backed by file-level evidence (paths cited).

## Next Step

Review acceptance before implementation per prompt final instruction: "Do not begin further development until the review has established a coherent, evidence-based product recovery plan." Package now complete.

