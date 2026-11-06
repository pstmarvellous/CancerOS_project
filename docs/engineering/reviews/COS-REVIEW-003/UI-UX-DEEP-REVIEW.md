# COS-REVIEW-003 — UI/UX DEEP REVIEW (Primary Deliverable — 40% priority)

**Review ID:** COS-REVIEW-003-B  
**Date:** 2026-11-05  
**Coverage:** All routes, components, global CSS, demo, case management, intake, viewer, simulation, charts, insights, nav

---

## 6.1 First-Time User Experience (Fresh Session Walkthrough)

### Steps attempted (no preloaded IDs)

1. Open `/` (Home).
   - `/` source: `apps/web/app/page.tsx` — shows headline "Explore Cancer Evolution in 3D", lead copy, two CTAs: "Create Research Case" → `/cases` and "Explore Synthetic Demonstration" → `/demo`. Good copy. Disclaimer synthetic present. Three feature cards.
   - **Fail:** Clicking "Create Research Case" without auth shows page requiring `?project=` param or sign-in. No hint where token comes from. First user stuck.

2. Open `/cases` without auth.
   - `research-cases.tsx` renders two choice cards (Create Research Case button scrolling to research-access, and Explore Synthetic). ResearchSessionPanel shows password field for token, help text "Provided by your research administrator. Browser stores only short-lived protected session cookie." Button "Sign in...".
   - **Problem:** No link to how to obtain token, no demo token, no project creation as researcher. Field is type password with maxLength 16384, no placeholder. Error when API unavailable is generic. After successful auth (not possible without JWT from API), `applySession` auto selects first project. But without credentials, page ends after sign-in form — no case list.
   - **Severity:** P0 blocker — onboarding fails.

3. Case library (`CaseLibrary`).
   - Present at bottom inside `<details>` collapsed by default: "Previously imported case summaries" — hidden unless user expands. It requires `initialProject` prop; when no project, shows "No project selected — Add ?project=<id> to the URL". Leaks UUID model. The case cards show display_code + data_revision only — not title. Secondary link "Open case" points to `/cases/detail?project=&patient=` — good but deep-link dependent.

4. Case detail (`/cases/detail`) without params → status `needs-selection` — must be Component showing "Add ?project=...".
   - `case-workspace.tsx`: `useSelection()` reads from searchParams. So every page needs query params. AppShell shows selection under `<details>` summary "Research case selected · advanced identifiers" with joined UUID fragments. For first-time user, this is opaque.

**Result:** Fresh user cannot progress past /cases without externally obtaining JWT + project UUID. Demo is only usable path.

### What user needs to understand (requirements vs reality)

| Question | Answer visible? | Evidence |
|---|---|---|
| What is CancerOS? | Yes | Home page headline + lead |
| What problem? | Partial | Feature cards but not clinical context |
| What can it do? | Partial | Lists 3 steps but not research case |
| Where to begin? | No | Two CTAs conflict; case path blocked |
| How to create case? | No | Requires admin + source + token |
| How to enter data? | No | Only after case+auth |
| How to access imaging? | No | Imaging tab hidden behind case selection |
| How to view twin? | No | /twin shows "No case loaded" generic |
| How to generate scenarios? | No | Simulation requires UUID + token input fields |
| How to access AI? | No | Insights requires state ID |

### Confusing interactions recorded

- Clicking Create Research Case button on /cases just scrolls to same-page sign-in — not navigation.
- Research access token input has no autocomplete, no copy-paste affordance explained.
- Project selector is `<select>` with 0–1 entries after auth; when single project, still shows dropdown.
- Case search placeholder "Title, case identifier or pseudonym" but filtering only works on already-loaded 25-item page; cursor pagination "Load more" exists.
- Two similar pages: `/timeline` and `/states` — both timelines but different implementations.
- AppShell `<Link href="/cases/detail">` preserves selection via `preserveSelection()` but if no selection, it drops to bare path.

