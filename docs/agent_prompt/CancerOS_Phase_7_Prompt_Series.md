# CancerOS Phase 7 — System-wide Final Quality and Integration Reviews

Version 1.0 | 23 October 2026 | Six separate P0 prompts | Workstreams 14 and 15

Use one prompt at a time in the CancerOS repository with COS-000, AGENTS.md, adopted decisions and the evidence ledger. Copy only that prompt's fenced text. This continues the Muse Spark-oriented structure with explicit role, scope, execution, usability, acceptance and evidence; it is not a benchmark claim. Creating the pack does not audit a repository, sign off a release, deploy, restore backups or create Git tags.

The source baseline remains the twelve drafted specifications (PRD-001; SPEC-003 through SPEC-012; COS-RA-001) plus COS-AUD-001 reconciliation baseline 1.0, whose adoption must be recorded honestly. PRD governs intent; SPEC-007 architecture; SPEC-008 plus adopted audit contracts/lifecycle; SPEC-003/004/005 scientific meaning; SPEC-009 interaction; SPEC-010/011 safety/evaluation. Roadmap/literature does not silently expand scope. Do not rewrite the specifications to match deficiencies in code.

## When and how to execute

COS-099–102 are reusable review prompts at major milestones. For milestone mode, inspect the actually implemented workstreams and record later requirements as not yet assessed. Do not require future Phase 6 deliverables merely to review Phase 2 work, and do not call a partial milestone review a full release approval. The prerequisite index names final-release predecessors; milestone execution substitutes available relevant code/evidence and lists its omissions.

Suggested review points: after data/imaging/twin integration (COS-040), complete simulation/fusion (COS-054/055), AI/API integration (COS-071), integrated UI (COS-080), and the Phase 6 candidate (COS-098). Run the relevant in-scope architecture/isolation/functionality checks, then COS-102 for the resulting fixes. These are scheduling recommendations, not five mandatory expensive repetitions of every test.

For final release, execute COS-099 → COS-100 → COS-101 → COS-102 → COS-103 → COS-104. Any new defect/fix returns to the affected review/remediation checks using a new candidate fingerprint. This verification loop is not a circular implementation prerequisite. COS-103 and COS-104 are final operations; milestone audits must not tag a partial prototype as a validated full release.

| Prompt | Output | Boundary |
| --- | --- | --- |
| COS-099 | Repository/specification compliance map and architecture findings | Read and verify real execution paths; no silent refactor or source-spec rewrite |
| COS-100 | Cross-module identity/provenance/transaction evidence | Test real API/database/job/storage boundaries, not just a topology diagram |
| COS-101 | Control inventory, full journey and failure/UX findings | Honest unavailable actions differ from dead/fake functionality |
| COS-102 | Risk-ordered fixes, regression evidence and engineering disposition | Technical sign-off remains conditional on final operations; never invent human clinical/owner approval |
| COS-103 | Candidate-bound deployed smoke, recovery and isolated restore record | Green health or backup schedules alone cannot prove recoverability |
| COS-104 | Exact validated tag, safe package and reproducibility chain | Freeze only supported scope; no tag moving, silent version drift or unauthorized remote publication |

## Audit record and findings contract

Each run records audit_run_id, mode, candidate commit and dirty-diff identity if applicable, build/config/deployment versions, specification identities/adoption, scope/exclusions, tool/environment, prior evidence reused and actual commands/results. Do not attribute dirty worktree observations solely to a clean commit.

Use stable finding IDs and separate fields for category (confirmed defect, suspected issue, missing evidence, accepted deviation), severity, status and evidence. Each entry needs requirement/decision, module/journey, exact reproduction or safe commit/file/symbol, expected/actual outcome, affected data/access/claims, proposed repair, owner/dependency and acceptance check. A grep match or missing test is not automatically proof of an exploit; describe the confidence/evidence accurately.

Audit completion is a task status. System readiness is a separate decision. Findings become verified_fixed only with executed checks. Missing data, review or deployment access remains blocked, never passed. Accepted nonblocking exceptions need actual existing authority/evidence; a coding agent cannot sign a fictional radiologist, security assessor or project owner.

## Requirements that cannot drift

- Keep canonical project-scoped APIs/generated clients, exact resource ownership, decimal-string quantities and typed source/relative time. C01–C06 require executable reads, durable revisions, independent timeline root, membership rules, real security/config and versioned dictionaries/scientific rules.
- Published snapshots/runs and accepted source content stay immutable; corrections append versions and current pointers/freshness remain explicit. Branches pin the original baseline hash. A branch has one shared observed baseline plus at least three simulated follow-ups, not four real visits.
- Synthetic descendants remain SYNTHETIC_GENERATED across geometry, measurement, notes and interpretation. General literature cannot establish missing patient facts; source observations, extracted assertions and background evidence stay distinct.
- Preserve physical units/frame/handedness and mask-based measurements. Same-shape arrays, same camera framing or a frame UID do not independently establish alignment/identity. Lab-only updates do not invent a new scan; DCE phases are not follow-up exams.
- Deny unauthorized exports, cross-patient/branch references and privilege escalation in backend/database/worker/cache/artifact paths. UI hiding is not access control. Every explicit publication and idempotent replay rechecks the applicable policy.
- JSON validity/citation resolution alone is not meaningful support. Numeric/unit/origin fidelity, abstention and prohibited-claim gates apply to template, live-model, saved and fallback results. No automatic optional forecasting, segmentation or grading enablement to improve presentation.
- Keep functional controls, precise next actions, drafts/retry safety, coherent selection and observed/simulated disclosure. A static preview/fake success/saved result is not the pending live output. Guide reset changes UI, not scientific data.

