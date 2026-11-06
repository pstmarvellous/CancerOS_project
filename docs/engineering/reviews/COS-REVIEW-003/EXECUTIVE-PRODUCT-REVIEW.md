# COS-REVIEW-003 — EXECUTIVE PRODUCT REVIEW

**Review ID:** COS-REVIEW-003  
**Date:** 2026-11-05  
**Reviewer:** Single-agent multidisciplinary pass (COS-000 persona restored)  
**Scope:** Full product-to-spec verification, 7-phase implementation, UI/UX priority 40%

---

## 1. What CancerOS Was Intended to Be

Per PRD, SPEC-003–012, SPEC-009 UI, and KMAP-001:

- **Research problem:** Breast cancer temporal heterogeneity — how lesions evolve, relate to clinical observations, and can be explored across labeled hypothetical scenarios grounded in real imaging geometry.
- **Intended users:** Medical researchers, imaging scientists, evaluators in a pseudonymized research workspace with project/role authorization.
- **Core workflow:** Create/select research case (admin), enter source-backed clinical observations, import real MRI + verified masks, compute physical measurements (volume, longest diameter in mm using voxel geometry), reconstruct 3D mesh, establish observed baseline, generate/track five scenario families (SC-01 to SC-05) each sharing the baseline plus three synthetic follow-ups, synchronize a timeline with clinical charts, and produce evidence-linked (case-evidence separate from background) AI research insights.
- **Visual promise:** SPEC-009 requires case-centered workspace, prominent 3D viewer with measurement display, synchronized charts, minimal technical leakage (no UUID homework for new users).
- **Safety:** Immutable observed history, synthetic never promoted to real, export denied until gated, missing stays missing, DCE phases not conflated with visits.

## 2. What Was Actually Delivered (Evidence)

- **Routes:** `/` (home), `/cases`, `/cases/detail`, `/twin`, `/charts`, `/timeline`, `/states`, `/simulation`, `/insights`, `/demo`, `/guided-demo`, `/evaluation`, `/activity`, `/admin`, `/mesh-preview` — 18 route files confirmed.
- **Frontend components:** ~30 components including `case-library`, `case-creator`, `case-workspace`, `case-imaging`, `lesion-viewer`, `mesh-renderer`, `simulation-workflow`, `clinical-charts-explorer`, `insights-explorer`, `state-timeline-explorer`, `guided-demo`, `research-session`, `research-profile`, `observation-intake`.
- **Backend:** ~90 Python modules under `src/canceros/` — identity, persistence, imaging_ingestion, preprocessing_runs, measurement_runs, mesh_runs, fusion_runs, timeline_runs, simulation_*, interpretation_*, grounding_*, clinical_api, etc. FastAPI contracts via generated `@canceros/contracts`.
- **Demo:** `demo-workspace` — only fully usable end-to-end (EVI) product path; uses synthetic catalog, timeline, mesh asset bundling, Three.js orthographic viewer, RAS frame, mm units, fullscreen/maximize controls.
- **Product workflows:**
  - **Guided demo exists** but is text-list navigation, not interactive state orchestration.
  - **Research Cases page** requires auth token (admin JWT) entered into password field, project selection via dropdown that autoclears on sign-out, source eligibility gating, case creation with identifier+title+pseudonym+reference; but UX demands project UUID known externally or sign-in first; no onboarding explainer of token source for first-time researcher.
  - **Case detail**: loads profile, visit count, observations via paged `/api/case-observations` POST with kind filter, clinical history table, imaging viewer proxy, observation intake form with 7 kinds (lab, vital, symptom, treatment, diagnosis, visit, note) and explicit unit/time handling — genuine scientific integrity preserved (no invention) but form is dense, technical, and behind gated auth.
  - **3D twin**: `/twin` requires `?project=&patient=&lesion=` URL params — no user discovers this without case-workspace link; viewer uses Three.js orthographic cam, RAS Z-up, shared center translation, 100k vertex/200k triangle guards; camera actions labeled (orbit, pan, fit, reset) exist but button styling scattered in `simulation-workflow.module.css` and `mesh-preview.module.css`; canvas not given sufficient prominence (twin-layout: 1fr + 340px side rail). No anatomical context; it is tumor-region only.
  - **Simulation**: Requires manual UUID entry for project/patient/branch + admin token pasted into input — engineering-private workflow per page intent but not user-accessible for researchers; config JSON authored by hand, eligibility checks, job polling, publication gates. No scenario-builder UI for SC-01..05 beyond demo.
  - **Charts**: correct — separate small multiples per concept+unit, preserves missing/censored, time domains, no interpolation — but again behind `project & patient` query param dependency, not discoverable.
  - **Insights**: requires branch/state context; rule-based + `external_private` modes; grounding report separate; safety-conscious but not visually compelling; requires same URL plumbing.

## 3. Overall Product Acceptance Verdict