---

## 6.2 Information Architecture

### Current nav (AppShell)

Primary: Overview (`/`), Research Cases (`/cases`), Digital Twin (`/twin`), Clinical Data (`/charts`), Hypothetical Scenarios (`/simulation`), AI Research Insights (`/insights`), Evaluation (`/evaluation`).

Case nav (when patient selected): Overview (`/cases/detail`), 3D Digital Twin (`/twin`), History & states (`/states`), Clinical Data (`/charts`), AI Research Insights (`/insights`), Hypothetical Scenarios (`/simulation`), Sources (`/sources` — not confirmed file).

Issue: Primary and case nav duplicate labels with different selection preservation. `/twin` maps to demo `?view=twin` when in `/demo` context — clever but confusing (demoViews mapping). Safety notice bar under header on every page except home.

### Missing destinations

- No unified workspace binding project/patient/lesion/branch/state in one scrollable journey.
- No persona landing distinguishing "I have real data" vs "I want synthetic demo".
- No imaging import guide or DCE context explanation.
- No scenario-family explainer page; families only coded as `SC-01..05` with labels in simulation-workflow `FAMILY` dict.

### Label problems

- "Hypothetical Scenarios" — correct scientific labeling but paired with "Configure a hypothetical research branch" — too technical; researcher expects "Scenarios".
- "Evaluation / Technical Details" — two audiences combined.
- "Research access" heading ambiguous — auth vs data access.
- Badges: `observed` (●), `derived` (■), `simulated` (◆), `warning` (◇/△) — color only (teal, blue, purple, brown) not accessible alone; symbols help but low contrast.

### Navigation depth

Level 1: primary nav tabs (7 items). Level 2: case nav (7 items) appears only after selection. But deep-linked pages (`/twin?project=&patient=&lesion=`) bypass case nav if lesion missing. User must edit URL.

### Case-centered workspace

Specified but not achieved. Header shows selection UUIDs under details. No breadcrumb trail. No back-to-case from twin that preserves project. Simulation page has breadcrumb "← Research workspace · History & states · Editor activity" but first is `/` not `/cases`.

**Recommendation:** Single workspace under `/workspace/[project]/[patient]` or query-param-driven unified `/cases/detail` with tabs rendering in place, not separate full pages.

---

## 6.3 Research Case & Patient Management (Detailed)

### Creation flow (`case-creator.tsx`)

Fields: identifier (pattern `[A-Za-z0-9._\-]+`), title, pseudonym, source `<select>` from eligible list, reference (source locator). `allowed` only if `role==='admin'`. Idempotency-key via `crypto.randomUUID()` refreshed on form change.

Good: pseudonymization enforcement, no names, pattern validation, source eligibility check, role gating.

Bad UX: Source `<select>` shows `title · origin` but title is source version title (technical). No source creation UI visible; eligible list can be empty with message "An administrator must register a source" — but no CTA. Form uses generic `className="form-grid"` 2-column but no grouping, no inline validation, error via `ErrorSummary` only post-submit. Success redirects via router.push — good but no confirmation toast.

Badge: Origin `real_source` vs synthetic visible.

### Library (`CaseLibrary`)

Shows 25? Actually uses `/api/cases?project=` returning `PatientPage` with `items` (PatientSummary: patient_id, display_code, data_revision). No modality counts, no updated date here. Empty state says "No approved cases yet — An administrator can review imports..." with link to guided-demo. Failed state retry button.

Search not in this component — search is in `ResearchCases` composite, which filters client-side `${title} ${case_identifier} ${pseudonym}` lowercased, showing "{filtered} of {loaded} loaded". Counts from visible records only — correct safety but confusing when more on server.

Uses `.case-grid` grid `repeat(auto-fill, minmax(280px,1fr))` — okay. Case cards show Status, Updated, Imaging records, Clinical records — helpful.

### Profile (`research-profile.tsx`)