## Risk and release decisions

Critical identity/privacy/provenance/physical-scale/prohibited-claim findings block affected exposure. Major stale UI mixtures, partial branch publication, missing required genuine longitudinal data or unrecoverable outputs block full P0 readiness. Cosmetic issues can be tracked only when information/access/functionality remains intact under actual governance. Do not average away one critical problem or relabel a mandatory gap optional.

D01/D03 need actual approved baseline/mask/linkage/annotation/geometry/rights evidence; D02 needs two genuine comparable real exams; D04 requires a verified external processing policy or truthful disabled/local scope; D05 needs actual independent/synthetic/fixture evaluation distinctions and failures; D06 needs deployed/target-device/recovery/rehearsal evidence and verified relevant event requirements. Optional models remain disabled where their gates are open. Five scenario entries are not necessarily five independent patients.

COS-102 records the engineering disposition and any actual required owner decisions, with operational verification pending. COS-103 verifies deployment/recovery of that exact candidate. COS-104 reconciles both plus scope/rights/evidence and freezes only a validated named release. Do not claim clinical validation, security certification, finalist selection, event submission or remote publication from these engineering reviews.

## Freeze and repository integrity

Preserve unrelated user changes and actual repository commit/tag conventions. The final tag resolves to an exact reviewed commit; existing tags are never moved/force-updated. If evidence commits follow the tested application build, distinguish application commit, evidence commit and deployed image digest and verify the difference. Never say an image was built from a later evidence commit when it was not.

Avoid circular manifests: hash fixed files/commits, then create sidecars and a recorded tag verification; do not edit a tagged commit to insert its own resulting identity. A clean authorized checkout and checksum verifier must reproduce the permitted fixture/startup slice, with scientific versus provider-output reproducibility limits disclosed.

Local annotated tagging is part of executing COS-104 once gates pass. Remote tag push/release publication is separate and proceeds only within already authorized session/repository scope. Do not invent signing keys or approval ceremonies. If blocked, assemble an honest candidate/evidence package without presenting it as a validated release.

Package public-safe source/instructions/contracts/locks/manifest/results/limitations and reference restricted evidence through approved access. Exclude credentials, protected mappings/notes/scans, signed grants, unapproved weights and sensitive logs. A manifest hash does not authorize data redistribution. Restores and destructive fault tests use an isolated target, never overwrite current scientific writes by default.

## Phase completion evidence

Six prompt tasks yield scoped audit reports, stable findings, verified remediation, deployed recovery/restore evidence, an accurate engineering/operational disposition and a frozen reproducible named release only when gates pass. Each report states what was tested, what failed, what remains unverified and the next action. Review completion and full release success are never interchangeable.

## Prompt index

