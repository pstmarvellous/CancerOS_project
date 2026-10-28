# CancerOS Phase 5 — Frontend and Demonstration Experience

Version 1.0 | 23 October 2026 | Workstream 10 | Nine separate P0 implementation prompts

Use one numbered prompt at a time in the CancerOS repository. Copy only its fenced text into the coding-agent session, retaining COS-000, AGENTS.md, adopted decisions and the ledger. This continues the clear Muse Spark-oriented structure: role, prerequisites, outcome, numbered work, usability, acceptance and completion evidence. It does not claim benchmarked model performance, executed implementation or clinical validation. Expert perspectives organize work/self-review; they do not create actual specialist approval.

## Baseline and integration rules

Use all twelve drafted specifications as the source set (PRD-001; SPEC-003 through SPEC-012; COS-RA-001), COS-AUD-001 reconciliation baseline 1.0 and actual Phase 1–4 code/evidence. Verify audit adoption rather than inventing approval. PRD governs intent, SPEC-007 architecture, SPEC-008 plus adopted audit APIs/lifecycle, SPEC-003/004/005 scientific meaning and SPEC-010/011 safety/evaluation. SPEC-009 governs browser routes/interaction within those boundaries; roadmap and literature do not silently add scope.

The application remains a breast-cancer research prototype, not a diagnostic/treatment system or whole-body twin. Earlier phases already introduce a shell, minimal viewer, timeline/chart components, simulation workflow and insights panel. Phase 5 consolidates and completes those components into a coherent product; it does not start a new website, static mockup or competing frontend. Inspect what actually exists, not what previous prompts merely proposed.

No P0 task depends on optional segmentation, temporal neural models, interpolation, continuous mesh morphing, playback, cross-branch side-by-side or raw MRI workstation functionality. Use verified imported masks and prepared geometry. Two-state comparison within a selected history is P0; branch switching works sequentially. Spatial overlays additionally require valid registration/QC.

## Execution order and screen ownership

Run COS-072–COS-080 sequentially by default. Prerequisite lists are task-specific; common Phase 1–4 governance, contracts and security apply throughout. The following mapping also assigns required SPEC-009 workflows that have no separate title in the nine-item inventory.

| Prompt | Primary scope | Required companion integration |
| --- | --- | --- |
| COS-072 | Design system, shell and navigation | Shared origin/time/status labels, role/capability navigation and selection ownership |
| COS-073 | Case library and selection | Accurate pagination/search/counts and verified longitudinal availability |
| COS-074 | Overview, Sources and completeness | Record inspector, source-backed editor observation/correction/retraction forms and limited admin import review |
| COS-075 | Interactive lesion viewer | Accessible controls, validated units/scale, layers and graphics fallback |
| COS-076 | State/branch/examination selection | Discrete timeline/slider, same-state synchronization and two-state comparison |
| COS-077 | Clinical/tumor charts and tables | Complete histories, treatment tracks, precise records and actual collection times |
| COS-078 | Scenario setup/run/publish/exploration | All five families, eligibility, durable progress and editor Activity |
| COS-079 | Grounded insights and evidence | Exact snapshot freshness, execution labels, uncertainty and source drill-down |
| COS-080 | Cross-screen completion/verification | Guided demo, Evaluation report screen, UX-01–UX-18, access/failure/accessibility/performance checks |

Every navigable destination must work or have an honest capability-specific empty/blocked state. A page stub or disabled “coming soon” button is not completion. Viewers/judges browse published authorized content; editor/admin controls require server permissions. The frontend cannot turn unknown pathology positive, approve rights, bypass QC or publish because a progress bar reached its end.

## Product behavior to preserve

1. The URL owns navigable project/patient/branch/run/state/lesion/compare/panel IDs; server responses own clinical data, eligibility, publication and job state; local state owns camera and temporary drafts. Do not put note contents, signed grants, protected mappings or clinical payloads in URLs, persistent browser storage or analytics.
2. One active selection drives heading, mesh, measurements, charts and insights. Cancel/ignore stale requests. While a new mesh loads, its viewport is loading; the previous mesh cannot sit under the new date. Reload/Back restores exact authorized selection or explains why it is unavailable, never silently substituting another case/state.
3. Show history context and per-item provenance separately. Map REAL_OBSERVED → Observed/circle, REAL_DERIVED → Derived from observed data/square, SYNTHETIC_GENERATED → Simulated/diamond/dashed. Interpolated/model estimates remain separately labeled gated capabilities. A branch retains one observed baseline plus at least three simulated follow-ups.
4. Preserve actual time basis and modality collection times. Historical geometry remains labeled with its source time; a lab-only update is not a new MRI. DCE phase changes stay within an examination. Unknown-time records stay unplaced. P0 commits only existing discrete states; no invented intermediate geometry or dates.
5. Server mask measurements and comparisons are authoritative. Browser decimal conversion is for bounded plotting/display only. No per-timepoint automatic normalization that hides physical growth, no volume/diameter mixing, and no overlay without valid spatial alignment.
6. Missing/censored/invalid observations do not become zero or normal. Avoid assumed reference bands, clinical response categories, health scores, treatment rankings and invented confidence. Labels and chart semantics must make observed, hypothetical and estimated content unmistakable.
7. A 201 observation receipt means saved, 202 means accepted/queued, a successful job means durable output, and publication follows its separate contract. Preserve drafts/idempotency keys on errors; never create a new run because the first response was lost. Explicit publication must identify the exact eligible run/report.

## Visual, accessibility and resource priorities

Use a restrained readable research workspace with a dark neutral lesion viewport, sensible hierarchy and progressive disclosure. The central twin must remain useful and source-linked, without forcing all clinical content into several small independent scroll areas. Keep context/time/measurement prominent, one primary action per task region, readable units and text-plus-shape origin cues. Use the SPEC-009 palette/type/spacing as a tested starting point, not an automatic contrast-compliance claim.

Support desktop rail/main/inspector, tablet reflow and narrow stacked layouts. Target WCAG 2.2 AA with keyboard/screen-reader/button/table alternatives, focus management, reduced motion, touch and 200% zoom/320px reflow. Automated scans supplement real manual interaction; they cannot establish complete conformance. No scientific task requires drag, hover, color or canvas alone.

Measure on the declared target rather than assuming GPU capability from a memory figure. Current target is Ryzen 5 3500U/8 GB with constrained graphics. Lazy-load 3D, bound asset/case memory, dispose GPU resources and prefetch at most an adjacent authorized state when appropriate. Proposed budgets: warm metadata p95 <700ms, manifest p95 <1.5s, prepared first mesh <=5s, camera >=30fps and initial demo GLB <=5MiB. Record actual hardware, browser, network, cold/warm conditions and failures. If unavailable, mark target-device validation pending.

## Scientific and demo gates

A working approved real case needs source/rights/linkage/mask/geometry review (D01/D03); a genuine repeated-exam case remains required for the full authentic longitudinal demonstration (D02). Synthetic branches and phase selectors cannot close that gate. External model access/policy, scientific evaluation and deployment/resource conditions remain separately evidenced (D04–D06). Keep deterministic/saved output truthful if live inference is unavailable.

Guided demo uses pinned authorized published IDs and a preflight check. An approximate five-minute sequence is a rehearsal assumption until event timing is verified. Restart resets UI/camera/guide progress only. It cannot delete observations, mutate the source, cancel jobs or manufacture a clean rerun. A static preview/recorded/saved result is labeled and never presented as the pending live result. Full 3D readiness still requires an actual supported-device interaction test.

