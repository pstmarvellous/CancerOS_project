# CancerOS Phase 2 — Data and Scientific Foundations

Version 1.0 | 23 October 2026 | 25 separate implementation prompts | 24 P0, 1 optional P1

These prompts are structured for clear execution with Meta Muse Spark: explicit role, prerequisites, outcome, numbered actions, usability behavior, acceptance checks and completion evidence. This is a prompt-structure adaptation, not a benchmarked claim about the model. The coding agent does not become the runtime clinical model; clinical inference is outside this phase except the separately gated optional segmentation adapter.

Use one numbered prompt at a time in the CancerOS repository. Copy only that task's fenced text. Retain COS-000 persona, AGENTS.md, the task ledger and generated contracts between sessions. Each prompt embeds core guardrails so it can also start a fresh session. The listed expert perspectives organize work; they do not represent actual specialist approval or require spawning a team. Inventory identifiers COS016–COS024 are normalized to COS-016–COS-024 for consistency with the other workstreams.

## Baseline and inputs

Use the twelve supplied documents (PRD-001, SPEC-003 through SPEC-012, COS-RA-001), COS-AUD-001 reconciliation baseline 1.0, and the Phase 1 implementation/evidence. Read current source files and relevant specifications before changing code. Record whether the reconciliation was adopted; do not manufacture approval. The audit's A01–A06 resolutions govern contradictions upon adoption. Keep any unadopted conflict isolated and recorded rather than inventing a competing interface. Existing source specifications remain unchanged.

Phase 1 deliverables are prerequisites to inspect, not evidence already achieved. In particular verify canonical contracts and early C01–C04 decisions, private storage, real authorization/session rules, migrations and working workers. These prompts close their Phase 2 portions; they do not imply every audit gate is closed. Use actual repository paths and implemented contracts, not speculative examples treated as existing files.

Authority: PRD-001 defines intent; SPEC-007 architecture; SPEC-008 plus adopted audit defines contracts/lifecycles; SPEC-003/004/005 scientific semantics; SPEC-010/011 safety and evaluation. SPEC-006/009 processing/presentation obey these contracts; SPEC-012 guides order and RA-001 is advisory.

Keep OBSERVED/SYNTHETIC state context separate from the five item-origin values REAL_OBSERVED, REAL_DERIVED, SYNTHETIC_GENERATED, INTERPOLATED and MODEL_PREDICTED. Synthetic descendants remain synthetic. Keep availability, technical QC, scientific review and publication independent. Measurements use canonical decimal-string quantities and typed time; missing is not zero, normal or negative. Source corrections and published history are append-only. Workers produce ready outputs; an explicit authorized command publishes.

## Execution order and priorities

Run COS-016–COS-029, skip COS-030 initially, then run COS-031–COS-040. COS-030 is the only P1 task: enable it only when weights/rights, COS-031 evaluation and COS-032 worker safeguards exist. No P0 task depends on automated segmentation. The dependency index lists task-specific predecessors; common Phase 1 governance, security and contract controls apply throughout.

Prioritize a functional small vertical slice: approved source → private identity linkage → validated clinical/imaging import → reviewed eligible mask → physical measurement → validated rotatable mesh → immutable state. Add a genuine repeated-exam case for truthful longitudinal comparison. Then exercise the synthetic geometry component against authorized run inputs. Finish one coherent pathway before adding source adapters or model integrations.

Ease of use means understandable labels, preserved input after errors, a precise next action, sensible validated defaults, visible provenance/units and honest empty/blocked states. Backend tasks expose typed statuses/actions suitable for later UI; they do not each create a new screen. COS-036 supplies a minimal working 3D preview; complete workspace navigation, production timeline/chart experiences and all clinical simulation families remain governed by later workstreams.

## Integration and release gates

| Gate | Required evidence / consequence |
| --- | --- |
| Source eligibility, D01/D03 | Actual approved release, rights for intended use, patient linkage, mask meaning and de-identification review. Fixtures permit coding; they cannot establish authentic patient results or authorize sharing. |
| Longitudinal case, D02 | Two genuine exams, valid time relation, reviewed lesion correspondence and comparable definitions. Registration additionally gates spatial overlays. DCE phases and synthetic visits cannot close this gate. |
| Evaluation independence, D05 | Frozen patient-group splits, independent eligible references where needed, all failure counts and predeclared metrics. A mask compared to itself is not model validation. |
| Executable scientific config, C06 | Versioned terminology/conversions, geometry tolerances and eligibility rules. Engineering tolerances are not clinical thresholds. Unknown required evidence blocks only the affected capability. |
| Runtime/security/resources, C05/D04/D06 | Actual access control/private asset checks, authorized provider policy if used, measured CPU/memory/performance and target-machine limitations. No public release by job completion. |
| Future simulation integration | COS-040 provides geometry, not the complete longitudinal rules engine. Production generation requires an authorized branch/run input and approved configuration. Later full-demo branches need one shared observed baseline plus at least three simulated follow-ups across the required five scenario families. |

Do not treat a missing review as an instruction to stop all coding. Implement authorized independent infrastructure and isolated synthetic fixtures, record the exact blocked real-data capability, and require evidence before enabling it. Coding-agent self-review cannot substitute for qualified scientific/rights review.

## Phase completion evidence

1. One runnable end-to-end workflow with exact commands, recorded versions and source manifests. State clearly whether it used real approved data or synthetic engineering fixtures.
2. Schema/contract and migration evidence; patient/project access tests; immutable lineage/history and failure-recovery tests; patient-group leakage report.
3. Independently calculated physical-volume fixtures, coordinate checks, mask/mesh QC and measured preview performance. Keep mask measurements authoritative.
4. Genuine real-pair review evidence or an explicit D02 block; no synthetic temporal result passed off as observation.
5. Synthetic target-versus-realized geometry checks, persistent labels, immutable baseline pinning and explicit publication gates. Missing upstream simulation integration remains visible.
6. Updated requirements matrix, task ledger and concise Phase 2 evidence report separating implemented, fixture-verified, real-data-verified, review-pending and blocked items. Do not declare release ready from task count alone.

## Prompt index

