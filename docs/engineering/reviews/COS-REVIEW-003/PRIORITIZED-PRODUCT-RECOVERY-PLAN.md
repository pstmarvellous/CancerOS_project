# PRIORITIZED PRODUCT RECOVERY PLAN — COS-REVIEW-003

**Date:** 2026-11-05  
**Principle:** Minimal effective changes, reuse existing backend, preserve safety invariants, clone demo workspace success pattern to real cases.

---

## P0 — Product usability blockers (must fix for researcher to complete journey)

### P0-01: Unified Case-Centered Workspace (single page with tabs)
**Gap:** 7 separate top pages requiring manual ?project=&patient=&lesion=&branch=&state= query param plumbing.  
**Fix files:** Create `apps/web/components/workspace.tsx` + `apps/web/app/workspace/page.tsx` or refactor `case-workspace.tsx` to include sub-tabs rendered in-place (not navigating away).  
**Steps:**
- After auth and project selection, list cases (reuse ResearchCases).
- Clicking case opens workspace with state selector held in component local state (not URL) but syncs to URL query using history.replaceState for deep linking.
- Tabs: Overview (profile + facts), Imaging & 3D (split 65% viewer / 35% measurements + lesion picker), Clinical (timeline left + observation table + intake collapsible), Scenarios (families SC-01..05 cards + builder forms + job list), Insights (context-bound + grounding), Evaluation (compact report).
- Preserve existing route pages as wrappers that redirect to workspace with params for backward compatibility.
- Reuse `demo-workspace.module.css` layout pattern (rail left, content, right rail collapsible).
**Acceptance:** First-time researcher can click "Open case" once and reach 3D viewer without editing URL. No UUID typing.

### P0-02: Onboarding & Token/Project Procurement Explanation
**Gap:** Token source unknown, project creation invisible.  
**Fix:**
- In `ResearchSessionPanel`, add details element explaining: dev mode `scripts/bootstrap_tools.py` (if present) or contact admin, plus link to `/admin` if role admin allows project creation (check if admin route exists).
- When session not authenticated, show two cards side-by-side: "I want to try synthetic demo" → `/demo` prominent, and "I have research access" → sign-in form with help.
- After auth, if no projects, show onboarding: "You are signed in but no projects assigned — ask admin for project access." Link to guided-demo.
- Fix collapsed "Previously imported case summaries" details: auto-open after auth if research cases empty but imported summaries exist.
**Files:** `research-session.tsx`, `research-cases.tsx`, `app.tsx page`

### P0-03: Eliminate Manual UUID Inputs Everywhere
**Gap:** `/simulation` demands UUIDs + token paste; `/twin` demands lesion UUID.  
**Fix:**
- In workspace, lesion picker populated from server list `GET /api/v1/projects/{pid}/patients/{pat}/lesions` (or similar) returning `[{lesion_id, display?}]`. Currently `lesion-viewer.tsx` loads via `/api/cases?project=` heuristic; refactor to proper lesions endpoint already exist? Inspect `imaging_discovery` endpoints; if missing, add proxy.
- Simulation builder: project, patient, branch selectors as dropdowns from loaded context, not text inputs. Branch list from `/branches` list endpoint. Token hidden: reuse ResearchSessionPanel session cookie instead of manual token input; `simulation-workflow.tsx` should call new proxy `/api/simulation/*` that reuses session auth instead of `Authorization: Bearer ${token}` from input. Remove token field.
**Files:** `simulation-workflow.tsx`, `lesion-viewer.tsx`, `case-workspace.tsx`

### P0-04: 3D Viewer Prominence & Measurement Overlay
**Gap:** Viewer too small, measurement outside, no scale/axes.  
**Fix:**
- CSS: workspace twin layout `grid-template-columns: minmax(0, 1.6fr) 380px` min-height 60vh. Viewer host `min-height: 560px`.
- Inside viewer, overlay badge top-left with exact volume + unit + measurement_basis (baseline_reference etc), plus fit/reset buttons floating bottom-right with icons (use inline SVG).
- Add scale reference: small ruler or "mm grid" toggle (optional, low priority but P0 needs at least mm label visible).
- Reuse demo-workspace viewer heading pattern for case twin too (previously only demo had maximize/fullscreen).
- Add maximize button in case twin similar to demo: `fullTwin` boolean expands viewer to overlay full viewport, collapses right rail.
**Files:** `lesion-viewer.tsx`, `mesh-renderer.tsx`, `globals.css`, maybe new `twin-viewer.module.css`

