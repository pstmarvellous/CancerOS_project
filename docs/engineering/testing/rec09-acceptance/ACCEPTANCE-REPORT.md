# COS-REC-09 — Independent Product Acceptance Report

**Date:** 2026-11-09. **Role:** independent QA (no credit taken for prior implementation summaries; every verdict below rests on checks executed in this session).
**Scope:** synthetic demonstration data and artificial fixture records only. No authentic patient data, rights, or clinical validation exists in this environment; nothing below establishes them.

## Environment

- Web: production `next start` on 127.0.0.1:3001 (`CANCEROS_SYNTHETIC_DEMO=1`, `API_BASE_URL=http://127.0.0.1:8001`), fresh Chromium profile per journey.
- API: disposable product fixture (`scripts/product_browser_fixture.py`) on 127.0.0.1:8001, synthetic-only sources, admin/viewer/outsider tokens, refreshed mid-session after expiry.
- Backend suites re-run in-session against disposable PostgreSQL + private versioned storage + queue.

## Journey verdicts (each decided separately; no combined score)

### Journey A — first-time visitor (synthetic demo): PASS

Browser, fresh profile, no instructions. Homepage purpose clear → demo launches → 3D canvas renders and responds to camera controls → all five scenarios selectable with measurements (SC-01…SC-05) → Day 37 shows **64 mm³** (matches served bundle value and `data-testid`) → clinical observations listed with relative days → insights view shows the local template with exact values and marks live Meta unavailable (no external call) → 390px layout has zero horizontal overflow. Zero console/page errors. Evidence: `journey-A.json`, `A-01…A-05.png`.

### Journey B — research case management (artificial account): PASS

Admin sign-in → case created and opened → artificial hemoglobin observation 9.1 g/dL saved → reload retains → corrected to 9.2 with Superseded revision retained → chart parity table shows 9.2/9.1 → navigate away and back → Case B sees none of Case A's data → sign-out revokes (session cookie gone, case URLs gated). Zero errors. Evidence: `journey-B.json`, `B-01…B-03.png`.

### Journey C — imaging (synthetic): PARTIAL (6/7 PASS, 1 FAIL)

Seeded via real APIs: synthetic NIfTI staged → previewed → confirmed → geometry validated (3×4×2, spacing 2×3×4 mm, RAS). In-browser: study → import → provenance → geometry PASS; absent mask shows the required message verbatim and synthesizes nothing; refresh retains the association. Full chain (mask → alignment → annotation → QC pass → measurement 48 mm³ → mesh → validated mesh-QC → lesion) all succeed via real APIs and the real worker. **FAIL: the case 3D viewer cannot display the validated mesh** — see defect D-01. Evidence: `journey-C.json`, `C-01…C-04.png`.

### Journey D — research workflow (simulation): PARTIAL/BLOCKED

API: simulation branch creation on the measured baseline succeeds (`journey-D.json`). Backend engine suites pass (see API evidence). BLOCKED in-browser: no eligible generated states exist and driving config→run→completion→states needs the full twin-state apparatus beyond this session; genuine scenario generation was **not** demonstrated in the browser, and demo playback was not substituted for it.

### Journey E — AI interpretation: PARTIAL

- Local explanation: PASS. Demo insights (Journey A) shows the deterministic local template with exact values and marks live unavailable. Case rule-based path verified by re-run backend template/grounding tests (25 passed) and REC-07 component tests (9 passed in-session).
- Live Meta: BLOCKED (correctly). `EXTERNAL_INFERENCE_ENABLED=false`, no export policy; `read_policy` raises `EXTERNAL_PROCESSING_NOT_ALLOWED`. No external request sent; no template presented as live output.
- Case insights in-browser on a generated state: BLOCKED (depends on Journey D states).

## Authorization boundaries: PASS

- Viewer creating a case with a valid body: **403**. Outsider reading a case: **404**. Cross-patient read as viewer: **403**. Probes in `api-probes.json`.
- Lesion-viewer geometry proxy ignored cookie sessions (401 for all browser users) — found and fixed during this acceptance (see D-02; fix verified by 401→409 progression and full suite).

## Separate readiness verdicts

- **Synthetic demonstration readiness: READY.** A first-time non-medical visitor completes the demo unassisted; all showcased functionality genuinely works.
- **Research-case management readiness: READY (synthetic scope).** Full lifecycle works with enforced isolation.
- **Imaging pipeline readiness: NOT READY.** Backend pipeline is sound, but the case 3D viewer cannot display validated results (D-01).
- **Simulation workflow readiness: NOT READY.** Engine code passes tests, but no browser-demonstrated generation path exists here.
- **AI integration readiness: READY (local only); LIVE BLOCKED (correctly).**
- **Overall portfolio demonstration readiness: NOT YET.** Journeys A and B are genuinely demonstrable; C/D are not end-to-end in the browser.
- **Clinical/research release readiness: NOT ASSESSED — no authentic data, rights, qualified review, or longitudinal evidence exists. Nothing in this report implies it.**

## Remaining-defect backlog

| ID | Severity | Finding | Reproduction |
|----|----------|---------|--------------|
| D-01 | Major | Case 3D viewer (LesionViewer) cannot resolve geometry for a genuinely created lesion: it probes only `mesh-qc-reports/{lesion.id}` and `mesh-qc-reports/{baseline_segmentation_id}`, but mesh-QC reports carry fresh UUIDs, so both return 404 and the viewer ends in 409. Backend chain (measurement 48 mm³, validated mesh-QC, lesion) all succeed. | Seed full chain (`scripts/seed_rec09_fullchain.py` + worker drain), open case Imaging & 3D, run workflow, Open 3D Model → "Current QC or source permission blocks display". API proof: baseline_seg→404, lesion.id→404, real mesh-qc id→200. |
| D-02 | Major (fixed) | Lesion-viewer geometry proxy dropped cookie-session auth (401 for all browser users). Fixed: use `researchAuthorization` in the geometry branch (`apps/web/app/api/lesion-viewer/route.ts`). Full suite re-run green. | Pre-fix twin screenshot in `C-04` history; post-fix 401→409 progression in Journey C re-run. |
| D-03 | Minor | `ux-recovery.spec.ts` asserts superseded homepage/demo copy and stale control names; fails against current UI. Left to owning workstream. | Run `npx playwright test tests/browser/ux-recovery.spec.ts`. |
| D-04 | Deferred | Browser-driven simulation config→run→states and case-insights-on-generated-state need the full twin-state apparatus; API evidence only in this session. | `scripts/attempt_rec09_simulation.py` stops after branch creation. |

## Evidence index

- `journey-A.json`, `journey-B.json`, `journey-C.json`, `journey-D.json`, `api-probes.json`
- Screenshots `A-01…A-05`, `B-01…B-03`, `C-01…C-04`
- Backend (re-run in-session): 41 imaging + 65 simulation/interpretation/twin tests passed; frontend suite 221 passed; typecheck/lint/build green
- Repro scripts: `scripts/seed_rec09_imaging.py`, `scripts/seed_rec09_fullchain.py`, `scripts/probe_rec09_negatives.py`, `scripts/attempt_rec09_simulation.py`, `tests/browser/rec09-acceptance.spec.ts`, `playwright.rec09.config.ts`
