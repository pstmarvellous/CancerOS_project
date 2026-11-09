# Critical review of COS-REC-06–09

Date: 2026-11-09. **Draft: fresh browser verification is pending.**

The owner requested independent scrutiny of the work claimed for prompts 7–10,
followed by completion of missing implementation. Prompt 11 supplies the mandatory
execution and evidence rules. Prior reports are claims to investigate, rather than
proof of completion. Original specifications, map packages and source documents
remain authoritative and unchanged.

## Initial completion assessment

| Stage | Required user outcome | Finding in the prior implementation/evidence | Initial decision |
| --- | --- | --- | --- |
| COS-REC-06 / prompt 7 | Eligible case study and mask pass geometry/alignment/QC, produce deterministic measurements and render their own 3D mesh | The prior acceptance report records a genuine mesh-display failure after a successful synthetic backend chain. Accepted formats, import restrictions and source rights remain subject to the imaging review. | PARTIAL; synthetic end-to-end browser gate failed. Authentic MRI remains separately BLOCKED. |
| COS-REC-07 / prompt 8 | Selected case/state resolves exact context and a correctly scoped local explanation; state changes clear stale results | Prior evidence substitutes a public demo template and backend/component tests for the required browser journey on a generated case state. No standalone Journey E artifact existed. | PARTIAL; case browser acceptance missing. Live Meta remains separately BLOCKED. |
| COS-REC-08 / prompt 9 | Understandable application, usable core keyboard actions and unclipped controls across major desktop/mobile screens | Only homepage/demo/gated-case screenshots existed. The test measured overlap/clipping without asserting them; only homepage overflow was asserted. Keyboard evidence was a single Tab landing on a link/button. Authenticated screens and 320px were untested. Full required before/after pairs were absent. | PARTIAL; `verified` and “Complete” overstate evidence. |
| COS-REC-09 / prompt 10 | Independent browser journeys A–E through genuine APIs, separate readiness decisions and actionable defects | A/B have useful but incomplete evidence; C explicitly fails mesh display; D stops after creating a branch; E lacks the required case-state browser journey. Some report claims have no corresponding test action. | PARTIAL; overall portfolio readiness is not established. |

Prompt 11 explicitly says a stage is complete only when every mandatory acceptance
condition has evidence. Its definition cannot be replaced with “execution and
reporting complete.” The previous handoff's distinction does not justify marking
unfinished mandatory product outcomes as verified. No ledger correction is claimed
in this draft; final ledger reconciliation belongs to the coordinating reviewer.

## Defects in the earlier acceptance evidence

1. **Mesh failure did not fail the browser suite.** The old Journey C explicitly
   excluded its `mesh-3d` FAIL from the final assertion. An acceptance suite must
   preserve the failure and return a failed test until the behavior is repaired.
2. **Simulation was not attempted beyond branch creation.**
   `scripts/attempt_rec09_simulation.py` created an origin and branch, then exited.
   It did not save a configuration, dispatch a job, execute the engine or inspect
   generated states. “Beyond this session” is an execution gap, not proof of an
   external eligibility blocker.
3. **Public demo checks were weaker than their descriptions.** All five scenario
   checks inspected shared-baseline values and required only a digit. The clinical
   check counted tables rather than checking observations and relative days. The
   explanation check looked for either `216` or `64`, without proving exact state
   binding. Automated copy checks do not establish unassisted human comprehension.
4. **Case-management report exceeded its recorded actions.** The old test did not
   return to Case A after leaving or exercise sign-out revocation. Case B isolation
   inspected its default summary, not its clinical records/chart surface.
5. **Mobile/accessibility claims were too broad.** The old REC-08 test calculated
   demo overflow, overlaps and clipping but never asserted those results. It did
   not test 320px, authenticated forms, keyboard activation, focus retention or
   keyboard camera/scenario/time controls. A first Tab does not prove usable core
   keyboard navigation.
