# USER JOURNEY FAILURE MAP — COS-REVIEW-003

**Date:** 2026-11-05  
**Method:** Code inspection + manual logical walkthrough (no live backend in review env, but path reproduction based on code).

---

## Journey 1: First-time researcher tries to understand CancerOS

| Step | Action | Expected | Actual | Obstacle | Severity | Reproduction |
|---|---|---|---|---|---|---|
|1|Open `/`|Sees explainer, two clear next steps: try demo or create real case with guide|Duplicate CTAs, no guide|No onboarding differentiation "I have data vs I want to explore"|Medium|`apps/web/app/page.tsx` has two CTAs both visible, demo link preserved as field-hint inline|
|2|Click Create Research Case|Landing explaining token/project/source|Goes to `/cases` which shows password box|Token source undefined|P0 blocker|Open `/cases` without auth → ResearchSessionPanel password input. No link to bootstrap script|

---

## Journey 2: Researcher with valid token but no case

Assume token procured (via external admin).

| Step | Action | Expected | Actual | Obstacle | Severity |
|---|---|---|---|---|---|
|1|Enter token in `/cases`|Signs in, shows projects dropdown|Shows project select but if single project, still dropdown|Minor|Medium|
|2|Select project|Case library auto loads with title, counts|Loads via `/api/research-cases?project=` but requires admin role for source options|If viewer role, source list empty|P0 for creators|
|3|Click Create Research Case button|Form with title etc|Form requires source select from eligible list; if no source eligible shows message "An administrator must register a source and record the applicable rights and privacy review. Your existing cases remain available."|No CTA to register source|P0|
|4|Fill form + save|Saves case, moves to detail|Saves via POST `/api/research-cases?project=` with idempotency key, pushes to `/cases/detail?project=&patient=`|Works if source exists|Pass when source present|
|5|Case detail|Overview with profile edit, clinical intake, imaging|Overview leads with what known/missing|Requires separate fetches `/api/case-detail`, `/api/case-visits`, `/api/case-observations` POST|Partial pass|

**Evidence files:**
- `research-cases.tsx` lines search-filtered loadMore etc
- `case-creator.tsx` eligible filtering
- `case-workspace.tsx` useSelection + load()

---

## Journey 3: Enter clinical observation

| Step | Action | Expected | Actual | Obstacle | Severity |
|---|---|---|---|---|---|
|1|In case detail, find Add observation|Prominent add button|Section header "SOURCE-BACKED DATA ENTRY — Add a clinical observation" with field-hint + form|Form dense but present|Medium|
|2|Pick kind/lab concept|Dropdowns|Two selects: kind then concept list|Concepts technical codes, no search|Medium|
|3|Enter value/unit/time/source|Grouped|Grouped: term*, source*, time precision, time input, value/unit etc + optional fields conditional|Field order not workflow natural; timestamp regex expects seconds+TZ ISO|Medium|
|4|Save|Accepted count toast|Calls `/api/research-observations?project=&patient=` + expected_revision + source_ref + observation JSON|Error handling present but revision may have changed causing 409|Medium|
|5|See result in history table|Table updates|Should reload via onSaved callback but manual refresh may be needed (check case-workspace onSaved refreshes list?)|Needs verify|Medium|

---

## Journey 4: Imaging ingestion & 3D viewer

| Step | Action | Expected | Actual | Obstacle | Severity |
|---|---|---|---|---|---|
|1|In case detail, open imaging section|Upload DICOM/NIfTI + DCE phase context|Component `CaseImaging` — code not inspected fully but likely list + upload|Upload maybe gated, no drag-drop|P0-P1|
|2|See lesion list|Picker with scan date + modality|LesionViewer loads lesions via fetch but shows needs-selection without context|User must discover lesion UUID via prior call|P0|
|3|Rotate/zoom tumor|Prominent viewer 60%+ viewport|Viewer host inside lesion-viewer body, controls separate buttons|Canvas too small, no scale bar, no measurement badge inside|P0|
|4|See measurements|Volume mm³ prominent|MeasurementReport presumably beside but in code `blockedMeasurement` separate|Measurement not inside viewport|P1|

**Repro file:** `lesion-viewer.tsx` `initialSelection(params)` reads project/patient/lesion query. `loadLesions` called on mount. `explain` maps status codes. 3D canvas failure shows "Retry 3D viewer" with graphics acceleration hint.

---

## Journey 5: Hypothetical scenarios (real, not demo)

| Step | Action | Expected | Actual | Obstacle | Severity |
|---|---|---|---|---|---|
|1|Click Hypothetical Scenarios tab|Shows 5 families cards, baseline picker, assumption forms|Shows `/simulation` page titled "Configure a hypothetical research branch" with token + UUID inputs and draft textarea|Manual UUID entry required|P0 blocker — usability fail|
|2|Enter config JSON|Form|Must write JSON matching baseline_hash, branch_id etc|JSON authoring exclusive to engineers|P0|
|3|Save draft|Immutable version|Calls `/branches/{branchId}/simulation-configs` POST expected_draft_revision + config|Works but revision handling manual|Medium|
|4|Inspect eligibility + schedule|Shows capability + sample dates|inspect() fetches eligibility + schedule-preview|Report display via StateFusionView? Not prominent|P1|
|5|Freeze run + poll job|Progress|freeze() calls `/branches/{branchId}/simulation-runs`|No auto-poll UI loop, token manual each request|P0|
|6|Publish with attestation|Checkbox + save|Attestation + reviewed fields|Unpublished stays hidden — user may think generation failed|P1|