View: title, origin badge, dl with case identifier, pseudonym, status, sex, age, medical history, source, created/updated. Edit button only if admin. Form: readOnly identifier/pseudonym, title, status select, sex select, age number + date, reference, medical history textarea. Saves via `/api/research-profile?project=&patient=` POST with expected_revision; captures revision.

Good provenance scaffolding.

UX issues: profile revision number shown only as hint, not prominent; age requires whole years + observation date but validation via regex; medical history textarea placeholder not hints.

### Persistence & reopening

Works via backend revision tracking. Frontend reload mechanism via `attempt` counter state increment button "Reload saved profile" / "Refresh cases". Manual refresh required after save — not auto.

No delete/archive from UI? Status dropdown includes draft/active/archived but no delete.

Case switching: via URL only; navigating between cases loses earlier case because no recent cases list.

---

## 6.4 Clinical Data Entry

Component: `observation-intake.tsx`

**Fields:**
- kind select: laboratory, vital, symptom, treatment, diagnosis, visit, note — mapped to concepts arrays.
- concept select per kind (hemoglobin, wbc, anc, etc.; heart_rate, temperature; fatigue, pain; etc.; chemotherapy, endocrine, etc.; source_pathology; clinical_visit, imaging_exam; source_note)
- original term * (exact doc label), source reference *, time precision (date/timestamp/unknown), time input (date or text with placeholder ISO 8601), and — if numeric kind — result form: exact/missing/censored with value+unit, missing_reason, comparator.
- For symptom: presence, reporter, optional severity + instrument + version.
- Treatment: event_type, exposure_status, regimen_text.
- Diagnosis: histology, side, ER/PR/HER2 status, clinical_stage, pathologic_stage, staging_system.
- Visit: label.
- Note: text.

**Assessment:**

Strengths: explicit source, time domain, unit enforcement, missing/censored forms preserved, no invented values. Handles ISO timestamp with seconds+TZ regex. Idempotency key rotation on change.

Weaknesses:
- Form is huge, single column `form-grid` with many conditional fields rendered inline; no progressive disclosure or sections beyond `<fieldset>Observation`.
- Field order technical: kind, concept, original_term, source, time precision, time — should start with source + time.
- No contextual help besides field-hint; unit list `units` dict hard-coded: hemoglobin g/dL,g/L etc. No validation message until submit.
- Concepts list only English lower-case keys — researcher may not know "hemoglobin" vs "hgb".
- Diagnosis fields (ER, PR, HER2) assume breast-specific but no explanation.
- No visit linkage helper (which visit does observation belong to?) — visit_id not in form? Backend supports `visit_id` filter, intake may need dedup.
- Save returns `{status, accepted_count, next_action}` but UI shows only count.
- Correction mode exists: `correction` prop allows replace with original retained.

**Clinical history table (`clinical-history-table.tsx`)** (not opened in detail) likely paged list.

---

## 6.5 3D Digital Twin Experience

**Components inspected:**
- `lesion-viewer.tsx` (17.4KB): from query `project, patient, lesion`, loads lesion list (`/api/cases?project=` variant or lesions endpoint), fetches measurement report + mesh asset + QC report, handles blocked measurement, transfer bytes, retry, pending AbortController.
- `mesh-renderer.tsx` (13.4KB): Three.js OrthographicCamera, RAS frame Z-up, shared center translation preserving physical origin, guard totalVertices>100k, triangles>200k, verifies unit mm, frame RAS, identity transform matrices, creates BufferGeometry, MeshStandardMaterial, OrbitControls with screenSpacePanning, minZoom 0.1 maxZoom 20, hemisphere + directional light, render loop respecting document.hidden.

**Canvas size & prominence:** In `/twin` page, `LesionViewer` rendered standalone, global.css twin-layout originally `minmax(0,1fr) 340px` but current twin page does not use twin-layout class? Page is simple `<LesionViewer/>`. Viewer host element sized via parent? Module CSS not inspected but likely constrained. Demo workspace (`demo-workspace.module.css`) has `.workspace` grid, `.viewer` with heading/actions/timeline.

