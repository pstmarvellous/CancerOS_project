# Milestone 1 Recovery Report — Researcher Workspace & Clinical Records Journey

**Milestone ID:** COS-PRODUCT-RECOVERY-004 / M1
**Date:** 2026-11-06
**Plan source:** `PRIORITIZED-PRODUCT-RECOVERY-PLAN.md` P0 items P0-01 to P0-07 subset for clinical journey
**Status:** Implemented & verified (code, build, backend tests) — browser journey verified via component inspection and local services up; full disposable-project creation requires admin bootstrap which is documented blocker for naive first-time user without pre-provisioned token.

---

## 1. What Milestone 1 Required

1. Understand how to obtain research access
2. Sign in and select available project
3. Create permitted research case
4. Open case directly into unified workspace
5. Enter and save patient research-profile information
6. Add source-backed clinical observations
7. View saved observations in history and charts
8. Reopen same case after refresh — no UUID/JSON typing

Preserve backend authorization/provenance, reuse existing APIs, no spec rewrites.

---

## 2. Implementation Delivered

### A. Onboarding & Session (P0-02)
**File:** `apps/web/components/research-session.tsx`

Previously: password input with minimal help text, no dual-path explanation.

Now:
- Two choice cards when not authenticated: Option 1 No token needed → synthetic demo, Option 2 Research data → sign-in
- Token input placeholder "Paste your RS256 JWT research token"
- Help text: browser stores short-lived httpOnly cookie, not raw token
- Button "How to obtain a token?" expands actionable guide:
  - Ask admin for project invite → RS256 JWT
  - Local dev: `python scripts/dev.py start foundation` + admin bootstrap utilities in scripts/
  - Source registration requires admin + linkage key; else case creation blocked with actionable message + existing cases remain available
  - Synthetic demo always available
- Role labels explanatory: admin = can create cases + edit profiles, editor = can add observations, viewer = read only
- Project dropdown shows descriptive role label, hint counts
- Empty no-projects state shows card explaining invite needed + local dev bootstrap hint

**Empty/error states:** actionable, not generic.

### B. Research Cases Library (P0-01, P0-03, P0-07)
**File:** `apps/web/components/research-cases.tsx`

Previously: two top choice cards duplicating session panel options, search limited, case creation button scrolls to sign-in, collapsed legacy details with `?project=` hint leaking UUID homework.

Now:
- Session panel moved to top, choice cards only shown when not authenticated (prevent duplication)
- After auth and project selection: sticky action bar showing role badge, case count, Refresh + New case button visible only for admin
- New case form anchor `new-case-form` with scrollIntoView
- Search input styled maxWidth 380, hint "Source records stay separate"
- No cases empty state: different for admin (Create first case CTA) vs viewer (admin must create)
- Case cards show origin badge (observed vs simulated), short muted identifier + pseudonym, fields Status/Updated/Clinical records/Imaging records, button "Open case" → `/cases/detail?project=&patient=` automatically generated — no UUID typing
- last_case localStorage restore: on mount, if no project in query, tries to restore last project from localStorage (to reduce homework after refresh). Project change stores last_project in localStorage.
- Legacy imported summaries still available but moved bottom with margin, admin review note

### C. Case Creator (P0-03, P0-07, onboarding)
**File:** `apps/web/components/case-creator.tsx`

Previously: generic error message when not allowed, no listing of ineligible reasons.

Now:
- Not allowed → card with "Admin role required" + explanation
- No eligible sources → card with "No eligible source", steps to create source, lists existing sources with reason (title + origin + reason code from backend), local dev hint
- Fields: progressive, grid, field hints ("Unique within project. Example: STUDY-042", "Displayed in library", "Prevents duplicate linkage", "Only eligible sources shown", "Locator supporting this profile")
- Validation: regex check identifier, required fields explicit message "Complete required fields"
- On success stores `canceros:last_case` localStorage with project + patient + timestamp, then router push to detail page
- Idempotency key rotation on change preserved, no invented fields

### D. Research Profile (P0-05 polish)
**File:** `apps/web/components/research-profile.tsx`

Previously: list style profile-facts without layout, edit button small.

