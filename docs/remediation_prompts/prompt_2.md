# COS-REC-01 — Unified Navigation and Case Context

**Role:** Senior Frontend Architect and Full-Stack Integration Engineer

**Mission:** Repair navigation, session context and existing frontend/backend contract mismatches.

Read AGENTS.md, the relevant UI/UX and API specifications, and the COS-REVIEW-003 findings.

## Required behavior

CancerOS must maintain one authoritative selection for:

- Current research project.
- Current research case.
- Selected scenario or branch.
- Selected timepoint or saved state.
- User permissions.

Reuse existing selection and authorization mechanisms where possible.

Do not introduce a second independent context store.

## Tasks

1. Inspect every global and case-specific navigation link.
2. Identify why global Digital Twin and Scenario routes lose an active case.
3. Repair case-context restoration across navigation, refresh and browser-back actions.
4. Fix Clinical Records permissions becoming stuck after refresh.
5. Repair incorrect request structures in existing scenario and insights frontend integrations, using canonical backend schemas.
6. Preserve security: session context must never grant access the server has not authorized.
7. Remove manual UUID entry from normal user journeys.
8. Keep technical identifier entry only in clearly identified advanced tools when justified.

## Example user journey

A user creates **Research Demo Case A**.

The user opens its Clinical Data page, then Digital Twin, then Hypothetical Scenarios, then returns to Clinical Data.

Expected:

- Every page refers to Research Demo Case A.
- No page says "Open a case first."
- No page asks the user to paste a patient or state UUID.
- The previously saved records are still available.
- Browser refresh preserves the authorized selection.
- Signing out removes access to protected case content.

If a case has no imaging, the Digital Twin should say:

"This case has no 3D model yet. Add an imaging study to continue."

It should not produce a generic request failure.

## Acceptance gate

PASS only when a real Playwright browser run proves the complete navigation journey, refresh, browser-back, sign-out, and cross-case isolation behavior.

Include negative tests for inaccessible cases and stale state selection.

Do not mark PASS because the pages render or because mock API responses succeed.

## Report

List changed files, broken routes repaired, real HTTP contract tests, browser steps, screenshots, and PASS/FAIL/BLOCKED.