**Camera controls:**
- In `lesion-viewer.tsx` real implementation: viewer-actions div with Fit, Reset, etc. Keyboard controls labeled in lead paragraph but actual buttons may be smaller. In `mesh-renderer`, `OrbitControls` enabled, damping false, touchAction none. Actions via ref `actions` allows external control.

**Measurement display:**
- Demo version: `.viewerHeading` shows name + day, `.viewerActions span.inlineMeasurement` shows exact_value mm³. Lesion viewer variant likely shows measurement report beside canvas but code truncated earlier not viewable; need infer: loaded includes measurement report, probably displayed in side panel.

**Scenario transitions:** In demo, scenario selector `<select>` bound to timeline points (baseline, day X). Points filtered by `measurement_basis` baseline_reference + mask_realized. Browse via buttons aria-pressed.

**Visual clarity:**
- Scene background `#111827` viewport color, tumor color `#c4b5fd` (light purple) or `#e9a38a` from CSS variable — low medical realism but clear.
- No anatomical breast context; geometric phantom only. Honest labeling ("Synthetic tumor region · geometric phantom · mm" aria-label).
- Loading performance: dynamic import `ssr:false` good; loading placeholder paragraph.

**Accessibility:** `aria-label` synthetic region, canvas role img, dataset attributes for render state, camera state. Keyboard trap for fullscreen implemented in demo workspace.

**UX problems:**
1. **Too small:** In case workflow `/twin`, canvas not maximized by default; controls scattered above; side panel 340px competes.
2. **Discovery:** Lesion list loading requires project + patient context; initial state `needs-selection` not actionable.
3. **No frame reference:** No scale bar, no axes helper indicating RAS orientation.
4. **No measurement overlay inside canvas** — volume shown outside.
5. **No lesion list visual selection** — user must know lesion UUID; picker may be dropdown but not prominent.
6. **Fullscreen/maximize exists in demo but not in case twin** (need verify). Reviewer notes: clone logic exists only in demo-workspace.

**Quantitative check:** Guard rejects huge meshes but no progressive LOD.

---

## 6.6 Longitudinal Simulation UX

**Current:** `/simulation` page renders `SimulationWorkflow` component which is handcrafted API client requiring manual project/patient/branch UUID inputs + token string input (plain text). Steps: Load branch → Save draft (JSON parsing) → Resume draft by configId → Inspect eligibility + schedule preview → Freeze run → poll job → inspection of completion → publication + attestation checkbox + review.

**State:** This is engineering-private workflow intentionally per intro: "Private engineering workflow" eyebrow, honest. But as product feature "Hypothetical Scenarios" it fails: researcher cannot configure scenario family via forms.

**Missing:** Family SC-01..05 explicit assumptions per synthetic spec: growth rates, response categories, shape variations. Treatment assumptions disabled ("Specific treatment assumptions remain disabled pending qualified policy review") per code check `config.treatment?.category !== 'no_specific_assumption'`. Good safety but no UI for allowed assumptions.

**Job progress:** Uses polling? Request logic uses idempotency key per request via Map; error messages for 401/403/404/409/412/422 helpful. 202 starts durable job.

**Demo as substitute:** Demo workspace covers SC-01..05 with precomputed timeline — user can explore what-if but not generate new. Distinction correct: demo plays precomputed states, not functioning research generation workflow.

**UX needs:**
- Scenario family cards with description, assumptions, preview.
- Forms for baseline selection (must be verified twin state), scheduling (days), geometry policy (none vs anatomical_mesh), measurement-only vs mesh.
- Eligibility report rendering: capability, reasons, next_action.
- Job progress bar, logs.

---

## 6.7 AI Research Experience