| ID | Priority | Workstream | Prompt | Task-specific prerequisites |
| --- | --- | --- | --- | --- |
| COS-016 | P0 | 03 | [Dataset source registry, licenses and attribution metadata](#cos-016--dataset-source-registry-licenses-and-attribution-metadata) | COS-015 |
| COS-017 | P0 | 03 | [Pseudonymous patient identities and source-patient mappings](#cos-017--pseudonymous-patient-identities-and-source-patient-mappings) | COS-016 |
| COS-018 | P0 | 03 | [Canonical clinical data schemas and controlled terminology](#cos-018--canonical-clinical-data-schemas-and-controlled-terminology) | COS-016, COS-017 |
| COS-019 | P0 | 03 | [Clinical visit, treatment and observation ingestion](#cos-019--clinical-visit-treatment-and-observation-ingestion) | COS-017, COS-018 |
| COS-020 | P0 | 03 | [Laboratory, vital-sign and symptom validation](#cos-020--laboratory-vital-sign-and-symptom-validation) | COS-018, COS-019 |
| COS-021 | P0 | 03 | [Dataset-specific metadata adapters for approved cohorts](#cos-021--dataset-specific-metadata-adapters-for-approved-cohorts) | COS-016, COS-017, COS-018, COS-019, COS-020 |
| COS-022 | P0 | 03 | [Provenance lineage, versioning and source immutability](#cos-022--provenance-lineage-versioning-and-source-immutability) | COS-016, COS-017, COS-018, COS-019, COS-021 |
| COS-023 | P0 | 03 | [Data completeness assessment, quarantine and quality reports](#cos-023--data-completeness-assessment-quarantine-and-quality-reports) | COS-019, COS-020, COS-021, COS-022 |
| COS-024 | P0 | 03 | [Duplicate detection and patient-level train, validation and test partitioning](#cos-024--duplicate-detection-and-patient-level-train-validation-and-test-partitioning) | COS-017, COS-021, COS-022, COS-023 |
| COS-025 | P0 | 04 | [DICOM and NIfTI ingestion with study and series association](#cos-025--dicom-and-nifti-ingestion-with-study-and-series-association) | COS-016, COS-017, COS-021, COS-022, COS-023 |
| COS-026 | P0 | 04 | [Imaging geometry, orientation, spacing and physical-coordinate validation](#cos-026--imaging-geometry-orientation-spacing-and-physical-coordinate-validation) | COS-025 |
| COS-027 | P0 | 04 | [MRI preprocessing, intensity normalization and sequence management](#cos-027--mri-preprocessing-intensity-normalization-and-sequence-management) | COS-024, COS-025, COS-026 |
| COS-028 | P0 | 04 | [Image and mask spatial alignment and resampling integrity](#cos-028--image-and-mask-spatial-alignment-and-resampling-integrity) | COS-026, COS-027 |
| COS-029 | P0 | 04 | [Reference segmentation mask import and annotation classification](#cos-029--reference-segmentation-mask-import-and-annotation-classification) | COS-022, COS-025, COS-026, COS-028 |
| COS-030 | P1 | 04 | [Optional nnU-Net or MONAI automated tumor segmentation integration](#cos-030--optional-nnu-net-or-monai-automated-tumor-segmentation-integration) | COS-029 |
| COS-031 | P0 | 04 | [Segmentation quality control and reference-mask evaluation](#cos-031--segmentation-quality-control-and-reference-mask-evaluation) | COS-026, COS-028, COS-029 |
| COS-032 | P0 | 04 | [Imaging processing jobs, artifact storage and failure recovery](#cos-032--imaging-processing-jobs-artifact-storage-and-failure-recovery) | COS-025, COS-026, COS-027, COS-028, COS-029, COS-031 |
| COS-033 | P0 | 05 | [Physical tumor measurements and volume calculation engine](#cos-033--physical-tumor-measurements-and-volume-calculation-engine) | COS-026, COS-029, COS-031, COS-032 |
| COS-034 | P0 | 05 | [Segmentation-to-3D-mesh reconstruction pipeline](#cos-034--segmentation-to-3d-mesh-reconstruction-pipeline) | COS-028, COS-032, COS-033 |
| COS-035 | P0 | 05 | [Mesh quality validation, simplification and coordinate preservation](#cos-035--mesh-quality-validation-simplification-and-coordinate-preservation) | COS-034 |
| COS-036 | P0 | 05 | [Breast-region anatomical context and illustrative geometry labeling](#cos-036--breast-region-anatomical-context-and-illustrative-geometry-labeling) | COS-034, COS-035 |
| COS-037 | P0 | 05 | [Real longitudinal study alignment and registration quality checks](#cos-037--real-longitudinal-study-alignment-and-registration-quality-checks) | COS-025, COS-026, COS-027, COS-028, COS-031, COS-032 |
| COS-038 | P0 | 05 | [Lesion identity matching and temporal measurement tracking](#cos-038--lesion-identity-matching-and-temporal-measurement-tracking) | COS-017, COS-022, COS-033, COS-037 |
| COS-039 | P0 | 05 | [Time-indexed digital twin state persistence and immutable history](#cos-039--time-indexed-digital-twin-state-persistence-and-immutable-history) | COS-018, COS-019, COS-022, COS-024, COS-032, COS-033, COS-038 |
| COS-040 | P0 | 05 | [Synthetic follow-up mask and mesh geometry generation](#cos-040--synthetic-follow-up-mask-and-mesh-geometry-generation) | COS-029, COS-031, COS-032, COS-033, COS-034, COS-035, COS-039 |

## Separate copyable prompts

### COS-016 — Dataset source registry, licenses and attribution metadata

```text
Task: COS-016 — Dataset source registry, licenses and attribution metadata
Priority: P0 | Workstream: 03
Prerequisites: COS-015; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Clinical informatics, privacy engineering and backend architecture.
Read: SPEC-003, SPEC-008, SPEC-010; audit D01/D03; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Make every imported resource traceable to a specific permitted source before clinical ingestion.

Implement
1. Implement versioned collection, release, component and artifact-source records. Capture source URL/citation, accession, retrieved date, manifest/checksum, license text or reference, attribution, access conditions, retention, and rights-review evidence. Keep dataset availability separate from authorization.
2. Model permissions per component and intended action: internal processing, external inference, derivative creation and public demonstration/redistribution. Unknown or expired permission blocks that action. A public download URL does not authorize every use. Preserve review identity/date; never fabricate a legal determination.
3. Add migrations, validation, authorized registry reads/writes and capability responses through the canonical contract. Attach immutable registry versions to later imports. Restrict arbitrary URL fetches and server-side requests; do not automatically download a cohort.
4. Supply clearly synthetic engineering examples and one minimal import guide for an actually available approved release. Retain required attribution on derived reports and exported bundles.

Make the next right action easy
Show source, release, permitted actions and the exact missing approval. Offer a concrete action such as “Add license evidence”; do not imply that pending review means approved. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Verify unknown rights deny publication, different releases retain different terms, unauthorized users cannot edit reviews, and a source-version update does not alter existing import provenance. Confirm fixture licenses are explicitly examples. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-017 — Pseudonymous patient identities and source-patient mappings

```text
Task: COS-017 — Pseudonymous patient identities and source-patient mappings
Priority: P0 | Workstream: 03
Prerequisites: COS-016; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Privacy engineering, clinical informatics and database integrity.
Read: SPEC-003, SPEC-008, SPEC-010; audit C05/D03; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Link records consistently without exposing original patient identifiers.

Implement
1. Implement project-scoped patient IDs and restricted source-patient mappings, unique within the approved source namespace/release rules. Generate opaque identifiers; do not encode diagnosis, dates, accession numbers or demographics in IDs.
2. Protect original linkage values with encryption and a keyed lookup digest where lookup is needed. Use the existing secrets/key-management abstraction, document key rotation and backup implications, and keep plaintext identifiers out of logs, URLs, frontend payloads and exported manifests. Pseudonymization is not proof of anonymity.
3. Define reviewed same-person links across releases/cohorts, with evidence, reviewer, confidence/status and reversible correction events. Do not automatically merge people from similar demographics or shared dates. Preserve mapping history and downstream invalidation signals.
4. Enforce patient/project authorization for every lookup. Support safe ingestion lookup without granting general mapping access; restrict map export and expose audited administrative operations only.

Make the next right action easy
Use a readable pseudonymous display label with source badges. For uncertain identity, explain the collision and request linkage review without displaying protected identifiers. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Exercise repeated imports, concurrent mapping creation, cross-project isolation, key lookup behavior, denied mapping access, redacted logs and correction history. Verify uncertain matches stay separate until reviewed. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-018 — Canonical clinical data schemas and controlled terminology

```text
Task: COS-018 — Canonical clinical data schemas and controlled terminology
Priority: P0 | Workstream: 03
Prerequisites: COS-016, COS-017; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Clinical informatics, API design and scientific integrity.
Read: SPEC-003/004, SPEC-008/010; audit C03/C06; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Create one typed clinical vocabulary and data envelope shared by ingestion, APIs and later simulation.

Implement
1. Extend canonical Pydantic/OpenAPI/TypeScript contracts for visits, diagnosis/pathology, treatments/exposures, laboratory observations, vital signs, symptoms and source notes. Reuse existing IDs, decimal-string quantities, provenance enums and error envelope; do not invent a second contract system.
2. Version supported dictionaries: analytes, units/conversions, treatment terms, receptor/pathology status, symptom instruments and missingness. Map source terms to local controlled codes with mapping version and original value. Record external terminology identifiers and their licensing/version when actually used; unknown stays unknown.
3. Implement absolute/relative time unions using the independent timeline-origin decision from C03. Preserve source precision, timezone/date-shift basis, uncertainty and missing times. Reject cyclic anchors and incomparable time domains; do not invent calendar dates or translate DCE phases into visits.
4. Separate observed versus synthetic state context, item provenance, quality status, availability and publication. Model negative, unknown, not tested, missing and invalid distinctly. Include value qualifiers and source locators. Make invalid combinations unrepresentable or explicitly rejected.

Make the next right action easy
Expose readable terminology and units through dictionary/capability reads. Explain unsupported terms and let an operator review mappings without silently coercing values. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Round-trip generated clients; reject invalid provenance/time combinations, bad units and self-anchors. Demonstrate missing receptor status differs from negative and a relative-only baseline can reference day zero without a fabricated date. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-019 — Clinical visit, treatment and observation ingestion

```text
Task: COS-019 — Clinical visit, treatment and observation ingestion
Priority: P0 | Workstream: 03
Prerequisites: COS-017, COS-018; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Backend engineering, clinical informatics and transactional reliability.
Read: SPEC-003, SPEC-008/010; audit C02/C04; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Ingest source-linked clinical records repeatably without silent alteration or partial patient updates.

Implement
1. Build a staged ingestion service and authorized canonical commands for supported visit, treatment and observation records. Validate schema, patient ownership, source rights/version, source locator, time basis and provenance before acceptance. Keep raw accepted source bytes private and immutable.
2. Define atomic batch boundaries and partial-batch policy explicitly. Use idempotency keys plus content fingerprints; exact retry returns the existing result, while conflicting reuse returns a typed conflict. Record accepted, rejected and quarantined item counts with stable IDs.
3. Append corrections/retractions rather than overwriting accepted observations. Integrate the durable patient revision journal or immutable input manifests from C02. Use the contract concurrency guards; update the revision and outbox within the same database transaction.
4. Preserve original values and treatment exposure intervals. Do not infer treatment delivery from an order, adherence from a prescription, or normal findings from absent fields. Do not auto-publish an imported patient state. Provide an extension point for COS-020 semantic rules and COS-022 full lineage without deferring mandatory source/revision capture.

Make the next right action easy
Provide validate-first results with row/field, reason and repair action; retain valid input after correction. Distinguish accepted data from published states and avoid duplicate “retry” submissions. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Test duplicate delivery, conflicting idempotency, concurrent correction, mixed-validity batches, rollback, denied patient access and revision N reconstruction after an N+1 correction. Confirm source values survive normalization. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-020 — Laboratory, vital-sign and symptom validation

```text
Task: COS-020 — Laboratory, vital-sign and symptom validation
Priority: P0 | Workstream: 03
Prerequisites: COS-018, COS-019; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Clinical data quality, measurement science and API usability.
Read: SPEC-003/004, SPEC-008/010/011; audit C06; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Reject malformed clinical data while preserving unusual, qualified and uncertain observations faithfully.

Implement
1. Implement versioned validation rules for only the supported analytes, vital-sign components and symptom instruments. Separate schema/unit errors, impossible structural values, review warnings and source-provided reference ranges. Do not invent universal normal ranges, safety grades or treatment decisions.
2. Store original value/unit plus canonical numeric value/unit and conversion-rule version. Use finite decimal arithmetic where appropriate; reject NaN/infinity. Preserve censored values such as “< detection limit”, ordinal scores, instrument version, negation and patient-reported versus clinician-reported origin.
3. Validate dimensional compatibility, component structure, declared scale bounds and source-specific restrictions. Blood pressure components are not a single scalar; a symptom score requires its named scale. Keep unsupported units or mappings quarantined rather than guessing.
4. Return structured rule IDs, severity, field paths and permitted next actions. Keep missing, unavailable, invalid and clinically abnormal separate. Integrate rules into staged ingestion with reproducible reports; a warning is not automatically a clinical contraindication.

Make the next right action easy
Display original and normalized units clearly, with plain-language review reasons. Preserve entered data and provide a supported unit or scale selection when repair is possible. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Use boundary and conversion fixtures, wrong dimensions, qualified/censored values, unknown instruments, negative impossible counts, missing values and abnormal-but-valid data. Verify exact conversion provenance and that absent results never become zero or normal. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-021 — Dataset-specific metadata adapters for approved cohorts

```text
Task: COS-021 — Dataset-specific metadata adapters for approved cohorts
Priority: P0 | Workstream: 03
Prerequisites: COS-016, COS-017, COS-018, COS-019, COS-020; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Clinical data engineering, breast imaging research and privacy.
Read: SPEC-003, SPEC-008/010; audit D01/D03; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Turn actual approved source metadata into canonical records through small, inspectable adapters.

Implement
1. Inspect the actual approved release files and data dictionary before implementing an adapter. Prioritize one available cohort that can supply a verified breast MRI and suitable mask. I-SPY, Duke or processed Breast DCE resources are candidates only when their actual release, rights and linkage are established; do not assume every cohort contains visits, labs, pathology and longitudinal imaging.
2. Define one adapter protocol: input manifest/version, supported entities, field mappings, time/identity rules, provenance, warnings, rejected records and deterministic output. Keep source-specific parsing outside canonical domain services. Use local approved inputs or explicitly authorized acquisition, not arbitrary remote fetching.
3. Preserve source column/row or document locators, accession mappings, annotation meaning, missingness, original codes and transformation versions. Associate processed datasets with their parent cohort so they cannot masquerade as independent patients.
4. Provide a minimal de-identified or wholly synthetic adapter fixture and a mapping report. Unsupported metadata remains unavailable; do not fabricate clinical follow-ups or derive pathology from filenames. Add further adapters only for approved inputs actually in scope.

Make the next right action easy
Offer a short source-to-import workflow with preview, unsupported fields and a concrete repair step. Show which requested capabilities this source can and cannot support. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Test deterministic import, missing columns, release/schema changes, corrupt rows, ambiguous identity, repeat imports and source-parent tracking. Compare mapped fields against the actual dictionary. If real data are unavailable, report the adapter as fixture-tested and real-data validation blocked. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-022 — Provenance lineage, versioning and source immutability

```text
Task: COS-022 — Provenance lineage, versioning and source immutability
Priority: P0 | Workstream: 03
Prerequisites: COS-016, COS-017, COS-018, COS-019, COS-021; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Data architecture, scientific reproducibility and privacy.
Read: SPEC-003/004, SPEC-008/010; audit A02/C02/D03; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Make every output explainable back to immutable inputs and a reproducible processing event.

Implement
1. Implement append-only source/artifact versions and processing-run lineage with parent IDs, content hashes, source release, parameters, code/config/environment versions and relevant model/checkpoint or random seed. Use private immutable object versions or equivalent write protection; hashes alone do not prevent overwrite.
2. Validate a lineage DAG: reject cycles, dangling parents and unauthorized cross-patient/project links. Define legitimate multi-input aggregates explicitly, retaining item-level origins rather than hiding mixed provenance behind one misleading label.
3. Enforce canonical origin rules: real-derived results require suitable real parents; every synthetic descendant remains SYNTHETIC_GENERATED, including measurements and meshes. Preserve INTERPOLATED/MODEL_PREDICTED distinctions when those capabilities are later enabled; processing is not evidence of clinical validity.
4. Append corrections, supersessions, retractions and rights-withdrawal events. Identify affected descendants, prevent prohibited new publication/export, and preserve authorized audit history under retention policy. Do not silently mutate snapshots or promise permanent retention against required deletion. Coordinate protected-map deletion and restricted audit tombstones with policy.

Make the next right action easy
Provide an authorized “View source and processing” path showing readable lineage, versions and restrictions. Explain why a derivative is blocked and which source/review needs attention. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Check cycle/cross-patient rejection, overwrite prevention, content tampering detection, synthetic-to-real relabel denial, revision history and withdrawal propagation. Rebuild one deterministic fixture output from its recorded manifest; do not equate that with independent scientific validation. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-023 — Data completeness assessment, quarantine and quality reports

```text
Task: COS-023 — Data completeness assessment, quarantine and quality reports
Priority: P0 | Workstream: 03
Prerequisites: COS-019, COS-020, COS-021, COS-022; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Clinical data quality, product usability and QA.
Read: SPEC-003/008/010/011; audit D01/D03; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Tell operators exactly which data are usable for each capability and how to resolve specific failures.

Implement
1. Define versioned, capability-specific completeness checks: clinical display, physical measurement, anatomical mesh, real temporal comparison and synthetic-baseline eligibility. Required fields must follow source/mask semantics; do not create a global patient “health” or “trust” score.
2. Record missing, unavailable, pending review, invalid, quarantined and usable states separately. Keep a failing artifact isolated when valid clinical records remain usable. Separate technical QC, scientific review, access eligibility and publication.
3. Implement quarantine reasons, ownership, remediation attempts and an audited revalidation path. Revalidation produces new evidence/version rather than editing accepted source records. Distinguish source correction from an operator-approved exception; neither may override non-negotiable integrity gates.
4. Expose authorized quality summary/detail reads and a deterministic report with denominator, rule version, failed fields/artifacts and dependent capabilities. Avoid sensitive source identifiers in general reports. Wire a small existing admin surface or documented CLI/API workflow; do not create a full new patient workspace.

Make the next right action easy
Lead with “Ready for measurement” or the precise blocking reason and next action. Show details on demand, preserve working records and avoid dead-end status-only screens. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Test missing versus zero, partial modality availability, quarantine scope, permission checks, repeated revalidation and stale reports after correction. Demonstrate one invalid mask cannot disable an otherwise valid clinical-only view and cannot be used for physical measurements. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-024 — Duplicate detection and patient-level train, validation and test partitioning

```text
Task: COS-024 — Duplicate detection and patient-level train, validation and test partitioning
Priority: P0 | Workstream: 03
Prerequisites: COS-017, COS-021, COS-022, COS-023; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Biostatistics, data engineering and scientific evaluation.
Read: SPEC-003/010/011; audit D05; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Prevent shared patients and their derivatives from contaminating held-out evaluation.

Implement
1. Implement original-patient grouping across source releases and known parent/processed cohorts. Use verified mappings as identity evidence; byte hashes flag duplicate artifacts but do not independently prove patient identity. Ambiguous overlap requires review and excludes affected held-out claims until resolved.
2. Produce a versioned, reproducible group-level split manifest with seed, grouping evidence, source versions, assignment and exclusions. Support train, validation, test, demo and unassigned roles explicitly; document whether demo cases overlap and exclude them from independent claims accordingly. Do not force a universal percentage split onto a tiny cohort.
3. Make every exam, lesion, note, augmentation and synthetic branch inherit the original patient group assignment. Fit learned preprocessing/normalization and tune thresholds on permitted training/validation data only. Freeze evaluation manifests before running reported test metrics.
4. On a later cross-split identity merge or duplicate discovery, record contamination, invalidate affected evaluation eligibility and require a new reviewed split/evaluation version. Never silently reassign historic runs or delete failure evidence.

Make the next right action easy
Show assignment, grouping basis and unresolved overlaps; provide a review queue and a clear explanation of why a case is ineligible for independent evaluation. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Assert zero group overlap on a frozen fixture, including processed-parent datasets, repeat visits and synthetic descendants. Test deterministic assignment, ambiguous matches, identity corrections and training-only fit access. Produce a leakage audit; fixture success is not a real-cohort leakage clearance. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-025 — DICOM and NIfTI ingestion with study and series association

```text
Task: COS-025 — DICOM and NIfTI ingestion with study and series association
Priority: P0 | Workstream: 04
Prerequisites: COS-016, COS-017, COS-021, COS-022, COS-023; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Medical imaging engineering, radiology informatics and security.
Read: SPEC-003/005/008/010; audit D01/D03; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Import authentic imaging into the correct patient, examination and sequence without guessing identity or exposing metadata.

Implement
1. Implement staged local/authorized upload ingestion for supported DICOM and NIfTI inputs. Record immutable byte hashes, source manifest, format, study/series association, acquisition metadata and patient linkage through the restricted mapping service. Reject ambiguous patient/study association.
2. Group DICOM instances by validated study/series and relevant frame/sequence dimensions. Sort slices by physical geometry, not filenames or InstanceNumber alone. Handle enhanced multiframe explicitly or reject it with a supported-format explanation. Detect mixed series, duplicate positions and unsupported compression.
3. For NIfTI, preserve affine/header metadata and require an approved association manifest when study/patient metadata are absent. Interpret 4D axes only from explicit sequence metadata; dynamic contrast phases are not longitudinal clinical visits.
4. Enforce file-size/decompression limits, archive path safety, private staging and strict parsing. Inspect metadata/de-identification evidence and flag possible burned-in identifiers for review before sharing. Do not claim tag stripping alone guarantees anonymization. Persist import reports; defer readiness to geometry and annotation QC.

Make the next right action easy
Show patient label, study, sequence and import progress before confirmation. Explain unsupported formats or uncertain association and preserve the validated upload for safe retry within policy. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Cover shuffled filenames, mixed series, corrupt/truncated files, archive traversal/bombs, ambiguous NIfTI association, multiframe policy and repeated upload. Verify private metadata never reaches normal logs or browser payloads and unreviewed inputs cannot publish. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-026 — Imaging geometry, orientation, spacing and physical-coordinate validation

```text
Task: COS-026 — Imaging geometry, orientation, spacing and physical-coordinate validation
Priority: P0 | Workstream: 04
Prerequisites: COS-025; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Imaging physics, numerical engineering and radiology QC.
Read: SPEC-005/008/011; audit D01/C06; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Establish trustworthy physical coordinates before any measurement, resampling or 3D rendering.

Implement
1. Implement a canonical imaging-geometry contract with shape, voxel-center convention, affine, declared physical units, coordinate frame, orientation, spacing and source transform metadata. Record explicit LPS/RAS conversions with direction; retain original geometry.
2. Validate finite/invertible transforms, positive supported spacings, unit certainty, slice consistency, duplicates, missing slices and irregular sampling. Handle irregular DICOM geometry through an explicit validated reconstruction policy or quarantine; do not pretend it is a regular grid.
3. Resolve NIfTI qform/sform disagreements through documented evidence/policy and visible review, not silent preference. Support oblique/anisotropic cases. Compute voxel volume from abs(det(affine[:3,:3])) in millimetres; do not assume a spacing product suffices for a sheared affine.
4. Expose geometry/QC reports and reusable index-to-world/world-to-index functions. A matching frame UID or array shape does not establish longitudinal alignment. Freeze bounded-fixture tolerances from SPEC-011 as engineering checks, not clinical accuracy limits.

Make the next right action easy
Show physical units, orientation and actionable blocking geometry errors. Operators should know whether to provide missing metadata, choose a verified transform or reject the source. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Use independently calculated cuboids with translation, rotation, anisotropy, reflection and obliquity; reject singular/nonfinite transforms and unknown units. Verify bounded coordinate round trips within 1e-5 mm and catch axis swaps, handedness reversal and double spacing. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-027 — MRI preprocessing, intensity normalization and sequence management

```text
Task: COS-027 — MRI preprocessing, intensity normalization and sequence management
Priority: P0 | Workstream: 04
Prerequisites: COS-024, COS-025, COS-026; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: MRI processing, reproducible ML engineering and radiology research.
Read: SPEC-003/005/011; audit D01/D05; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Produce reproducible MRI inputs while preserving acquisition meaning and original data.

Implement
1. Build a versioned preprocessing pipeline with supported sequence/channel identification, validated ordering, optional bias correction/normalization and explicit resampling parameters. Start with the minimal verified sequence needed by the imported-mask pathway; do not require a model or GPU.
2. Keep accepted source images immutable. Record each output transform, intensity method, fitted parameters, software/config version, input hashes and valid spatial frame. Reuse common geometry functions and lineage rather than hand-coded orientation changes.
3. Manage dynamic contrast phases using acquisition evidence. Require within-exam motion/alignment checks before operations that assume voxelwise phase correspondence. Unknown phases remain unknown. Intensity normalization is a numerical processing method, not a calibrated perfusion measurement or biological response estimate.
4. Avoid leakage: any cohort-fitted preprocessing learns only from the allowed training partition. Define behavior for all-zero/constant images, nonfinite values, absent channels and inconsistent scans. Do not fabricate missing sequences or make every acquisition look artificially comparable.

Make the next right action easy
Use sensible validated defaults and show selected sequences, preprocessing steps and reasons for blocked processing. Retain the source view and expose processing details on request. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Check deterministic hashes/tolerances in a pinned environment, no source mutation, preserved transforms, constant-image handling, phase misordering and missing channels. Verify held-out patients cannot enter fit operations and normalization is not presented as a clinical quantity. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-028 — Image and mask spatial alignment and resampling integrity

```text
Task: COS-028 — Image and mask spatial alignment and resampling integrity
Priority: P0 | Workstream: 04
Prerequisites: COS-026, COS-027; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Image registration mathematics, label integrity and QA.
Read: SPEC-005/008/011; audit D01/C06; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Align labels to an explicitly chosen image grid without silently changing their anatomical meaning.

Implement
1. Implement a reusable image/mask alignment service with source/target affine, shape, units, frame and transform direction. Require patient/study association evidence. Equal array dimensions do not establish alignment; large discrepancies must quarantine the pair.
2. Preserve original masks/images. If resampling is necessary, create a new version with an explicit target grid, transform, interpolation policy and lineage. Use nearest-neighbor or another explicitly justified label-preserving method for discrete masks; never apply ordinary intensity interpolation and round silently.
3. Check label sets, bounds, physical extents, overlap, component counts and before/after volume differences. Do not auto-resize a mask to make it fit. Treat resampling-related volume change as measured error with declared engineering tolerances, not guaranteed volume invariance.
4. Provide aligned preview assets and a report suitable for COS-029 annotation import and COS-031 QC. Implement against synthetic geometry fixtures now, so this task does not depend on the later importer. Reviewer acceptance remains separate from a numerical overlay score.

Make the next right action easy
Provide an overlay preview with source/target labels and a clear choice to accept a documented alignment or request corrected metadata. Never conceal an automatic geometry change. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Cover translated/rotated/flipped grids, anisotropy, label preservation, mismatched patients, partial out-of-bounds masks and identity transforms. Confirm raw masks remain unchanged and failed alignment cannot produce a measurement-ready artifact. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-029 — Reference segmentation mask import and annotation classification

```text
Task: COS-029 — Reference segmentation mask import and annotation classification
Priority: P0 | Workstream: 04
Prerequisites: COS-022, COS-025, COS-026, COS-028; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Breast radiology, annotation science and imaging data engineering.
Read: SPEC-003/005/008/010; audit D01; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Import masks with honest annotation meaning and explicit eligibility for anatomical measurements.

Implement
1. Import supported approved mask formats through canonical image/mask association and alignment services. Require source/version, patient/study, annotator or method when available, label dictionary, coordinate definition and source image linkage. Missing evidence stays explicitly unknown.
2. Classify annotations by meaning: reviewed anatomical tumor contour, model proposal, functional enhancement region, bounding box, approximate/illustrative geometry or unknown. Preserve human versus algorithmic authorship and review status separately. Define a capability matrix; a functional tumor volume or bounding box must not silently become anatomical tumor volume.
3. Map distinct lesion labels to stable annotation objects without collapsing every positive voxel into one lesion. Support multi-lesion selections explicitly and reject ambiguous label dictionaries. Keep accepted original masks immutable; aligned derivatives retain lineage.
4. Require technical QC and recorded scientific review evidence before enabling anatomical claims/publication. A coding agent cannot sign off as a radiologist. When review is unavailable, retain limited fixture/preview functionality and state the blocked gate. Imported masks are the P0 route; automated segmentation is not a dependency.

Make the next right action easy
Show annotation class, source, label/lesion selection and permitted uses before processing. Explain why a reference region supports only a restricted measurement. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Verify multi-label import, wrong-study masks, unknown authorship, invalid labels and alignment failure. Show that a functional region and bounding box cannot pass the anatomical eligibility guard, while a valid reviewed contour can proceed to technical QC. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-030 — Optional nnU-Net or MONAI automated tumor segmentation integration

```text
Task: COS-030 — Optional nnU-Net or MONAI automated tumor segmentation integration
Priority: P1 | Workstream: 04
Prerequisites: COS-029; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Medical segmentation research, ML operations and evaluation.
Read: SPEC-005/006/010/011; audit A06/D01/D05; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Add one optional segmentation adapter only when an eligible checkpoint and evaluation pathway exist.

Implement
1. Treat this as P1. Keep the verified imported-mask pathway fully usable with this feature disabled. Inspect actual checkpoint access, license, architecture, input sequence requirements, preprocessing, inference hardware and training-cohort overlap; do not assume a breast-specific validated model exists.
2. Implement one provider-neutral segmentation adapter for the selected nnU-Net or MONAI implementation, not both by default. Pin package/checkpoint hashes and reproducible inference settings; integrate existing geometry and lineage contracts. Never substitute a general language model or a generic segmentation demo for evaluated breast tumor segmentation.
3. Every result starts as a model proposal with model/checkpoint provenance and technical QC status. It cannot become a reviewed reference by self-approval. Enable real inference only after COS-031 evaluation and COS-032 job controls are available and the relevant review gates are recorded.
4. If weights/rights/data are missing, complete the adapter contract and isolated mock tests, document the exact dependency, and leave runtime inference disabled. Do not download unapproved weights, train on test patients or report fixture outputs as real model performance.

Make the next right action easy
Hide or clearly disable unsupported inference with a readable reason; offer approved mask import as the available next action. Show model version and proposal status when enabled. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Test the disabled path, unsupported channels, timeout/failure propagation, deterministic adapter fixtures, output affine/labels and checkpoint identity. When genuinely enabled, report patient-separated evaluation including all failed cases; no invented accuracy target or achieved metric. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-031 — Segmentation quality control and reference-mask evaluation

```text
Task: COS-031 — Segmentation quality control and reference-mask evaluation
Priority: P0 | Workstream: 04
Prerequisites: COS-026, COS-028, COS-029; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Imaging QA, biostatistics and annotation science.
Read: SPEC-005/010/011; audit D01/D05; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Separate technical mask validity from measured segmentation accuracy and independent review.

Implement
1. Implement mask QC for geometry, legal labels, finite data, unexpected extent, source association, disconnected components and annotation-specific eligibility. Define meaningful empty-mask handling: confirmed absence, missing annotation and failed processing are different conditions. Do not remove legitimate multifocal lesions automatically.
2. Implement evaluation against an independently suitable reference where one actually exists: Dice, a pinned symmetric HD95 definition in physical mm, absolute/relative volume error and detection/processing failures. Preserve metric implementation/version, spacing, case eligibility, denominator, empty-label handling and exclusions.
3. Never score an imported mask against itself and claim segmentation accuracy. Self-consistency can check transfer/alignment only. Avoid universal “clinically acceptable” Dice thresholds; keep technical gates separate from predeclared scientific acceptance. Zero-reference relative error is undefined, not zero.
4. Publish authorized per-case QC/evaluation reports with review status and all attempts/failures. This P0 task works for imported references without COS-030. Model evaluation attaches later through the same interface; missing independent references block accuracy claims, not honest imported-mask processing.

Make the next right action easy
Show “Technical checks passed”, “Needs review” and “Independent accuracy not evaluated” distinctly. Link a failing check to its overlay/source and next repair step. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Use known overlap/distance fixtures with anisotropic spacing, both-empty/one-empty masks, malformed geometry and missing reference. Confirm failed attempts remain in counts, NaN cannot pass a gate and self-comparison is excluded from claimed model accuracy. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-032 — Imaging processing jobs, artifact storage and failure recovery

```text
Task: COS-032 — Imaging processing jobs, artifact storage and failure recovery
Priority: P0 | Workstream: 04
Prerequisites: COS-025, COS-026, COS-027, COS-028, COS-029, COS-031; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Distributed job reliability, storage security and imaging engineering.
Read: SPEC-007/008/010/011; Phase 1 COS-012/013; audit A03/C02/C05; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Run imaging pipelines reliably with durable outputs, transparent progress and safe retries.

Implement
1. Integrate the actual ingestion/QC/preprocessing operations into the existing CPU-worker/job system. Capture an immutable input manifest at enqueue, authorized patient/project, data revision, source/config hashes and processing version. Do not reconstruct an old job from current heads.
2. Use a transactional outbox, leases/heartbeats, bounded time/memory/concurrency, cancellation, retry classification and idempotent stage commits. Reject stale lease results and duplicate finalization. Processing progress must reflect completed stages; do not invent percentages.
3. Stage artifacts privately, validate bytes/checksums/QC, then finalize references in a guarded database transaction. Object storage and SQL are not one atomic transaction: define crash recovery and safe orphan cleanup that never deletes referenced assets. Issue short-lived authorized asset grants without logging secrets.
4. Separate job success, artifact readiness, review and publication. A successful worker cannot publish automatically. Implement explicit authorized idempotent publication and rollback-safe failure states under the existing contract. Provide structured errors and retain safe diagnostic evidence.

Make the next right action easy
Display queued/running/validating/ready/failed/cancelled with the current stage, repair guidance and only safe retry/cancel actions. Avoid repeated imports when a job is still running. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Inject worker death, lease expiry, duplicate delivery, queue outage, object/SQL failure, cancellation and stale completion. Verify no double publication, no partial public artifact, revision-pinned replay and cross-project asset denial. Measure an actual small CPU fixture run and record its resource use. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-033 — Physical tumor measurements and volume calculation engine

```text
Task: COS-033 — Physical tumor measurements and volume calculation engine
Priority: P0 | Workstream: 05
Prerequisites: COS-026, COS-029, COS-031, COS-032; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Measurement science, imaging geometry and scientific reporting.
Read: SPEC-005/008/011; audit D01/C06; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Calculate reproducible physical quantities from eligible masks without overstating clinical meaning.

Implement
1. Implement explicit lesion-label selection and anatomical/functional measurement types. Compute voxel volume using abs(det(A3x3)) after validated millimetre conversion; mask volume is selected voxel count times voxel volume. Convert mm3 to cm3 by dividing by 1000 and preserve full precision in canonical decimal-string outputs.
2. Provide world-coordinate centroid, physical bounds and only clearly defined supported diameter/extent measures. Name a bounding-box extent as such; do not label it RECIST diameter or infer treatment response, stage, subtype or prognosis. Preserve method/config version, mask hash, units and eligibility evidence.
3. Distinguish unavailable, invalid and confirmed absent tumor. Do not turn a missing mask into zero volume. Handle multifocal selections and zero denominators explicitly. Record measurement uncertainty only when supported; unknown uncertainty remains unknown.
4. Store immutable measurement records linked to input revision and mask version. Keep display rounding separate from calculation. Use source mask measurements as authoritative even when later meshes are simplified. Provide authorized reads with origin and measurement definition.

Make the next right action easy
Show units, lesion selection, source date/time basis and a readable measurement definition. Explain why a quantity is unavailable rather than showing a misleading zero. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Use an independent calculation for cuboids, anisotropic/oblique/reflected affines and multi-label masks. Meet SPEC-011 fixture arithmetic tolerance max(1e-6 mm3, 1e-9 times expected volume); test unit conversion, zero denominator and missing-mask rejection. Keep these engineering checks separate from clinical accuracy. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-034 — Segmentation-to-3D-mesh reconstruction pipeline

```text
Task: COS-034 — Segmentation-to-3D-mesh reconstruction pipeline
Priority: P0 | Workstream: 05
Prerequisites: COS-028, COS-032, COS-033; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Scientific visualization, computational geometry and imaging physics.
Read: SPEC-005/008/009/011; audit D01; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Create a tumor mesh whose position, scale and origin remain tied to the source mask.

Implement
1. Implement a CPU reconstruction pipeline from eligible selected mask labels, using a pinned algorithm such as marching cubes. Document the voxel-center/surface convention and boundary padding. Keep distinct lesions separate or encode explicit object membership; no silent merging.
2. Apply the validated index-to-world affine exactly once. Handle reflections, winding and normals explicitly. Preserve patient-space frame and an invertible display transform. If GLB uses metres, document/apply the millimetre-to-metre factor of 0.001 exactly once; do not normalize each tumor independently and destroy size comparisons.
3. Store immutable original reconstruction, format/unit metadata, bounding box, counts, mask hash, algorithm/config version and private artifact references. Make reconstruction idempotent through the shared job pipeline. Retain canonical mask measurements rather than substituting mesh volume.
4. Reject corrupt/unsupported masks with clear reasons. A box or illustrative surrogate may appear only as explicitly labeled illustrative geometry, never a reconstructed anatomical tumor. Output should be consumable by the later authorized viewer without exposing private source paths.

Make the next right action easy
Expose reconstruction progress and distinguish a validated reconstruction from a preview or illustrative shape. A failed mesh must leave the original mask and valid measurements accessible. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Check known-size cuboids, translations, anisotropy, negative determinant/winding, empty labels and boundary-touching masks. Verify world bounds and display round trips, detect double scaling and prove source mask measurements remain unchanged by mesh reconstruction. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-035 — Mesh quality validation, simplification and coordinate preservation

```text
Task: COS-035 — Mesh quality validation, simplification and coordinate preservation
Priority: P0 | Workstream: 05
Prerequisites: COS-034; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Computational geometry, frontend performance and scientific QA.
Read: SPEC-005/009/011; audit D06/C06; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Produce efficient display meshes without hiding geometry distortion or invalid scale.

Implement
1. Validate finite vertices, index ranges, degeneracy, orientation, component identity and supported topology. Check watertightness before any mesh-volume claim and define how self-intersection checks are performed and limited. Do not delete small components merely because they look inconvenient.
2. Implement bounded simplification/optional smoothing with versioned parameters and separate immutable LOD artifacts. Preserve world transforms, lesion identities, original mesh and mask. Record vertex/triangle reduction, surface displacement, bounds and mask-to-mesh volume differences where computable.
3. Freeze engineering display tolerances before evaluation. If a requested size budget violates integrity, retain the higher-detail mesh or fail the simplification with guidance; do not silently distort it. Treat payload size/performance targets as measured targets, not guarantees.
4. Provide lightweight preview metadata and a validated LOD selection policy for the existing frontend. Measure an actual fixture on available hardware and identify representative-data/target-laptop checks still missing. Source mask measurements remain authoritative across all LODs.

Make the next right action easy
Choose the simplest validated display automatically; show loading and a recoverable error with a retry/higher-detail option. Place technical mesh diagnostics in a details panel, keeping origin and units visible. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Compare original/LOD bounds, centroid, physical units and displacement against frozen tolerances. Cover invalid indices, degenerate triangles, nonmanifold/open meshes and multiple legitimate components. Record payload bytes, memory and load timing without presenting fixture benchmarks as full real-data performance. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-036 — Breast-region anatomical context and illustrative geometry labeling

```text
Task: COS-036 — Breast-region anatomical context and illustrative geometry labeling
Priority: P0 | Workstream: 05
Prerequisites: COS-034, COS-035; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: 3D UX, breast imaging science and accessibility.
Read: SPEC-005/009/010; Phase 1 COS-011; audit D01/D03/D06; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Make the tumor understandable and rotatable without manufacturing patient-specific anatomy.

Implement
1. Add approved breast-region context only when source segmentation or other eligible evidence exists. Label patient-derived versus illustrative context at layer/object level. Generic anatomy must be unmistakably illustrative and cannot support patient-specific distance, invasion or surgical conclusions. If context would mislead, omit it with a clear explanation.
2. Implement a minimal reusable authorized mesh preview in the existing frontend if none exists: rotate, pan, zoom, reset/fit, lesion selection and context visibility controls. Fetch validated assets through canonical authenticated reads/grants; preserve physical scale, orientation and stable camera conventions. Do not build the full future clinical workspace.
3. Keep tumor origin, annotation class, units and actual observation/relative time visible. Provide keyboard-operable controls, readable focus states, text equivalents and non-color-only distinctions. Show loading, empty, blocked and recoverable-error states with a useful next action.
4. Keep context transforms separate and traceable. Do not alter tumor geometry to fit generic anatomy. Avoid asserting right/left orientation when evidence is missing. Confirm whether public-demo rights cover both tumor assets and context assets.

Make the next right action easy
Default to a clear tumor view with a short control hint and Reset view button. Explain illustrative context in the viewport, not only in a hidden disclaimer; keep advanced diagnostics optional. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Verify authorized/private asset access, unit/scale preservation, layer labels, reset behavior, keyboard actions and missing-context fallback. Record an actual interaction smoke test on fixture meshes; do not claim it proves clinical anatomical accuracy. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-037 — Real longitudinal study alignment and registration quality checks

```text
Task: COS-037 — Real longitudinal study alignment and registration quality checks
Priority: P0 | Workstream: 05
Prerequisites: COS-025, COS-026, COS-027, COS-028, COS-031, COS-032; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Longitudinal imaging research, registration science and radiology QC.
Read: SPEC-005/010/011; audit D02; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Support truthful spatial comparison between two genuine examinations while retaining their original measurements.

Implement
1. Verify two distinct real examinations for the same reviewed patient identity, valid time relation and suitable sequence/anatomical correspondence. Contrast phases from one exam do not qualify. If no genuine pair exists, implement fixture-tested infrastructure and record D02 as blocked.
2. Implement an explicit moving-to-fixed registration protocol, beginning with an appropriate validated rigid method. Add deformable registration only under a separately evaluated protocol. Record transforms/inverses, input hashes, reference frame, algorithm/config, interpolation and quality evidence. A shared frame UID alone is insufficient.
3. Combine numerical checks with anatomical overlay/landmark review; an optimizer score is not scientific acceptance. Reject singular/implausible mappings and quantify round-trip/bounds errors. Preserve original source images, masks and measurements; create aligned display derivatives with label-safe interpolation.
4. Failed registration blocks spatial overlay/location claims. It need not block comparison of independently valid scalar volumes when lesion identity and measurement definitions are comparable. Never imply observed change proves treatment causation.

Make the next right action easy
Show actual examination times and alignment status. Offer side-by-side original views when overlay is unavailable and explain exactly what review or metadata is needed. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Use known-transform fixtures, failed/inverted transforms, different patients, same-exam phases and low-quality alignment. Verify original volumes remain intact. Real-pair acceptance requires recorded anatomical review; fixture registration cannot close the genuine longitudinal gate. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-038 — Lesion identity matching and temporal measurement tracking

```text
Task: COS-038 — Lesion identity matching and temporal measurement tracking
Priority: P0 | Workstream: 05
Prerequisites: COS-017, COS-022, COS-033, COS-037; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Breast oncology research, longitudinal data modeling and UX.
Read: SPEC-005/008/009/010; audit D02/C04; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Track the same lesion over time without forcing uncertain matches or incomparable measurements.

Implement
1. Implement stable patient-scoped lesion identities and append-only examination-to-lesion associations with source/reviewer evidence, status and version. Distinguish annotation label ID from lesion identity. Capture candidate matches, unresolved cases and split/merge relationships explicitly.
2. Use geometry/registration as supporting evidence, never an automatic nearest-centroid proof of identity. Require appropriate review for ambiguous or multifocal cases. Correcting a match appends history and invalidates affected comparisons without rewriting published snapshots.
3. Build ordered measurement series from explicit source time and comparable definitions. Preserve per-point study/mask/method/units/provenance. Do not merge functional enhancement volume, anatomical mask volume and bounding-box extents into one trajectory. No silent carry-forward or artificial dates.
4. Compute absolute/percentage changes only for eligible matched quantities; zero baselines and missing values remain explicit. Keep authentic and simulated series distinct. Do not automatically assign RECIST response or clinical progression from these research measurements.

Make the next right action easy
Show matched/unresolved lesions, real observation markers and gaps. Explain why two points cannot be compared and offer source review or lesion mapping as the next action; retain a readable table alongside any chart. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Cover ambiguous matches, multifocal labels, split/merge events, same-day ties, zero baseline, missing visits, incompatible definitions and corrected identity. Ensure simulated descendants never appear as observed evidence and registration failure does not suppress otherwise valid comparable scalar values. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-039 — Time-indexed digital twin state persistence and immutable history

```text
Task: COS-039 — Time-indexed digital twin state persistence and immutable history
Priority: P0 | Workstream: 05
Prerequisites: COS-018, COS-019, COS-022, COS-024, COS-032, COS-033, COS-038; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Database/API architecture, temporal data integrity and product UX.
Read: SPEC-004/005/008/009/010; audit C01-C04/A03; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Persist reproducible time states that show exactly which evidence was available without rewriting history.

Implement
1. Implement versioned state assembly from immutable source members under the adopted C04 policy. Persist patient/origin/time, OBSERVED or SYNTHETIC context, input IDs/hash, data revision, assembly-policy version, measurement/asset membership and missing/conflict reasons. Do not infer current values from historical images or silently carry observations forward.
2. Implement durable revision-pinned reconstruction and stable cursor semantics. Rebuilding revision N after N+1 correction must use its original membership/manifest, not current database heads. Preserve actual source times and label historical-context members separately from current evidence.
3. Separate build job, readiness, review and explicit authorized publication. Published snapshots are immutable; corrections/retractions append new versions and eligibility events. Keep branches pinned to their original baseline hash; never silently rebase them. Concurrent publication must be guarded and idempotent.
4. Implement canonical state/timeline/detail reads and only required contract additions via the established change process. Generate clients/examples together. Reuse valid artifacts for lab-only changes; avoid unnecessary mesh jobs. Surface eligibility, available actions, source links and provenance for the frontend.

Make the next right action easy
A timeline selection must show the exact state, observation date/time basis and current versus historical members. Make “not available at this visit” explicit; keep corrections discoverable without making old states silently change. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Verify relative day-zero without cycles, lab-only states, same-day conflicts, late records, N/N+1 rebuilds, stable pagination, concurrent publication and unauthorized writes. Check published hashes and branch baselines remain stable after source correction; withdrawal can restrict access without falsifying retained history. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

### COS-040 — Synthetic follow-up mask and mesh geometry generation

```text
Task: COS-040 — Synthetic follow-up mask and mesh geometry generation
Priority: P0 | Workstream: 05
Prerequisites: COS-029, COS-031, COS-032, COS-033, COS-034, COS-035, COS-039; inherited Phase 1 governance/security/contracts apply throughout.
Expert perspectives: Simulation engineering, scientific geometry and safety UX.
Read: SPEC-004/005/008/010/011; audit A02/A03/C06; relevant repository code/contracts and prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, applying the COS-000 expert-team persona and repository AGENTS.md. Use the named expert perspectives below with top-tier engineering rigor; do not claim company affiliation, clinical credentials, human review or independent validation. Use actual tools if available. If working alone, label review as self-review. Do not assume subagents or special Muse Spark tool capabilities.

Execute this task in the existing repository; do not merely describe a plan. First inspect applicable instructions, source documents, audit adoption/decisions, contract ownership, prerequisite evidence and current implementation. Keep the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse modules and generated contracts; do not rewrite the twelve specifications.

Implement the smallest complete usable workflow, including migrations, authorization, typed contracts, processing, error states and meaningful tests where required. Preserve source provenance, unknown values, original units/time and immutable history. APIs stay under /api/v1/projects/{project_id}, except documented health/identity exceptions. Add missing contracts through the established decision process before dependent code. No unapproved external data/model exports or paid jobs. Keep engineering fixtures conspicuously synthetic.

Proceed with reversible authorized work. When a genuine prerequisite is missing, complete independent work, keep the affected capability disabled and record the exact missing evidence/owner; never turn a blocked gate into a passing test. Prioritize correctness and safe action, then ease of understanding/use, then polish. Avoid speculative abstractions and additional infrastructure.

Outcome
Generate measurable simulated geometry from an eligible baseline without presenting simulation as observed disease or a validated forecast.

Implement
1. Implement the geometry component behind a typed versioned input: eligible baseline mask/hash, branch/run identity, target relative time, explicitly named target metric/quantity, shape-operation version/config and seed. Consume an authorized simulation run; do not invent a clinical trajectory generator or treatment-response coefficients in this task.
2. For a volume-driven baseline operation, use a documented physical-space transform such as isotropic scaling by the cube root of target/baseline volume. Apply correct world-space center/affine handling, label preservation and bounds checks. Distinguish a configured simulated zero-volume endpoint from missing geometry; do not infer cure or surgery.
3. Measure the realized output mask through COS-033, then reconstruct/QC meshes through COS-034/035. Store target, realized volume, tolerance and operation lineage. Require nonzero targets to meet max(one output voxel volume, 1 percent of target), unless the frozen configuration is stricter. Fail or transparently reject unachievable targets; never display target values as measured values.
4. All output descendants remain SYNTHETIC_GENERATED. Persist ready branch-state outputs through COS-039, pinned to the observed baseline and relative timeline origin; require separate publication. Do not create fake real study IDs/dates. Engineering fixtures may mock authorized runs only in isolated test configuration.

Make the next right action easy
Display persistent “Simulated” labels on viewport, timeline and quantities. Show observed baseline, target and realized size distinctly, with actionable bounds/tolerance failures. Do not claim containment in breast tissue without eligible anatomical evidence. For backend-only work, implement the typed status/action/error contract and a usable CLI/API example; do not claim a complete frontend exists. Never expose a disabled or placeholder action as working functionality.

Acceptance checks
Cover growth/shrinkage, anisotropy, reflection, deterministic seed/config, tiny/zero targets, clipped geometry, invalid baselines and failed tolerance. Assert synthetic provenance survives measurement/mesh/state processing and cannot enter observed evaluation. Record missing simulation-run integration as blocked; this task alone does not complete all five scenario families. Test relevant authorization boundaries and happy/error paths against the implemented behavior. Keep test tolerances versioned; they are not clinical thresholds.

Required completion evidence
- Deliver working code and applicable migrations/generated schemas/clients, focused tests and a short runbook with actual commands and expected outcomes. Keep secrets and patient identifiers out of examples.
- Run the relevant checks, report actual results and failures, and distinguish engineering-fixture verification, real-data validation and specialist review. Skipped mandatory checks are not passes; do not invent metrics.
- Update the traceability matrix, task ledger, contract decisions and release-gate evidence. Record changes, commands/results, known limits and the single next recommended action. Mark complete only for the scope actually verified.
- Final response: implemented behavior; files/contracts changed; checks run; remaining dependency or risk. Keep this concise. Provide decision rationale and evidence, not hidden internal reasoning.
```