### P0-05: Clinical Observation Entry UX Simplification
**Gap:** Dense single form with 7 kinds, many conditional fields.  
**Fix:**
- Group into steps: 1) What kind? (cards with icons: Lab, Vital, Symptom, Treatment, Diagnosis, Visit, Note). 2) Which concept? (searchable select, not long list). 3) Values (dynamic per kind). 4) Time + Source.
- Field order: Source reference, collection time, concept, original term, value/unit, additional context (instrument etc).
- Progressive disclosure: only show severity when presence symptomatic etc.
- Keep existing validation but surface field-level error near input, not only ErrorSummary after submit.
- Maintain source-backed + missing handling.
**Files:** `observation-intake.tsx`

### P0-06: Scenario Builder Replacing Manual JSON
**Gap:** Simulation workflow JSON handwriting.  
**Fix:**
- Forms: pick shared observed baseline from state list (dropdown showing day + measurement), pick scenario family SC-01..05 (cards with description from FAMILY dict), pick geometry policy none vs anatomical_mesh, schedule (days list — three follow-ups default but editable), assumptions text (free text for engineering policy, but treatment category locked to no_specific_assumption with visible explanation).
- On save, generate JSON conforming to `SimulationConfig` contract programmatically, then call same save endpoints. Reuse preview eligibility display.
- Job list: table with run_id, family, creation time, status (running/succeeded/failed), completion report link, publish button with attestation textarea + reviewed checkbox.
**Files:** `simulation-workflow.tsx` major rewrite or new `scenario-builder.tsx`

### P0-07: Actionable Empty & Error States
**Gap:** Generic "The authorized read failed" + "Add ?project=id" leakage.  
**Fix:**
- For each data load, differentiate: no-auth (show sign-in card), no-project (show project picker), no-case (show create-case CTA), no-lesion (show lesion picker CTA), no-branch (show create branch CTA with baseline), blocked QC (show source-mask measurement fallback explicitly).
- Replace "Add ?project=... to the URL" with "Select a project above; project list shown after signing in."
**Files:** All `explain()` functions + components.

---

## P1 — Functional product completion

### P1-01: Unify Timeline Routes (/timeline & /states → single component)
- Merge `observation-timeline.test.tsx`/`observation-timeline.tsx` + `state-timeline-explorer.tsx` + `state-fusion-view.tsx` into one Timeline page component with two tracks: observation markers + state snapshots.
- Baseline pinning + compare mode via `compare` query param already partially supported in `preserveSelection`.
- Use single URL `/workspace` tab "Timeline".
**Files:** `timeline\page.tsx`, `states\page.tsx`, `observation-timeline.tsx`, `state-timeline-explorer.tsx`

### P1-02: Imaging Upload & DCE Phase UI
- Add drag-drop zone in case-imaging for DICOM/NIfTI, showing study/series metadata: modality, acquisition date, slice count, spacing, orientation, phase label.
- Distinguish DCE phases vs visits visually (badge: phase 1..n, not visit).
- Progress indicator for imaging_jobs.
**Files:** `case-imaging.tsx`, `imaging_api.py` proxy

### P1-03: Clinical Charts Synchronization with Timeline Selection
- Charts explorer currently separate; embed in workspace Clinical tab with timeline filter: selected state filters chart window, or date brush.
- Small multiples already good; add concept filter search, unit toggle if duplicates.
**Files:** `clinical-charts-explorer.tsx`, `trend-view.tsx`

### P1-04: Insights Evidence Drill-down Improvement
- Replace hash slices with human readable "Snapshot from [date] — run [short id]".
- Show evidence cards grouped: case evidence vs background passages, each with source link + open observation.
- Show grounding status badge: grounded vs ungrounded + reasons.
- Show model identity badge when external_private used (e.g., "Meta Llama — private candidate").
**Files:** `insights-explorer.tsx`, `interpretation-panel.tsx`