6. **Screenshot coverage was incomplete.** Five REC-08 after-shots do not supply
   the required eight-screen before/after comparison. Historical before images
   cannot be fabricated retrospectively. Any new visual fix needs a genuine
   current-baseline image and a matching post-change viewport image.
7. **Frontend typecheck scope was unclear.** `npm run typecheck` uses
   `apps/web/tsconfig.json`, which includes the app tree, not root-level browser
   tests/configs. A separate strict TypeScript check is required for that harness.

## Remediation under review

The coordinating reviewer owns final integration, browser execution and verdicts.
The following changes are present or in progress and must not be mistaken for a
fresh browser pass:

- Imaging linkage, import workflow and negative-case remediation are being
  reviewed through the existing imaging services and private storage boundary.
- The browser acceptance suite now requires the mesh step to pass and adds actual
  generation, generated-state inspection and a selected-case local explanation.
- REC-08 now asserts document overflow and visible control overlap/clipping at
  1440, 390 and 320px. It covers public screens plus an authenticated case library,
  creation form and clinical form, and exercises actual keyboard navigation and
  activation for launch, camera, scenario, time and maximized viewer focus.
- Stale homepage/launch/camera selectors in `ux-recovery.spec.ts` were updated.
- The simulation-builder review identified query hydration, branch-selection
  synchronization, stale saved assumptions and current draft-revision issues.
  The coordinating reviewer reports corrections; browser verification remains
  pending.
- A bounded fixture worker uses the actual canonical outbox/Redis/imaging worker,
  including simulation commands. It requires local explicitly disposable SQL,
  local queue/private storage, a synthetic fixture bundle and synthetic project
  source versions. It refuses foreign ready-queue work, suppresses private
  exception payloads and enforces a maximum 900-second process wall limit. This
  is test infrastructure, not a second application processing engine.

## Checks actually performed by the acceptance-review workstream

| Command or action | Actual result | Limit |
| --- | --- | --- |
| `uv run pytest tests/test_simulation_runs.py -q` | 5 existing tests passed; 2 new tests failed because the tests expected 403 for unknown project while the established authorization boundary returns 404 | This attempt failed; it is not a seven-test pass. |
| `uv run pytest tests/test_simulation_runs.py -q -k latest_config --tb=short` after correcting those expectations | **2 passed, 5 deselected**, 28.04 seconds | The complete seven-test file was not rerun after this test-only correction. |
| New latest-config service test | Empty branch returns none; exact newest revision/seed returned; old draft remains immutable; wrong role/project/patient/branch denied; withdrawn latest draft fails closed without falling back | Disposable synthetic SQL and private storage only. |
| New latest-config HTTP test | Genuine JWT/SQL authorization; unauthenticated 401; current draft round-trip; cross-project/patient 404; viewer 403; branch withdrawal 409 | Does not establish clinical or authentic-data validity. |
| `uv run ruff check scripts/recovery_test_worker.py tests/test_simulation_runs.py` | PASS | Only these owned Python files. |
| `uv run ruff format --check scripts/recovery_test_worker.py tests/test_simulation_runs.py` | PASS; both formatted | Formatting is not behavioral acceptance. |
| `npx.cmd playwright test --config playwright.rec-audit-ui.config.ts --list` | PASS; 3 tests discovered | Discovery does not execute browser journeys. |
| `npx.cmd tsc --noEmit --strict --skipLibCheck --target ES2022 --module ESNext --moduleResolution Bundler --lib ES2022,DOM,DOM.Iterable tests/browser/rec08-usability.spec.ts tests/browser/rec09-acceptance.spec.ts tests/browser/ux-recovery.spec.ts playwright.rec-audit-ui.config.ts` | PASS, exit 0 | Checks the three browser specs and UI audit configuration, independently of the app-only typecheck. |
| Fixture worker short smoke | Actual worker became ready and processed 3 transport deliveries; supervisor stopped at its wall limit | Delivery count does not prove successful job result status. No clinical data or external inference was used. |

