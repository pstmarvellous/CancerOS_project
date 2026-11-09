# COS-REC-00 recovery reverification

Date: 2026-11-08 (Africa/Lagos). Branch: `cos-rec-00-security-reverification`, starting at `12b9502` from `cos-rec-05-case-management`. Result: **PASS for the bounded local artificial-data recovery baseline**. No real-data processing, publication, deployment or external inference is authorized by this result.

## Findings and correction

The earlier fix already binds the saved-detail HTTP route to the patient's grant and stored patient ID. Its original six tests passed unchanged when dependencies were ready. This run did not reproduce the old detail-route vulnerability on the starting implementation.

However, `saved_runs.reuse_exact` still authorized only project membership. A retained context and saved-result query returned saved metadata to a viewer/editor lacking a current patient grant. Two new negative tests reproduced that service defect before correction (expected HTTPException was not raised). This is a demonstrated service-layer defect; the HTTP reuse route separately builds an authorized context, and this report does not claim an HTTP exploit of that route.

Reuse now checks current patient authorization before lookup or report construction. Detail lookup also predicates SQL on project **and patient** as defense in depth. Tests cover direct Patient-B requests without a grant, Patient-A URLs with Patient-B result IDs, both grants present but mismatched URL/result, authorized A/B retrieval, revoked patient grants, missing bearer authentication and removed project membership. Real RS256 authentication, disposable PostgreSQL and the actual FastAPI detail route are used without mocking `read_saved` or authentication. Denials return the canonical 404 problem with no saved ID, context hash or result content; unauthenticated reads return 401.

The old recovery record excluded a failing frontend security check. Case components wrote pseudonymous case/project identifiers to persistent browser storage. Those writes are removed. URLs preserve refresh/back selection; the existing server session retains only the last successfully backend-authorized case selection. The new internal `GET /api/research-selection` rechecks backend access and returns only project/patient identifiers. Sign-out removes the session and selection. Explicit bearer clients cannot alter/read a separate cookie session's remembered selection. Legacy browser keys are removed on case restoration/remember/sign-out. Static guards now inspect production `.ts` and `.tsx` sources; test-only storage fixtures are excluded. The report-producing hardening test executes its prerequisite checks before writing success.

The original 11 mypy errors in generated manual-input typing were also corrected: static-only canonical input types describe the dynamically projected models; runtime schemas remain unchanged; the note branch narrows on its typed discriminator; encoded source content is explicitly wrapped in SecretStr. No new dependency or schema migration was introduced.

## Executed verification

| Command | Result |
| --- | --- |
| `uv run python -m pytest tests/test_saved_runs.py tests/test_security_hardening.py tests/test_patient_linkage.py tests/test_api.py tests/test_interpretation_runs.py tests/test_context_runs.py tests/test_imaging_ingestion.py tests/test_research_workspace.py tests/test_demo_cases_synthetic.py tests/test_case_navigation_contracts.py tests/test_runtime_identity.py -q --tb=no --junitxml=.local/rec00-reverify-backend.xml` | 70 passed; 0 failures/errors/skips |
| `uv run python -m pytest tests/test_research_workspace.py tests/test_case_navigation_contracts.py -q --tb=no` | 21 passed after the final Python discriminator/type correction; overlaps the 70 above |
| `npm.cmd test -- --reporter=default` | 189 passed in 33 files, including 8 new memory/session-selection tests |
| `npx.cmd playwright test -c playwright.rec00.config.ts` | 4 Chromium journeys passed, no skips: navigation/isolation/sign-out; synthetic 3D demo/scenario/follow-up/refresh; case creation/observation/correction/history; denied demo operations |
| `npm.cmd run build` | Production build passed; 3 existing dynamic filesystem-tracing warnings retained |
| `npm.cmd run typecheck`, `npm.cmd run lint` | Passed |
| `uv run mypy` | Passed, 111 source files |
| `uv run ruff check src/canceros/saved_runs.py src/canceros/research_workspace.py tests/test_saved_runs.py tests/test_security_hardening.py scripts/check_boundaries.py scripts/verify_recovery_artifacts.py` | Passed |
| `npm.cmd run contracts:check` | Passed; existing FastAPI OpenAPI and generated clients unchanged |
| `uv run python scripts/check_boundaries.py`, `uv run python scripts/check_hygiene.py` | Passed production boundaries and Git-visible restricted-path/known-secret checks |
| `uv run python scripts/verify_recovery_artifacts.py` | Passed known-secret/private-key-marker check of public assets, browser static assets and this run's artificial evidence; see artifact-scan.json |
| `uv run python scripts/dev.py start foundation` and `uv run python scripts/dev.py status` | Foundation started successfully; private object roundtrip and database/queue readiness passed; API and web reachable |

These are bounded regression suites, not the entire Python test inventory. Unit selection-route tests mock upstream responses; the browser journeys independently exercise RS256, SQL and real HTTP services with artificial cases. The backend's existing FastAPI/httpx deprecation warning and a demo test's return-not-None warning remain.

## Current workflow and evidence