SPEC-009 UX-01–UX-18 and SPEC-011 define evidence. At least three formative task participants are desirable when feasible; report actual participation and limitations. Mistaking simulated values for real findings is a blocking disclosure defect. A polished screenshot does not pass usability, access, synchronization, performance or genuine-data gates.

## Phase completion evidence

- Real API-connected journey: case → exact source/derived mesh → state change → charts/table → two-state comparison → labeled scenario → grounded evidence/summary → actual evaluation/limitations.
- Functional role-appropriate observation update and limited import/Activity flows, with safe concurrency/retry/publication behavior.
- Browser integration plus manual interaction/accessibility tests; deliberate selection races, unavailable assets, denied access, provider/grounding/graphics failures and recovery.
- Measured performance, formative usability evidence where available, and a concise report separating implemented, fixture-tested, approved real-data verified, review-pending and blocked scope.
- Updated traceability, task ledger and release gates. Do not call the prototype fully ready while mandatory scientific/access/disclosure/3D evidence is missing.

## Prompt index

| ID | Priority | Prompt | Task-specific prerequisites |
| --- | --- | --- | --- |
| COS-072 | P0 | [Global design system, navigation and responsive application shell](#cos-072--global-design-system-navigation-and-responsive-application-shell) | COS-011, COS-036, COS-050, COS-051, COS-052, COS-063, COS-066, COS-067, COS-068, COS-069, COS-070, COS-071 |
| COS-073 | P0 | [Research case dashboard and patient selection](#cos-073--research-case-dashboard-and-patient-selection) | COS-066, COS-069, COS-071, COS-072 |
| COS-074 | P0 | [Patient profile, source information and record completeness](#cos-074--patient-profile-source-information-and-record-completeness) | COS-018, COS-020, COS-023, COS-066, COS-067, COS-069, COS-071, COS-072, COS-073 |
| COS-075 | P0 | [Interactive 3D tumor viewer and camera controls](#cos-075--interactive-3d-tumor-viewer-and-camera-controls) | COS-026, COS-033, COS-034, COS-035, COS-036, COS-067, COS-069, COS-071, COS-072, COS-073 |
| COS-076 | P0 | [Imaging date selector, observed/synthetic state slider and tumor comparisons](#cos-076--imaging-date-selector-observedsynthetic-state-slider-and-tumor-comparisons) | COS-038, COS-051, COS-052, COS-054, COS-069, COS-071, COS-072, COS-075 |
| COS-077 | P0 | [Laboratory, vital-sign, symptom and treatment timeline charts](#cos-077--laboratory-vital-sign-symptom-and-treatment-timeline-charts) | COS-018, COS-020, COS-051, COS-052, COS-053, COS-066, COS-069, COS-071, COS-072, COS-076 |
| COS-078 | P0 | [Simulation setup, generation progress and branch exploration](#cos-078--simulation-setup-generation-progress-and-branch-exploration) | COS-041, COS-042, COS-049, COS-050, COS-068, COS-069, COS-071, COS-072, COS-074, COS-076, COS-077 |
| COS-079 | P0 | [Evidence-linked AI insights, uncertainties and provenance presentation](#cos-079--evidence-linked-ai-insights-uncertainties-and-provenance-presentation) | COS-058, COS-061, COS-062, COS-063, COS-064, COS-065, COS-070, COS-071, COS-072, COS-074, COS-076, COS-077, COS-078 |
| COS-080 | P0 | [Integrated UI states, accessibility, usability and failure handling](#cos-080--integrated-ui-states-accessibility-usability-and-failure-handling) | COS-071, COS-072, COS-073, COS-074, COS-075, COS-076, COS-077, COS-078, COS-079 |

## Separate copyable prompts

### COS-072 — Global design system, navigation and responsive application shell

```text
Task: COS-072 — Global design system, navigation and responsive application shell
Priority: P0 | Workstream: 10
Prerequisites: COS-011, COS-036, COS-050, COS-051, COS-052, COS-063, COS-066, COS-067, COS-068, COS-069, COS-070, COS-071; inherited Phase 1–4 governance/security/contracts apply.
Expert perspectives: Product design, frontend architecture, accessibility and scientific communication.
Read: SPEC-009 sections 3–6, 11–14 and 16; SPEC-008; audit C01–C05; existing Next.js components; relevant repository components/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed design, engineering and scientific perspectives with top-tier research-product rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approvals you do not have. Working alone means self-review, not a fabricated expert team.

Execute this one task in the existing repository. Inspect relevant source specifications, COS-AUD-001 adoption/decisions, actual prerequisite code/evidence, existing frontend components and generated API contracts first. Keep Next.js/TypeScript and the established backend architecture. Reuse earlier viewer/timeline/chart/summary slices and shared selection state; do not create another demo application or rewrite the twelve documents. Browser routes follow SPEC-009; REST uses the canonical /api/v1/projects/{project_id} contract and documented exceptions. Record missing contract changes before implementation and regenerate clients; never infer absent scientific fields.

Prioritize ease of understanding, the next right action, working functionality and complete recovery paths. Keep case/context/time/origin visible with readable labels, not unexplained abbreviations. Server data owns measurements, eligibility, publication and job status; the browser owns interaction, not scientific truth. Use exact IDs/hashes, original units/times and immutable history. Missing is not zero/normal; synthetic descendants remain synthetic. No client-only authorization, invented claims or hidden provider exports.

Implement against real authenticated APIs. Conspicuously synthetic fixtures are allowed for isolated development/failure tests, never as a silent production fallback. If approved data or a contract is absent, finish independent work, show an honest capability-specific blocked state and record the owner/evidence needed. A placeholder button, screenshot or static model is not functioning integration. Avoid extra frameworks, speculative P1 features and paid services. Do not spawn agents merely because expert perspectives are listed.

Outcome
Unify the existing frontend into one readable responsive research application without replacing working components or contracts.

Implement
1. Inventory existing routes, tokens, viewer/chart/timeline/summary components and generated clients. Extend/reconcile the Phase 1 shell and Phase 2–4 thin slices; avoid a parallel demo app, second design system or speculative framework migration. Produce a compact component/route ownership map and preserve working behavior while closing gaps.
2. Implement SPEC-009 browser routes and navigation: Cases, Guided demo and Evaluation globally; Activity for authorized editors and Data administration for admins. Case navigation is Overview, Twin workspace, Scenarios and Sources. Findings/Records/Evidence are contextual inspector tabs, not a chatbot page. Keep active project/case/history visible; roles/capabilities come from the server, not client assumptions.
3. Apply the restrained light research canvas, white surfaces and dark neutral viewport. Reuse/adapt documented tokens: canvas #F6F8FB, text #172033, action #1D4ED8, observed #0F766E, derived #1D4ED8, simulated #6D28D9, viewport #111827 and lesion #E9A38A. Verify actual contrast; do not claim the proposed palette is automatically compliant. Use 16px body/1.5 line height, readable labels, tabular quantities and consistent spacing. No decorative whole-body anatomy, severity glow or unexplained abbreviations.
4. Centralize readable provenance/time/status components: Observed, Derived from observed data and Simulated with text plus distinct markers. Keep origin separate from technical QC, availability and publication; “checks passed” never means clinically validated or healthy. Preserve full quantities for record detail and round presentation only.
5. Define selection ownership now: URL carries authorized project/patient/branch/run/state/lesion/panel/comparison IDs; server owns scientific/job state; local state owns camera, drafts and disclosure panels. Reuse the existing selection coordinator and generated client. At >=1200px use rail/main/inspector, at 768–1199 collapse/reflow, below 768 stack. Maintain useful 320px and 200%-zoom workflows without page-level horizontal scrolling. Add landmarks, Skip to content, visible focus and reduced-motion behavior.

Make the next right action easy
Give each task region one clear primary action and plain-language labels. Keep status explanations near affected content and technical detail on demand. Every navigation destination must resolve to a functional implemented screen or an honest capability-specific state, not a blank scaffold.

Acceptance checks
Verify route reload/Back restores authorized selection, active labels and context. Exercise viewer/editor/admin navigation, unknown capability enums, session expiry and logout cache clearance. Check responsive layout, keyboard order and real text/background combinations. Record shell/component evidence; do not mark later screen functionality complete from navigation alone. Verify the relevant project/patient/branch authorization and actual API request/response paths, not only mocked component rendering.

Completion evidence
- Deliver working frontend code, shared typed components/client integration, focused behavior tests and a short runbook with actual commands. Use synthetic/public-safe fixtures; never include protected identifiers or credentials in examples or test artifacts.
- Run applicable type/lint/build, component and browser integration checks. Include manual interaction/accessibility checks where required and record actual device/browser. Distinguish synthetic fixture evidence, approved real-data operation and human review; skipped mandatory checks are not passes.
- Update requirements traceability, task ledger, contract decisions and release gates. Record what works, remaining limits and the next recommended action. All meaningful visible controls need a working action or a clear capability explanation.
- Final response: behavior delivered; key files; checks/results; material dependency/limitation. Keep it concise and evidence-based. Do not claim clinical validation or finished release readiness from visual polish.
```

### COS-073 — Research case dashboard and patient selection

```text
Task: COS-073 — Research case dashboard and patient selection
Priority: P0 | Workstream: 10
Prerequisites: COS-066, COS-069, COS-071, COS-072; inherited Phase 1–4 governance/security/contracts apply.
Expert perspectives: Research workflow design, frontend data integration and privacy-aware UX.
Read: SPEC-009 sections 4.1/4.2 and 11/12; SPEC-008 patient list/detail/cursors; audit D01–D03; relevant repository components/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed design, engineering and scientific perspectives with top-tier research-product rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approvals you do not have. Working alone means self-review, not a fabricated expert team.

Execute this one task in the existing repository. Inspect relevant source specifications, COS-AUD-001 adoption/decisions, actual prerequisite code/evidence, existing frontend components and generated API contracts first. Keep Next.js/TypeScript and the established backend architecture. Reuse earlier viewer/timeline/chart/summary slices and shared selection state; do not create another demo application or rewrite the twelve documents. Browser routes follow SPEC-009; REST uses the canonical /api/v1/projects/{project_id} contract and documented exceptions. Record missing contract changes before implementation and regenerate clients; never infer absent scientific fields.

Prioritize ease of understanding, the next right action, working functionality and complete recovery paths. Keep case/context/time/origin visible with readable labels, not unexplained abbreviations. Server data owns measurements, eligibility, publication and job status; the browser owns interaction, not scientific truth. Use exact IDs/hashes, original units/times and immutable history. Missing is not zero/normal; synthetic descendants remain synthetic. No client-only authorization, invented claims or hidden provider exports.

Implement against real authenticated APIs. Conspicuously synthetic fixtures are allowed for isolated development/failure tests, never as a silent production fallback. If approved data or a contract is absent, finish independent work, show an honest capability-specific blocked state and record the owner/evidence needed. A placeholder button, screenshot or static model is not functioning integration. Avoid extra frameworks, speculative P1 features and paid services. Do not spawn agents merely because expert perspectives are listed.

Outcome
Help a researcher find and open an authorized case with an accurate picture of available data.

Implement
1. Implement the Cases library using the generated patient API and approved server summaries. Desktop uses a compact table; narrow layouts use labeled cards. Show pseudonymous case code, source/release, known subtype/side, supported examination count, published branch count and modality availability only when provided by authorized data. Unknown reads “Not recorded”; no invented age, avatar, diagnosis confidence or patient photograph.
2. Implement supported display-code search, source/modality/verified longitudinal filters and cursor pagination. Use server-supported semantics or a fully loaded bounded approved demo manifest. Never search just the current page and imply it is the whole cohort. Keep query/filter/snapshot state coherent on return; handle expired cursors by explaining and restarting the list safely.
3. Make Open case the primary action, with Start guided demo and role-appropriate Import data as secondary actions. Present a clear opening choice for baseline versus latest accessible observed state; retain a valid explicit previous selection instead of guessing a new one. Real longitudinal availability means verified distinct examinations, not DCE phases, synthetic branches or unreviewed study counts.
4. Separate no matching filters, no approved cases, restricted project, loading and server failure states. Give a viewer an exploration/help path and an administrator the actual import/review path; do not expose a nonfunctional upload button or anonymous patient submission.
5. On switching patients, clear prior clinical panels and patient-specific selection immediately, reset camera and fetch/authorize the new case. Bound in-memory caches by full identity/context; discard stale responses. Display only published/eligible resources allowed for the role; never derive counts from inaccessible records.

Make the next right action easy
Use a short research-prototype disclosure and readable availability labels. Explain “No cases match” with Clear filters and “No approved cases yet” with the correct role-specific action. Keep filter controls usable on touch and keyboard without making a user learn internal dataset terminology.

Acceptance checks
Test multi-page search/filter behavior, accurate authorized counts, zero/missing counts, unknown subtype, cursor expiry and empty/restricted/error states. Rapidly open two different cases under delayed responses and prove no previous-case fields flash in the new case. Verify genuine follow-up badges cannot be created by MRI phase or synthetic follow-up counts. Verify the relevant project/patient/branch authorization and actual API request/response paths, not only mocked component rendering.

Completion evidence
- Deliver working frontend code, shared typed components/client integration, focused behavior tests and a short runbook with actual commands. Use synthetic/public-safe fixtures; never include protected identifiers or credentials in examples or test artifacts.
- Run applicable type/lint/build, component and browser integration checks. Include manual interaction/accessibility checks where required and record actual device/browser. Distinguish synthetic fixture evidence, approved real-data operation and human review; skipped mandatory checks are not passes.
- Update requirements traceability, task ledger, contract decisions and release gates. Record what works, remaining limits and the next recommended action. All meaningful visible controls need a working action or a clear capability explanation.
- Final response: behavior delivered; key files; checks/results; material dependency/limitation. Keep it concise and evidence-based. Do not claim clinical validation or finished release readiness from visual polish.
```

### COS-074 — Patient profile, source information and record completeness

```text
Task: COS-074 — Patient profile, source information and record completeness
Priority: P0 | Workstream: 10
Prerequisites: COS-018, COS-020, COS-023, COS-066, COS-067, COS-069, COS-071, COS-072, COS-073; inherited Phase 1–4 governance/security/contracts apply.
Expert perspectives: Clinical informatics, form UX, provenance presentation and privacy engineering.
Read: SPEC-009 sections 4.2, 4.6–4.8; SPEC-008 observations/imports; SPEC-010; audit C03/C06/D01/D03; relevant repository components/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed design, engineering and scientific perspectives with top-tier research-product rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approvals you do not have. Working alone means self-review, not a fabricated expert team.

Execute this one task in the existing repository. Inspect relevant source specifications, COS-AUD-001 adoption/decisions, actual prerequisite code/evidence, existing frontend components and generated API contracts first. Keep Next.js/TypeScript and the established backend architecture. Reuse earlier viewer/timeline/chart/summary slices and shared selection state; do not create another demo application or rewrite the twelve documents. Browser routes follow SPEC-009; REST uses the canonical /api/v1/projects/{project_id} contract and documented exceptions. Record missing contract changes before implementation and regenerate clients; never infer absent scientific fields.

Prioritize ease of understanding, the next right action, working functionality and complete recovery paths. Keep case/context/time/origin visible with readable labels, not unexplained abbreviations. Server data owns measurements, eligibility, publication and job status; the browser owns interaction, not scientific truth. Use exact IDs/hashes, original units/times and immutable history. Missing is not zero/normal; synthetic descendants remain synthetic. No client-only authorization, invented claims or hidden provider exports.

Implement against real authenticated APIs. Conspicuously synthetic fixtures are allowed for isolated development/failure tests, never as a silent production fallback. If approved data or a contract is absent, finish independent work, show an honest capability-specific blocked state and record the owner/evidence needed. A placeholder button, screenshot or static model is not functioning integration. Avoid extra frameworks, speculative P1 features and paid services. Do not spawn agents merely because expert perspectives are listed.

Outcome
Make case facts, missingness and source evidence understandable, with safe source-backed editor updates and limited admin import review.

Implement
1. Implement Overview and Sources using exact authorized case/state records. Show pseudonymous identity, collection/release, source-supported side/pathology/receptors, baseline lesion/annotation meaning, measurement/method/time basis, actual-history availability and source-rights summary. Distinguish observed source facts, derived quantities and unknown values; do not infer receptor status from a scenario or complete sparse real records with synthetic data.
2. Present completeness by capability/modality, not a patient health or trust score. Show missing, not recorded, invalid, pending review and access restricted distinctly using safe server messages. Source/processing drill-down opens exact record revisions, source locator summaries, annotation class, quality/reviewer evidence and permitted lineage. Never expose protected source-patient mappings, private storage paths or raw hashes of sensitive identifiers.
3. Complete the editor Add observation/correction/retraction workflow already backed by COS-066: supported kind → approved source evidence/time → concept/value/unit/context → review. Use server dictionaries and typed time variants, including the independent relative origin and unresolved time. Preserve qualifiers, symptom scales and separate blood-pressure components. Client cannot assign authenticity, accepted status or revision. Notes reference verified private artifacts.
4. Submit atomic source-backed batches with retained idempotency key and If-Match. Handle 201 as saved, then show actual dependent-job/state status. Keep the current snapshot stable and offer the new published snapshot explicitly. On 412 preserve safe input and show source/version differences; do not force overwrite. On 422 focus linked field errors. Corrections append evidence; retractions require a concrete confirmation/reason and retain history.
5. Complete a limited admin Data administration/import surface using existing approved upload/manifest/import/QC/publication APIs. Show staged artifacts, rights/linkage/QC evidence and actionable quarantine failures; upload completion is not publication. Do not build a new general data-management platform or solicit real patient uploads from public visitors.

Make the next right action easy
Lead with what is known, what is missing and what the selected capability needs next. Keep ordinary exploration confirmation-free; reserve confirmations for concrete retractions/withdrawals. Offer exact source drill-down without overwhelming the overview with internal processing IDs.

Acceptance checks
Test missing/negative receptor distinction, annotation classes, source-redaction, capability-specific completeness and role-specific controls. Exercise supported observation types, unknown-time entry, valid abnormal labs, atomic errors, lost-response retry, correction/retraction history and unchanged current snapshot. Verify a judge cannot write through UI or direct API and an unapproved import cannot become an approved case. Verify the relevant project/patient/branch authorization and actual API request/response paths, not only mocked component rendering.

Completion evidence
- Deliver working frontend code, shared typed components/client integration, focused behavior tests and a short runbook with actual commands. Use synthetic/public-safe fixtures; never include protected identifiers or credentials in examples or test artifacts.
- Run applicable type/lint/build, component and browser integration checks. Include manual interaction/accessibility checks where required and record actual device/browser. Distinguish synthetic fixture evidence, approved real-data operation and human review; skipped mandatory checks are not passes.
- Update requirements traceability, task ledger, contract decisions and release gates. Record what works, remaining limits and the next recommended action. All meaningful visible controls need a working action or a clear capability explanation.
- Final response: behavior delivered; key files; checks/results; material dependency/limitation. Keep it concise and evidence-based. Do not claim clinical validation or finished release readiness from visual polish.
```

### COS-075 — Interactive 3D tumor viewer and camera controls

```text
Task: COS-075 — Interactive 3D tumor viewer and camera controls
Priority: P0 | Workstream: 10
Prerequisites: COS-026, COS-033, COS-034, COS-035, COS-036, COS-067, COS-069, COS-071, COS-072, COS-073; inherited Phase 1–4 governance/security/contracts apply.
Expert perspectives: Scientific visualization, 3D interaction design, accessibility and graphics performance.
Read: SPEC-005 geometry; SPEC-009 sections 7/13/14; SPEC-008 artifact grants; audit D01/D06; relevant repository components/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed design, engineering and scientific perspectives with top-tier research-product rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approvals you do not have. Working alone means self-review, not a fabricated expert team.

Execute this one task in the existing repository. Inspect relevant source specifications, COS-AUD-001 adoption/decisions, actual prerequisite code/evidence, existing frontend components and generated API contracts first. Keep Next.js/TypeScript and the established backend architecture. Reuse earlier viewer/timeline/chart/summary slices and shared selection state; do not create another demo application or rewrite the twelve documents. Browser routes follow SPEC-009; REST uses the canonical /api/v1/projects/{project_id} contract and documented exceptions. Record missing contract changes before implementation and regenerate clients; never infer absent scientific fields.

Prioritize ease of understanding, the next right action, working functionality and complete recovery paths. Keep case/context/time/origin visible with readable labels, not unexplained abbreviations. Server data owns measurements, eligibility, publication and job status; the browser owns interaction, not scientific truth. Use exact IDs/hashes, original units/times and immutable history. Missing is not zero/normal; synthetic descendants remain synthetic. No client-only authorization, invented claims or hidden provider exports.

Implement against real authenticated APIs. Conspicuously synthetic fixtures are allowed for isolated development/failure tests, never as a silent production fallback. If approved data or a contract is absent, finish independent work, show an honest capability-specific blocked state and record the owner/evidence needed. A placeholder button, screenshot or static model is not functioning integration. Avoid extra frameworks, speculative P1 features and paid services. Do not spawn agents merely because expert perspectives are listed.

Outcome
Turn the existing minimal mesh preview into a usable data-connected viewer that preserves physical scale and honest anatomical meaning.

Implement
1. Extend the existing Three.js/React Three Fiber or selected viewer implementation; do not create another geometry pipeline. Load eligible precomputed GLB/glTF through authorized manifests/read grants. Retain selected lesion, source mask/measurement references, world frame, handedness and explicit millimetre/metre display transform. Server mask measurements remain authoritative; browser mesh estimates are not scientific replacements.
2. Provide Rotate, Pan, Zoom, Fit view, Reset view, Layers and Controls help with pointer/touch and labeled keyboard/button alternatives. No drag/pinch/right-click-only task, entry auto-rotation or keyboard trap. Prevent global scroll capture; use Interact with 3D/Done when touch needs an explicit mode. Add frame-valid presets/orientation indicators only when metadata supports them; otherwise state orientation unavailable.
3. Preserve camera orientation and scale across comparable states; initial fit establishes a common series framing, not independent per-state normalization that hides growth. Offer explicit refit for major bounds changes and prevent unnoticed clipping. Switching patients resets camera/layers. A centered lesion is not evidence of registered breast position; omit screen rulers unless projection/scale is verified.
4. Keep lesion selection and physical measurements accessible outside canvas. Label patient-derived and illustrative context at layer level; leave misleading illustrative anatomy off by default. Missing geometry shows measurements and an honest empty state; no placeholder tumor. Historical geometry is opt-in with actual source time and relation. Zero/residual/resected semantics come from persisted records, not an empty mesh guess.
5. Lazy-load graphics, cap rendering resolution, select validated LODs, dispose old GPU resources/listeners and bound prefetch. On lost WebGL/memory pressure use an approved same-state static preview if available plus tables, clearly labeled, with Retry 3D. That fallback does not pass the interactive release gate. Document signed-grant expiry/renewal without infinite retries or secret-bearing logs.

Make the next right action easy
Keep the selected lesion, origin, actual imaging time and measurement visible while the viewport stays uncluttered. Provide concise help on demand and a one-click fit/reset action. Preserve non-3D navigation and data inspection through loading or graphics failure.

Acceptance checks
Verify rotation/pan/zoom/fit by mouse, touch and keyboard without changing measurements. Compare known fixture sizes at a fixed camera to catch double scaling, axis flips and independent autofit. Exercise multiple lesions, missing/historical context, expired grants and context loss. Measure first usable mesh, frames/second, transfer size and memory over repeated state switches on the declared device; report gaps if target hardware/real assets are unavailable. Verify the relevant project/patient/branch authorization and actual API request/response paths, not only mocked component rendering.

Completion evidence
- Deliver working frontend code, shared typed components/client integration, focused behavior tests and a short runbook with actual commands. Use synthetic/public-safe fixtures; never include protected identifiers or credentials in examples or test artifacts.
- Run applicable type/lint/build, component and browser integration checks. Include manual interaction/accessibility checks where required and record actual device/browser. Distinguish synthetic fixture evidence, approved real-data operation and human review; skipped mandatory checks are not passes.
- Update requirements traceability, task ledger, contract decisions and release gates. Record what works, remaining limits and the next recommended action. All meaningful visible controls need a working action or a clear capability explanation.
- Final response: behavior delivered; key files; checks/results; material dependency/limitation. Keep it concise and evidence-based. Do not claim clinical validation or finished release readiness from visual polish.
```

### COS-076 — Imaging date selector, observed/synthetic state slider and tumor comparisons

```text
Task: COS-076 — Imaging date selector, observed/synthetic state slider and tumor comparisons
Priority: P0 | Workstream: 10
Prerequisites: COS-038, COS-051, COS-052, COS-054, COS-069, COS-071, COS-072, COS-075; inherited Phase 1–4 governance/security/contracts apply.
Expert perspectives: Temporal UX, frontend state coordination and longitudinal imaging integrity.
Read: SPEC-009 sections 7.3/8/9.3/11/13; SPEC-008 comparison/state/time contracts; audit C02–C04/D02; relevant repository components/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed design, engineering and scientific perspectives with top-tier research-product rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approvals you do not have. Working alone means self-review, not a fabricated expert team.

Execute this one task in the existing repository. Inspect relevant source specifications, COS-AUD-001 adoption/decisions, actual prerequisite code/evidence, existing frontend components and generated API contracts first. Keep Next.js/TypeScript and the established backend architecture. Reuse earlier viewer/timeline/chart/summary slices and shared selection state; do not create another demo application or rewrite the twelve documents. Browser routes follow SPEC-009; REST uses the canonical /api/v1/projects/{project_id} contract and documented exceptions. Record missing contract changes before implementation and regenerate clients; never infer absent scientific fields.

Prioritize ease of understanding, the next right action, working functionality and complete recovery paths. Keep case/context/time/origin visible with readable labels, not unexplained abbreviations. Server data owns measurements, eligibility, publication and job status; the browser owns interaction, not scientific truth. Use exact IDs/hashes, original units/times and immutable history. Missing is not zero/normal; synthetic descendants remain synthetic. No client-only authorization, invented claims or hidden provider exports.

Implement against real authenticated APIs. Conspicuously synthetic fixtures are allowed for isolated development/failure tests, never as a silent production fallback. If approved data or a contract is absent, finish independent work, show an honest capability-specific blocked state and record the owner/evidence needed. A placeholder button, screenshot or static model is not functioning integration. Avoid extra frameworks, speculative P1 features and paid services. Do not spawn agents merely because expert perspectives are listed.

Outcome
Keep one explicit history/run/state selection synchronized across the header, mesh, measurements, charts and insights.

Implement
1. Extend the existing selection coordinator into the authoritative URL-driven key: project, patient, observed/branch/run context, state, lesion and optional comparison. Authorize/restore all IDs on direct link, reload and Back. Withdrawn/inaccessible links show their status with an offered accessible alternative; never silently replace the requested snapshot.
2. Implement Actual history versus Hypothetical scenario selection with separate rails. A branch begins at the shared Observed baseline followed by at least three labeled Simulated follow-ups. Respect actual/shifted/relative time bases. Unknown-time records appear unplaced. Use true elapsed spacing where comparable; an index-based slider is labeled Observation sequence and shows actual times. Add Previous/Next and a select-list equivalent.
3. Commit only existing persisted discrete states in P0. Drag preview may highlight a target, but no mesh morphing, fabricated intermediate dates, autoplay or implied continuous clinical progression. Examinations and within-exam DCE phases are separate selectors; if phase assets are unsupported, show availability honestly rather than a fake control. Phase changes never create visits.
4. On selection, cancel/ignore stale keyed requests and load the exact manifest. Header, cursor, quantities, interpretation scope and mesh belong to the same state. While new geometry loads, show that state's loading panel; do not leave the old mesh under its new date. A lab-only state has no current scan; optional historical geometry carries its own timestamp. Branch changes resolve an existing state rather than assuming Day 60 exists everywhere.
5. Implement Pin A/Pin B two-state comparison through the canonical API with explicit lesion/metric/time/provenance, values, absolute/percentage change and comparability reasons. Use matched physical display scale; overlay only with permitted registration/QC. Unregistered views state spatial alignment not established. Narrow screens use labeled A/B switching. Cross-branch side-by-side and continuous playback remain P1; sequential branch exploration is sufficient.

Make the next right action easy
Always answer “Which case, history, time and lesion am I viewing?” Keep unavailable comparison reasons readable and both underlying states accessible. Use visible markers/text for baseline and synthetic points; a generic context badge alone is insufficient.

Acceptance checks
Test rapid timeline/branch/patient switching under delayed responses, missing Day 60, deep-link restoration, unknown time and lab-only updates. Verify DCE phase isolation, keyboard slider value text/Home/End/arrows and list alternatives. Test zero baseline, incompatible mask meaning/units/lesions, unregistered comparison and same-camera growth visibility; no authoritative arithmetic is recomputed in the browser. Verify the relevant project/patient/branch authorization and actual API request/response paths, not only mocked component rendering.

Completion evidence
- Deliver working frontend code, shared typed components/client integration, focused behavior tests and a short runbook with actual commands. Use synthetic/public-safe fixtures; never include protected identifiers or credentials in examples or test artifacts.
- Run applicable type/lint/build, component and browser integration checks. Include manual interaction/accessibility checks where required and record actual device/browser. Distinguish synthetic fixture evidence, approved real-data operation and human review; skipped mandatory checks are not passes.
- Update requirements traceability, task ledger, contract decisions and release gates. Record what works, remaining limits and the next recommended action. All meaningful visible controls need a working action or a clear capability explanation.
- Final response: behavior delivered; key files; checks/results; material dependency/limitation. Keep it concise and evidence-based. Do not claim clinical validation or finished release readiness from visual polish.
```

### COS-077 — Laboratory, vital-sign, symptom and treatment timeline charts

```text
Task: COS-077 — Laboratory, vital-sign, symptom and treatment timeline charts
Priority: P0 | Workstream: 10
Prerequisites: COS-018, COS-020, COS-051, COS-052, COS-053, COS-066, COS-069, COS-071, COS-072, COS-076; inherited Phase 1–4 governance/security/contracts apply.
Expert perspectives: Scientific data visualization, clinical measurement semantics and accessible frontend engineering.
Read: SPEC-009 section 9; SPEC-008 chart query/comparison contracts; SPEC-010/011; relevant repository components/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed design, engineering and scientific perspectives with top-tier research-product rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approvals you do not have. Working alone means self-review, not a fabricated expert team.

Execute this one task in the existing repository. Inspect relevant source specifications, COS-AUD-001 adoption/decisions, actual prerequisite code/evidence, existing frontend components and generated API contracts first. Keep Next.js/TypeScript and the established backend architecture. Reuse earlier viewer/timeline/chart/summary slices and shared selection state; do not create another demo application or rewrite the twelve documents. Browser routes follow SPEC-009; REST uses the canonical /api/v1/projects/{project_id} contract and documented exceptions. Record missing contract changes before implementation and regenerate clients; never infer absent scientific fields.

Prioritize ease of understanding, the next right action, working functionality and complete recovery paths. Keep case/context/time/origin visible with readable labels, not unexplained abbreviations. Server data owns measurements, eligibility, publication and job status; the browser owns interaction, not scientific truth. Use exact IDs/hashes, original units/times and immutable history. Missing is not zero/normal; synthetic descendants remain synthetic. No client-only authorization, invented claims or hidden provider exports.

Implement against real authenticated APIs. Conspicuously synthetic fixtures are allowed for isolated development/failure tests, never as a silent production fallback. If approved data or a contract is absent, finish independent work, show an honest capability-specific blocked state and record the owner/evidence needed. A placeholder button, screenshot or static model is not functioning integration. Avoid extra frameworks, speculative P1 features and paid services. Do not spawn agents merely because expert perspectives are listed.

Outcome
Provide linked chart/table views of actual source times and simulated trajectories without hiding gaps or mixing incompatible measures.

Implement
1. Extend existing chart/table components and fetch complete authorized histories through the supported API/query semantics. Pin patient/context/run/time-domain/revision filters across pagination. Do not plot the first page as the full history; show bounded range/loading/partial-data status until needed pages are resolved. Preserve decimal strings in tables; bounded numeric conversion is for plotting only.
2. Implement selected lesion volume or diameter, laboratory small multiples, vital panels, symptom observations, treatment-event/exposure tracks and modality-availability views. Each chart shows metric, unit, context/time basis, origin legend and equivalent table. Keep units/annotation meanings separate; no mixed-unit dual axes, unrelated lesion aggregation or diagnostic availability heat map.
3. Plot genuine elapsed spacing for compatible domains and keep unknown-time records in an explicit unplotted table/count. Missing/invalid data are not zero. Censored values retain comparator/threshold markers. No default smoothing, spline interpolation, gap filling or synthetic supplementation of observed charts. Connecting segments are labeled visual guides, not new evidence. Symptoms retain the instrument/ordinal meaning; step persistence requires actual support.
4. Reference intervals come only from applicable recorded context; show varying/absent intervals honestly, with tooltip/table values when continuous bands mislead. Treatment markers distinguish recorded and hypothetical exposures; unknown stop dates are open, not fabricated. Show systolic/diastolic components with readable labels. Equivalent two-state metrics share y-axis scales; disclose truncated axes and avoid exaggerated response displays.
5. Synchronize selected-state cursors while preserving each observation's own time and current/historical relation. Clicking a point opens its exact authorized record; offer Open associated snapshot only when a real link exists. Use server-computed comparisons/descriptions. Distinguish observed circles, derived squares and simulated diamonds/dashed lines with text, not color alone. No forecast layer becomes enabled by adding a chart.

Make the next right action easy
Make focus/click/touch tooltips show time, value/unit, origin, source and relevant quality. Provide table and short descriptive summary alternatives. Prefer readable small panels over a dense all-metric dashboard; keep missing-data explanations beside the affected chart.

Acceptance checks
Verify complete pagination, partial failures, incompatible time domains, censored/missing values, variable intervals, ordinal scales and open treatment intervals. Test exact point-to-record links, state cursor synchronization, keyboard/touch tooltips and table parity. Compare rendered data with backend fixture IDs/values; clinical arithmetic must not depend on rounded chart labels. Verify the relevant project/patient/branch authorization and actual API request/response paths, not only mocked component rendering.

Completion evidence
- Deliver working frontend code, shared typed components/client integration, focused behavior tests and a short runbook with actual commands. Use synthetic/public-safe fixtures; never include protected identifiers or credentials in examples or test artifacts.
- Run applicable type/lint/build, component and browser integration checks. Include manual interaction/accessibility checks where required and record actual device/browser. Distinguish synthetic fixture evidence, approved real-data operation and human review; skipped mandatory checks are not passes.
- Update requirements traceability, task ledger, contract decisions and release gates. Record what works, remaining limits and the next recommended action. All meaningful visible controls need a working action or a clear capability explanation.
- Final response: behavior delivered; key files; checks/results; material dependency/limitation. Keep it concise and evidence-based. Do not claim clinical validation or finished release readiness from visual polish.
```

### COS-078 — Simulation setup, generation progress and branch exploration

```text
Task: COS-078 — Simulation setup, generation progress and branch exploration
Priority: P0 | Workstream: 10
Prerequisites: COS-041, COS-042, COS-049, COS-050, COS-068, COS-069, COS-071, COS-072, COS-074, COS-076, COS-077; inherited Phase 1–4 governance/security/contracts apply.
Expert perspectives: Scenario workflow design, asynchronous UX and research simulation safety.
Read: SPEC-009 sections 4.5/4.8/11/12; SPEC-004/008; audit A02/A03/A05/A06; relevant repository components/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed design, engineering and scientific perspectives with top-tier research-product rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approvals you do not have. Working alone means self-review, not a fabricated expert team.

Execute this one task in the existing repository. Inspect relevant source specifications, COS-AUD-001 adoption/decisions, actual prerequisite code/evidence, existing frontend components and generated API contracts first. Keep Next.js/TypeScript and the established backend architecture. Reuse earlier viewer/timeline/chart/summary slices and shared selection state; do not create another demo application or rewrite the twelve documents. Browser routes follow SPEC-009; REST uses the canonical /api/v1/projects/{project_id} contract and documented exceptions. Record missing contract changes before implementation and regenerate clients; never infer absent scientific fields.

Prioritize ease of understanding, the next right action, working functionality and complete recovery paths. Keep case/context/time/origin visible with readable labels, not unexplained abbreviations. Server data owns measurements, eligibility, publication and job status; the browser owns interaction, not scientific truth. Use exact IDs/hashes, original units/times and immutable history. Missing is not zero/normal; synthetic descendants remain synthetic. No client-only authorization, invented claims or hidden provider exports.

Implement against real authenticated APIs. Conspicuously synthetic fixtures are allowed for isolated development/failure tests, never as a silent production fallback. If approved data or a contract is absent, finish independent work, show an honest capability-specific blocked state and record the owner/evidence needed. A placeholder button, screenshot or static model is not functioning integration. Avoid extra frameworks, speculative P1 features and paid services. Do not spawn agents merely because expert perspectives are listed.

Outcome
Make all five configured scenario families easy to run, inspect and explicitly publish without changing actual history.

Implement
1. Complete the existing scenario workspace using server definitions, eligibility and branch/run APIs. Show five readable families: Strong simulated reduction; Modest change or stability; Increasing simulated burden; Initial reduction then regrowth; Worsening clinical indicators. These are research templates, not formal clinical response categories or treatment rankings.
2. Implement four steps: Choose baseline; Choose scenario/hypothetical exposure; Review assumptions including schedule; Generate and validate. Keep tumor and clinical-condition settings separate, support irregular modality schedules within the frozen schema, and put seed/engine/config versions in advanced details. A complete branch references one observed baseline plus at least three generated follow-ups.
3. Use actual eligibility reasons and required source facts. Unknown receptor status stays unknown; the browser cannot unlock an exposure, invent pathology/ranges, expose unconstrained mode or request a dose. Explain unavailable options and support the permitted narrower workflow. Present target versus realized measurements and geometry limits honestly; never rename desired targets as actual measured output.
4. Preserve draft inputs, stable idempotency key and server ETags for a deliberate attempt. 202 starts a durable job, not a successful scenario. Poll with Retry-After/backoff and safe hidden-tab behavior; leaving the page does not cancel work. Show stages, unknown-progress indicators, validation report, recoverable failure and Cancellation requested until acknowledged. Retry the same uncertain submission rather than creating a new run/seed accidentally.
5. Publish scenario is a separate authorized action for the exact ready run/report, with complete validation and current rights. Judges only browse published runs. Keep previous published content usable during reruns/failures; baseline supersession is visible without rebasing. Branch switching preserves exact run identity and sends selection to COS-076. Complete editor Activity with authorized job discovery, or known job references if the adopted contract provides only that bounded scope.

Make the next right action easy
Explain assumptions before Generate and show the next action after each stage: inspect validation, repair a field, retry safely or publish. Keep “Simulated” visible in branch names, viewport, quantities and timeline; improve discoverability without cluttering the main workspace with engine terminology.

Acceptance checks
Exercise all five families, independent worsening indicators with shrinking/stable tumor, missing eligibility, duplicate clicks, lost response, 412/422/429, cancellation and worker failure. Verify no partially completed or unpublished run is shown to judges, source baseline remains unchanged and previously completed output is never presented as the result of a still-running command. Verify the relevant project/patient/branch authorization and actual API request/response paths, not only mocked component rendering.

Completion evidence
- Deliver working frontend code, shared typed components/client integration, focused behavior tests and a short runbook with actual commands. Use synthetic/public-safe fixtures; never include protected identifiers or credentials in examples or test artifacts.
- Run applicable type/lint/build, component and browser integration checks. Include manual interaction/accessibility checks where required and record actual device/browser. Distinguish synthetic fixture evidence, approved real-data operation and human review; skipped mandatory checks are not passes.
- Update requirements traceability, task ledger, contract decisions and release gates. Record what works, remaining limits and the next recommended action. All meaningful visible controls need a working action or a clear capability explanation.
- Final response: behavior delivered; key files; checks/results; material dependency/limitation. Keep it concise and evidence-based. Do not claim clinical validation or finished release readiness from visual polish.
```

### COS-079 — Evidence-linked AI insights, uncertainties and provenance presentation

```text
Task: COS-079 — Evidence-linked AI insights, uncertainties and provenance presentation
Priority: P0 | Workstream: 10
Prerequisites: COS-058, COS-061, COS-062, COS-063, COS-064, COS-065, COS-070, COS-071, COS-072, COS-074, COS-076, COS-077, COS-078; inherited Phase 1–4 governance/security/contracts apply.
Expert perspectives: Research explanation UX, evidence inspection, privacy and AI safety.
Read: SPEC-009 sections 4.7/5/10; SPEC-008 interpretation/freshness; SPEC-010 SAFE-13–21; relevant repository components/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed design, engineering and scientific perspectives with top-tier research-product rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approvals you do not have. Working alone means self-review, not a fabricated expert team.

Execute this one task in the existing repository. Inspect relevant source specifications, COS-AUD-001 adoption/decisions, actual prerequisite code/evidence, existing frontend components and generated API contracts first. Keep Next.js/TypeScript and the established backend architecture. Reuse earlier viewer/timeline/chart/summary slices and shared selection state; do not create another demo application or rewrite the twelve documents. Browser routes follow SPEC-009; REST uses the canonical /api/v1/projects/{project_id} contract and documented exceptions. Record missing contract changes before implementation and regenerate clients; never infer absent scientific fields.

Prioritize ease of understanding, the next right action, working functionality and complete recovery paths. Keep case/context/time/origin visible with readable labels, not unexplained abbreviations. Server data owns measurements, eligibility, publication and job status; the browser owns interaction, not scientific truth. Use exact IDs/hashes, original units/times and immutable history. Missing is not zero/normal; synthetic descendants remain synthetic. No client-only authorization, invented claims or hidden provider exports.

Implement against real authenticated APIs. Conspicuously synthetic fixtures are allowed for isolated development/failure tests, never as a silent production fallback. If approved data or a contract is absent, finish independent work, show an honest capability-specific blocked state and record the owner/evidence needed. A placeholder button, screenshot or static model is not functioning integration. Avoid extra frameworks, speculative P1 features and paid services. Do not spawn agents merely because expert perspectives are listed.

Outcome
Connect readable insights to exact case records and permitted background evidence, with honest uncertainty and execution labels.

Implement
1. Complete the contextual Findings/Records/Evidence inspector already introduced in earlier phases. Scope it to selected case/state/hash/branch/run and show Supported findings, Changes, Missing information and Limitations. Discover exact eligible interpretations through the canonical API; no guessed IDs or generic patient chatbot.
2. Show only published/validated output. Editors may request a research summary with an explicit permitted execution choice; viewers inspect approved results. Never stream private model tokens or render rejected partial prose. Distinguish AI-assisted, Previously generated and Rule-based summary, with model/template/version, time and corpus detail on demand. A denied external request explains the policy and offers a separately permitted local action; no hidden export or automatic policy override.
3. Each finding opens its exact case observation/measurement or approved passage. Label Case evidence separately from Background evidence. Preserve source document version/date/locator, permissions, span correctness and note access restrictions. Metadata-only sources stay metadata-only; a DOI/link alone is not patient-specific support. Escape source/generated content and use verified persisted citation targets, not arbitrary model URLs.
4. Present measurement/annotation/registration limitations, missing/conflicting source information and simulation assumptions by type. Unknown uncertainty is not a confidence gauge; parameter ranges are not calibrated prediction intervals. No treatment ranking, survival score, unsupported stage/resistance/causality or formal response grade appears in copy or actions. Preserve independent tumor and clinical-condition findings.
5. Display exact historical freshness: a result can be valid for its selected older snapshot while superseded for the current timeline. Offer Open latest view explicitly instead of silently changing it. Selection changes cancel/ignore stale result/evidence requests and close or rescope the drawer. Provider/grounding failure leaves verified measurements and tables usable; safe fallback stays labeled and source-linked.

Make the next right action easy
Lead with a concise supported explanation and what remains unknown, then allow deeper evidence inspection. Keep Back/drawer close returning to the same state and keyboard focus. A withheld summary should say why and what can still be inspected, without reassuring invented prose.

Acceptance checks
Test exact claim-to-record/passage navigation, metadata-only evidence, restricted notes, missing inputs, conflicts, failed grounding and model outage. Verify saved/local/model labels, historical freshness, no invented confidence, HTML/script escaping and hostile source text. Race summary/evidence requests against state/branch changes and prove no prior-snapshot claim appears as current. Verify the relevant project/patient/branch authorization and actual API request/response paths, not only mocked component rendering.

Completion evidence
- Deliver working frontend code, shared typed components/client integration, focused behavior tests and a short runbook with actual commands. Use synthetic/public-safe fixtures; never include protected identifiers or credentials in examples or test artifacts.
- Run applicable type/lint/build, component and browser integration checks. Include manual interaction/accessibility checks where required and record actual device/browser. Distinguish synthetic fixture evidence, approved real-data operation and human review; skipped mandatory checks are not passes.
- Update requirements traceability, task ledger, contract decisions and release gates. Record what works, remaining limits and the next recommended action. All meaningful visible controls need a working action or a clear capability explanation.
- Final response: behavior delivered; key files; checks/results; material dependency/limitation. Keep it concise and evidence-based. Do not claim clinical validation or finished release readiness from visual polish.
```

### COS-080 — Integrated UI states, accessibility, usability and failure handling

```text
Task: COS-080 — Integrated UI states, accessibility, usability and failure handling
Priority: P0 | Workstream: 10
Prerequisites: COS-071, COS-072, COS-073, COS-074, COS-075, COS-076, COS-077, COS-078, COS-079; inherited Phase 1–4 governance/security/contracts apply.
Expert perspectives: End-to-end product QA, accessibility, scientific disclosure, demo engineering and performance.
Read: SPEC-009 sections 12–19 and UX-01–UX-18; SPEC-010/011; audit D01–D06; relevant repository components/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed design, engineering and scientific perspectives with top-tier research-product rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approvals you do not have. Working alone means self-review, not a fabricated expert team.

Execute this one task in the existing repository. Inspect relevant source specifications, COS-AUD-001 adoption/decisions, actual prerequisite code/evidence, existing frontend components and generated API contracts first. Keep Next.js/TypeScript and the established backend architecture. Reuse earlier viewer/timeline/chart/summary slices and shared selection state; do not create another demo application or rewrite the twelve documents. Browser routes follow SPEC-009; REST uses the canonical /api/v1/projects/{project_id} contract and documented exceptions. Record missing contract changes before implementation and regenerate clients; never infer absent scientific fields.

Prioritize ease of understanding, the next right action, working functionality and complete recovery paths. Keep case/context/time/origin visible with readable labels, not unexplained abbreviations. Server data owns measurements, eligibility, publication and job status; the browser owns interaction, not scientific truth. Use exact IDs/hashes, original units/times and immutable history. Missing is not zero/normal; synthetic descendants remain synthetic. No client-only authorization, invented claims or hidden provider exports.

Implement against real authenticated APIs. Conspicuously synthetic fixtures are allowed for isolated development/failure tests, never as a silent production fallback. If approved data or a contract is absent, finish independent work, show an honest capability-specific blocked state and record the owner/evidence needed. A placeholder button, screenshot or static model is not functioning integration. Avoid extra frameworks, speculative P1 features and paid services. Do not spawn agents merely because expert perspectives are listed.

Outcome
Verify a complete backend-connected research journey and finish the guided demo/evaluation experience with honest failure recovery.

Implement
1. Integrate region-level loading, empty, invalid, forbidden, expired, stale, withdrawn and successful states across every screen. Messages say what failed, what remains usable and the next valid action. Loading artwork must not resemble real tumor geometry. Keep durable outcomes in panels/Activity, not only toasts. Clear patient-bearing in-memory data on logout/access change; do not persist patient payloads, grants or notes in localStorage, service-worker offline caches or analytics.
2. Complete the compact Evaluation screen from actual authorized versioned reports/artifacts: task/protocol, cohort/independent patient count, real versus synthetic outcomes, pipeline/model versions, split/method, failures, metrics and limitations. Missing evidence reads Not evaluated; open real-follow-up or review gates remain visible. No decorative accuracy percentages or synthetic branches counted as independent real patients.
3. Implement Guided demo as a read-only sequence manifest of authorized case/state/run/report IDs with Previous/Next/Restart/Exit and preflight for access, published assets, genuine follow-up, graphics and prepared summaries. Approximate five-minute pacing is rehearsal guidance, not verified organizer timing. Restart resets UI selection/camera/progress only; it cannot delete observations, cancel jobs or regenerate branches. Editor live-write demonstrations stay explicit and isolated; show actual pending jobs and separately labeled saved results when needed.
4. Map UX-01–UX-18 to executable/manual evidence. Target WCAG 2.2 AA without claiming conformance from an automated scan: check semantic landmarks/labels, keyboard and screen-reader flow, focus visibility/return, safe dialog Escape, polite announcements, non-color-only provenance, table alternatives, reduced motion, touch and 200% zoom/320px reflow. Verify 4.5:1 normal text, 3:1 large text and relevant essential controls/markers, with target-size requirements from SPEC-009.
5. Fault-inject provider outage, failed grounding, 401/403/404/412/422/429, expired grants, missing objects, worker restart/cancel, slow/out-of-order responses and WebGL loss. Prove coherent selection, safe retries, baseline immutability and no partially published branch. Measure warm metadata p95 <700ms, manifest p95 <1.5s, first prepared mesh <=5s, camera target >=30fps and initial <=5MiB mesh budget on declared conditions; these remain targets until measured. Use at least thirty warm navigation/five cold smoke trials, reporting failures and hardware limits.
6. Run real interactive task sessions with at least three participants when feasible, including an unfamiliar user and research/clinician perspective where available. Record actual participants, task completion/errors/time and observed/simulated comprehension; self-review cannot invent participants or expert signoff. Any participant mistaking simulated results for real observations blocks disclosure readiness until fixed/retested. Keep non-canvas information available, while requiring a genuine supported-device interactive 3D test separately.

Make the next right action easy
Finish one coherent journey: open case → inspect real/derived mesh and exact sources → select/compare states → read charts/tables → explore a labeled branch → inspect grounded findings → see measured evaluation limits. Ordinary navigation needs no confirmation; sensitive retraction/withdrawal has a concrete confirmation.

Acceptance checks
Run browser integration against the actual local API/persistence/workers/private artifacts, plus isolated failure fixtures. Record each UX acceptance result and evidence origin; screenshots alone cannot pass interaction, performance or usability tests. Produce a concise Phase 5 report separating implemented, fixture-tested, real-data-verified, participant-reviewed and blocked scope. No full-readiness claim while mandatory real-data, disclosure, authorization or 3D gates remain open. Verify the relevant project/patient/branch authorization and actual API request/response paths, not only mocked component rendering.

Completion evidence
- Deliver working frontend code, shared typed components/client integration, focused behavior tests and a short runbook with actual commands. Use synthetic/public-safe fixtures; never include protected identifiers or credentials in examples or test artifacts.
- Run applicable type/lint/build, component and browser integration checks. Include manual interaction/accessibility checks where required and record actual device/browser. Distinguish synthetic fixture evidence, approved real-data operation and human review; skipped mandatory checks are not passes.
- Update requirements traceability, task ledger, contract decisions and release gates. Record what works, remaining limits and the next recommended action. All meaningful visible controls need a working action or a clear capability explanation.
- Final response: behavior delivered; key files; checks/results; material dependency/limitation. Keep it concise and evidence-based. Do not claim clinical validation or finished release readiness from visual polish.
```

