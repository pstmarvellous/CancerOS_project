# COS-REC-08 reference context

Scope: assigned implementation task; specialist self-review through architecture,
data-integrity/security and verification perspectives; no independent clinical review.

Queries executed: usability, navigation, accessibility against capability, academic and repository/scientific maps.
Exact commands, output, IDs and incoming/outgoing dependency/guard/verification edges:
[COS-REC-08.json](COS-REC-08.json). Unmatched queries are gaps, not successful source reviews.

Original specification sections inspected: prompt_9 product design; SPEC-009 UI/UX; SPEC-007 architecture; SPEC-010 safety.
Agent guidance: COS-000 sections 3–8/11; repository instructions sections 2–8;
COS-REF-001 sections 2–3/15–23; COS-HACK-001 sections 2–3/9/11/17.

## COS-REC-08 implementation update (2026-11-09)

Scope: professional product/design refinement without backend or framework changes.
Specialist self-review: product design, UX writing, accessibility, frontend.

### Capability map (Knowlage_map_1)

Queries `usability`, `navigation`, `accessibility`: 0 capability nodes, 0 academic
behaviors, 0 edges (expected — the maps cover scientific/technical capabilities,
not product copy). Recorded as a map gap, not coverage. Governing source for this
task is COS-SPEC-009 plus the prompt table; authority-and-scope and
reference-consultation-policy applied.

### Findings (verified in a real browser, not assumed)

- Zero horizontal overflow at 1440×900 and 390×844 on homepage and the full demo
  journey (Day 37 selection, 64 mm³ verified against the served bundle).
- Zero overlapping or clipped primary controls at both widths; zero textboxes on
  public journeys (no UUID entry); keyboard Tab lands on a link/button.
- Gated `/cases` explains access with labeled credential entry only (no
  project/patient/UUID field).
- An initial 503 on `POST /api/demo-session` traced to the default Playwright
  config (no `CANCEROS_SYNTHETIC_DEMO=1`, API down); the remediation harness
  (`playwright.remediation.config.ts` pattern) serves the demo cleanly. No UI
  defect; harness documented.
- Existing `ux-recovery.spec.ts` asserts superseded homepage copy
  ("Evolution in 3D", "Launch Digital Twin Demo") — pre-existing drift in
  another workstream's file, left untouched; the new REC-08 spec covers the
  current copy.

### Changes (surgical, meaning preserved)

- User-facing "persisted state(s)" → "saved timepoint(s)" in the states page,
  timeline explorer, insights explorer, workspace timeline copy and guided-demo
  step title. Deliberately kept: "authorized" (access semantics), "source-backed"
  (provenance guarantee), "fixture-tested"/"snapshot hash" (already in technical
  details), "persisted snapshot" (contract-adjacent immutable-record term), all
  code identifiers.
- New `playwright.rec08.config.ts` (demo-enabled port-3001 harness mirroring the
  remediation pattern) and `tests/browser/rec08-usability.spec.ts`: overflow,
  overlap/clipping, UUID-entry, keyboard-focus, gated-state and screenshot
  evidence at desktop + 390px widths.
- Updated 3 test assertions for the new copy (2 files, directly required).

### Blocked / remaining

Live authenticated journeys need the product API + fixture bundle (unavailable
here); unit/component/route coverage plus the public-surface browser probe is
the evidence. UX-04/05/07/08/09 manual and UX-18 measurement sessions remain
open per the existing UX checklist. Before/after screenshot pairs across the
full prompt list (8 screens) not produced — after-shots recorded for homepage,
demo (both widths) and gated cases; no visual change was made to those screens
beyond copy, so no visual regression is claimed or hidden.

### Hackathon Compliance Impact

Preservation, source privacy, truthful contribution records. No external request.
Architecture preserved; changed files and checks in the task ledger (COS-REC-08).

## Hackathon Compliance Impact

Applies to preservation, source privacy and truthful contribution records. No external
model request is authorized by this task record. Models/rules/access remain unverified.
Architecture is preserved; refer to the task ledger for changed files and actual checks.