- [Navigation evidence](navigation/rec01-navigation-evidence.json): case retained across direct tool entry, charts/scenarios, refresh/back; stale state handling, cross-case isolation and viewer/sign-out denials.
- [Case evidence](cases/rec05-cases-evidence.json): artificial cases A/B created; observation 12.3 corrected to 12.4 g/dL, prior revision retained; reload and case isolation verified; no persistent browser case keys.
- [Demo evidence](demo/rec02-demo-evidence.json): fresh token-free homepage launch, WebGL canvas/rotation, hypothetical scenario/follow-up selection and refresh. The displayed region is a synthetic geometric phantom, not authentic breast anatomy or clinical forecasting.
- Screenshots under `cases/`, `navigation/`, `demo/`; case-correction and demo-follow-up screenshots were visually inspected. The former revealed stale local-storage copy, which was corrected before the final browser rerun.
- Framework receipts remain ignored in `.local/rec00-reverify-backend.xml` and `.local/rec00-browser-results.json`; sanitized counts are recorded in `verification.json`. Ephemeral fixture credentials are never attached to evidence.
- [Reference review](../../reference-reviews/COS-REC-00-REVERIFY.md) records consulted specifications/maps, security sources and source gaps.

## Exact implementation and test changes

- `src/canceros/saved_runs.py`; `src/canceros/research_workspace.py`.
- `apps/web/lib/case-selection.ts`; `apps/web/lib/research-session.ts`.
- `apps/web/app/api/case-detail/route.ts`; new `apps/web/app/api/research-selection/route.ts`.
- `apps/web/components/app-shell.tsx`, `case-creator.tsx`, `research-cases.tsx`, `simulation-builder.tsx`, `unified-workspace.tsx`.
- `tests/test_saved_runs.py`; `tests/test_security_hardening.py`; new `apps/web/lib/case-selection.test.tsx`, `apps/web/lib/research-selection.test.tsx`.
- `scripts/check_boundaries.py`; new `scripts/verify_recovery_artifacts.py`; new `playwright.rec00.config.ts`.
- `tests/browser/rec01-navigation.spec.ts`, `rec02-demo.spec.ts`, `rec05-cases.spec.ts`, `ux-recovery.spec.ts`: configurable evidence directories/base URLs preserve historical evidence; the case test also checks empty browser storage after creation. The recovery config explicitly runs current REC-02 demo coverage and the legacy file's still-applicable demo-denial test, not its obsolete UI-copy journey.
- This evidence directory, `docs/engineering/reference-reviews/COS-REC-00-REVERIFY.{md,json}`, `docs/engineering/task-ledger.json`, `docs/engineering/checkpoint.md`.

## Failed attempts, preservation and limits

The first baseline run encountered five database setup errors while PostgreSQL was starting, plus the existing browser-storage failure: 4 passed, 1 failed, 5 errors. The source-grant reproduction subsequently failed correctly on the old service. Early expanded tests had fixture defects (missing membership and deleting membership before its grants), and a denial-envelope assertion expected the wrong response shape; these were corrected. A first browser launcher command lost flags through nested npm, then two checks failed on intentional removal of local-storage restore and stale demo copy. Session-backed restore fixed the navigation regression; the maintained REC-02 journey verifies current demo behavior. Initial mypy runs failed before the compatibility fixes. Failed attempts are not counted as passes.

The initial full pytest connection traceback exposed a local disposable database credential in tool output; it was not copied into these evidence files. Subsequent database runs use `--tb=no`. The known-secret scan verifies the generated public/browser artifacts, not confidentiality of that earlier tool transcript. Local development credentials must not be reused as deployment credentials.

All initial uncommitted review edits, the deleted milestone report, untracked independent-review material and remediation prompts were preserved. No reset, clean, commit, push or database reset/drop was performed. Artificial HTTP fixtures commit rows to the explicitly disposable test database; those rows are not rolled back by the outer fixture. Generated private test objects can also remain. Historical auto-written demo/security receipts were restored to their starting content; current results are recorded here.

Residual limits: Next.js still warns that dynamic demo-bundle filesystem tracing can include excessive server files in deployment output; deployment packaging needs a separate review before release. This run scans known local credentials and private-key markers, not arbitrary PHI, Git history or all dependencies. Server sessions are process-local and expire; restarting the web process requires signing in again. Source rights, qualified scientific review, authentic baseline/longitudinal evidence, live-provider access, deployment and publication gates remain open. No critical saved-result defect remains in the exercised scope; this is not a complete security audit or authorization to use real patient data.

## Reproduce locally

Use the locked dependencies and startup commands in `infrastructure/README.md`: `uv sync --locked`, `npm.cmd ci`, `npm.cmd run build`, `uv run python scripts/dev.py start foundation`. Run backend tests only after dependency readiness. For browser verification, start `uv run python scripts/product_browser_fixture.py`, then `npx.cmd playwright test -c playwright.rec00.config.ts`; stop only that fixture with `uv run python scripts/product_browser_fixture.py --stop`. It uses the local disposable test database; the browser config owns the separate loopback web port 3001. Foundation remains on port 3000. `uv run python scripts/dev.py stop foundation` stops the tracked local services while retaining data.

Hackathon Compliance Impact: privacy, accurate contribution/evidence reporting and outage independence apply. No model call or external patient-data transmission occurred; model/rule eligibility remains unverified. Architecture, source specifications and original maps are preserved.
