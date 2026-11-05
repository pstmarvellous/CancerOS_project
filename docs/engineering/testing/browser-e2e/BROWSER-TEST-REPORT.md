# COS-E2E-001 Browser Test Report

## Journeys actually executed (real Chromium, live loopback stack)

1. **Shell honesty** (`tests/browser/shell.spec.ts`): landing headline, safety
   banner, API-connectivity check, keyboard focus, 390 px overflow — PASS.
2. **Eleven-route sweep** (`tests/browser/e2e-journey-probe.spec.ts`): every
   route renders its real heading (no 404 page), zero console/page errors,
   zero HTTP 5xx. Case-gated routes (`/cases /twin /states /charts /insights
   /guided-demo`) show honest empty states ("Open an authorized case",
   "No project selected"); workflow routes render directly. Screenshots in
   `route-*.png` — PASS.
3. **Negative paths** (`tests/browser/e2e-negative-probe.spec.ts`): zero-UUID
   mesh load → access-denied status; unknown project case list → restricted/
   not-found messaging; no page errors; no secret/traceback echo — PASS.

## Defects found and fixed (minimal, in-scope)

- **D1 — stale production build served.** `/twin /states /charts /insights`
  returned 404 because `apps/web/.next` predated the route pages. Fix: rebuilt
  (`npm run build --workspace @canceros/web`) and restarted the tracked web
  process. Verified: all 200. Regression guard: the journey probe asserts no
  route renders the 404 page.
- **D2 — React hydration error #418 on `/cases`.** `CaseLibrary` read
  `window.location.search` in a lazy `useState` initializer, so SSR
  ("needs-project") and first client render ("loading") disagreed.
  Intermediate render-time `setState` attempts introduced error #301 loops.
  Fix: `apps/web/components/case-library.tsx` now uses Next.js
  `useSearchParams()` inside `Suspense` (the pattern `AppShell` already uses),
  with explicit `initialProject` passthrough for tests. Verified: probe
  asserts zero console errors; `tsc --noEmit` clean; `case-library` +
  `app-shell` component tests 5/5 green.

## Not executed in the browser (explicit, with reason)

- **Mesh 3D interaction (§8)** and **simulation/timeline browser flows
  (§9–10):** the existing specs (`mesh-preview`, `phase3-timeline`) require
  disposable fixture APIs that refuse to start while the dev stack occupies
  port 8000. Stopping the stack mid-session to run them would have destroyed
  the Pass 3–5 evidence environment. Backend coverage for the same pipelines
  is green (29 imaging/measurement + 32 simulation-contract tests this
  session). The viewer/simulation browser runs remain NOT_RUN, not passed.
- **Full case → MRI → mesh → simulation → insights journey (§12):** blocked —
  no seeded demo case exists in the development database, and none should be
  invented (demo fixtures are honesty gates by design). The UI correctly
  refuses to guess a selection.
- **Live Meta inference (§11):** blocked by the export-policy gate (see
  `META-LIVE-INTEGRATION-REPORT.md`). No call attempted.

## No silent substitutions

No screenshots were fabricated; every PNG in this directory was captured by
the passing probe. No mock was presented as live behavior. Skipped/blocked
items keep their status in `E2E-TEST-MATRIX.md`.
