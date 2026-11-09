# Original requirements to delivered behavior

Baseline: the twelve original source documents, freshly inventoried in [source-inventory.json](evidence/source-inventory.json). Document status is proposed/draft as printed; blanket formal adoption is not evidenced. This matrix was reconstructed independently, not copied from earlier audits or existing completion labels. It covers the important product requirements and failure boundaries, rather than pretending to be exhaustive line-level certification.

## Reading the matrix

Statuses have their requested literal meanings: `FULLY_IMPLEMENTED_AND_VERIFIED`, `IMPLEMENTED_BUT_NOT_USER_ACCESSIBLE`, `PARTIALLY_IMPLEMENTED`, `BACKEND_ONLY`, `UI_ONLY_OR_MOCK`, `BLOCKED_BY_EXTERNAL_DEPENDENCY`, `NOT_IMPLEMENTED`, `NOT_VERIFIED`, `NOT_APPLICABLE`. A status applies only to the row's stated scope. Synthetic verification is never authentic-data verification.

Evidence keys: **B** = fresh browser observation in [checks](evidence/browser-checks.json)/[journeys](USER-JOURNEY-FAILURE-MAP.md); **C** = current code inspection; **P** = [executable contract/function probes](evidence/contract-probes.json); **T** = [119 synthetic/unit/MockTransport checks](evidence/tests-summary.json). Screenshots are linked in the relevant U/J finding.

Actual implementation file groups:

| Key | Files inspected |
| --- | --- |
| F1 | `apps/web/components/app-shell.tsx`, `case-library.tsx`, `case-creator.tsx`, `research-session.tsx`, `unified-workspace.tsx`, `research-profile.tsx` |
| F2 | `apps/web/components/observation-intake.tsx`, `clinical-history-table.tsx`, `clinical-charts-explorer.tsx`, `state-timeline-explorer.tsx` |
| F3 | `apps/web/components/case-imaging.tsx`, `lesion-viewer.tsx`, `mesh-renderer.tsx`, `apps/web/app/admin/page.tsx` |
| F4 | `apps/web/app/simulation/page.tsx`, `components/simulation-builder.tsx`, `app/api/simulation/route.ts` |
| F5 | `apps/web/components/insights-explorer.tsx`, `app/api/insights/route.ts`, `components/interpretation-panel.tsx` |
| F6 | `apps/web/components/demo-workspace.tsx`, `guided-demo.tsx`, `evaluation-report.tsx`, `ux-checklist.tsx`, `apps/web/lib/synthetic-demo.ts` |
| S1 | `src/canceros/research_api.py`, `research_workspace.py`, `clinical_ingestion.py`, `clinical_api.py`, `patient_linkage.py`, `identity.py`, migrations |
| S2 | `src/canceros/imaging_ingestion.py`, `imaging_formats.py`, `imaging_geometry.py`, `annotation_import.py`, `physical_measurements.py`, `mesh_reconstruction.py`, imaging worker modules |
| S3 | `src/canceros/twin_states.py`, `simulation_runs.py`, `simulation_execution.py`, `scenario_families.py`, `clinical_generation_runs.py`, `synthetic_geometry.py`, `dependent_updates.py`, `state_api.py` |
| S4 | `src/canceros/context_runs.py`, `context_contracts.py`, `interpretation_runs.py`, `provider_gateway.py`, `saved_api.py`, `saved_runs.py`, grounding/retrieval modules |

## Case, clinical and UI requirements