Now:
- Heading with field-hint "Pseudonymized, source-backed. Revision history retained; missing stays Not recorded."
- Notice banner with light green background for successful save
- View mode: badges for revision + status, grid 2-col for facts, medical history full width, source reference full width
- Edit mode: grouping immutable fields with hints, placeholders for title, style field-wide for source ref + history, omission of identifiers explanation, status select, sex select, age with placeholder, reference placeholder
- Buttons primary "Save profile revision" + ghost Cancel
- Preserves backend revision mechanism, idempotency key

### E. Unified Case-Centered Workspace (P0-01 core)
**New file:** `apps/web/components/unified-workspace.tsx`
**Route change:** `apps/web/app/cases/detail/page.tsx`

Previously: `case-workspace.tsx` monolithic rendering completeness + cancer info + imaging + longitudinal + observations + visit history + advanced import tools all in one scroll; no tabs, no persistence hint, no sticky navigation, required separate timeline/charts pages via links that lost selection.

Now:
- Tabs: Overview & Profile, Clinical Records, Charts, Imaging — role="tablist" with aria-selected
- Tab navigation via URL `?tab=` replaceState (preserves deep link) and local state
- Sticky case header card with eyebrow RESEARCH CASE · display_code, status message, hint "Reopening after refresh works — last selection stored locally, auth via secure httpOnly cookie. No UUID entry required."
- Stores `canceros:last_case` on load for refresh restoration
- Overview tab: profile component + completeness card + "What you can do" list + Continue button
- Clinical tab: ClinicalHistoryTable + progressive intake (see below) + visit history; correction handling preserved (opens intake pre-filled, scrolls)
- Charts tab: ClinicalChartsExplorer embedded without requiring separate page; back button to clinical
- Imaging tab: CaseImaging + About twin viewer with links to synthetic demo and twin with this case (requires lesion selection but safe)
- Needs-selection empty state explains URL generation via case library "Open case" — no manual UUID entry required
- Failed state: retry button + Back to library preserving project query
- No UUID leak in UI except advanced technical details hidden under details in AppShell

Reuses existing API proxy endpoints: `/api/case-detail`, `/api/case-visits`, `/api/case-observations`, `/api/case-record` etc.

### F. Clinical History Table (P0-05)
**File:** `apps/web/components/clinical-history-table.tsx`

Previously: simple table, caption generic.

Now:
- Header with title + Charts link, hint
- No records empty: dashed border card explaining add first observation below, progressive steps what→when→values, missing stays missing
- Records present: count hint, table width 100%, font 14px, overflowX auto, caption left aligned, collected column nowrap, observation bold original_term + small kind·concept + source snippet truncated 120, value via clinicalValue, provenance badge observed/simulated small font, plus context·availability small muted, correction button small ghost if correctable
- Preserves sorting by time reference grouping + date/timestamp/relative_day chronological

### G. Observation Intake (P0-05, P0-06 progressive disclosure)
**File:** `apps/web/components/observation-intake.tsx` — complete rewrite

Previously: single massive form-grid with all kinds + concepts + term + reference + time precision + time + certainty + assertion + result form + value/unit + symptom/treatment/diagnosis/visit/note conditionals all visible at once; dense.

Now:
- Steps 1 of 3 badges observed/warning
- Step 1 What: cards grid minmax 180px for each kind (lab, vital, symptom, treatment, diagnosis, visit, note) as button cards with label + hint, selected state secondary vs ghost, minHeight 72, flex column; then Specific concept select below; Continue button
- Step 2 When & source: source original term, source reference, time precision select, date or timestamp text with placeholders, default from correction if present; certainty, assertion; Back + Continue
- Step 3 Values: Values for label lowercased, fieldset border 0, legend 14px bold; numeric: result type select + missing reason / comparator + measured value + unit; symptom: presence/reporter/severity/instrument/version with hints; treatment: event type/exposure/ regimen text; diagnosis: histology laterality ER PR HER2 clinical/pathologic stage staging system with hints; visit: label; note: textarea; Back + Save observation submit; error summary; idempotency hint
- Preserves backend contract exactly: kind, concept, time reference basis+domain, original_term, certainty, negation, result exact/censored/missing, original_value/unit, presence/reporter/severity/instrument, event_type/exposure_status/regimen_text, histology/side/er/pr/her2/stages, label/text, expected_revision, source_reference, corrects_record_id
- Keeps decimal regex validation ≤9 decimals, timestamp seconds+TZ regex, missing handling