| ID | Priority | Workstream | Prompt | Final-release prerequisites |
| --- | --- | --- | --- | --- |
| COS-099 | P0 | 14 | [Full repository architecture and specification compliance audit](#cos-099--full-repository-architecture-and-specification-compliance-audit) | COS-002, COS-003, COS-008, COS-087, COS-097, COS-098 |
| COS-100 | P0 | 14 | [Cross-module integration, identity isolation and provenance audit](#cos-100--cross-module-integration-identity-isolation-and-provenance-audit) | COS-022, COS-024, COS-050, COS-064, COS-071, COS-081, COS-086, COS-099 |
| COS-101 | P0 | 14 | [End-to-end functionality, dead controls and demonstration reliability audit](#cos-101--end-to-end-functionality-dead-controls-and-demonstration-reliability-audit) | COS-080, COS-087, COS-093, COS-094, COS-095, COS-096, COS-098, COS-099, COS-100 |
| COS-102 | P0 | 14 | [Risk-based remediation backlog, regression verification and release sign-off](#cos-102--risk-based-remediation-backlog-regression-verification-and-release-sign-off) | COS-099, COS-100, COS-101 |
| COS-103 | P0 | 15 | [Final deployment verification, service recovery and backup validation](#cos-103--final-deployment-verification-service-recovery-and-backup-validation) | COS-089, COS-090, COS-091, COS-092, COS-093, COS-102 |
| COS-104 | P0 | 15 | [Freeze the validated release, tag the repository and assemble reproducibility evidence](#cos-104--freeze-the-validated-release-tag-the-repository-and-assemble-reproducibility-evidence) | COS-097, COS-098, COS-102, COS-103 |

## Separate copyable prompts

### COS-099 — Full repository architecture and specification compliance audit

```text
Task: COS-099 — Full repository architecture and specification compliance audit
Priority: P0 | Workstream: 14
Final-release prerequisites: COS-002, COS-003, COS-008, COS-087, COS-097, COS-098; inherited Phase 1–6 governance/security/contracts apply.
Audit modes: milestone or final_release. Listed prerequisites are for final release; in milestone mode use available relevant evidence and explicitly record later/untested scope.
Expert perspectives: Principal software architecture, scientific specification review, platform engineering and product integrity.
Read: All twelve specification identities and adopted COS-AUD-001 overlay; AGENTS.md/decisions/traceability; actual repository and release manifests; actual repository/configuration and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approvals you do not have. If reviewing your own implementation, disclose self-review; no fabricated audit team or reviewer signature.

Execute this one task in the existing repository using actual code, data permissions, tests and deployment evidence. Inspect relevant specifications, COS-AUD-001 adoption/decisions and predecessor records first. Reuse the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture, canonical project APIs and generated contracts. Do not rewrite twelve specifications, introduce new features/infrastructure or reinterpret scientific invariants merely to close a finding.

Preserve source identity/rights, original-patient isolation, precise units/time, immutable history and synthetic provenance. Keep observed/synthetic context separate from QC, availability and publication. Missing is not normal/zero; fixtures are not authentic data; a technical pass is not clinical validation. Protect secrets, source maps, restricted notes and signed grants in all reports/logs/packages.

Proceed with authorized reversible inspection, meaningful checks and in-scope remediation where this task requests it. Respect existing account/budget/action authorization rather than inventing new approval ceremonies. If actual data, review, credentials or authority are absent, complete independent work and a concrete reviewable result, record the owner/evidence needed and keep the affected gate blocked. Skipped mandatory checks are not passes. Do not spawn agents merely because multiple expert perspectives are named.

Outcome
Produce a concise evidence-based compliance and architecture-drift audit of the repository that actually exists.

Implement
1. Establish audit_run_id, mode=milestone or final_release, audited commit, dirty-worktree/diff identity, environment/config manifests, specification hashes/adoption and in-scope workstreams. Final release uses the listed completed-predecessor evidence; milestone mode uses the actually built scope and explicitly marks later requirements not yet assessed. Preserve user changes. Do not label an uncommitted tree as the named clean commit or invent approved baseline adoption.
2. Inventory tracked applications/packages, entrypoints, migrations, workers, generated contracts/clients, config, tests, deployment manifests and documentation. Follow actual execution paths rather than directory names alone. Map requirements to implemented code, executable evidence, missing behavior and deliberate P1/deferred scope. All twelve source documents stay unchanged; conflicts resolve through domain authority and recorded decisions, not whichever document was opened last.
3. Check the established modular FastAPI/Next.js/PostgreSQL/private-object/CPU-worker architecture and repository boundaries. Detect duplicate domain services, competing state/identity stores, preliminary API catalogs, mismatched enums/units/time types, unauthorized microservices/infrastructure and stale generated clients. A justified adopted decision is not drift; an undocumented local reinterpretation is.
4. Inspect closure of C01–C06: required discovery/read contracts, durable as-of history, independent relative-time root, versioned membership/assembly, actual auth/config and executable dictionaries/scientific rules. Verify migrations enforce ownership/history beyond permissive JSON or comments. Check that browser routes are not confused with REST routes and model/tool exports remain bounded.
5. Compare implementation, tests, deployment and public/docs claims against the same scope/version. Inspect placeholders, demo-only adapters, hardcoded patient values, environment bypasses, skipped mandatory tests and unimplemented paths advertised as complete. Separate a documented honest fixture/disabled capability from a production path that silently fabricates behavior.
6. Report confirmed defects, suspected issues needing verification, missing evidence and accepted deviations separately. Every finding needs a stable ID, requirement/decision, reproducible path or exact commit/file/symbol, affected capability, severity, rationale and proposed minimal remedy. Keep a short executive report plus machine-readable traceability/findings; avoid an indiscriminate rewrite or whole-source dump. Route functional fixes to COS-102; do not silently refactor while auditing.

Make the next right action easy
Make the report easy to act on: current architecture, highest-impact gaps, what is verified and the next repair in dependency order. An incomplete future milestone feature is not automatically a regression, but it cannot count as completed release behavior.

Acceptance checks
Inspect actual entrypoints/contracts/migrations and run narrowly relevant existing build/schema/import checks when needed to validate findings. Record commands and limitations. Verify every claimed compliance/defect has evidence, no domain scope was silently expanded and audit completion is distinguished from software readiness.

Completion evidence
- Produce a short human report and machine-readable audit/result index with run ID/mode, exact candidate/environment/spec versions, scope, commands, findings/checks and gate disposition. Reference safe commit/file/symbol or permitted artifacts for reproducibility.
- Record confirmed defects, suspected issues, missing evidence, accepted deviations and verified fixes separately. Retain before/after failures and actual denominators; do not claim tests or specialist review that did not occur.
- Update traceability, task/finding ledger, decision/claim records and release gates. Reuse valid prior evidence; rerun affected checks for changes/failures/unresolved concerns. Task completion and release readiness are different statuses.
- Final response: named scope reviewed/delivered; highest-priority results; actual verification; open blocker and next action; precise disposition. Keep concise. No full-readiness, clinical-validation or external-publication claim without evidence.
```

### COS-100 — Cross-module integration, identity isolation and provenance audit

```text
Task: COS-100 — Cross-module integration, identity isolation and provenance audit
Priority: P0 | Workstream: 14
Final-release prerequisites: COS-022, COS-024, COS-050, COS-064, COS-071, COS-081, COS-086, COS-099; inherited Phase 1–6 governance/security/contracts apply.
Audit modes: milestone or final_release. Listed prerequisites are for final release; in milestone mode use available relevant evidence and explicitly record later/untested scope.
Expert perspectives: Data architecture, application security, scientific lineage and transaction/reliability QA.
Read: SPEC-003/004/005/008/010/011; COS-AUD-001; existing ownership/provenance/revision tests; actual repository/configuration and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approvals you do not have. If reviewing your own implementation, disclose self-review; no fabricated audit team or reviewer signature.

Execute this one task in the existing repository using actual code, data permissions, tests and deployment evidence. Inspect relevant specifications, COS-AUD-001 adoption/decisions and predecessor records first. Reuse the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture, canonical project APIs and generated contracts. Do not rewrite twelve specifications, introduce new features/infrastructure or reinterpret scientific invariants merely to close a finding.

Preserve source identity/rights, original-patient isolation, precise units/time, immutable history and synthetic provenance. Keep observed/synthetic context separate from QC, availability and publication. Missing is not normal/zero; fixtures are not authentic data; a technical pass is not clinical validation. Protect secrets, source maps, restricted notes and signed grants in all reports/logs/packages.

Proceed with authorized reversible inspection, meaningful checks and in-scope remediation where this task requests it. Respect existing account/budget/action authorization rather than inventing new approval ceremonies. If actual data, review, credentials or authority are absent, complete independent work and a concrete reviewable result, record the owner/evidence needed and keep the affected gate blocked. Skipped mandatory checks are not passes. Do not spawn agents merely because multiple expert perspectives are named.

Outcome
Trace complete data flows and prove boundaries hold across modules, not merely inside individual services.

Implement
1. Use the same audit candidate/mode and a named set of isolated test projects/patients/branches. Trace approved source registry → restricted identity → clinical/imaging import → mask/measurement/mesh → snapshot → simulation → fusion/context → interpretation/evidence → UI/export. Record exact resource IDs/hashes internally and safe redacted evidence for reports.
2. Challenge every transition and nested reference with cross-project/patient/branch IDs through both APIs and direct disposable-database invalid writes. Include resource registry, lineage/claim links, source passages, artifact grants, jobs/retries, caches, observation corrections and evaluation/group splits. Explicit baseline references are the only permitted shared observed-to-branch links; generic research concepts/evidence do not grant cross-patient access.
3. Verify canonical ownership/provenance through derived outputs: real source derivation remains source-linked; every synthetic descendant stays synthetic, including meshes/measurements/trends and extracted synthetic-note facts. Shared observed baseline items retain observed origin. Missing real clinical data is never replaced by synthetic fields or used to unlock exposure compatibility.
4. Test revision N after N+1 correction/retraction, late data and rights withdrawal. Published content/members and branch baseline hashes stay immutable; current pointers/freshness/access may change only through the contract. Source time, modality-specific collection and historical geometry remain distinct. Prevent future/hidden simulator data leaking into forecast/interpretation inputs.
5. Exercise atomic observation/outbox writes, idempotent command replay with reauthorization, lease/cancel/finalization races and validated ready-versus-published states. Confirm no partial branch or private candidate becomes viewer-visible. Check artifact bytes/version, transform/units, evidence support and source withdrawal propagate coherently without silent data rewrites.
6. Recheck denied egress, least-privilege workers, protected mappings, signed-grant leakage and original-patient split inheritance across processed cohorts/descendants. Use safe local mocks/adversarial fixtures where possible; no unauthorized live export or attacks on third-party systems. Attribute each failure to the specific violated boundary with a minimal reproduction and downstream impact.

Make the next right action easy
Report each broken handoff as “input → service boundary → incorrect output/access → required repair.” Keep technical failure details available without exposing source identity, secrets or restricted notes in shared audit reports.

Acceptance checks
Run actual persistence/API/worker/storage integration for the selected boundary matrix, including negative paths; a diagram or mocked response cannot pass ownership enforcement. Record tested and untested edges, current denials, immutable hashes and attempted/failed counts. Any confirmed privacy/provenance/identity violation blocks affected exposure until repaired and reverified.

Completion evidence
- Produce a short human report and machine-readable audit/result index with run ID/mode, exact candidate/environment/spec versions, scope, commands, findings/checks and gate disposition. Reference safe commit/file/symbol or permitted artifacts for reproducibility.
- Record confirmed defects, suspected issues, missing evidence, accepted deviations and verified fixes separately. Retain before/after failures and actual denominators; do not claim tests or specialist review that did not occur.
- Update traceability, task/finding ledger, decision/claim records and release gates. Reuse valid prior evidence; rerun affected checks for changes/failures/unresolved concerns. Task completion and release readiness are different statuses.
- Final response: named scope reviewed/delivered; highest-priority results; actual verification; open blocker and next action; precise disposition. Keep concise. No full-readiness, clinical-validation or external-publication claim without evidence.
```

### COS-101 — End-to-end functionality, dead controls and demonstration reliability audit

```text
Task: COS-101 — End-to-end functionality, dead controls and demonstration reliability audit
Priority: P0 | Workstream: 14
Final-release prerequisites: COS-080, COS-087, COS-093, COS-094, COS-095, COS-096, COS-098, COS-099, COS-100; inherited Phase 1–6 governance/security/contracts apply.
Audit modes: milestone or final_release. Listed prerequisites are for final release; in milestone mode use available relevant evidence and explicitly record later/untested scope.
Expert perspectives: Product QA, frontend/back-end integration, accessibility and demo reliability.
Read: SPEC-009 UX-01–UX-18; SPEC-011/012; frozen case/guide/deployment manifests; current UI/API; actual repository/configuration and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approvals you do not have. If reviewing your own implementation, disclose self-review; no fabricated audit team or reviewer signature.

Execute this one task in the existing repository using actual code, data permissions, tests and deployment evidence. Inspect relevant specifications, COS-AUD-001 adoption/decisions and predecessor records first. Reuse the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture, canonical project APIs and generated contracts. Do not rewrite twelve specifications, introduce new features/infrastructure or reinterpret scientific invariants merely to close a finding.

Preserve source identity/rights, original-patient isolation, precise units/time, immutable history and synthetic provenance. Keep observed/synthetic context separate from QC, availability and publication. Missing is not normal/zero; fixtures are not authentic data; a technical pass is not clinical validation. Protect secrets, source maps, restricted notes and signed grants in all reports/logs/packages.

Proceed with authorized reversible inspection, meaningful checks and in-scope remediation where this task requests it. Respect existing account/budget/action authorization rather than inventing new approval ceremonies. If actual data, review, credentials or authority are absent, complete independent work and a concrete reviewable result, record the owner/evidence needed and keep the affected gate blocked. Skipped mandatory checks are not passes. Do not spawn agents merely because multiple expert perspectives are named.

Outcome
Verify that visible product promises and demonstration controls work against real backend behavior under normal and failure conditions.

Implement
1. Inventory routes and meaningful visible controls by viewer/editor/admin role: navigation, case/filter/pagination, source records, observation forms, 3D controls/layers, state/phase/lesion selectors, comparison, charts/tables, simulation/run/publication, insights/citations, Activity, admin imports, Evaluation and guide controls. Classify working, correctly unavailable with reason, dead/no-op, misleading, inaccessible and not tested. A legitimately gated optional feature is not a dead-control defect.
2. Walk the complete ordinary UI and guided sequence against the authorized actual API/deployment, not a separate static fixture site. Confirm clicks produce the intended request/state/result and that saved values survive reload as appropriate. Detect fake success toasts, local-only writes, hardcoded counts, unimplemented filters, first-page-only histories, guessed result IDs and loading screens that never resolve.
3. Challenge rapid case/branch/state switching with delayed/reversed requests. Header, mesh, chart cursor, values and insight must belong to the same selected snapshot. Confirm physical scale/camera consistency, missing versus zero, unknown/shifted time, DCE phase versus exam, historical scan labeling, incompatible comparisons and source-linked evidence. No morphing or synthetic visit can masquerade as a real follow-up.
4. Verify actual 3D rotate/pan/zoom/fit with keyboard/touch/button alternatives, table/source navigation without WebGL, focus/Back restoration, reduced motion, narrow reflow/zoom and readable origin/units. Check all five scenario families, observed baseline plus three follow-ups, independent clinical deterioration and genuine repeated-exam evidence. Static fallback remains labeled and does not pass interactive readiness.
5. Fault-inject provider/grounding failure, lost response, 401/403/404/412/422/429, expired grant, missing object, worker cancel/restart and graphics loss in an isolated environment. Preserve drafts, idempotency, valid prior states and exact fallback labels. Restart guide changes UI only; previous prepared output is never renamed as a pending live result.
6. Verify actual measured device/browser/network/performance and existing usability evidence. Repeat only invalidated/necessary checks, retaining slow/failing trials and real participant limitations. Record screenshots/video only when permitted as supporting evidence, never as substitutes for interactions or actual consent/review. Prioritize a short list of blockers with exact steps, expected/actual behavior and evidence.

Make the next right action easy
Judge the product by ease of understanding and the next right action, not screen count or visual polish. Flag unexplained abbreviations, redundant confirmations, hidden provenance and errors without repair paths where they obstruct the required journey.

Acceptance checks
Map UX-01–UX-18 and each critical control group to executed outcomes with browser/API evidence. Test role denial on the server as well as hidden UI controls. Mark unavailable real data/deployment or device tests blocked. Any observed/simulated confusion, stale mixed state, unauthorized action or fabricated functionality prevents the corresponding readiness claim.

Completion evidence
- Produce a short human report and machine-readable audit/result index with run ID/mode, exact candidate/environment/spec versions, scope, commands, findings/checks and gate disposition. Reference safe commit/file/symbol or permitted artifacts for reproducibility.
- Record confirmed defects, suspected issues, missing evidence, accepted deviations and verified fixes separately. Retain before/after failures and actual denominators; do not claim tests or specialist review that did not occur.
- Update traceability, task/finding ledger, decision/claim records and release gates. Reuse valid prior evidence; rerun affected checks for changes/failures/unresolved concerns. Task completion and release readiness are different statuses.
- Final response: named scope reviewed/delivered; highest-priority results; actual verification; open blocker and next action; precise disposition. Keep concise. No full-readiness, clinical-validation or external-publication claim without evidence.
```

### COS-102 — Risk-based remediation backlog, regression verification and release sign-off

```text
Task: COS-102 — Risk-based remediation backlog, regression verification and release sign-off
Priority: P0 | Workstream: 14
Final-release prerequisites: COS-099, COS-100, COS-101; inherited Phase 1–6 governance/security/contracts apply.
Audit modes: milestone or final_release. Listed prerequisites are for final release; in milestone mode use available relevant evidence and explicitly record later/untested scope.
Expert perspectives: Engineering ownership, risk triage, scientific safety and change-control QA.
Read: COS-099/100/101 findings; SPEC-010/011 release severity; AGENTS.md/decision policy; actual candidate evidence; actual repository/configuration and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approvals you do not have. If reviewing your own implementation, disclose self-review; no fabricated audit team or reviewer signature.

Execute this one task in the existing repository using actual code, data permissions, tests and deployment evidence. Inspect relevant specifications, COS-AUD-001 adoption/decisions and predecessor records first. Reuse the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture, canonical project APIs and generated contracts. Do not rewrite twelve specifications, introduce new features/infrastructure or reinterpret scientific invariants merely to close a finding.

Preserve source identity/rights, original-patient isolation, precise units/time, immutable history and synthetic provenance. Keep observed/synthetic context separate from QC, availability and publication. Missing is not normal/zero; fixtures are not authentic data; a technical pass is not clinical validation. Protect secrets, source maps, restricted notes and signed grants in all reports/logs/packages.

Proceed with authorized reversible inspection, meaningful checks and in-scope remediation where this task requests it. Respect existing account/budget/action authorization rather than inventing new approval ceremonies. If actual data, review, credentials or authority are absent, complete independent work and a concrete reviewable result, record the owner/evidence needed and keep the affected gate blocked. Skipped mandatory checks are not passes. Do not spawn agents merely because multiple expert perspectives are named.

Outcome
Turn verified findings into minimal tested fixes and a precise engineering disposition for the audited candidate.

Implement
1. Consolidate/deduplicate findings with stable references back to each audit. Record confirmed versus suspected/missing-evidence status, severity, affected journey/gate, likelihood/reach, dependencies, owner, reproducible acceptance, effort and evidence. Critical identity/privacy/provenance/physical-scale/prohibited-claim defects precede other work. Major genuine-data gaps, stale states, partial publication and unrecoverable output cannot be downgraded to cosmetic issues.
2. Produce a dependency-ordered remediation backlog and execute authorized reversible in-scope fixes, rather than stopping after writing a list. Prefer the smallest coherent change and add meaningful regression coverage for real defects. Do not introduce new architecture/features, fabricate patient data/review, disable mandatory tests or rewrite source specifications to make implementation appear compliant.
3. For each fix preserve failing evidence, commit/diff identity and before/after reproduction. Run targeted regression plus dependent contract/migration/API/browser/scientific checks appropriate to the actual change. Reuse still-valid frozen evidence; do not repeatedly broaden expensive suites without changed dependencies or unresolved concerns. Contract/rule changes follow adopted decisions and regenerate affected clients/config/evaluation versions.
4. Re-audit changed boundaries and update each finding to verified_fixed, open, blocked or explicitly accepted_nonblocking under existing governance, with evidence and real authority. A changed code path is not a verified fix. Missing rights, genuine longitudinal exams or qualified review stay concrete blocked dependencies; never substitute synthetic evidence or an agent persona approval.
5. Record engineering disposition for the named commit/scope: blocked, ready_for_final_operational_verification or milestone_review_complete_with_gaps. “Release sign-off” here is an evidence-based engineering record, not clinical certification or an invented project-owner signature. Follow actual repository/session authority; do not create a new human approval ceremony for routine fixes. Record explicitly required owner/reviewer decisions honestly if still absent.
6. Hand COS-103 a candidate fingerprint and exact remaining operational checks. Full final release readiness is conditional on deployed recovery verification and COS-104 identity/freeze consistency. If an active critical exposure is found, restrict/disable the affected path within existing authorization, preserve evidence and report it; do not continue showcasing the defect to protect the demo narrative.

Make the next right action easy
Make the backlog usable as executable small tasks with a clear acceptance test and owner, and lead the sign-off report with what can ship for which scope and what blocks it. Avoid an average risk score that conceals a single critical failure.

Acceptance checks
Demonstrate fixes with actual rerun outcomes and explicit remaining gaps. Verify every closed finding has evidence, no test result was fabricated/waived and no excluded requirement was silently marked done. A completed remediation report can still correctly conclude blocked; do not emit a final release pass before COS-103/104 evidence exists.

Completion evidence
- Produce a short human report and machine-readable audit/result index with run ID/mode, exact candidate/environment/spec versions, scope, commands, findings/checks and gate disposition. Reference safe commit/file/symbol or permitted artifacts for reproducibility.
- Record confirmed defects, suspected issues, missing evidence, accepted deviations and verified fixes separately. Retain before/after failures and actual denominators; do not claim tests or specialist review that did not occur.
- Update traceability, task/finding ledger, decision/claim records and release gates. Reuse valid prior evidence; rerun affected checks for changes/failures/unresolved concerns. Task completion and release readiness are different statuses.
- Final response: named scope reviewed/delivered; highest-priority results; actual verification; open blocker and next action; precise disposition. Keep concise. No full-readiness, clinical-validation or external-publication claim without evidence.
```

### COS-103 — Final deployment verification, service recovery and backup validation

```text
Task: COS-103 — Final deployment verification, service recovery and backup validation
Priority: P0 | Workstream: 15
Final-release prerequisites: COS-089, COS-090, COS-091, COS-092, COS-093, COS-102; inherited Phase 1–6 governance/security/contracts apply.
Execution mode: final_release. Candidate-changing fixes return to the affected audit/remediation checks before continuing.
Expert perspectives: Site reliability, secure operations, disaster recovery and release integration.
Read: SPEC-007/008/010/011; COS-089/093 restore/rollback evidence; COS-102 candidate disposition; actual deployment; actual repository/configuration and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approvals you do not have. If reviewing your own implementation, disclose self-review; no fabricated audit team or reviewer signature.

Execute this one task in the existing repository using actual code, data permissions, tests and deployment evidence. Inspect relevant specifications, COS-AUD-001 adoption/decisions and predecessor records first. Reuse the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture, canonical project APIs and generated contracts. Do not rewrite twelve specifications, introduce new features/infrastructure or reinterpret scientific invariants merely to close a finding.

Preserve source identity/rights, original-patient isolation, precise units/time, immutable history and synthetic provenance. Keep observed/synthetic context separate from QC, availability and publication. Missing is not normal/zero; fixtures are not authentic data; a technical pass is not clinical validation. Protect secrets, source maps, restricted notes and signed grants in all reports/logs/packages.

Proceed with authorized reversible inspection, meaningful checks and in-scope remediation where this task requests it. Respect existing account/budget/action authorization rather than inventing new approval ceremonies. If actual data, review, credentials or authority are absent, complete independent work and a concrete reviewable result, record the owner/evidence needed and keep the affected gate blocked. Skipped mandatory checks are not passes. Do not spawn agents merely because multiple expert perspectives are named.

Outcome
Verify the actual final candidate deployment and its recoverability without risking current scientific data or assuming previous smoke tests still apply.

Implement
1. Identify the exact candidate commit/image/schema/config/corpus/model/data manifests and compare COS-102 evidence to deployed frontend/API/workers. Verify actual origin/TLS/session, role/project/patient/branch restrictions, private assets, source rights and permitted model capabilities. Do not call a local build a deployment or an old image the new candidate. Use only existing authorized account/budget/scope; complete independent checks and record absent access instead of inventing URLs.
2. Run clean-browser viewer and isolated presenter/admin smoke journeys against the actual deployment: approved case, source-derived rotating mesh, exact state/chart/table/comparison, published scenario, grounded or labeled local/saved summary and permitted evidence/evaluation. Check judge access duration and no new dataset/provider exposure. Recheck role denial and fallback labels after deployment configuration changes.
3. Verify API/worker readiness and graceful recovery from controlled restart, queue outage, lease expiry, duplicate job delivery, cancellation and optional-provider failure. Use an isolated canary/test namespace for destructive failure injection; do not kill production dependencies or corrupt live data without specific authorization. Confirm durable outbox recovery, no duplicate publication, no stale result and valid prior states remain accessible.
4. Restore the selected current database backup plus exact referenced object versions/manifests into an isolated environment, including protected key access through the approved mechanism. Verify object bytes/hashes, lineage, historical revision N after N+1 correction, branch baseline/run pointers and actual ability to read permitted artifacts. A backup-job success or old restore report is insufficient if relevant dependencies changed; reuse unaffected evidence with a documented validity check.
5. Rehearse pinned compatible app/config rollback and postrollback checks without overwriting current writes. A destructive database downgrade is not default rollback. Measure achieved RPO/RTO, resource/performance and essential cost limits against declared targets, recording conditions/failures. Check actual alerts and safe operator commands without leaking credentials/grants.
6. Produce an operational verification record bound to this candidate and environment: pass_for_named_scope or blocked, exact checks, recovery evidence, versions, timestamps, operator identity/role and remaining limitations. New functional/configuration defects return to the COS-102 remediation loop; any candidate-changing fix invalidates affected prior sign-off and must be reverified before freeze.

Make the next right action easy
Provide a concise runbook with verify, recover, rollback and stop conditions, each naming the target environment and safe next action. Patient-facing degradation remains understandable; internal logs contain only safe request/resource IDs.

Acceptance checks
Execute and record actual deployed smoke/recovery/restore outcomes, or explicitly block the unexecuted operational gate. Confirm database and object history remain consistent and prior publication immutable. Report measured versus targeted recovery/performance; no blanket “production ready” or zero-data-loss claim from green health checks.

Completion evidence
- Produce a short human report and machine-readable audit/result index with run ID/mode, exact candidate/environment/spec versions, scope, commands, findings/checks and gate disposition. Reference safe commit/file/symbol or permitted artifacts for reproducibility.
- Record confirmed defects, suspected issues, missing evidence, accepted deviations and verified fixes separately. Retain before/after failures and actual denominators; do not claim tests or specialist review that did not occur.
- Update traceability, task/finding ledger, decision/claim records and release gates. Reuse valid prior evidence; rerun affected checks for changes/failures/unresolved concerns. Task completion and release readiness are different statuses.
- Final response: named scope reviewed/delivered; highest-priority results; actual verification; open blocker and next action; precise disposition. Keep concise. No full-readiness, clinical-validation or external-publication claim without evidence.
```

### COS-104 — Freeze the validated release, tag the repository and assemble reproducibility evidence

```text
Task: COS-104 — Freeze the validated release, tag the repository and assemble reproducibility evidence
Priority: P0 | Workstream: 15
Final-release prerequisites: COS-097, COS-098, COS-102, COS-103; inherited Phase 1–6 governance/security/contracts apply.
Execution mode: final_release. Candidate-changing fixes return to the affected audit/remediation checks before continuing.
Expert perspectives: Release management, software provenance, reproducible packaging and scientific communication.
Read: COS-102/103 current candidate records; repository version/tag conventions; SPEC-010/011/012 evidence requirements; actual repository/configuration and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approvals you do not have. If reviewing your own implementation, disclose self-review; no fabricated audit team or reviewer signature.

Execute this one task in the existing repository using actual code, data permissions, tests and deployment evidence. Inspect relevant specifications, COS-AUD-001 adoption/decisions and predecessor records first. Reuse the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture, canonical project APIs and generated contracts. Do not rewrite twelve specifications, introduce new features/infrastructure or reinterpret scientific invariants merely to close a finding.

Preserve source identity/rights, original-patient isolation, precise units/time, immutable history and synthetic provenance. Keep observed/synthetic context separate from QC, availability and publication. Missing is not normal/zero; fixtures are not authentic data; a technical pass is not clinical validation. Protect secrets, source maps, restricted notes and signed grants in all reports/logs/packages.

Proceed with authorized reversible inspection, meaningful checks and in-scope remediation where this task requests it. Respect existing account/budget/action authorization rather than inventing new approval ceremonies. If actual data, review, credentials or authority are absent, complete independent work and a concrete reviewable result, record the owner/evidence needed and keep the affected gate blocked. Skipped mandatory checks are not passes. Do not spawn agents merely because multiple expert perspectives are named.

Outcome
Freeze only the verified named release, create a non-destructive repository tag and assemble a safe verifiable evidence package.

Implement
1. Reconcile the current worktree/commit, deployed image digests, schema/config/corpus/model identities, scientific input/split/demo manifests and COS-102/103 decisions. Verify mandatory gates for the declared full or explicitly reduced scope. Missing required genuine-data/privacy/disclosure/operational evidence cannot become a full P0 pass. If blocked, produce a candidate package labeled blocked; do not create a tag or manifest that falsely claims validated release status.
2. Preserve user changes and inspect repository commit/tag/signing rules. Stage/commit only task-owned evidence or fixes under existing authorization, using isolation where needed; never discard or silently include unrelated work. Any code/config/model/data change since the audited candidate needs affected verification and deployment reconciliation before freeze. Evidence-only additions must be identified and their effect checked, not treated as tested application code automatically.
3. Record validated_application_commit, deployed build/image digest and release_evidence_commit separately when evidence was committed after the application build. Prove any difference contains only authorized evidence changes, or rebuild/reverify. Avoid circular self-hashes: generate an external final manifest/sidecar over already fixed commits/files rather than editing a tagged commit to include its own resulting hash.
4. Once gates are satisfied, create an annotated local version/release tag on the exact reviewed repository commit using actual naming conventions and meaningful scope/manifest references. Verify its resolved commit and annotation. Never move/delete/force an existing tag; if the name conflicts, report it and use the established versioning decision. Sign only with an available authorized key and report signed versus unsigned honestly. Push/publish only if existing session/repository authorization includes that action; local tag creation is distinct from remote publication.
5. Assemble source/build instructions, dependency locks/inventory, migration/contract/config versions, evidence/result indices, source-rights/attribution summaries, patient-split/scenario manifests, exact demo IDs, runbooks, restore/rollback results, limitations/claim ledger and safe operator handoff. Restricted artifacts stay referenced through approved access, not copied publicly. Exclude keys/.env secrets, linkage maps, raw restricted notes/scans, signed URLs, unapproved weights and sensitive logs.
6. Produce SHA-256 checksums and a verifier for the package manifest; verify byte identity and the tag→commit→build/deployment/evidence chain from a clean authorized checkout. Reproduce supported fixture checks and dependency startup within the declared environment; distinguish deterministic scientific replay from provider prose that is not guaranteed byte-identical. Publish an honest release note and final status with exact tag/commit/package identities, remaining limits and rollback reference. Later fixes create a new candidate/tag and targeted audit, never mutate this frozen release.

Make the next right action easy
Make the handoff immediately usable: what version is frozen, what scope passed, how to start/reproduce the safe slice, how to access permitted demo assets and how to recover. Explain unavailable credentials/data separately without including them in the package.

Acceptance checks
Verify tag target/annotation, clean checkout, checksum verifier, manifest/report alignment, actual image/deployment mapping and privacy/license scans. Record local versus remotely pushed tag and candidate-blocked versus validated-frozen status accurately. An archive, tag or release note alone is not evidence of passing tests, external publication, finalist selection or clinical validation.

Completion evidence
- Produce a short human report and machine-readable audit/result index with run ID/mode, exact candidate/environment/spec versions, scope, commands, findings/checks and gate disposition. Reference safe commit/file/symbol or permitted artifacts for reproducibility.
- Record confirmed defects, suspected issues, missing evidence, accepted deviations and verified fixes separately. Retain before/after failures and actual denominators; do not claim tests or specialist review that did not occur.
- Update traceability, task/finding ledger, decision/claim records and release gates. Reuse valid prior evidence; rerun affected checks for changes/failures/unresolved concerns. Task completion and release readiness are different statuses.
- Final response: named scope reviewed/delivered; highest-priority results; actual verification; open blocker and next action; precise disposition. Keep concise. No full-readiness, clinical-validation or external-publication claim without evidence.
```