**Inspect flow (`insights-explorer.tsx`):**
- Needs `project, patient, branch, state` params. Shows context loader via POST `/api/insights?action=context&state=` with optional branch_id. Context bound to exact snapshot hash + context_hash. Then generate summary: mode rule_based (deterministic) vs external_private (Meta/opt) with idempotency key.
- Report type `InterpretationReport` with snapshot_hash, context_hash, execution_mode.
- Grounding report separate (`GroundingReport`) — must be run before saving.
- Saved interpretation ID tracked; drawer for evidence drill-down.

**Gounding:** Correct — case evidence separate from background passages; unknown uncertainty never confidence gauge. Finding opens exact observation or approved passage.

**Live Meta inference:** `provider_api.py` + `provider_gateway.py` exist; checkResearchWorkspace validates bearer RS256. But frontend does not expose Meta live status beyond "Private external candidate ready". No model identity badge, no cost warning, but safe.

**UX:** Heavy technical metadata — snapshot hash slice 12 shown; exportable yes/no. Insight panel `interpretation-panel` probably lists findings.

**Problem:** Without branch/state pre-selected, page shows generic need-selection empty state, user does not know how to get state ID (must from /states). No linked navigation.

---

## 6.8 Visual Design and Interaction Quality

**Typography:** Inter system sans; headings `clamp(30px,4vw,44px)` tight negative tracking; H2 21px; lead 18px muted; good hierarchy. Eyebrows 12px uppercase spaced, teal observed. But inconsistent heading sizes in cards (card h2 21px vs case-card h2 19px).

**Color:** Canvas `#f6f8fb`, surface white, text `#172033`, muted #475569, border `#cbd5e1`, action #1d4ed8 hover #1e3a8a, observed #0f766e, derived #1d4ed8, simulated #6d28d9, viewport #111827, lesion #e9a38a. Palette coherent but warns `warning` #92400e brown low contrast on white? Check WCAG.

**Buttons:** Styles fragmented — `button` global blue, .button-primary, .button-secondary, .button-ghost, .button-danger, plus `.button` class from global actions `a.button`. `.button-secondary` background #eef2ff border action — okay. `.button-ghost` transparent border. Min-height 44px accessible. However multiple primaries per page (demo: retry, maximize etc.), visual weight confusing.

**Icons:** None — no icon system, only symbols ● ■ ◆ ◇ △ for badges + text labels. No SVG icon library.

**Spacing/alignment:** Cards 28px padding desktop, 20px mobile; grids gap 24px; but case-grid gap 16px; twin layout gap 24px. Inconsistent.

**Cards:** Standard `.card` white border 1px solid, radius 12px. `.case-card` variant? Contains dl case-fields each row border-top #e8edf3 — visually repetitive.

**Forms:** `.form-grid` auto-fit minmax 220px; inputs border 1px #64748b (strong) radius 8px min-height 44px. Labels flex column bold 14px. field-hint 13px muted. Usable but dense.

**Tables:** Not seen; history table likely plain.

**Charts:** Clinical charts explorer uses small multiples, correct but no overall chart design.

**Toolbars:** Viewer-actions flex wrap gap 8px; buttons min-height 40px font 13px inside. Not toolbar semantic.

**Nav:** Header 84px min-height white bottom border; brand 24px bold; nav-list flex wrap gap 4px 16px; link padding 10px 4px bold 14px; active underline action offset 4px.

**Responsive:** Media query max-width 680px header switches column, grid becomes 1fr main padding 32px 20px. No tablet breakpoint. Demo workspace modules not inspected but likely have responsive.

**Accessibility:** skip-link, focus-visible outline 3px #92400e offset 4px, role alert/ status many places, aria-pressed on timeline buttons, aria-current page. Good foundation but not audited: color-only badges, no dark mode preference? prefers-reduced-motion support yes.

**Empty states:** Present (No approved cases, No research cases, This state unavailable, The 3D view could not load with retry, Unable to complete). However many are generic "The authorized read failed..." not actionable.

**Loading:** `Loading research workspace…` simple paragraph; no skeleton, but adequate.