| Requirement / source locator | Intended behavior | Implementation / user entry | Status and evidence | Missing functionality, UX impact and correction | Priority |
| --- | --- | --- | --- | --- | --- |
| PRD FR-001–003 pp15–16; UJ-02 pp10–11 | Create/retrieve stable pseudonymous research profile linked to source | F1/S1; Home → Cases → New research case | PARTIALLY_IMPLEMENTED; B J02 | Artificial admin creation/reopen works. Authentic source/import baseline incomplete. Complete controlled onboarding, preserve pseudonymization. | P0 |
| PRD FR-004–007; SPEC-009 §4.2 p3 | Visits, supported updates and meaningful profile completeness | F1/F2/S1; case Overview/Clinical | PARTIALLY_IMPLEMENTED; B J02/J03, C | Profile revision works. Source/baseline/receptor/history availability fragmented. Link completeness to actual evidence/actions. | P1 |
| SPEC-009 §§3/11, UX-01 | Same recognizable case and state across navigation/reload | F1; primary and case navigation | PARTIALLY_IMPLEMENTED; B J04/J06 | Primary nav loses case; clinical refresh stalls. One selection/capability owner, readable case label. | P0 |
| SPEC-009 §4.1 pp2–3 | Authorized truthful searchable case library | F1/S1; `/cases` | PARTIALLY_IMPLEMENTED; B two artificial cases | Basic loaded-case search/list/reopen surfaced. Real cohort, modality/repeated-history filters and full-scale pagination not verified. Complete supported discovery. | P1 |
| SPEC-008 §16 p15; SPEC-009 §3 p2 | Editors submit source-backed observations, viewers read | F1/F2/S1; Clinical Records | PARTIALLY_IMPLEMENTED; C | UI and manual API require admin despite editor description. Align minimum action roles plus patient grants. Editor browser trial not run. | P0 |
| PRD UJ-06 pp13–14; SPEC-009 §4.6 p6 | Source/time/kind/value/unit/review submission | F2/S1; Add observation | PARTIALLY_IMPLEMENTED; B artificial lab save | Persistence works; cosmetic stepper, no final review or relative-day input in this form. Complete meaningful steps/dictionary flow. | P1 |
| SPEC-009 §4.6/UX-11 | Source-supported correction/retraction, reason, old/new review | F2/S1; Correct | PARTIALLY_IMPLEMENTED; B artificial correction | Replacement works. Missing reason/review/retraction in this workspace. Surface authoritative correction contracts. | P1 |
| SPEC-003 clinical model; SPEC-009 §§4.6/9 | Labs/vitals/symptoms/treatment/diagnosis/notes with preserved meaning | F2/S1; category choices | PARTIALLY_IMPLEMENTED; B choices, C | Only lab save exercised; other subtypes, private-note attachment and import not browser-verified. Test each reviewed subtype without fabricating missingness. | P1 |
| SPEC-009 §4.6; PRD FR-006/034 | Saved observation → durable processing → optional new published state | S1/S3/F2; save receipt | BACKEND_ONLY for dependent orchestration; C/B | Outbox/revision exists; no finished update-job handoff. Preserve old snapshot, expose status/new-state action. | P1 |
| SPEC-009 §§8–9 pp9–10 | Charts use actual compatible time, exact quantities, record links | F2; Charts | PARTIALLY_IMPLEMENTED; B J03, C | Exact active corrected table works; plot uses record order. Implement elapsed-time semantics and units/record inspection. | P1 |
| SPEC-009 §§8/11, UX-04/05 | Selected state atomically drives geometry, chart cursor and records | F2/F3/S3; Timeline → panels | PARTIALLY_IMPLEMENTED; C | Component-local selection, incomplete day-only filter, no mesh handoff. Use exact state membership/time domain. Populated-state browser race test pending. | P0 |
| SPEC-009 §§7.3/9.2, PRD comparison | Two selected states compared with provenance/comparability | F2/S3; Pin A/B | PARTIALLY_IMPLEMENTED; C | Textual A/B uses B's stored changes, not verified chosen-pair calculation; no synchronized geometry. Bind explicit comparison and supported metrics. | P1 |
| SPEC-009 §4.7 p6 | Sources and exact record/background evidence inspection | F1/F3/F5/S4; source fragments | PARTIALLY_IMPLEMENTED; C | Sources destination removed; evidence UI blocked by context contracts. Add case Sources and exact permitted locator views. | P1 |
| SPEC-009 §4.8 p6 | Admin staged import/rights/linkage/QC/publication | S1/S2; `/admin` | BACKEND_ONLY; B J05/C | Static page despite admin session; no normal file/manifest workflow. Implement owned staged import, not a rights bypass. | P0 |
| SPEC-009 §4.8 p6 | Actual jobs/results/cancellation/retry | S3; `/activity` | UI_ONLY_OR_MOCK; B J10/C | Page is placeholder, not job discovery. Surface authorized jobs or known session references honestly. | P1 |
| SPEC-009 §§13/18 UX-14/15 | Accessible labels, keyboard, focus, reflow | F1–F6; all screens | PARTIALLY_IMPLEMENTED; B camera/mobile, C | Semantic gaps and mobile entry columns; screen-reader/contrast/zoom/touch hardware untested. Manual acceptance required. | P1 |
| SPEC-009 §15/UX-17 | Pinned preflighted guide, safe truthful reset | F6; Guided demo | PARTIALLY_IMPLEMENTED; B J10 | Bare route links, checkbox preflight and unestablished reset claims. Bind actual manifest/readiness. | P1 |
| SPEC-009 §4.9/UX-18; SPEC-011 §13 | Versioned evaluation with denominators and limitations | F6; Evaluation | UI_ONLY_OR_MOCK for report delivery; B/C | Static fixture claims, incorrect original UX-ID mapping; no report retrieval. Publish authorized immutable measured reports. | P1 |