The five existing tests and two corrected new tests passed in separate invocations;
this draft deliberately does not describe them as one clean seven-test run.
Disposable test credentials are excluded from this report. A dependency deprecation
warning from the installed Starlette/httpx test client remains unrelated to the
acceptance verdict.

## Fresh acceptance matrix — pending integration results

The first stricter UI baseline has now executed. The public-screen test passed at
all three widths. The keyboard test stopped on a harness error: both the timeline
and chart correctly exposed a selected Day button, while the test incorrectly
expected one across the whole page. The authenticated-screen test exposed a real
320px defect: 14px document overflow and overlapping footer-link bounding boxes.
All 27 baseline screenshots and nine screen measurements are retained under
`usability/before/`. They are genuine pre-remediation captures, not reconstructed
historical screenshots.

The corrective changes wrap the clinical step badges/headings and action rows,
allow the category grid to fit nested narrow cards, remove duplicated step
headings and present the case footer as separately spaced wrapping links. The
keyboard assertion now checks the timeline and chart separately against the
served follow-up's exact identifier, day and measured value. Modal keyboard
checks also verify both focus-wrap directions. Post-change browser results remain
pending; static review has not established a separate modal-focus product defect.

The standalone strict browser check passed after these changes. The app typecheck
attempt failed on TS7023 return-type annotations in `lesion-viewer.test.tsx` lines
18 and 111, owned by the imaging workstream; no pass is claimed for that attempt.

| Area / journey | Required evidence | Fresh status |
| --- | --- | --- |
| A: synthetic demonstration | Fresh browser launch, real camera interaction, distinct scenario follow-ups, time/observation parity, correctly labeled explanation | PENDING |
| B: case management | Create, save, reopen, append correction, chart, leave/return, clinical isolation, sign-out denial | PENDING |
| C: synthetic imaging | Private input, geometry/alignment/QC, deterministic measurement, correct mesh, refresh persistence, negative scope/input cases | PENDING |
| D: actual simulation | Explicit configuration, canonical queued job, real worker completion, generated timepoints and synchronized observations | PENDING |
| E: selected-case local interpretation | Exact state context and values, supporting references, scope isolation, stale-result clearing, recoverable errors | PENDING |
| Live Meta | Verified account/model/access, valid export authorization and actual permitted grounded response | BLOCKED; no enablement or transmission authorized by this review |
| REC-08 layout and keyboard | All required screens, 1440/390/320px, visible control bounds, keyboard actions/focus and genuine screenshot comparisons | PENDING; historical full before set absent |
| Authentic MRI | Documented source rights, de-identification, qualified geometry/annotation review and independent reference | BLOCKED; owner: data-rights/scientific-review roles |
| Clinical/research release | Applicable privacy, scientific and longitudinal verification | NOT ASSESSED; synthetic engineering checks cannot establish it |
| Overall portfolio demonstration | Showcased workflows genuinely work without developer intervention | NOT ESTABLISHED pending fresh browser outcomes |

## Remaining work before final decisions

- Finish the coordinated fresh browser runs and retain step-level artifacts,
  screenshots/traces and backend result identities/hashes where appropriate.
- Reconcile each failed check against a product defect, stale harness assumption
  or an exact external gate. Record owner, missing evidence and next action.
- Verify mobile/authenticated screens and keyboard behavior rather than relying
  on build/component results. Preserve failures from the initial strict run.
- Record further targeted backend tests from the imaging and interpretation
  reviewers; strict typing of the three audited browser specs already passed.
- Issue separate readiness decisions for synthetic demo, research cases, imaging,
  simulation, local AI, live AI, portfolio demonstration and clinical release.
- Update the task ledger and handoff only after those results are known.

## Hackathon Compliance Impact

This review preserves source privacy, truthful contribution/evidence reporting,
provider-neutral integration and deterministic scientific computation. No genuine
patient data or restricted source materials are exported, and no model output is
misrepresented as live Meta inference. Authentic source rights, provider access,
scientific review, competition eligibility and publication remain separate gates.