---

## 6.9 End-to-End Journey Testing (Browser-Equivalent Code Walk)

Attempted:

**Journey A: Open → Create research case → Enter observation → Imaging → Twin → Scenarios → Timeline → Insights**

1. Open `/` → OK.
2. Click "Create Research Case" → /cases → Requires sign-in. Provide invalid token → 401/403 error UI. Real JWT required from `API_BASE_URL http://127.0.0.1:8000` endpoint `/api/v1/workspace`. Backend not running in review env. **Blocked.**
3. Alternative path `/demo` → Loads via `/api/demo-session` POST then `/api/demo` GET catalog. Needs API for catalog; without backend, fails to "demo could not load" with retry. If API available, catalog provides scenarios SC-01..05 + timeline. Demo workspace rail left navigation (Overview, 3D Twin, Scenarios, Clinical, Insights, Technical) + scenario select dropdown. Middle viewer 3D. Right measurements collapsible. Timeline at bottom with buttons for each day. Can navigate scenario + state via URL `?view=twin&scenario=SC-01&state=point-id`. Measured value shown. **Partial success** only with API.
4. Twin without case → shows need-selection. Even with project/patient/lesion valid UUIDs, lesion list fetch from `/api/cases?project=` or lesions endpoint returns list; then measurement + mesh + QC fetched; viewer rendered. **Requires manual URL plumbing.**
5. Charts `/charts?project=&patient=&state=` — ClinicalChartsExplorer loads observation page via `/api/case-observations` POST kind filter. Grouped per concept+unit+instrument. No charts visible without data.
6. Simulation `/simulation` — manual UUID entry, token paste. Cannot configure without branch loaded. Branch load requires existing branch from backend. No branch creation UI in workspace.
7. Insights `/insights?project=&patient=&branch=&state=` — needs state id from /states.

**Reproducible blockers:**

- Backend dependency: all research pages hit `/api/research-session` first; if API down, shows "Research access could not be checked."
- Auth provisioning: no on-page guidance for token generation; developer must run script `scripts/bootstrap_tools.py` maybe? Or admin creates token externally.
- UUID homework: user must copy project id from dropdown value? Project select hidden value is UUID, but visible text is name · role. After selection, other pages still want `?project=` param typed; researcher may lose selection when clicking primary nav unless preservation works (preserveSelection uses project/patient/branch/run/state/lesion but not always propagated because AppShell reads from useSearchParams each render, reads only current path params — if navigate via Link without query, params lost? Code tries to preserve: if selection.patient and demoViews, target = preserveSelection(...). But some Links not using preserveSelection, so selection can be lost.)

**Screenshots:** Not captured in this environment (no browser automation). Provide file-level evidence per section above.

---

## Summary Table: Screen-by-screen UX severity

| Screen | Accessibility | Usability | Visual | Severity |
|---|---|---|---|---|
| Home `/` | Good | Partial | Good | Medium — sane but CTAs confusing |
| Research Cases `/cases` | Good (role attributes) | Fail | Partial | P0 — onboarding blocker |
| Case Detail `/cases/detail` | Good alerts | Partial | Partial | P1 — needs single workspace |
| Twin `/twin` | Good aria | Partial | Fail prominence | P0 — viewer not prominent/no onboarding |
| Charts `/charts` | Good | Partial | Partial | P1 |
| States `/states` | Needs check | Partial | Partial | P1 — overlap with timeline |
| Timeline `/timeline` | Needs check | Partial | Partial | P1 |
| Simulation `/simulation` | Good messages | Fail | Partial | P0 — engineer-only |
| Insights `/insights` | Good | Partial | Partial | P1 |
| Demo `/demo` | Good (keyboard trap, fullscreen) | Pass (synthetic only) | Good | Best path |
| Guided Demo `/guided-demo` | Good | Partial (text list) | Partial | P2 |

Recommendations detailed in recovery plan.