## Imaging, simulation and scientific requirements

| Requirement / source locator | Intended behavior | Implementation / user entry | Status and evidence | Missing functionality, UX impact and correction | Priority |
| --- | --- | --- | --- | --- | --- |
| SPEC-003 §12 p24; SPEC-005 AC-IMG-01 | Import authorized genuine MRI with source/identity fidelity | S2/F3; no finished import surface | PARTIALLY_IMPLEMENTED; C | Staging explicitly rejects nonfixture origin. Rights and review are missing evidence; authentic path also missing code. Implement controlled reviewed-source path. | P0 |
| SPEC-005 geometry §§8–10; SPEC-011 §5 p3 | Preserve affine/origin/spacing/units, image/mask alignment | S2; processing APIs/workers | PARTIALLY_IMPLEMENTED; T/C | Engineering geometry checks pass. Authentic overlay/qualified review and release-case validation absent. | P0 |
| SPEC-005 MRI semantics; SAFE-06 | DCE phases remain within one examination | S2 `imaging_formats.py:132–161` | PARTIALLY_IMPLEMENTED; C/T | Explicit phase semantics inspected; real source metadata/UI examination navigation not verified. | P1 |
| SPEC-005 segmentation; SPEC-011 §1 | Verified imported mask remains viable without checkpoints | S2/F3 | PARTIALLY_IMPLEMENTED; C/T | Fixture annotation/QC exists, origin fixed synthetic. Complete genuine mask meaning/rights/review path. | P0 |
| SPEC-005 measurement; SPEC-011 §5 | Physical volume from labeled voxels × absolute affine determinant | S2 `physical_measurements.py:42` | PARTIALLY_IMPLEMENTED; T/C | Synthetic arithmetic verified; real mask/reference comparison not established. No formal response grade inferred. | P0 |
| SPEC-005 mesh; SPEC-009 §7.1 | Preserve physical mesh/frame and server measurements | S2/F3; demo or case imaging | PARTIALLY_IMPLEMENTED; T/B/C | Phantom works. Authentic derived mesh, anatomy/context and independent reference not established. | P0 |
| SPEC-009 §7.2 / UX-02 | Camera pointer/touch/button/keyboard alternatives | F3/F6; demo viewer | PARTIALLY_IMPLEMENTED; B/C | Buttons, keyboard, maximize/fullscreen exercised. Initial touch capture and real-device/assistive tests remain. | P1 |
| SPEC-009 §7.4 / UX-13 | Missing/WebGL failure preserves valid metadata and retry | F3/F6 | NOT_VERIFIED at failure runtime; C | Fallback code exists; no lost-context/low-memory browser trial here. Do not count missing lesion as successful WebGL recovery. | P1 |
| PRD FR-029–036; SAFE-03/04 | Immutable authentic baseline and distinct synthetic histories | S1/S3 | PARTIALLY_IMPLEMENTED; C/T | History machinery exists; observed_baseline_verified fixed false and branches fixture-only. Establish actual reviewed baseline. | P0 |
| SPEC-004 AC-S01–12; PRD FR-017–028 | Five reproducible families from observed baseline + 3 follow-ups | S3/F4; scenarios | PARTIALLY_IMPLEMENTED; T/P/C | Engines work in fixtures; current route/payload failures and authentic gate block ordinary workflow. | P0 |
| SPEC-009 §4.5/UX-12 | Baseline → family/exposure → assumptions → generate/validate/publish | F4/S3 | IMPLEMENTED_BUT_NOT_USER_ACCESSIBLE; B J07/P | Empty props, wrong versions/required params/methods; no branch creation surface. Repair real contract integration. | P0 |
| SPEC-004 constrained eligibility; SPEC-009 §4.5 | Known clinical setting governs permitted hypothetical exposure | S3; builder | PARTIALLY_IMPLEMENTED; C | Guards exist, but published authentic baseline false/test restrictions; useful reasons lost. Integrate reviewed baseline and explain eligibility. | P0 |
| SPEC-004 clinical generation | Labs/vitals/symptoms/exposure with time, units and missingness | S3; prepared demo Clinical Data | PARTIALLY_IMPLEMENTED; C/B | Sparse artificial weight/fatigue observations shown. Meaningful clinical charts and reviewed genuine linkage remain incomplete. | P1 |
| SPEC-009 §8/UX-06 | Five prepared families and four discrete demo positions | F6; opt-in `/demo` | FULLY_IMPLEMENTED_AND_VERIFIED **only for prepared phantom scope**; B | All five loaded with 4 positions. This row does not satisfy shared authentic-baseline requirement. | P1 deployment |
| SPEC-011 §11 p6; PRD AC-10 p34 | Genuine repeated-imaging case distinct from DCE phases | No verified release case delivered | BLOCKED_BY_EXTERNAL_DEPENDENCY; no acceptance evidence | Source/access/identity/comparability and independent review needed; additional onboarding implementation also required. Major P0 incompleteness. | P0 |
| SPEC-011 §§6/8/9/12 | Independent image/volume validation, multi-seed science and measured usability/performance | Tests/research modules; evaluation | NOT_VERIFIED for full release | This review ran five focused files, not the release protocol. Supply actual denominators, reviewers, hardware and failure results. | P0 release |