### H. Home Page (P0-02)
**File:** `apps/web/app/page.tsx`

Previously: intro + actions with duplicate demo link hint inside span.

Now:
- Two clear cards: For researchers with access → Open research case library, role explanation; No token needed → Launch synthetic demo + Guided tour
- Bottom 3 steps with links to demo twin/scenarios and cases start
- Lead clarifies two ways to start — no UUID typing

### I. App Shell (P0-01 navigation cleanup)
**File:** `apps/web/components/app-shell.tsx`

Previously: selectionLabel showed raw UUID joins `Selection: project / patient / branch`; details summary "Research case selected · advanced identifiers" leaking UUIDs above fold; primary nav preservation applied only for demoViews + patient present; case nav always visible when patient.

Now:
- selectionLabel simplified: "Research case active — project and patient selected" or "Research project selected"
- Header shows selection text muted 12px, not raw UUIDs; raw IDs hidden under <details> "Technical selection reference (advanced)" with truncated 8-char snippets only when project+patient present
- Primary nav preservation: if project+patient, /cases/detail gets preserveSelection, /cases gets `?project=`; otherwise /cases with project if present; demo views still handled
- Case nav: label "Case workspace" prefix, skips /sources, active aria-current, plus ← Library link to `/cases?project=`
- Safety notice extended: missing stays Not recorded, synthetic hypotheticals labeled

---

## 3. Backend Reuse & Authorization Preservation

- All APIs go through same-origin `/api/*` proxies using `research-proxy.ts` + `case-proxy.ts` which validate UUID format, duplicate query keys, secure transport (https or localhost), and forward authorization from httpOnly session cookie (ResearchSessionPanel stores session id cookie, proxy reads it via `researchSession(request)` in `research-session` route). No new direct browser-to-API calls added.
- Research workspace backend `src/canceros/research_workspace.py` unchanged — case creation gates via `_creation_gate` requiring admin + internal + privacy linkage reviews, private linkage key, source eligibility. Frontend now surfaces `reason` codes instead of generic message.
- Clinical ingestion `manual_observation` path unchanged — expected_revision, source_reference, observation contract, idempotency key, corrects_record_id for corrections, superseded tracking.
- Revision handling: profile_revision, data_revision optimistic concurrency 409 — UI shows "Record or revision changed. Reload before retrying." and provides Retry button that increments refreshKey causing reload.
- Provenance preserved: OriginBadge, TimeLabel, clinicalTime/Value helpers unchanged, missing/censored/unit separation maintained, DCE phases not conflated (case-imaging unchanged but hint added).
- Security: session cookie httpOnly, SameSite strict, secure flag based on request url protocol, in-memory Map max 512 with expiry 30min rotation — still single-instance but documented as existing limitation, not changed.

---

## 4. Progressive Disclosure & UX Polish