**Evidence:** `simulation-workflow.tsx` lines 44-146 require `UUID.test(project) && patient && branchId && token.trim()` before any act. Draft revision text input string '0' converted via Number. CONFIG treatment category gated.

---

## Journey 6: Demo (synthetic) — SUCCESS path

| Step | Action | Expected | Actual |
|---|---|---|---|
|1|Open `/demo`|Synthetic workspace opens|Calls POST `/api/demo-session` then GET `/api/demo` catalog|
|2|Pick scenario|Family SC-01 default|Select value family triggers navigate pushState + fetch scenario mesh|
|3|Rotate 3D|Orbit controls|OrbitControls with pan mode toggle|
|4|Pick timeline point|Buttons day 0, day X etc with volume|State buttons aria-pressed, inline measurement|
|5|Switch views|Overview, Twin, Scenarios, Clinical, Insights, Technical|VIEWS mapping preserved in URL `?view=twin` etc|
|6|Maximize/Fullscreen|Large viewer|FullTwin boolean + native fullscreen API with trap + body overflow hidden|

**Works** when API available returning DemoCatalog with 5 scenarios + meshes.

**Why it works:** Single workspace component orchestrates selection internally, no external UUID homework, no role gates, precomputed assets.

**Lesson:** Real workspace should clone this pattern.

---

## Journey 7: Clinical charts & timeline sync

| Step | Action | Expected | Actual | Obstacle | Severity |
|---|---|---|---|---|---|
|1|Open Clinical Data with project/patient|Shows lab small multiples, vitals, symptoms, treatments|ClinicalChartsExplorer loads 100 records via ObservationPage POST + grouped by concept+unit|Requires project+patient query|P1|
|2|Switch panel|lab/vitals/symptom/treatment tabs|Panel state via useState panel key plus description field|Panels present|Pass|
|3|Timeline sync|Click point filters charts etc|ObservationTimeline / StateTimelineExplorer separate components using project/patient/state query|Two timeline pages confuse|P1|
|4|Compare two states|Pin second|State timeline explorer may have compare feature (compare query param)|compare param supported in preserveSelection but UI not clear|P1|

---

## Journey 8: AI insights

| Step | Action | Expected | Actual | Obstacle | Severity |
|---|---|---|---|---|---|
|1|Open Insights with project/patient/state|Context loads bound to snapshot hash|InsightsExplorer loadContext POST action=context|Needs state param, else needs-selection|P0|
|2|Generate rule-based summary|Button|Rule-based mode POST action=interpret mode rule_based|Generates|Partial|
|3|Inspect grounding|Open grounding report|Request action=ground? (not fully inspected) display separate|Technical hash display|P1|
|4|Private Meta candidate|External private mode|Requires private policy gate, external API key model gateway|Blocked until policy evidence|Intentional essential blocker but not explained UX-wise|P1|

---

## Journey 9: Guided demo 7 steps

| Step | Action | Expected | Actual | Obstacle |
|---|---|---|---|---|
|1|Open `/guided-demo`|List 7 steps with where/href/what/check|Steps array static in component, navigation buttons Previous/Next disabled without checkbox confirmed|Text only, does not drive real UI|
|2|Step navigation|Automated walkthrough|Only link via href, not state passing|Checkbox gate "I understand read-only" before Next|
|3|Exit|Return overview|Link to `/` present|Pass|

**Verdict:** Guided demo correct as safety placeholder but not genuine interactive tour.

---

## Cross-cutting failure patterns

1. **UUID leak:** User must handle UUIDs when URL query lacks them. No human-friendly slugs. AppShell hides raw selection under details but still raw.
2. **Empty state not actionable:** "No project selected — Add ?project=id to URL" tells engineer what to do but not researcher how to get project id. Should say "Sign in, then select a project from list" (fix exists after auth but before auth it's manual).
3. ** Role confusion:** Many pages say "An administrator can review imports; a viewer can follow the guided demo instead." User may be viewer intentionally but product still reports as error.
4.  **Two sources of truth for case list:** `/api/cases` (PatientPage) vs `/api/research-cases`. Both similar but not same counts.
5. **No deep linking preservation on direct nav:** Clicking primary nav while on `/cases/detail?project=&patient=` loses patient unless preserveSelection applied — AppShell applies preserveSelection only for certain demos and when patient present, but not uniformly. Simulation link preserves? Cases detail via preserveSelection copies selection, but Overview link to "/" loses context.
6. **Offline:** When API down, every page shows same ambiguous "Research access could not be checked". Not differentiated per page.
7. **3D failure recovery:** Only demo has failed3D with retry button; case twin retry exists per lesion-viewer but less visible.

---

## Severity ratings used

- P0: blocks core research journey; first-time user cannot succeed
- P1: major usability degradation but workaround exists
- P2: polish / refinement / secondary audience