## Intelligence, security and architecture requirements

| Requirement / source locator | Intended behavior | Implementation / user entry | Status and evidence | Missing functionality, UX impact and correction | Priority |
| --- | --- | --- | --- | --- | --- |
| SPEC-006 §§10–14; AC-AI16 p34 | Selected-state evidence-linked explanation for authentic and synthetic histories | S4/F5; Insights | PARTIALLY_IMPLEMENTED; P/C/B | Manual UUID and four incompatible requests. Connect current state/context, correct schemas, ground/persist and inspect exact evidence. | P0 |
| PRD FR-045; SPEC-012 §7 | Usable deterministic/approved saved fallback during provider outage | S4/F5/F6 | PARTIALLY_IMPLEMENTED; B/P/C | Demo template works; actual context/template UI contracts fail. Fallback does not close Meta requirements. | P0 |
| SPEC-006 §21 p32; COS-HACK §§5/10 | Substantive eligible Meta research-agent integration | S4, separate live-test harness | NOT_IMPLEMENTED in ordinary app; C | Mock/test-only gateway, external candidates rejected, no app caller for live path. Access/terms/export/tool evidence separately required. | P0 hackathon |
| SPEC-010 SAFE-01/02; SPEC-009 §5 | Real, derived, synthetic, interpolated, model origin remain distinct | S1–S4/F3/F6 | PARTIALLY_IMPLEMENTED; C/T/B | Phantom labeling good. Renderer hardcodes synthetic for real-case reuse; authentic origin path absent. Pass artifact origin explicitly. | P0 semantics |
| SPEC-008 §§16–18; SPEC-010 privacy | Project AND patient authorization on every result read | S1/S4; saved detail API | PARTIALLY_IMPLEMENTED; P/C | Saved detail ignores patient path and grant; function probe returns fabricated metadata. Fix/retest negative ownership and withdrawal. | P0 release |
| SPEC-010 external processing; COS-HACK §11 | Deny unapproved export; no invented live results | S4/F6 | PARTIALLY_IMPLEMENTED; C/T/B | Denial and honest demo labels observed; full deployment/export threat analysis not run. Preserve gate while enabling authorized integration. | P0 |
| SPEC-007 §§1–4; SPEC-008 contracts | Modular API/workers/web/private SQL/storage; central typed contracts | Current source/manifests/infrastructure | PARTIALLY_IMPLEMENTED; build/C | Architecture fits. Handwritten requests bypass generated input correctness. Enforce runtime contract acceptance at UI boundary. | P0 |
| SPEC-012 §11 p7 | Separate data/function/intelligence/safety/operations/presentation release gates | Runbooks, local launchers | NOT_VERIFIED for release | Local services/build are not deployment, backup/restore, real roles, performance or scientific approval. | P0 release |
| Optional forecasting, mask editing, full radiology workstation | Do not make optional features prerequisites | Optional code/plans | NOT_APPLICABLE to blocking P0 recovery | Preserve abstention; do not broaden scope into training, care recommendations or extra infrastructure. | Deferred |