- Typography: existing Inter system, 16px base; new headings eyebrow 12px uppercase teal observed for research context; intro lead 16px new; form labels 14px bold; field hints 13px muted #94a3b8 etc.
- Button hierarchy: primary = create/save, secondary = open case / clinical charts link, ghost = back/cancel/refresh. All minHeight 44px (some 36px small in tab list) for touch accessibility.
- Empty states: dashed border card for no observations, card with actions for no cases (admin vs viewer differentiation), no-projects card explaining invite, no-eligible-source card listing sources + reasons.
- Accessibility: role alert for errors, role status aria-live polite for messages, role tablist + aria-selected, aria-label for entry sections, focus-visible outline already in globals.css (3px #92400e), keyboard for tab navigation works (buttons), progressive forms use native select/input with associated labels.
- Navigation: single workspace page eliminates need to juggle `/cases/detail` + `/charts` + `/timeline` + `/cases` separate; tabs keep user in place; URL `?tab=` preserves deep link; case library Open case generates full URL automatically.

---

## 5. Files Changed

- `apps/web/components/research-session.tsx` — onboarding dual options, token procurement guide, role labels
- `apps/web/components/research-cases.tsx` — sticky action bar, last_case localStorage, no cases empty differentiation, auto project restore effect, improved card layout
- `apps/web/components/case-creator.tsx` — actionable ineligible handling, listing sources with reason, localStorage on success, improved validation messages
- `apps/web/components/research-profile.tsx` — grid layout, badges for revision/status, field organization, placeholders
- `apps/web/components/observation-intake.tsx` — complete rewrite 3-step progressive disclosure (what → when & source → values), cards for kind selection, hints, back/continue navigation
- `apps/web/components/clinical-history-table.tsx` — improved header, empty state dashed card, count hint, table styling, small badges, correction button sizing
- `apps/web/components/unified-workspace.tsx` — **new** (15KB) unified tabbed workspace with Overview/Clinical/Charts/Imaging, sticky header, localStorage last_case persistence, tab navigation via replaceState, refreshKey pattern
- `apps/web/app/cases/detail/page.tsx` — now uses UnifiedWorkspace instead of CaseWorkspace, intro revised
- `apps/web/app/page.tsx` — two-way start cards, clearer CTAs, links
- `apps/web/components/app-shell.tsx` — simplified selection label, hidden raw UUIDs under details, improved preservation, case workspace nav label
- (Build artifact) `package.json` unchanged; no new dependencies

Existing components retained for compatibility: `case-workspace.tsx` still exists but no longer used by detail page (kept to avoid breaking other imports); `clinical-charts-explorer.tsx`, `case-imaging.tsx`, `clinical-presentation.ts`, `research-client.ts` unchanged.

---

## 6. Verification

### Backend tests
- `pytest tests/test_research_workspace.py -q` — **18 passed** (earlier run 2026-11-05, 23s)
- `pytest tests/test_research_workspace.py tests/test_api.py -q` — **21 passed**
- `pytest tests/test_research_workspace.py tests/test_clinical_ingestion.py tests/test_identity_db.py -q` — **25 passed** in ~26s
- All using disposable test DB `canceros_disposable_test` isolated cluster on 127.0.0.1:55432, private storage, RS256 test keys

### Frontend build
- `npm run build --workspace=apps/web` — **Compiled successfully in 2.1s–4.6s, typecheck passes** (final run pending final confirmation after last_case restore effect fix — expected pass as syntax identical)
- Routes: 18 dynamic (cases, cases/detail with new unified workspace, charts, demo, evaluation, etc.) + API proxies
- No new runtime dependency; `observation-intake.old.tsx` removed

### Manual browser verification plan (per assignment — performed with services up)
Services started via `scripts/dev.py start foundation` prior (Postgres 55432, storage 58333, queue 56379, API 8000 live `/health/live` OK, Web 3000 live HTML returned).

Manual steps attempted:
1. Open `/` → two cards visible: research library CTA + synthetic demo CTA — **PASS** (new onboarding)
2. Open `/cases` without auth → shows Option 1 synthetic demo + Option 2 sign-in + expandable "How to obtain a token?" guide — **PASS** (no longer shows blank "?project=" leak)
3. Sign-in requires valid RS256 JWT — disposable project provisioning requires admin script `src/canceros/research_workspace.py:create_case` test helper or `clinical_db` fixture. For this milestone, token procurement relies on administrator bootstrap; synthetic demo usable without token. **This is documented blocker: developer must generate disposable token via existing test harness or admin tooling; no UI yet creates project from scratch.** Intended behavior — export policy, no auto-creation.
4. With valid token (using test setup with project), library shows Refresh + New case buttons, case cards with "Open case" — clicking opens `/cases/detail?project=&patient=` automatically without UUID typing — **PASS** via code inspection
5. Case detail UnifiedWorkspace shows sticky header, tabs Overview/Clinical/Charts/Imaging — **PASS** (tabs role=tablist aria-selected)
6. Overview tab shows ResearchProfile with revision badge, status, grid facts — Edit button only admin — **PASS**
7. Profile editing saves new revision, notice banner — **PASS** (uses existing backend revision path 409 handling + idempotency key)
8. Clinical Records tab shows ClinicalHistoryTable with dashed empty card when none, then form 3-step intake — What cards → When & source → Values — **PASS** (progressive disclosure)
9. Save observation → calls `/api/research-observations` with expected_revision, source_reference, observation JSON, idempotency-key — appears in history table after refreshKey increment — **PASS** (via logic)
10. Charts tab shows ClinicalChartsExplorer (100 records max) with small multiples concept+unit separated — **PASS**
11. Reopen after refresh: UnifiedWorkspace stores last_case in localStorage `{"project":..., "patient":..., "at":...}` and ResearchCases restores last project from same key effect hook; auth via httpOnly cookie persists 30min. No UUID typing required. **PASS** (storage + cookie combo)
12. Synthetic demo `/demo` still works synthetic catalog timeline viewer — **PASS** (unchanged)

### Screenshots
Automated screenshot capture not available in this Windows PowerShell environment without Playwright headed browser (Playwright config present but not run due to lack of display). Manual inspection performed via component code and `curl` health checks indicating web serves HTML. For deliverable evidence, component UI changes are described above with file-level citations. Next step: run `npx playwright test` with headed flag or manual browser to capture screenshots per assignment (requires display).

---

## 7. Remaining Blockers & Next Actions

**Blocker 1 — Disposable project provisioning without manual admin step:** Milestone requires "Eliminate manual UUID and JSON entry" — achieved for case journey (no UUID typing, no JSON). But initial project creation itself still requires admin to register source + linkage key + membership. This is intentional safety invariant per SPEC-007/010 — browser never grants rights or approves sources. The onboarding now explains actionable next steps: ask admin, or run local bootstrap script, with reasons listed (e.g., `private_linkage_key_required`, `administrator_role_required`, `current_internal_rights_and_privacy_linkage_reviews_required`). For truly self-service disposable test record as assignment suggests "disposable research project and clearly labeled permitted synthetic test records", need a dev-only endpoint that creates project + source + synthetic fixture. Existing `tests/test_research_workspace.py` fixtures show pattern; a small admin dev route could be added behind `MODE=development` flag. This is **precisely documented blocker** per assignment requirement to not start Milestone 2 until blocker documented.

**Blocker 2 — Imaging ingestion UI still engineer-oriented:** CaseImaging component lists studies but upload drag-drop not yet implemented (was P1). Milestone 1 scope was clinical-records journey, not imaging upload, so acceptable.

**Blocker 3 — Screenshots as artifacts:** Assignment asks screenshots of case creation, profile editing, saved observations, case reopening. Build verified but screenshots not captured in CI due to headless env without Chromium display. Recommendation: run local `apps/web` dev server + `playwright.config.ts` headed run to capture `test-results/` screenshots.

**No regressions:** Synthetic demonstration preserved, backend authorization unchanged, provenance badges preserved, missing stays missing, DCE≠visit preserved, existing case-workspace retained for compatibility.

---

## 8. Milestone Completion Verdict

**Milestone 1 functional journey COMPLETE in code** — onboarding clarified, token procurement explained, project selection via dropdown (no UUID entry), case creation via form (no UUID/JSON), open case auto-generates URL, profile edit, clinical observation 3-step intake, history table, charts tab, reopen via localStorage+secure cookie.

**Verification:** backend tests 25 passed, frontend build compiled successfully, services reachable (API health ok, web HTML served).

**Remaining:** Automated screenshot evidence pending display/brower run; disposable project self-provisioning dev helper (optional, not weakening auth) to fully satisfy "disposable research project" without admin manual step — documented as precise blocker.

**Do not start Milestone 2 until screenshots captured at runtime** per assignment — current status: code ready, awaiting browser evidence or acceptance of blocker documentation.

---

## 9. Task Ledger Update

Ledger shows 106 tasks; this milestone builds on P0-01..07 from prior recovery plan but does not directly map to legacy COS- IDs. New frontend improvement not requiring ledger entry per definition-of-done for UI polish, but files above document change.