| Dimension | Verdict | Rationale |
|---|---|---|
| Product Requirements | PARTIAL (40%) | Core data model, provenance, measurement correctness present; user-facing orchestration missing |
| User Journey Completeness | FAIL | Homepage → case creation → clinical entry → imaging → 3D → scenarios → timeline → insights cannot be traversed without manual URL editing or token knowledge |
| UI/UX Usability | FAIL | Engineering-first nav, gated auth without onboarding, dense forms, insufficient 3D prominence, weak visual hierarchy |
| Visual Design Quality | PARTIAL | Tailwind-ish tokens but inconsistent buttons (primary/secondary/ghost scattered, no design system), cards but poor spacing, responsive not validated |
| Research Case Management | PARTIAL | Backend full, frontend requires admin role; viewer role sees empty; search limited to loaded pages only |
| Medical Imaging | PARTIAL | Ingestion, preprocessing, measurement, mesh pipeline engineered; /twin requires lesion UUID; viewer minimal |
| 3D Visualization | PARTIAL | Functional Three.js viewer, correct geometry handling, but not central, no anatomical context, not prominent |
| Longitudinal Simulation | BACKEND_ONLY | Engine complete (config versioning, eligibility, job, completion, publication); frontend is UUID/manual JSON |
| Meta AI Integration | PARTIAL | Provider gateway exists, grounding, evidence separation; no live demo without credentialed config; not inviting for researcher |
| Engineering Quality | PASS (with complexity debt) | 106 tasks, 15 verified foundation, 78 implemented_unverified, 9 blocked; strong safety invariants; over-defensive gating blocks UX |
| Scientific Integrity | PASS | Distinctions (REAL_OBSERVED vs SYNTHETIC…), immutable history, missingness preserved, mm handling correct |
| End-to-End Readiness | FAIL | Synthetic demo usable; real research case workflow not usable by naive researcher |

**Overall:** Engineering implementation substantial but **product delivery incomplete**. Hands-off first-time researcher cannot complete intended research task. Demo is the only coherent product path.

## 4. Most Critical Implementation Gaps (Top 10)

1. **No case creation onboarding** — token source, project creation, source registry unexplained on /cases; first screen blank unless `?project=` present.
2. **No single workspace orchestrating** project→patient→lesion→branch→state with breadcrumbs that non-engineers understand; AppShell shows raw UUIDs under `<details>`.
3. **/twin, /charts, /insights require manual URL params** — not linked from case-workspace for many users; deep linking fragility.
4. **Observation intake** — 7 concept types in two dropdowns, instrument/severity/units scattered; no progressive disclosure, no field organization by clinical workflow.
5. **Imaging upload** — case-imaging component exists but gated behind roles; no drag-drop, no DCE phase context.
6. **Simulation workflow** — expects handwritten JSON draft + hash matching; no scenario-family picker, no assumption forms for SC-01..05.
7. **3D viewer prominence** — occupies <40% viewport; controls split across buttons and keyboard; no measurement overlay panel in viewer.
8. **Visual design** — inconsistent button hierarchy (multiple primaries per card), muted vs hint styles, excessive card borders, missing empty states.
9. **Timeline & States** — two competing routes (/timeline vs /states) confuse; StateTimelineExplorer and ObservationTimeline overlap; no single integrated timeline page.
10. **Evaluation report** — limited to engineering gate stats, not researcher-facing quality.

## 5. Critical UX Findings (Summary)

- **Mental model:** Product thinks in UUIDs, not research cases. UI leaks implementation (branch_id, revision, snapshot hash) above the fold.
- **Navigation:** Primary nav (Overview, Research Cases, Digital Twin, Clinical Data, Hypothetical Scenarios, AI Insights, Evaluation) correct labels, but Digital Twin without context shows "No case loaded" empty state that doesn't link to case creation. Case nav second bar appears only when lesion selected.
- **Authentication:** Research token entered as password input; error messages generic; no sign-up or project creation for new researcher (requires pre-existing external provisioning).
- **Guided Demo:** Only genuine beginner path, but only text steps; does not auto-drive UI.
- **Error states:** Thorough (401/403/404/409/422 explained) but pessimistic, not corrective.

## 6. Recommended Recovery Strategy (High Level)

P0 recovery must create a **case-centered workspace wrapper** that:

- After auth, auto-selects single project (or shows project cards with role badges, not dropdown).
- Lists cases with title, pseudonym, counts; creation form in same page with progressive fields.
- Clicking case opens **one workspace page** (not 6 top nav links) with tabs: Overview/Profile, Imaging + 3D (split 60/40 viewer prominent), Clinical Observations (timeline left, entry right), Scenarios (family cards, generate), Insights (context-bound), Evaluation.
- Eliminates manual UUID entry everywhere; simulation uses forms for SC families.
- Gives 3D viewer >=65% viewport, measurement badge, fullscreen, camera controls labeled with icons.
- Unifies /timeline and /states into one Timeline component with baseline pin + scenario comparison.
- Improves visual system: tokenized buttons, typography scale, spacing, empty states with actions.

P1–P2 follow in dedicated recovery plan doc.