## A–F capability distinction

“Integrated” below means real connections within the stated scope, not merely imports or matching type names.

| Capability | A documented | B implemented | C integrated | D accessible | E usable | F verified in this review |
| --- | --- | --- | --- | --- | --- | --- |
| Pseudonymous case/profile | Yes | Yes | Artificial API/SQL path | Admin session | Basic artificial task yes | Browser create/edit/reopen |
| Clinical save/correct | Yes | Yes | Artificial API/SQL/chart path | Admin after Overview | Partial; refresh/roles/review gaps | One lab/correction only |
| Authentic imaging baseline | Yes | Incomplete | No complete path | No ordinary workflow | No | Blocking source inspected |
| Physical geometry/mesh | Yes | Yes | Fixture worker/API/demo | Demo; owned fixture paths | Phantom yes | Focused tests + browser |
| New five-family simulation | Yes | Engines yes | Fixture pipeline; UI broken | Form route fails | No ordinary run | Unit/contract tests, not UI run |
| Prepared family playback | Yes, bounded allowance | Yes | Prepared bundle and viewer | Opt-in demo | Yes, artificial scope | Five families/four states |
| Research timeline/chart/AI synchronization | Yes | Pieces | Incomplete | Fragmented | Not complete | Code; limited chart save |
| Grounded research insights | Yes | Backend yes | UI request drift | Manual ID then invalid contracts | No complete task | Contract probes |
| Live Meta agent | Yes/tension recorded | Harness/boundary | No app integration | No | No | No live verification |
| Immutable scientific history | Yes | Revision/snapshot code | Fixture persistence | Authorized APIs | Partial product workflow | Limited correction + unit scope |
| Report/operations release | Yes | Static UI/runbooks | Incomplete | Page accessible | Not release-ready | Local build/start only |

## Authority conflicts retained

SPEC-008 owns canonical REST; earlier illustrative endpoints do not authorize alternate request shapes. SPEC-009 explicitly resolves P0 two-state versus P1 simultaneous branch comparison and unavailable-model fallbacks. SAFE-02 retains synthetic origin in synthetic descendants. All source versions/hashes are verified; formal whole-baseline adoption is not inferred from their existence or from the decision register's pending-adoption entries.

SPEC-006's named Meta P0 requirement, SPEC-012's conditional provider/fallback and COS-HACK's substantive Meta directive require separate acceptance claims. The fallback must remain usable; it cannot be described as full Meta completion. Five-minute research rehearsal guidance and the directive's three-minute submission format are different artifacts. Current competition schedules/rules were not verified for submission, and no publication/submission was authorized by this review.