### P1-05: Evaluation & Technical Details Researcher-Friendly
- Current `/evaluation` unknown content; factor into two panels: researcher summary (what twin states exist, which scenarios available, provenance colors) + engineering details (jobs, versions, blocked gates).
- Surface external dependency blocks (segmentation checkpoint missing) as "Optional — using approved reference masks".

### P1-06: Case Library Search & Server Pagination
- Extend backend to support title/identifier/pseudonym search server-side, or document current client-only search limitation clearly.
- Show loaded count vs total count if API returns total.
**Files:** `research-cases.tsx`

### P1-07: Security Session Persistence
- Replace in-memory Map with Redis or at least filesystem fallback for multi-replica; or at least document single-instance limitation. Not P0 but prevents deployment logout surprises.

---

## P2 — Presentation & refinement

### P2-01: Design System Tokenization
- Consolidate button classes into single module `components/ui/button.tsx` with variants primary/secondary/ghost/danger + sizes.
- Typography: define scale for h1 (44), h2 (21), h3 (17), eyebrow (12), lead (18), body (16), hint (13).
- Spacing: use 8pt scale tokens: gap 8,16,24,32.
- Badge system: component `<Badge origin={}/>` with color + symbol + label + accessible title.
- EmptyState component `<EmptyState title description action />`.

### P2-02: Layout Polish
- Homepage feature cards: align grid, remove duplicate "Demo link preserved" inline hint inside actions span (should be separate note).
- Header brand + selection details: avoid UUID detail summary for non-engineers; instead show breadcrumb trail "Project / Case / Lesion" with human names, only advanced UUID under engineering disclosure.
- Footer technical disclaimer minimal.

### P2-03: Responsive & Touch
- Ensure 3D viewer touch: OrbitControls touchAction none already; test pan/zoom on tablet.
- Two-column workspace collapses to single-column below 900px (right rail below). Demo-workspace already handles leftOpen/rightOpen collapsed.

### P2-04: Accessibility
- Add `aria-label` to lesion picker, scenario cards, timeline buttons (current has aria-pressed but not label).
- Ensure color contrast #92400e outline meets 3:1 etc; badges not color-only (symbols help but need label).
- Keyboard navigation through workspace tabs with roving tablist.

### P2-05: Performance & LOD
- Mesh guard 100k verts / 200k tris ok; add loading skeleton for viewer.
- Demo catalog may be large; prefetch scenario meshes lazy.

### P2-06: Optional Slice Viewer (OHIF)
- Evaluate if OHIF/Cornerstone integration still required vs mesh-only sufficient for finalist demo; if kept optional, add page explaining "MRI slice view available via imported data" but not block twin.

---

## Dependency Order for Implementation After Review

1. P0-02 onboarding fix (small)
2. P0-07 empty states (small, pervasive)
3. P0-01 unified workspace shell (medium — new component, reuses existing)
4. P0-03 eliminate UUID inputs (medium)
5. P0-04 viewer prominence (small-medium)
6. P0-06 scenario builder (medium-large)
7. P0-05 clinical entry simplification (medium)
8. P1-01 timeline unification (medium)
9. P1-02 imaging upload (medium)
10. Remaining P1 then P2 polish

**Do NOT start implementation until review is accepted.** This review preserves source documents unmodified; recovery plan only proposes changes.

---

## How to Verify Recovery

- First-time user (token provided by admin) can in single browser session:
  Open / → Create Research Case (source must pre-exist? admin creates source via /admin) → Open case → See Overview profile → Add 2 clinical observations (lab + vital) → See them in history table → Open Imaging & 3D tab → See lesion list + rotate tumor → Open Scenarios → Pick SC-01 → Generate with form (no JSON) → See job progress → See new states in Timeline → Select state → See measurement update synchronized in viewer + charts → Open Insights → Generate rule-based summary → Grounding shows evidence.

- Synthetic demo still works unchanged.

- Number of manual URL edits required: zero.

- Number of UUID typing required: zero (beyond auto-filled hidden values).
