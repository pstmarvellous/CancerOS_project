# CancerOS Phase 4 — AI Evidence and Interaction

Version 1.0 | 23 October 2026 | 15 separate implementation prompts | All P0

Use one numbered prompt at a time in the CancerOS repository. Copy that task's fenced text into the coding-agent session; retain COS-000, AGENTS.md, the ledger and adopted contract decisions. Each prompt includes a role, prerequisites, concrete outcome, numbered implementation steps, usability guidance, acceptance checks and completion evidence. This continues the Muse Spark-oriented prompt structure without claiming benchmarked model performance. The named expert perspectives support self-review; they do not establish real clinical credentials or independent approval.

## Authoritative baseline and prerequisites

Use the twelve drafted specifications (PRD-001, SPEC-003 through SPEC-012, COS-RA-001), COS-AUD-001 baseline 1.0 and actual Phase 1–3 implementation/evidence. Verify whether the audit overlay was adopted; do not manufacture approval or treat drafted prompts as completed code. PRD defines intent, SPEC-007 architecture, SPEC-008 plus adopted audit contracts, SPEC-003/004/005 scientific meaning, and SPEC-010/011 safety/evaluation. SPEC-006/009 obey those boundaries; roadmap/literature does not silently expand scope.

The existing sources remain unchanged. Workstream 08 adds bounded NLP, relational knowledge, curated retrieval and grounded explanation. Workstream 09 audits/completes the canonical HTTP layer over those existing services. Earlier phases already require routes/security for their usable slices; COS-066–071 must close gaps and conformance, not recreate domain logic or introduce a second endpoint catalog. Inventory COS057–COS065 is normalized to COS-057–COS-065.

## Execution sequence and safety handoffs

Run COS-057–COS-071 in order by default. No task depends on P1 automated segmentation or the COS-056 temporal neural experiment. Runtime forecast/interpolation remain gated and cannot become enabled through interpretation wording.

| Handoff | Contract and boundary |
| --- | --- |
| COS-057 provider boundary | Implement adapter, capability discovery, strict parsing and denied-by-default egress. A runtime Meta account/model/API is verified separately; coding-agent access is not proof. |
| COS-058 extracted facts | Exact note version/spans, negation, certainty and time remain attached. Extracted assertions do not overwrite canonical observations or unlock treatment compatibility automatically. |
| COS-059–061 knowledge/evidence | PostgreSQL relationships and a small approved corpus are sufficient. Citation existence, relevance and meaningful support are different checks. |
| COS-062 context | Immutable snapshot-bound facts, deterministic calculations, missingness and permitted evidence. Local context and externally exportable payload are distinct. |
| COS-063 generation → COS-064 gate | Earlier generation runs use a fail-closed validator interface. Candidates remain private until grounding/safety validation is implemented and passed; this forward enablement gate is not a circular coding prerequisite. |
| COS-065 persistence/fallback | Exact-context reuse, auditable model identity and truthful saved/rule-based labels. Recheck current permissions/eligibility on every cache hit. |
| COS-066–070 APIs | Finish the adopted routes and generated clients; reuse services. Add only formally recorded missing contracts, including C01 discovery/evaluation reads. |
| COS-071 conformance | End-to-end verification and gap closure. Protection, ownership checks and request validation are required in every task before this final check. |

The live provider path may remain blocked under D04. P0 still requires an executable adapter contract, deterministic summaries, fixture-supported source-span extraction, retrieval/grounding and honest capability/error behavior. A disallowed explicit external request returns 403 EXTERNAL_PROCESSING_NOT_ALLOWED, with no transmission. Provider outages may use a permitted labeled fallback; policy refusals are not hidden as outages. If event rules require a specific live provider, that separate unverified event dependency remains open.

## Non-negotiable scientific and privacy behavior

- Valid JSON is a formatting check. A resolvable citation is a reference check. Neither establishes factual support or clinical suitability. General literature cannot establish a missing patient-specific finding.
- Preserve immutable observed baseline/source records and generated branch/run identity. Synthetic descendants stay synthetic; extracted real-note facts are derived assertions. Never mix a latest lab with a historical scan and describe both as a new visit.
- Do arithmetic outside the LLM. Preserve quantity/unit, qualifiers, exact times, source references, missing/conflicting evidence and known limitations. No invented confidence percentage or calibrated prediction interval.
- Do not publish unsupported diagnoses/staging, resistance, treatment rankings/doses/prescriptions, survival probabilities, causal toxicity or formal response grades. Attributed historical clinician statements remain historical evidence, not new CancerOS recommendations.
- Notes, papers, metadata and generated output are untrusted data. They cannot grant permissions, execute tools/code/SQL, request arbitrary URLs or export records. Restricted context, source maps, private storage keys and signed grants never become public model/UI content.
- Prefer bounded templates and reviewed claim structures for the public demonstration. Novel prose without a proven validation/review path stays private. Escape rendered text and use persisted safe source references for navigation.

## Canonical HTTP behavior to preserve

All project routes use /api/v1/projects/{project_id}; /api/v1/me and documented health routes are explicit exceptions. Use the adopted C01–C04 decisions for missing reads, durable revisions, independent time origins and exact snapshot assembly. No parallel legacy /api/ai, /api/imaging or /cases catalogs.

SPEC-008 controls strict requests, decimal-string quantities, typed time, signed snapshot cursors, safe errors and no-store private responses. Mutations use scoped Idempotency-Key; mutable aggregates also use strong If-Match. Recheck authorization before replay. Valid replay returns the original committed result before stale-precondition handling. Missing precondition is 428; mismatch 412; conflicting key reuse 409. Async 202 with Location/Retry-After signals acceptance only. Nested IDs require independent ownership checks, including citations, validation reports and asset IDs.

Defaults remain the documented configurable prototype limits: 1 MiB request bodies, 100 atomic observation entries, list default 25/max 100, 512 MiB upload objects, 120-second asset grants and seven-day idempotency retention. These are operational defaults, not clinical/legal claims. Viewer/judge access does not automatically include original DICOM, notes or linkage. Already issued signed URLs may survive until expiry; claim immediate revocation only when the chosen delivery mechanism provides it.

## Verification and usability priorities

Keep workflows readable, preserve drafts on error and name the next valid action. Display origin, source/time, execution mode and freshness. Backend services expose typed capability/status/error information; the thin interpretation panel reuses existing state/timeline views. Avoid technical abbreviations, inert buttons and forced provider setup for basic deterministic functionality.

Freeze the initial SPEC-011 language suite with at least sixty reviewed cases: twenty grounded, twenty missing/conflicting/temporal/negation and twenty adversarial/prohibited-claim cases. Use a separate development set; freeze model/prompt/corpus/decoding settings before final scoring. Three external runs per case are an initial target when genuinely enabled; retain every output/failure. Disclose absent reviewers or unavailable live access rather than claiming the gate passed.

Report extraction precision/recall, negation/time/span fidelity; retrieval relevance/precision at k and citation support; claim-level and case-level unsupported rates; abstention/coverage; latency, failures and cost per accepted output. Finite-suite release gates require 100% numeric/unit/origin correctness for published outputs, zero published critical prohibited claims and correct abstention on every predefined critical insufficient-evidence case. Similarity or an LLM judge alone is not a scientific reference. A model failure can leave deterministic functionality available, but mandatory grounding/privacy gates cannot be waived.

## Phase completion evidence

1. A runnable source-span extraction → relational/source linking → curated retrieval → immutable context → validated interpretation → exact-state persisted result workflow, with truthful fixture/live/real-data labels.
2. Actual challenge-suite results, source/corpus rights evidence, egress denial tests and clear provider/model/export-policy status. Unknown provider behavior keeps export disabled.
3. Generated canonical API/client artifacts and real persistence/worker/private-object integration tests for patient, imaging, simulation, state/comparison and AI/evidence flows.
4. Role/ownership, expiry, replay/concurrency, recovery, snapshot/cache isolation and stale-selection evidence. No published private candidate or cross-patient citation leak.
5. An updated traceability/ledger and concise Phase 4 evidence report: implemented, fixture-verified, live-verified, review-pending and blocked. Release, clinical suitability and organizer requirements remain separately evidenced decisions.

## Prompt index

| ID | Priority | Workstream | Prompt | Task-specific prerequisites |
| --- | --- | --- | --- | --- |
| COS-057 | P0 | 08 | [Meta Model API integration, provider adapter and structured output validation](#cos-057--meta-model-api-integration-provider-adapter-and-structured-output-validation) | COS-005, COS-008, COS-010, COS-014, COS-018, COS-022, COS-032, COS-053 |
| COS-058 | P0 | 08 | [Clinical note fact extraction, negation and temporal expression handling](#cos-058--clinical-note-fact-extraction-negation-and-temporal-expression-handling) | COS-018, COS-020, COS-022, COS-024, COS-057 |
| COS-059 | P0 | 08 | [Clinical concept and source-linked knowledge relationship model](#cos-059--clinical-concept-and-source-linked-knowledge-relationship-model) | COS-018, COS-022, COS-038, COS-053, COS-058 |
| COS-060 | P0 | 08 | [Curated research evidence ingestion, licensing and versioned indexing](#cos-060--curated-research-evidence-ingestion-licensing-and-versioned-indexing) | COS-016, COS-018, COS-022, COS-059 |
| COS-061 | P0 | 08 | [Evidence retrieval, relevance filtering and citation verification](#cos-061--evidence-retrieval-relevance-filtering-and-citation-verification) | COS-059, COS-060 |
| COS-062 | P0 | 08 | [Structured research interpretation context builder](#cos-062--structured-research-interpretation-context-builder) | COS-022, COS-039, COS-051, COS-052, COS-053, COS-054, COS-057, COS-058, COS-059, COS-061 |
| COS-063 | P0 | 08 | [Evidence-linked AI interpretation and explanatory output generation](#cos-063--evidence-linked-ai-interpretation-and-explanatory-output-generation) | COS-052, COS-053, COS-057, COS-058, COS-061, COS-062 |
| COS-064 | P0 | 08 | [Hallucination checks, numerical grounding, prohibited claims and abstention](#cos-064--hallucination-checks-numerical-grounding-prohibited-claims-and-abstention) | COS-005, COS-007, COS-057, COS-058, COS-061, COS-062, COS-063 |
| COS-065 | P0 | 08 | [AI result persistence, model audit, cache and outage fallback](#cos-065--ai-result-persistence-model-audit-cache-and-outage-fallback) | COS-022, COS-032, COS-039, COS-054, COS-057, COS-062, COS-063, COS-064 |
| COS-066 | P0 | 09 | [Patient, diagnosis and observation API implementation](#cos-066--patient-diagnosis-and-observation-api-implementation) | COS-008, COS-017, COS-018, COS-019, COS-020, COS-023, COS-039, COS-054 |
| COS-067 | P0 | 09 | [Imaging, segmentation and geometry API implementation](#cos-067--imaging-segmentation-and-geometry-api-implementation) | COS-025, COS-026, COS-028, COS-029, COS-031, COS-032, COS-033, COS-034, COS-035, COS-036, COS-066 |
| COS-068 | P0 | 09 | [Simulation creation, branch management and status APIs](#cos-068--simulation-creation-branch-management-and-status-apis) | COS-041, COS-042, COS-049, COS-050, COS-065, COS-066 |
| COS-069 | P0 | 09 | [Digital twin state, timeline and comparison APIs](#cos-069--digital-twin-state-timeline-and-comparison-apis) | COS-039, COS-051, COS-052, COS-053, COS-054, COS-066, COS-067, COS-068 |
| COS-070 | P0 | 09 | [AI interpretation, evidence and evaluation APIs](#cos-070--ai-interpretation-evidence-and-evaluation-apis) | COS-057, COS-058, COS-059, COS-060, COS-061, COS-062, COS-063, COS-064, COS-065, COS-069 |
| COS-071 | P0 | 09 | [Authentication, authorization, request validation and API contract testing](#cos-071--authentication-authorization-request-validation-and-api-contract-testing) | COS-008, COS-014, COS-015, COS-057, COS-064, COS-065, COS-066, COS-067, COS-068, COS-069, COS-070 |

## Separate copyable prompts

### COS-057 — Meta Model API integration, provider adapter and structured output validation

```text
Task: COS-057 — Meta Model API integration, provider adapter and structured output validation
Priority: P0 | Workstream: 08
Prerequisites: COS-005, COS-008, COS-010, COS-014, COS-018, COS-022, COS-032, COS-053; inherited Phase 1–3 governance/security/contracts apply.
Expert perspectives: LLM platform engineering, privacy/security, API architecture and scientific safety.
Read: SPEC-006 sections 6, 12–16; SPEC-008 inference contracts; SPEC-010 SAFE-19–21; audit A04/D04; relevant repository code/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approval you do not have. If working alone, label the review as self-review; do not assume subagents or special Muse Spark tools.

Execute this single task in the existing repository. Inspect instructions, relevant specifications, COS-AUD-001 adoption/decisions, current code/contracts and actual prerequisite evidence first. Preserve the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse existing services and the canonical /api/v1/projects/{project_id} API, with documented health/identity exceptions. Add missing contracts through versioned decisions and regenerate OpenAPI/clients/examples together; do not rewrite twelve source documents or create competing routes.

Prioritize correct working behavior, clear choices, easy next actions and complete error/recovery paths. Preserve exact patient/branch/time context, unknown values, units and immutable source/history. Keep OBSERVED/SYNTHETIC context separate from item provenance, review, availability and publication; synthetic descendants remain SYNTHETIC_GENERATED. Authorization and safe validation apply now, not only at COS-071. No unrestricted SQL/tools, unapproved data exports or paid compute.

Proceed with authorized reversible implementation. When actual provider/data/review evidence is missing, complete independent code and conspicuously synthetic fixture checks, disable the affected capability and record the exact dependency/owner. Never invent model capabilities, source rights, clinical claims or evaluation results. Use typed statuses/errors/actions and runnable examples for backend tasks; build only the requested thin integration into existing screens. Do not expose placeholders as functioning controls.

Outcome
Build a real provider-adapter boundary and honest local execution path without assuming Meta access or authorizing patient export.

Implement
1. Inspect the actual account, environment and approved provider/model policy. Check current official provider documentation before selecting an endpoint, SDK, model ID, authentication or structured-output/tool capability. Record what was verified and what remains unavailable; Muse Spark coding-agent use does not prove runtime API access. Keep provider/model identifiers externally configured. Never fabricate a supported URL, entitlement, immutable model revision or zero-retention guarantee.
2. Implement a provider-neutral interface for extraction/interpretation with typed requests, bounded responses, capability discovery, cancellation/timeouts, retryable versus permanent failures, rate/cost budgets and usage metadata. Keep credentials server-side. Add one Meta adapter only to the extent actual documentation/access supports it; no speculative vendor zoo or direct browser-to-provider calls.
3. Implement the denied-by-default egress gateway: versioned field/data-class allowlist, source rights, purpose, provider/account/region and verified retention/training policy. Recheck immediately before every transmission, including retries/tool calls. Exclude raw DICOM, protected identity mappings, signed URLs and unrestricted notes. Authorized note extraction needs its own approved narrow payload; an environment flag is not export-policy approval.
4. Use native schema constraints when supported and strict server-side parsing regardless. Reject extra fields, oversized/truncated responses, wrong references and nonfinite values. Valid JSON does not prove grounding. Establish a fail-closed output-validation interface now; external candidates stay private until the complete COS-064 gate is implemented and passed. No raw token stream reaches users before validation.
5. Supply deterministic execution and isolated provider mocks, labeled accurately. An explicit disallowed external request returns 403 EXTERNAL_PROCESSING_NOT_ALLOWED; do not disguise a policy refusal as an outage. A caller can separately select the permitted local mode.

Make the next right action easy
Expose readable capabilities such as “Local summary available” and “External model unavailable: policy review required.” Do not expose keys or force users to configure credentials for basic measurements and deterministic summaries.

Acceptance checks
Verify denied export makes zero network calls; test allowlisted payloads, policy withdrawal before retry, secret redaction, malformed JSON, truncation, timeout, rate limiting and cancellation. Mock tests prove adapter handling only. If a live call is authorized and available, record its exact model identity and limitations; otherwise leave live enablement blocked. Verify the relevant project/patient/branch authorization and happy/error paths against actual implementation.

Completion evidence
- Deliver applicable code, migrations, versioned configuration/prompts/schemas, generated contracts/clients, focused tests and a short runbook with actual commands. Use no protected identifiers or credentials in examples.
- Run relevant checks and report real results, denominators, failures and limits. Distinguish mocks/fixtures, live provider verification, real-data evaluation and qualified scientific review. Skipped mandatory checks are not passes.
- Update traceability, task ledger, contract decisions and release gates. Record what is implemented, what is blocked and the next recommended action. Creating a prompt or passing JSON validation is not completed scientific validation.
- Final response: behavior delivered; key files/contracts; commands/results; material limitation/dependency. Keep it concise; provide rationale and evidence, not hidden internal reasoning.
```

### COS-058 — Clinical note fact extraction, negation and temporal expression handling

```text
Task: COS-058 — Clinical note fact extraction, negation and temporal expression handling
Priority: P0 | Workstream: 08
Prerequisites: COS-018, COS-020, COS-022, COS-024, COS-057; inherited Phase 1–3 governance/security/contracts apply.
Expert perspectives: Clinical NLP, clinical informatics, Unicode text engineering and privacy.
Read: SPEC-006 section 6; SPEC-008 extracted_facts and span convention; SPEC-010/011; relevant repository code/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approval you do not have. If working alone, label the review as self-review; do not assume subagents or special Muse Spark tools.

Execute this single task in the existing repository. Inspect instructions, relevant specifications, COS-AUD-001 adoption/decisions, current code/contracts and actual prerequisite evidence first. Preserve the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse existing services and the canonical /api/v1/projects/{project_id} API, with documented health/identity exceptions. Add missing contracts through versioned decisions and regenerate OpenAPI/clients/examples together; do not rewrite twelve source documents or create competing routes.

Prioritize correct working behavior, clear choices, easy next actions and complete error/recovery paths. Preserve exact patient/branch/time context, unknown values, units and immutable source/history. Keep OBSERVED/SYNTHETIC context separate from item provenance, review, availability and publication; synthetic descendants remain SYNTHETIC_GENERATED. Authorization and safe validation apply now, not only at COS-071. No unrestricted SQL/tools, unapproved data exports or paid compute.

Proceed with authorized reversible implementation. When actual provider/data/review evidence is missing, complete independent code and conspicuously synthetic fixture checks, disable the affected capability and record the exact dependency/owner. Never invent model capabilities, source rights, clinical claims or evaluation results. Use typed statuses/errors/actions and runnable examples for backend tasks; build only the requested thin integration into existing screens. Do not expose placeholders as functioning controls.

Outcome
Extract only supported source-span facts from authorized notes while preserving negation, uncertainty, subject and time.

Implement
1. Implement a bounded extraction schema/service using the provider interface or an explicitly scoped deterministic parser. Accept an immutable verified note artifact/version and its authorized patient/branch/time context, not arbitrary public patient uploads. Record extractor/prompt/schema versions and exact normalized-text hash/normalization version.
2. Every extracted fact retains concept/original mention, value/unit if explicit, certainty, negation, experiencer, temporal assertion, source note ID and exact span. Use zero-based Unicode code-point offsets, end exclusive, as SPEC-008 requires; convert JavaScript UTF-16 offsets correctly. Validate that spans reproduce exact text and belong to the same note/patient/branch. Keep protected span text behind appropriate access controls.
3. Distinguish affirmed, denied, possible, historical, planned and “assess for” statements. Family-history findings are not patient diagnoses; a proposed test is not an actual result. Preserve documented clinician recommendations only as historical quotations/assertions, never new CancerOS advice. Do not infer numeric symptom severity, receptor status or cancer stage from vague text.
4. Resolve relative dates only from a verified authorized note anchor with source precision/time domain. Ambiguous “last visit” remains unresolved without evidence. Retain conflicting facts from different notes and qualifiers/censoring. Unit normalization uses existing dictionaries, not model guesses.
5. Keep extracted facts as derived assertions with source lineage and validation status; they cannot overwrite authoritative observations or unlock clinical eligibility automatically. Real-note derived output retains real-source derivation; facts extracted from synthetic notes remain synthetic. Use synthetic edge-case notes if authentic notes are unavailable and report the scope honestly.

Make the next right action easy
Show the extracted fact beside its authorized supporting span with “Negated”, “Uncertain”, “Historical” or “Time unresolved” labels. Provide correction/review actions that append evidence rather than silently editing source text.

Acceptance checks
Test scope-limited parser versus model on supported fixtures: negation, hypothetical plans, family history, conflicting notes, explicit/absent severity, relative-time ambiguity, censored units and prompt injection. Include emoji/combining characters for span offsets. Report entity/value precision/recall, negation/time/span correctness, unsupported facts and coverage; no real-note accuracy claim from synthetic fixtures. Verify the relevant project/patient/branch authorization and happy/error paths against actual implementation.

Completion evidence
- Deliver applicable code, migrations, versioned configuration/prompts/schemas, generated contracts/clients, focused tests and a short runbook with actual commands. Use no protected identifiers or credentials in examples.
- Run relevant checks and report real results, denominators, failures and limits. Distinguish mocks/fixtures, live provider verification, real-data evaluation and qualified scientific review. Skipped mandatory checks are not passes.
- Update traceability, task ledger, contract decisions and release gates. Record what is implemented, what is blocked and the next recommended action. Creating a prompt or passing JSON validation is not completed scientific validation.
- Final response: behavior delivered; key files/contracts; commands/results; material limitation/dependency. Keep it concise; provide rationale and evidence, not hidden internal reasoning.
```

### COS-059 — Clinical concept and source-linked knowledge relationship model

```text
Task: COS-059 — Clinical concept and source-linked knowledge relationship model
Priority: P0 | Workstream: 08
Prerequisites: COS-018, COS-022, COS-038, COS-053, COS-058; inherited Phase 1–3 governance/security/contracts apply.
Expert perspectives: Clinical knowledge modeling, relational architecture and scientific integrity.
Read: SPEC-006 section 9; SPEC-008 resource/claim/lineage ownership; SPEC-010; relevant repository code/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approval you do not have. If working alone, label the review as self-review; do not assume subagents or special Muse Spark tools.

Execute this single task in the existing repository. Inspect instructions, relevant specifications, COS-AUD-001 adoption/decisions, current code/contracts and actual prerequisite evidence first. Preserve the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse existing services and the canonical /api/v1/projects/{project_id} API, with documented health/identity exceptions. Add missing contracts through versioned decisions and regenerate OpenAPI/clients/examples together; do not rewrite twelve source documents or create competing routes.

Prioritize correct working behavior, clear choices, easy next actions and complete error/recovery paths. Preserve exact patient/branch/time context, unknown values, units and immutable source/history. Keep OBSERVED/SYNTHETIC context separate from item provenance, review, availability and publication; synthetic descendants remain SYNTHETIC_GENERATED. Authorization and safe validation apply now, not only at COS-071. No unrestricted SQL/tools, unapproved data exports or paid compute.

Proceed with authorized reversible implementation. When actual provider/data/review evidence is missing, complete independent code and conspicuously synthetic fixture checks, disable the affected capability and record the exact dependency/owner. Never invent model capabilities, source rights, clinical claims or evaluation results. Use typed statuses/errors/actions and runnable examples for backend tasks; build only the requested thin integration into existing screens. Do not expose placeholders as functioning controls.

Outcome
Represent traceable clinical relationships in PostgreSQL without turning associations or model assertions into established patient facts.

Implement
1. Extend existing canonical resource/concept tables with typed relationship records for patient, lesion, observation, measurement, exposure, outcome, publication, evidence statement and simulation branch. Define edge meaning, allowed source/target kinds, ownership, time/context, assertion origin, supporting record/span and validation/review status. Reuse existing patient/lesion IDs; no duplicate identity graph.
2. Enforce project/patient/branch integrity with real FKs/registry checks. Only explicit baseline links can cross observed-to-branch boundaries. Research publications/concepts may be shared within their authorized scope, but that never grants access to another patient's facts. Keep generic evidence relationships separate from patient-specific observations.
3. Distinguish recorded association, reported assertion, hypothetical simulation and supported general research statement. An ASSOCIATED_WITH edge does not mean CAUSES; a model-generated relationship is a proposal until its evidence path is validated. Do not automatically establish resistance, adverse-event causation or treatment efficacy from temporal coincidence.
4. Persist relationship versions/corrections and source lineage. Restrict traversal to authorized kinds/depth/page budgets; return readable evidence links and uncertainty. Check cycles only where a relation is defined acyclic, such as provenance; ordinary concept relationships may be cyclic. Use PostgreSQL explicit tables, not a new graph database or graph neural network.
5. Provide a small executable fixture demonstrating a real/derived source assertion, a synthetic baseline-derived link and a conflicting extracted assertion, with source drill-down and safe redaction.

Make the next right action easy
Present relationships as readable statements with “Source-supported”, “Extracted assertion” or “Simulated” status and a source link. Do not expose internal graph terminology as the primary workflow or make unverified edges look authoritative.

Acceptance checks
Test allowed edge kinds, ownership, dangling resources, branch isolation, cross-patient traversal denial, bounded traversal and correction history. Verify generic literature cannot establish an undocumented patient outcome and a valid concept cycle is not incorrectly rejected as a lineage cycle. Verify the relevant project/patient/branch authorization and happy/error paths against actual implementation.

Completion evidence
- Deliver applicable code, migrations, versioned configuration/prompts/schemas, generated contracts/clients, focused tests and a short runbook with actual commands. Use no protected identifiers or credentials in examples.
- Run relevant checks and report real results, denominators, failures and limits. Distinguish mocks/fixtures, live provider verification, real-data evaluation and qualified scientific review. Skipped mandatory checks are not passes.
- Update traceability, task ledger, contract decisions and release gates. Record what is implemented, what is blocked and the next recommended action. Creating a prompt or passing JSON validation is not completed scientific validation.
- Final response: behavior delivered; key files/contracts; commands/results; material limitation/dependency. Keep it concise; provide rationale and evidence, not hidden internal reasoning.
```

### COS-060 — Curated research evidence ingestion, licensing and versioned indexing

```text
Task: COS-060 — Curated research evidence ingestion, licensing and versioned indexing
Priority: P0 | Workstream: 08
Prerequisites: COS-016, COS-018, COS-022, COS-059; inherited Phase 1–3 governance/security/contracts apply.
Expert perspectives: Research information science, evidence curation, licensing metadata and retrieval engineering.
Read: SPEC-006 section 10; SPEC-008 evidence tables; SPEC-010; audit D03; relevant repository code/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approval you do not have. If working alone, label the review as self-review; do not assume subagents or special Muse Spark tools.

Execute this single task in the existing repository. Inspect instructions, relevant specifications, COS-AUD-001 adoption/decisions, current code/contracts and actual prerequisite evidence first. Preserve the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse existing services and the canonical /api/v1/projects/{project_id} API, with documented health/identity exceptions. Add missing contracts through versioned decisions and regenerate OpenAPI/clients/examples together; do not rewrite twelve source documents or create competing routes.

Prioritize correct working behavior, clear choices, easy next actions and complete error/recovery paths. Preserve exact patient/branch/time context, unknown values, units and immutable source/history. Keep OBSERVED/SYNTHETIC context separate from item provenance, review, availability and publication; synthetic descendants remain SYNTHETIC_GENERATED. Authorization and safe validation apply now, not only at COS-071. No unrestricted SQL/tools, unapproved data exports or paid compute.

Proceed with authorized reversible implementation. When actual provider/data/review evidence is missing, complete independent code and conspicuously synthetic fixture checks, disable the affected capability and record the exact dependency/owner. Never invent model capabilities, source rights, clinical claims or evaluation results. Use typed statuses/errors/actions and runnable examples for backend tasks; build only the requested thin integration into existing screens. Do not expose placeholders as functioning controls.

Outcome
Build a small reproducible approved evidence corpus with passage-level provenance and action-specific rights.

Implement
1. Define an evidence-source manifest and import workflow for selected authoritative publications/protocols or legally usable research information. Inspect actual document contents and metadata before inclusion. Verify title, authors/publisher, DOI/canonical URL, publication/update dates, document version, topic/subtype/setting and correction/retraction status where available. Earlier supplied literature links are candidates, not automatically verified evidence.
2. Capture license/access/quotation/export restrictions per content component and intended action. PubMed indexing, a PMC page or public URL alone is not blanket reuse permission. Separate metadata-only records from usable full-text/excerpts. Do not bypass paywalls, copy unlicensed full texts or embed restricted text through an external service without approved policy.
3. Store immutable authorized bytes/text versions with hashes, retrieval date, extraction/normalization version and stable passage locators such as section/page/table/character span. Treat document content as untrusted data. Preserve context when chunking; mark OCR/extraction uncertainty rather than silently damaging numerical tables.
4. Implement versioned PostgreSQL full-text/keyword indexing as the working baseline. Embeddings are optional; if justified, retain model/version/dimensions/passage/corpus identity and apply export rules. Do not add a separate vector service solely for this task.
5. Produce immutable corpus manifests and atomic index activation. New versions, retractions and rights restrictions append metadata and update current eligibility without rewriting historical interpretation hashes. Remove restricted text from active retrieval/caches according to policy; audit history is not permission to retain disallowed content forever.

Make the next right action easy
Give curators a short preview → rights/metadata validation → index workflow. Show approved, metadata-only, needs review and excluded states with a precise next action; ordinary viewers see only eligible evidence.

Acceptance checks
Test duplicate DOI/content versions, incomplete license, metadata-only sources, extraction failures, malformed PDFs, unsafe import URLs and retraction/rights withdrawal. Verify reproducible passage IDs/hashes, consistent corpus activation and no unauthorized text in search excerpts or embeddings. Verify the relevant project/patient/branch authorization and happy/error paths against actual implementation.

Completion evidence
- Deliver applicable code, migrations, versioned configuration/prompts/schemas, generated contracts/clients, focused tests and a short runbook with actual commands. Use no protected identifiers or credentials in examples.
- Run relevant checks and report real results, denominators, failures and limits. Distinguish mocks/fixtures, live provider verification, real-data evaluation and qualified scientific review. Skipped mandatory checks are not passes.
- Update traceability, task ledger, contract decisions and release gates. Record what is implemented, what is blocked and the next recommended action. Creating a prompt or passing JSON validation is not completed scientific validation.
- Final response: behavior delivered; key files/contracts; commands/results; material limitation/dependency. Keep it concise; provide rationale and evidence, not hidden internal reasoning.
```

### COS-061 — Evidence retrieval, relevance filtering and citation verification

```text
Task: COS-061 — Evidence retrieval, relevance filtering and citation verification
Priority: P0 | Workstream: 08
Prerequisites: COS-059, COS-060; inherited Phase 1–3 governance/security/contracts apply.
Expert perspectives: Information retrieval, scientific evidence review and application security.
Read: SPEC-006 section 10; SPEC-008 evidence/claim links; SPEC-010/011; relevant repository code/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approval you do not have. If working alone, label the review as self-review; do not assume subagents or special Muse Spark tools.

Execute this single task in the existing repository. Inspect instructions, relevant specifications, COS-AUD-001 adoption/decisions, current code/contracts and actual prerequisite evidence first. Preserve the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse existing services and the canonical /api/v1/projects/{project_id} API, with documented health/identity exceptions. Add missing contracts through versioned decisions and regenerate OpenAPI/clients/examples together; do not rewrite twelve source documents or create competing routes.

Prioritize correct working behavior, clear choices, easy next actions and complete error/recovery paths. Preserve exact patient/branch/time context, unknown values, units and immutable source/history. Keep OBSERVED/SYNTHETIC context separate from item provenance, review, availability and publication; synthetic descendants remain SYNTHETIC_GENERATED. Authorization and safe validation apply now, not only at COS-071. No unrestricted SQL/tools, unapproved data exports or paid compute.

Proceed with authorized reversible implementation. When actual provider/data/review evidence is missing, complete independent code and conspicuously synthetic fixture checks, disable the affected capability and record the exact dependency/owner. Never invent model capabilities, source rights, clinical claims or evaluation results. Use typed statuses/errors/actions and runnable examples for backend tasks; build only the requested thin integration into existing screens. Do not expose placeholders as functioning controls.

Outcome
Retrieve relevant permitted passages and distinguish citation resolution from actual support for a claim.

Implement
1. Implement a bounded retrieval service over an explicit corpus version. Normalize the research query and supported concepts; filter by permitted source, topic, breast-cancer subtype, setting, publication/revision and rights. Unknown subtype must not be silently assigned. Start with transparent keyword ranking and a documented top-k policy; optional vector reranking must beat the same-corpus baseline under a frozen protocol.
2. Return stable document/passage IDs, exact permitted text/locator/hash, source metadata, relevance rationale and eligibility restrictions. Exclude retracted/withdrawn or inapplicable evidence from current support under the recorded policy. A no-match result is valid and cannot be filled with invented citations or unrelated general text.
3. Verify reference existence, active version, locator integrity and intended-use access. Citation resolution may use approved metadata/allowlisted fetches or a verified offline manifest; never dereference a model-supplied arbitrary URL, private address or credential-bearing link. Handle unavailable external sites as unverifiable, not verified by plausible DOI formatting.
4. Represent meaningful passage-to-claim support separately from link validity. General research evidence cannot establish an unrecorded patient fact or individualized treatment effect. For unreviewed semantic support, retain a candidate status and require the bounded claim/review path; a similarity score or second LLM is not sufficient scientific adjudication.
5. Version relevance labels and retrieval settings. Create answerable, irrelevant, conflicting, outdated and no-evidence fixture queries. Freeze a separate final evaluation set rather than tuning repeatedly on reported test cases.

Make the next right action easy
Show why a passage was selected, the exact usable excerpt and source/date. Explain “No suitable evidence found” with a narrower supported question or a curator action; never present retrieval rank as clinical confidence.

Acceptance checks
Measure precision at k, recall at k only with a sufficiently complete relevance set, context compatibility, citation resolution and unsupported-source rate. Test malformed IDs, mismatched passage hashes, irrelevant subtype, retractions, injection and unavailable URLs. Record failed/abstained queries and distinguish fixture relevance labels from reviewed scientific judgments. Verify the relevant project/patient/branch authorization and happy/error paths against actual implementation.

Completion evidence
- Deliver applicable code, migrations, versioned configuration/prompts/schemas, generated contracts/clients, focused tests and a short runbook with actual commands. Use no protected identifiers or credentials in examples.
- Run relevant checks and report real results, denominators, failures and limits. Distinguish mocks/fixtures, live provider verification, real-data evaluation and qualified scientific review. Skipped mandatory checks are not passes.
- Update traceability, task ledger, contract decisions and release gates. Record what is implemented, what is blocked and the next recommended action. Creating a prompt or passing JSON validation is not completed scientific validation.
- Final response: behavior delivered; key files/contracts; commands/results; material limitation/dependency. Keep it concise; provide rationale and evidence, not hidden internal reasoning.
```

### COS-062 — Structured research interpretation context builder

```text
Task: COS-062 — Structured research interpretation context builder
Priority: P0 | Workstream: 08
Prerequisites: COS-022, COS-039, COS-051, COS-052, COS-053, COS-054, COS-057, COS-058, COS-059, COS-061; inherited Phase 1–3 governance/security/contracts apply.
Expert perspectives: Multimodal architecture, privacy minimization and temporal scientific integrity.
Read: SPEC-006 sections 4, 11–14; SPEC-008 InterpretationRequest/freshness; SPEC-010; relevant repository code/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approval you do not have. If working alone, label the review as self-review; do not assume subagents or special Muse Spark tools.

Execute this single task in the existing repository. Inspect instructions, relevant specifications, COS-AUD-001 adoption/decisions, current code/contracts and actual prerequisite evidence first. Preserve the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse existing services and the canonical /api/v1/projects/{project_id} API, with documented health/identity exceptions. Add missing contracts through versioned decisions and regenerate OpenAPI/clients/examples together; do not rewrite twelve source documents or create competing routes.

Prioritize correct working behavior, clear choices, easy next actions and complete error/recovery paths. Preserve exact patient/branch/time context, unknown values, units and immutable source/history. Keep OBSERVED/SYNTHETIC context separate from item provenance, review, availability and publication; synthetic descendants remain SYNTHETIC_GENERATED. Authorization and safe validation apply now, not only at COS-071. No unrestricted SQL/tools, unapproved data exports or paid compute.

Proceed with authorized reversible implementation. When actual provider/data/review evidence is missing, complete independent code and conspicuously synthetic fixture checks, disable the affected capability and record the exact dependency/owner. Never invent model capabilities, source rights, clinical claims or evaluation results. Use typed statuses/errors/actions and runnable examples for backend tasks; build only the requested thin integration into existing screens. Do not expose placeholders as functioning controls.

Outcome
Create one bounded immutable authorized context containing exactly the evidence available for the selected snapshot.

Implement
1. Implement an immutable interpretation-context model with project/patient/state/branch/run, selected snapshot hash, assembly/data revision, purpose, optional comparison, exact input IDs/versions and corpus/retrieval versions. Reuse fused state and deterministic comparisons; do not re-query current heads to fill an old snapshot or create a competing state assembly policy.
2. Separate verified patient facts/measurements, extracted assertions, general research evidence, synthetic assumptions, treatment history, quality, missing/conflicting evidence and limitations. Preserve units, actual member times, historical-geometry labels and origin at item level. Keep tumor change distinct from clinical deterioration. Disabled forecasts and hidden simulator truth cannot enter the context.
3. Resolve every nested reference with current authorization and intended-use rights. Local context and externally exportable payload are different views. Apply allowlisted minimization, note-span policy, size/token budgets and identifier substitution where appropriate. A hash records identity; it does not authorize disclosure. Never send source maps, signed URLs or storage credentials.
4. Define deterministic selection/truncation rules that retain critical negation, provenance, conflicts and safety limits. If essential context cannot fit, return a narrower scope or insufficient evidence rather than silently dropping decisive facts. Record omissions and exact payload/context hashes.
5. Treat notes, documents and user questions as untrusted content, separate from system instructions. If approved tool access is needed, expose narrowly typed read-only operations scoped to this context with budgets and reauthorization; no arbitrary SQL, URL fetching, file access or permission changes. Prefer a complete bounded context over an unnecessary agent loop.

Make the next right action easy
Display the selected state/time, comparison and analysis scope before generation. Explain which modalities are missing, historical or excluded from external processing, without exposing restricted data. Preserve the user's selection when generation is blocked.

Acceptance checks
Test old snapshot after a source correction, stale comparison, cross-branch references, critical-negation truncation, missing modalities and denied export fields. Verify repeat context hashes for identical scientific inputs, no future data/hidden simulation truth and correct distinction between local context and transmitted payload. Verify the relevant project/patient/branch authorization and happy/error paths against actual implementation.

Completion evidence
- Deliver applicable code, migrations, versioned configuration/prompts/schemas, generated contracts/clients, focused tests and a short runbook with actual commands. Use no protected identifiers or credentials in examples.
- Run relevant checks and report real results, denominators, failures and limits. Distinguish mocks/fixtures, live provider verification, real-data evaluation and qualified scientific review. Skipped mandatory checks are not passes.
- Update traceability, task ledger, contract decisions and release gates. Record what is implemented, what is blocked and the next recommended action. Creating a prompt or passing JSON validation is not completed scientific validation.
- Final response: behavior delivered; key files/contracts; commands/results; material limitation/dependency. Keep it concise; provide rationale and evidence, not hidden internal reasoning.
```

### COS-063 — Evidence-linked AI interpretation and explanatory output generation

```text
Task: COS-063 — Evidence-linked AI interpretation and explanatory output generation
Priority: P0 | Workstream: 08
Prerequisites: COS-052, COS-053, COS-057, COS-058, COS-061, COS-062; inherited Phase 1–3 governance/security/contracts apply.
Expert perspectives: Research communication, LLM orchestration and scientific safety UX.
Read: SPEC-006 section 12; SPEC-008 section 13.6; SPEC-010 SAFE-20/21; audit A04; relevant repository code/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approval you do not have. If working alone, label the review as self-review; do not assume subagents or special Muse Spark tools.

Execute this single task in the existing repository. Inspect instructions, relevant specifications, COS-AUD-001 adoption/decisions, current code/contracts and actual prerequisite evidence first. Preserve the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse existing services and the canonical /api/v1/projects/{project_id} API, with documented health/identity exceptions. Add missing contracts through versioned decisions and regenerate OpenAPI/clients/examples together; do not rewrite twelve source documents or create competing routes.

Prioritize correct working behavior, clear choices, easy next actions and complete error/recovery paths. Preserve exact patient/branch/time context, unknown values, units and immutable source/history. Keep OBSERVED/SYNTHETIC context separate from item provenance, review, availability and publication; synthetic descendants remain SYNTHETIC_GENERATED. Authorization and safe validation apply now, not only at COS-071. No unrestricted SQL/tools, unapproved data exports or paid compute.

Proceed with authorized reversible implementation. When actual provider/data/review evidence is missing, complete independent code and conspicuously synthetic fixture checks, disable the affected capability and record the exact dependency/owner. Never invent model capabilities, source rights, clinical claims or evaluation results. Use typed statuses/errors/actions and runnable examples for backend tasks; build only the requested thin integration into existing screens. Do not expose placeholders as functioning controls.

Outcome
Generate concise source-linked research explanations while keeping unvalidated candidates private.

Implement
1. Implement the canonical interpretation pipeline using the frozen COS-062 context. Support a deterministic template mode that works without provider access and an external candidate-generation mode only through COS-057. Record execution mode truthfully; do not describe rules, saved text or mock output as live Muse Spark reasoning.
2. Emit the SPEC-008 structured findings/limitations/evidence contract. Each finding has kind, observation/measurement/passage references and, for numerical findings, deterministic metric/value/unit fields. Calculate changes outside the LLM. Prefer backend-rendered numeric text from verified fields over unconstrained model arithmetic, with explicit rounding/qualifier policy.
3. Separate observed findings, synthetic scenario descriptions and general background. Explain independent tumor/clinical trends, missingness, conflicts and uncertainty type. A publication can explain a concept but cannot prove an unrecorded patient finding. Do not invent formal response grades, prognosis, resistance, causality or recommended treatment.
4. Apply the existing fail-closed validator interface from COS-057; model candidates remain private until COS-064 is implemented and the required checks pass. Reject unsupported references/schema/content with bounded retry only when safe; every retry rechecks export policy. Novel unconstrained prose needs a demonstrated validation/review path, otherwise use bounded reviewed templates or abstain.
5. Add a minimal interpretation panel in the existing state view: concise summary, expandable findings/source links, uncertainties and execution-mode label. Match selected snapshot/branch IDs and discard stale results after selection changes. Show no raw streamed tokens, model chain-of-thought or hidden draft claims.

Make the next right action easy
Lead with a short explanation of what changed and what remains unknown. Make each factual finding open its evidence. Label “Simulated”, “Rule-based summary” or “Saved result” prominently where applicable; provide a safe narrower summary when full interpretation is unsupported.

Acceptance checks
Compare template and external candidate outputs on identical input fixtures. Test missing labs, lab-only updates, synthetic shrinkage with worsening indicators, unresolved conflicts, invalid references and provider failure. Verify no candidate becomes visible before validation and no general research claim is promoted into a patient diagnosis. Verify the relevant project/patient/branch authorization and happy/error paths against actual implementation.

Completion evidence
- Deliver applicable code, migrations, versioned configuration/prompts/schemas, generated contracts/clients, focused tests and a short runbook with actual commands. Use no protected identifiers or credentials in examples.
- Run relevant checks and report real results, denominators, failures and limits. Distinguish mocks/fixtures, live provider verification, real-data evaluation and qualified scientific review. Skipped mandatory checks are not passes.
- Update traceability, task ledger, contract decisions and release gates. Record what is implemented, what is blocked and the next recommended action. Creating a prompt or passing JSON validation is not completed scientific validation.
- Final response: behavior delivered; key files/contracts; commands/results; material limitation/dependency. Keep it concise; provide rationale and evidence, not hidden internal reasoning.
```

### COS-064 — Hallucination checks, numerical grounding, prohibited claims and abstention

```text
Task: COS-064 — Hallucination checks, numerical grounding, prohibited claims and abstention
Priority: P0 | Workstream: 08
Prerequisites: COS-005, COS-007, COS-057, COS-058, COS-061, COS-062, COS-063; inherited Phase 1–3 governance/security/contracts apply.
Expert perspectives: AI safety evaluation, measurement verification, adversarial QA and clinical scientific review.
Read: SPEC-010 SAFE-01–25; SPEC-011 section 9; SPEC-008 FAILED_GROUNDING; audit D04/D05; relevant repository code/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approval you do not have. If working alone, label the review as self-review; do not assume subagents or special Muse Spark tools.

Execute this single task in the existing repository. Inspect instructions, relevant specifications, COS-AUD-001 adoption/decisions, current code/contracts and actual prerequisite evidence first. Preserve the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse existing services and the canonical /api/v1/projects/{project_id} API, with documented health/identity exceptions. Add missing contracts through versioned decisions and regenerate OpenAPI/clients/examples together; do not rewrite twelve source documents or create competing routes.

Prioritize correct working behavior, clear choices, easy next actions and complete error/recovery paths. Preserve exact patient/branch/time context, unknown values, units and immutable source/history. Keep OBSERVED/SYNTHETIC context separate from item provenance, review, availability and publication; synthetic descendants remain SYNTHETIC_GENERATED. Authorization and safe validation apply now, not only at COS-071. No unrestricted SQL/tools, unapproved data exports or paid compute.

Proceed with authorized reversible implementation. When actual provider/data/review evidence is missing, complete independent code and conspicuously synthetic fixture checks, disable the affected capability and record the exact dependency/owner. Never invent model capabilities, source rights, clinical claims or evaluation results. Use typed statuses/errors/actions and runnable examples for backend tasks; build only the requested thin integration into existing screens. Do not expose placeholders as functioning controls.

Outcome
Implement and evaluate the mandatory publication gate for every interpretation mode.

Implement
1. Validate schema, ownership, snapshot hash, record/passage membership, provenance, current rights and numeric/value/unit fidelity before publication. Compare all numerical statements to deterministic source fields under declared display rounding and qualifier rules. Catch signs, denominators, percentages, dates and volume-versus-diameter errors; unsupported or inconsistent numbers fail closed.
2. Separate citation resolution from meaningful support. Verify source spans, negation, time, subject and assertion scope. Enforce a bounded allowed-claim policy: no invented MRI/labs, staging, survival, resistance, treatment ranking/prescribing, automatic RECIST/CTCAE, synthetic-as-real or unsupported adverse-event causation. A historical source statement may be attributed as such without becoming new advice.
3. Combine deterministic checks, restricted templates/claim schemas and documented review for semantic claims. Do not promise that regexes, a second LLM or embedding similarity can guarantee general entailment. Unsupported novel prose stays private; reject the candidate or generate a fresh independently validated narrower template. Never silently delete a dangerous clause and publish an incoherent remnant.
4. Return structured insufficient_evidence, not_comparable or FAILED_GROUNDING with reason codes as appropriate. Missing modalities may permit a narrower valid summary, but critical unresolved evidence requires abstention. Model self-confidence is not calibrated uncertainty. Templates, cached outputs and saved summaries must pass the same current eligibility gates.
5. Build/freeze SPEC-011's initial sixty-case suite: twenty source-grounded, twenty missing/conflicting/temporal/negation, twenty adversarial/prohibited-claim cases. Keep development separate; version reference labels, prompts, corpus, decoding/model configuration. Seek actual second-review adjudication for ambiguous labels where feasible; disclose absent review. If an external model is enabled, aim for three runs per case and retain every output/failure.

Make the next right action easy
Explain why an interpretation was withheld using a readable reason and available next action. Keep verified measurements accessible. Do not replace a rejected clinical claim with a reassuring generic success message.

Acceptance checks
Report numeric/unit fidelity, origin fidelity, supported-claim fraction, case/claim unsupported rates, prohibited critical claims, appropriate/unnecessary abstention and coverage with denominators. Frozen-suite gates are 100% numeric/unit/origin fidelity for published outputs, zero published critical prohibited claims and correct abstention on every predefined critical insufficient case. Any critical failure blocks affected publication; finite-suite success is not proof of perfect safety. Verify the relevant project/patient/branch authorization and happy/error paths against actual implementation.

Completion evidence
- Deliver applicable code, migrations, versioned configuration/prompts/schemas, generated contracts/clients, focused tests and a short runbook with actual commands. Use no protected identifiers or credentials in examples.
- Run relevant checks and report real results, denominators, failures and limits. Distinguish mocks/fixtures, live provider verification, real-data evaluation and qualified scientific review. Skipped mandatory checks are not passes.
- Update traceability, task ledger, contract decisions and release gates. Record what is implemented, what is blocked and the next recommended action. Creating a prompt or passing JSON validation is not completed scientific validation.
- Final response: behavior delivered; key files/contracts; commands/results; material limitation/dependency. Keep it concise; provide rationale and evidence, not hidden internal reasoning.
```

### COS-065 — AI result persistence, model audit, cache and outage fallback

```text
Task: COS-065 — AI result persistence, model audit, cache and outage fallback
Priority: P0 | Workstream: 08
Prerequisites: COS-022, COS-032, COS-039, COS-054, COS-057, COS-062, COS-063, COS-064; inherited Phase 1–3 governance/security/contracts apply.
Expert perspectives: Inference operations, secure caching, temporal persistence and auditability.
Read: SPEC-008 intelligence schemas/freshness/races; SPEC-010 retention; SPEC-011 resilience; relevant repository code/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approval you do not have. If working alone, label the review as self-review; do not assume subagents or special Muse Spark tools.

Execute this single task in the existing repository. Inspect instructions, relevant specifications, COS-AUD-001 adoption/decisions, current code/contracts and actual prerequisite evidence first. Preserve the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse existing services and the canonical /api/v1/projects/{project_id} API, with documented health/identity exceptions. Add missing contracts through versioned decisions and regenerate OpenAPI/clients/examples together; do not rewrite twelve source documents or create competing routes.

Prioritize correct working behavior, clear choices, easy next actions and complete error/recovery paths. Preserve exact patient/branch/time context, unknown values, units and immutable source/history. Keep OBSERVED/SYNTHETIC context separate from item provenance, review, availability and publication; synthetic descendants remain SYNTHETIC_GENERATED. Authorization and safe validation apply now, not only at COS-071. No unrestricted SQL/tools, unapproved data exports or paid compute.

Proceed with authorized reversible implementation. When actual provider/data/review evidence is missing, complete independent code and conspicuously synthetic fixture checks, disable the affected capability and record the exact dependency/owner. Never invent model capabilities, source rights, clinical claims or evaluation results. Use typed statuses/errors/actions and runnable examples for backend tasks; build only the requested thin integration into existing screens. Do not expose placeholders as functioning controls.

Outcome
Persist reproducible validated results and provide safe exact-context reuse or labeled fallback during outages.

Implement
1. Persist model registry/run, extracted facts, immutable context, candidate/validation outcome, interpretation/claim links and permitted audit metadata using canonical tables. Record configured/returned model identity, unresolved revision limitations, prompt/schema/validator versions, corpus manifest, input hashes, decoding settings, timestamps, usage and failure stage. Apply approved retention; minimize raw prompts/responses and never put sensitive copies in routine logs.
2. Separate private candidates, validated ready results and publication eligibility under the adopted interpretation lifecycle. Do not invent a new public command to expose results. Jobs cannot bypass COS-064. A source correction creates new context/results; old interpretations remain records of exact historical inputs with independent current-for-snapshot and superseded-for-current-timeline signals.
3. Key internal result reuse by authorized project/patient/branch/run/state/context hash, purpose, execution mode, model/prompt/schema/validator/corpus versions and material generation settings. Recheck current access/rights/policy and exact snapshot on every hit; never reuse another patient's or a mismatched state's “similar” answer. Do not cache signed URLs. Private application caching does not authorize HTTP/browser shared caching of patient data.
4. Handle provider failure with bounded retries/circuit breaker, durable job state and explicit deterministic fallback where permitted. An exact-context previously validated result may be displayed as saved after revalidation; it is not live output. A policy refusal remains 403 and is not converted into an outage. Keep raw measurements/trends available even if generation fails.
5. Propagate source/corpus withdrawal, validator changes, access revocation and retention/deletion into active caches/publication eligibility without rewriting retained scientific hashes. Prevent stale job results attaching to a new selected state. Add auditable safe retry/cancel operations and idempotent finalization.

Make the next right action easy
Show “Validated model summary”, “Rule-based fallback”, “Saved result for this snapshot” or a precise unavailable status. Include freshness/time and source drill-down; preserve the selected view and offer only an effective retry.

Acceptance checks
Inject outages, timeout, malformed output, database/object failure, policy revocation, duplicate delivery and stale completion. Verify cache isolation/version misses, exact-context reuse, validation on fallback, immutable history and permitted retention cleanup. Measure actual schema/grounding rejection, failure rate, latency and cost per accepted result with all attempts counted. Verify the relevant project/patient/branch authorization and happy/error paths against actual implementation.

Completion evidence
- Deliver applicable code, migrations, versioned configuration/prompts/schemas, generated contracts/clients, focused tests and a short runbook with actual commands. Use no protected identifiers or credentials in examples.
- Run relevant checks and report real results, denominators, failures and limits. Distinguish mocks/fixtures, live provider verification, real-data evaluation and qualified scientific review. Skipped mandatory checks are not passes.
- Update traceability, task ledger, contract decisions and release gates. Record what is implemented, what is blocked and the next recommended action. Creating a prompt or passing JSON validation is not completed scientific validation.
- Final response: behavior delivered; key files/contracts; commands/results; material limitation/dependency. Keep it concise; provide rationale and evidence, not hidden internal reasoning.
```

### COS-066 — Patient, diagnosis and observation API implementation

```text
Task: COS-066 — Patient, diagnosis and observation API implementation
Priority: P0 | Workstream: 09
Prerequisites: COS-008, COS-017, COS-018, COS-019, COS-020, COS-023, COS-039, COS-054; inherited Phase 1–3 governance/security/contracts apply.
Expert perspectives: Backend/API engineering, clinical data integrity and consumer usability.
Read: SPEC-008 sections 6, 11–13; audit C01–C05; existing Phase 2/3 routes and clients; relevant repository code/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approval you do not have. If working alone, label the review as self-review; do not assume subagents or special Muse Spark tools.

Execute this single task in the existing repository. Inspect instructions, relevant specifications, COS-AUD-001 adoption/decisions, current code/contracts and actual prerequisite evidence first. Preserve the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse existing services and the canonical /api/v1/projects/{project_id} API, with documented health/identity exceptions. Add missing contracts through versioned decisions and regenerate OpenAPI/clients/examples together; do not rewrite twelve source documents or create competing routes.

Prioritize correct working behavior, clear choices, easy next actions and complete error/recovery paths. Preserve exact patient/branch/time context, unknown values, units and immutable source/history. Keep OBSERVED/SYNTHETIC context separate from item provenance, review, availability and publication; synthetic descendants remain SYNTHETIC_GENERATED. Authorization and safe validation apply now, not only at COS-071. No unrestricted SQL/tools, unapproved data exports or paid compute.

Proceed with authorized reversible implementation. When actual provider/data/review evidence is missing, complete independent code and conspicuously synthetic fixture checks, disable the affected capability and record the exact dependency/owner. Never invent model capabilities, source rights, clinical claims or evaluation results. Use typed statuses/errors/actions and runnable examples for backend tasks; build only the requested thin integration into existing screens. Do not expose placeholders as functioning controls.

Outcome
Complete and reconcile canonical patient/clinical APIs over existing domain services instead of rebuilding them.

Implement
1. Inventory current routes/OpenAPI/generated clients and map requirements to existing implementations, gaps and duplicates. Preserve the canonical project base. Finish patient list/detail, visits, filtered observations, exact observation read from the adopted C01 decision, diagnosis variants and required dictionary/capability reads. Diagnosis is a typed source-backed observation; do not invent a parallel diagnosis store or uncontrolled CRUD catalog.
2. Wire observation-batches, corrections and retractions to existing validated transactional services. All bundle entries validate or none commit; default maximum is 100 entries and default request-body limit 1 MiB per SPEC-008 unless a versioned config changes it. Client fields cannot select project ownership, provenance, accepted status or revision. Direct arbitrary synthetic writes remain disallowed.
3. Preserve absolute/relative/unknown time unions and the resolved C03 origin mapping. Return original/canonical units, value qualifiers, source/provenance, missingness and data revision without protected linkage fields. Corrections append source-backed replacements; changing observation kind follows new-record plus retraction semantics.
4. Implement canonical signed snapshot cursors/filter binding, ETags/If-Match, idempotency and concurrency. Recheck authorization before replay; return original committed operation before applying stale-precondition logic to a valid replay. Queue dependent updates via the same transaction/outbox. Return typed field/action errors and deterministic receipts.
5. Generate OpenAPI/examples/client updates and migrate existing consumers to the authoritative routes. Keep authorization and contract tests in this task; COS-071 later verifies system coverage, not initial protection.

Make the next right action easy
Enable a readable patient selection → observation review → source-backed update → revision/status workflow. Return precise field errors, preserve valid entered values and distinguish accepted data from a ready/published state.

Acceptance checks
Test list/detail/filter/exact-read paths, patient/project isolation, source-only diagnosis creation, invalid/atomic batches, unsupported units, zero-versus-missing, correction races and history. Verify 401/404/403 policy, 428/412 preconditions, idempotent retry and cursor snapshot consistency. Use real persistence integration tests as well as generated-client type checks. Verify the relevant project/patient/branch authorization and happy/error paths against actual implementation.

Completion evidence
- Deliver applicable code, migrations, versioned configuration/prompts/schemas, generated contracts/clients, focused tests and a short runbook with actual commands. Use no protected identifiers or credentials in examples.
- Run relevant checks and report real results, denominators, failures and limits. Distinguish mocks/fixtures, live provider verification, real-data evaluation and qualified scientific review. Skipped mandatory checks are not passes.
- Update traceability, task ledger, contract decisions and release gates. Record what is implemented, what is blocked and the next recommended action. Creating a prompt or passing JSON validation is not completed scientific validation.
- Final response: behavior delivered; key files/contracts; commands/results; material limitation/dependency. Keep it concise; provide rationale and evidence, not hidden internal reasoning.
```

### COS-067 — Imaging, segmentation and geometry API implementation

```text
Task: COS-067 — Imaging, segmentation and geometry API implementation
Priority: P0 | Workstream: 09
Prerequisites: COS-025, COS-026, COS-028, COS-029, COS-031, COS-032, COS-033, COS-034, COS-035, COS-036, COS-066; inherited Phase 1–3 governance/security/contracts apply.
Expert perspectives: Imaging backend integration, private artifact access and 3D consumer contracts.
Read: SPEC-008 study/segmentation/imaging-job/artifact/upload/import routes; SPEC-005/010; audit D01/D03; relevant repository code/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approval you do not have. If working alone, label the review as self-review; do not assume subagents or special Muse Spark tools.

Execute this single task in the existing repository. Inspect instructions, relevant specifications, COS-AUD-001 adoption/decisions, current code/contracts and actual prerequisite evidence first. Preserve the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse existing services and the canonical /api/v1/projects/{project_id} API, with documented health/identity exceptions. Add missing contracts through versioned decisions and regenerate OpenAPI/clients/examples together; do not rewrite twelve source documents or create competing routes.

Prioritize correct working behavior, clear choices, easy next actions and complete error/recovery paths. Preserve exact patient/branch/time context, unknown values, units and immutable source/history. Keep OBSERVED/SYNTHETIC context separate from item provenance, review, availability and publication; synthetic descendants remain SYNTHETIC_GENERATED. Authorization and safe validation apply now, not only at COS-071. No unrestricted SQL/tools, unapproved data exports or paid compute.

Proceed with authorized reversible implementation. When actual provider/data/review evidence is missing, complete independent code and conspicuously synthetic fixture checks, disable the affected capability and record the exact dependency/owner. Never invent model capabilities, source rights, clinical claims or evaluation results. Use typed statuses/errors/actions and runnable examples for backend tasks; build only the requested thin integration into existing screens. Do not expose placeholders as functioning controls.

Outcome
Expose validated imaging and geometry services through one typed private API with correct eligibility and asset behavior.

Implement
1. Reconcile existing study list/detail, acquisitions, segmentation metadata and imaging-job routes with SPEC-008. Reuse Phase 2 processing; add only necessary registered read contracts for measurement/geometry discovery identified by actual consumers. Keep mask type, lesion IDs, spatial units/frame, source time, QC, provenance and availability explicit.
2. Wire private upload-session/completion/import verification and explicit import publication through existing admin services. Enforce supported sizes/formats, expected versus actual byte count/hash/object version and source/rights association. No browser-selected bucket/object key, arbitrary remote URL ingestion or anonymous patient upload endpoint.
3. Return safe artifact manifests and short-lived authorized read grants, not storage credentials or permanent public links. Apply access and intended-use rights per grant; a viewer can access an approved mesh without automatically receiving original DICOM/notes. Default grant expiry is the contract's configurable 120 seconds. Never store grants as artifact identities or log their URLs.
4. Distinguish imported reviewed masks, model proposals and illustrative context; P1 model routes stay unavailable until registered/evaluated. Expose unavailable/blocked/ready states with reasons. Job 202 is acceptance, not a completed segmentation or mesh. Worker credentials remain scoped.
5. Document withdrawal behavior honestly: an already issued signed URL can survive to expiry unless authenticated proxy/provider revocation enforces immediate denial. Preserve transforms/unit metadata consumed by the viewer and prevent publication of failed QC geometry.

Make the next right action easy
Return enough capability/status data for the viewer to show the correct scan/mask/mesh and repair action. Expired grants get safe renewal guidance; missing geometry does not masquerade as an empty tumor.

Acceptance checks
Test unauthorized nested IDs, mesh-versus-source permissions, rejected corrupt uploads, object version mismatch, cross-study masks, expired grants and post-withdrawal policy. Exercise job acceptance/progress/failure plus manifest-to-actual-byte retrieval. Verify no scale/orientation metadata is dropped by API serialization. Verify the relevant project/patient/branch authorization and happy/error paths against actual implementation.

Completion evidence
- Deliver applicable code, migrations, versioned configuration/prompts/schemas, generated contracts/clients, focused tests and a short runbook with actual commands. Use no protected identifiers or credentials in examples.
- Run relevant checks and report real results, denominators, failures and limits. Distinguish mocks/fixtures, live provider verification, real-data evaluation and qualified scientific review. Skipped mandatory checks are not passes.
- Update traceability, task ledger, contract decisions and release gates. Record what is implemented, what is blocked and the next recommended action. Creating a prompt or passing JSON validation is not completed scientific validation.
- Final response: behavior delivered; key files/contracts; commands/results; material limitation/dependency. Keep it concise; provide rationale and evidence, not hidden internal reasoning.
```

### COS-068 — Simulation creation, branch management and status APIs

```text
Task: COS-068 — Simulation creation, branch management and status APIs
Priority: P0 | Workstream: 09
Prerequisites: COS-041, COS-042, COS-049, COS-050, COS-065, COS-066; inherited Phase 1–3 governance/security/contracts apply.
Expert perspectives: Simulation service integration, lifecycle concurrency and product UX.
Read: SPEC-008 scenario/eligibility/branch/run/publication/job routes; SPEC-004; audit A02/A03/A05/C01; relevant repository code/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approval you do not have. If working alone, label the review as self-review; do not assume subagents or special Muse Spark tools.

Execute this single task in the existing repository. Inspect instructions, relevant specifications, COS-AUD-001 adoption/decisions, current code/contracts and actual prerequisite evidence first. Preserve the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse existing services and the canonical /api/v1/projects/{project_id} API, with documented health/identity exceptions. Add missing contracts through versioned decisions and regenerate OpenAPI/clients/examples together; do not rewrite twelve source documents or create competing routes.

Prioritize correct working behavior, clear choices, easy next actions and complete error/recovery paths. Preserve exact patient/branch/time context, unknown values, units and immutable source/history. Keep OBSERVED/SYNTHETIC context separate from item provenance, review, availability and publication; synthetic descendants remain SYNTHETIC_GENERATED. Authorization and safe validation apply now, not only at COS-071. No unrestricted SQL/tools, unapproved data exports or paid compute.

Proceed with authorized reversible implementation. When actual provider/data/review evidence is missing, complete independent code and conspicuously synthetic fixture checks, disable the affected capability and record the exact dependency/owner. Never invent model capabilities, source rights, clinical claims or evaluation results. Use typed statuses/errors/actions and runnable examples for backend tasks; build only the requested thin integration into existing screens. Do not expose placeholders as functioning controls.

Outcome
Connect the five-family engine to typed branch/run APIs without duplicating simulation logic or allowing partial publication.

Implement
1. Reconcile scenario-definition discovery, eligibility checks, draft branch creation/detail/list from C01, run submission/detail and explicit publication with existing services. Return versioned parameter schemas, supported options and precise eligibility reasons. A draft may exist while insufficient; generation remains blocked until required source-supported evidence exists.
2. Preserve required baseline ID/hash, ruleset/config version, decimal-string parameters and seed as a nonnegative signed-64-bit JSON string. Reject unknown keys, incorrect hash, stale config and incompatible exposure. The route/session determines project ownership; every baseline, branch, run and validation report must match patient/context.
3. Runs freeze inputs and enqueue through existing jobs/outbox. Idempotent submission returns the same job rather than duplicate simulations. Viewer accounts see only publication-eligible published branch/run content; editors/admins receive permitted draft/validation information. Preserve prior published runs when a new run fails or remains in progress.
4. Explicit publication verifies the exact completed run/report/hash, all required follow-ups, scenario/geometry/clinical safety and current rights. Guard the branch pointer with If-Match and idempotency; job success cannot publish. Cancellation, retry and validation failures use existing canonical job/resource commands, not ad hoc destructive branch endpoints.
5. Provide run-specific timeline links and baseline_superseded/freshness metadata. A branch references the observed baseline plus at least three synthetic follow-ups; do not copy baseline observations as new synthetic inputs or rebase on later source corrections.

Make the next right action easy
Keep the create → check → run → inspect → publish workflow understandable with action availability and field-level reasons. Preserve drafts and give progress/stage details; avoid letting repeated button presses start duplicate runs.

Acceptance checks
Test all five definitions, missing receptors, invalid seed/parameters, cross-branch report IDs, stale baseline, concurrent runs/publications and denied viewer writes. Verify incomplete runs remain invisible as completed branches, prior runs are retrievable under permissions and every generated descendant retains synthetic provenance. Verify the relevant project/patient/branch authorization and happy/error paths against actual implementation.

Completion evidence
- Deliver applicable code, migrations, versioned configuration/prompts/schemas, generated contracts/clients, focused tests and a short runbook with actual commands. Use no protected identifiers or credentials in examples.
- Run relevant checks and report real results, denominators, failures and limits. Distinguish mocks/fixtures, live provider verification, real-data evaluation and qualified scientific review. Skipped mandatory checks are not passes.
- Update traceability, task ledger, contract decisions and release gates. Record what is implemented, what is blocked and the next recommended action. Creating a prompt or passing JSON validation is not completed scientific validation.
- Final response: behavior delivered; key files/contracts; commands/results; material limitation/dependency. Keep it concise; provide rationale and evidence, not hidden internal reasoning.
```

### COS-069 — Digital twin state, timeline and comparison APIs

```text
Task: COS-069 — Digital twin state, timeline and comparison APIs
Priority: P0 | Workstream: 09
Prerequisites: COS-039, COS-051, COS-052, COS-053, COS-054, COS-066, COS-067, COS-068; inherited Phase 1–3 governance/security/contracts apply.
Expert perspectives: Temporal API architecture, scientific comparisons and frontend synchronization.
Read: SPEC-008 states/state-build/comparison contracts; audit C01–C04; SPEC-009/010; relevant repository code/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approval you do not have. If working alone, label the review as self-review; do not assume subagents or special Muse Spark tools.

Execute this single task in the existing repository. Inspect instructions, relevant specifications, COS-AUD-001 adoption/decisions, current code/contracts and actual prerequisite evidence first. Preserve the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse existing services and the canonical /api/v1/projects/{project_id} API, with documented health/identity exceptions. Add missing contracts through versioned decisions and regenerate OpenAPI/clients/examples together; do not rewrite twelve source documents or create competing routes.

Prioritize correct working behavior, clear choices, easy next actions and complete error/recovery paths. Preserve exact patient/branch/time context, unknown values, units and immutable source/history. Keep OBSERVED/SYNTHETIC context separate from item provenance, review, availability and publication; synthetic descendants remain SYNTHETIC_GENERATED. Authorization and safe validation apply now, not only at COS-071. No unrestricted SQL/tools, unapproved data exports or paid compute.

Proceed with authorized reversible implementation. When actual provider/data/review evidence is missing, complete independent code and conspicuously synthetic fixture checks, disable the affected capability and record the exact dependency/owner. Never invent model capabilities, source rights, clinical claims or evaluation results. Use typed statuses/errors/actions and runnable examples for backend tasks; build only the requested thin integration into existing screens. Do not expose placeholders as functioning controls.

Outcome
Expose coherent revision-pinned state, timeline and comparison reads that keep the 3D view and clinical data synchronized.

Implement
1. Complete existing state list/detail, observed state-build and adopted timeline/read extensions over COS-039/051–054. Maintain one authoritative route/schema family. Return exact state/run ID, snapshot/data revision, source member IDs/times, context, missingness/conflicts and current versus historical relations. Do not reconstruct old states from mutable heads.
2. Resolve relative-time roots through the adopted C03 contract, never a self-referencing baseline. Timeline pages pin signed cursor/filter/order/revision semantics. Keep unknown times unplaced and shifted/relative time labeled; DCE phases are not extra visits. Branch reads reference a specific published run when needed for stable history.
3. Expose comparisons using deterministic services: comparable/not_comparable/insufficient_data, exact from/to IDs, lesion/metric/units, input references, values and reasons. Zero-baseline percentages are null; incompatible anatomy/functional region/diameter metrics cannot be compared. Mixed contexts explicitly identify hypothetical_vs_observed, not treatment efficacy.
4. Observed state builds accept expected revision and OBSERVED context only through the canonical command. Synthetic states come from authorized runs. Lab-only updates can retain historical geometry with its actual time/notice, never a new acquisition. State readiness/publication remains separate from queued computation.
5. Return coherent manifests with stable artifact IDs so clients resolve grants for the selected state only. Cancel/discard stale frontend responses using selection identity and snapshot hash. Include freshness and valid next actions without blending latest labs into a historical mesh snapshot.

Make the next right action easy
Selecting a timeline point must produce one identifiable state across summary, chart and 3D view. Explain unavailable comparisons, historical scans and unresolved time in plain language; retain table alternatives and source drill-down.

Acceptance checks
Test N after N+1 correction, root-relative baseline, stable pagination, late/conflicting records, lab-only states, wrong-branch comparison and zero baseline. Simulate out-of-order responses and verify old geometry cannot appear as the newly selected scan. Test unauthorized state builds and exact historical read reproducibility. Verify the relevant project/patient/branch authorization and happy/error paths against actual implementation.

Completion evidence
- Deliver applicable code, migrations, versioned configuration/prompts/schemas, generated contracts/clients, focused tests and a short runbook with actual commands. Use no protected identifiers or credentials in examples.
- Run relevant checks and report real results, denominators, failures and limits. Distinguish mocks/fixtures, live provider verification, real-data evaluation and qualified scientific review. Skipped mandatory checks are not passes.
- Update traceability, task ledger, contract decisions and release gates. Record what is implemented, what is blocked and the next recommended action. Creating a prompt or passing JSON validation is not completed scientific validation.
- Final response: behavior delivered; key files/contracts; commands/results; material limitation/dependency. Keep it concise; provide rationale and evidence, not hidden internal reasoning.
```

### COS-070 — AI interpretation, evidence and evaluation APIs

```text
Task: COS-070 — AI interpretation, evidence and evaluation APIs
Priority: P0 | Workstream: 09
Prerequisites: COS-057, COS-058, COS-059, COS-060, COS-061, COS-062, COS-063, COS-064, COS-065, COS-069; inherited Phase 1–3 governance/security/contracts apply.
Expert perspectives: AI service integration, evidence access control and scientific evaluation UX.
Read: SPEC-008 interpretation/evidence/provenance/validation routes; audit C01/D04/D05; SPEC-010/011; relevant repository code/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approval you do not have. If working alone, label the review as self-review; do not assume subagents or special Muse Spark tools.

Execute this single task in the existing repository. Inspect instructions, relevant specifications, COS-AUD-001 adoption/decisions, current code/contracts and actual prerequisite evidence first. Preserve the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse existing services and the canonical /api/v1/projects/{project_id} API, with documented health/identity exceptions. Add missing contracts through versioned decisions and regenerate OpenAPI/clients/examples together; do not rewrite twelve source documents or create competing routes.

Prioritize correct working behavior, clear choices, easy next actions and complete error/recovery paths. Preserve exact patient/branch/time context, unknown values, units and immutable source/history. Keep OBSERVED/SYNTHETIC context separate from item provenance, review, availability and publication; synthetic descendants remain SYNTHETIC_GENERATED. Authorization and safe validation apply now, not only at COS-071. No unrestricted SQL/tools, unapproved data exports or paid compute.

Proceed with authorized reversible implementation. When actual provider/data/review evidence is missing, complete independent code and conspicuously synthetic fixture checks, disable the affected capability and record the exact dependency/owner. Never invent model capabilities, source rights, clinical claims or evaluation results. Use typed statuses/errors/actions and runnable examples for backend tasks; build only the requested thin integration into existing screens. Do not expose placeholders as functioning controls.

Outcome
Expose grounded interpretations and their supporting evidence/evaluation records without exposing private candidates or a raw model proxy.

Implement
1. Complete interpretation-job submission, exact result reads and adopted C01 interpretation discovery/evaluation reads. Use state_id, input_snapshot_hash, research_summary purpose, external-mode selection and optional comparison exactly as the canonical contract defines. Reject stale/mismatched state context; no free-form external-model endpoint or general patient-data tool gateway.
2. Wire job creation to the bounded context, egress policy, candidate generation, COS-064 validation and COS-065 persistence. Explicit disallowed export returns 403 EXTERNAL_PROCESSING_NOT_ALLOWED. Provider outage may yield a labeled permitted deterministic fallback; unsupported references/claims fail with FAILED_GROUNDING. 202 never implies a validated published interpretation.
3. Return execution mode, exact model identity when available, corpus version, findings with record/measurement/passage references, limitations, uncertainties and freshness. An empty finding set with insufficient_evidence is valid. Preserve current-for-snapshot and superseded-for-current-timeline meanings; never swap in a latest-state summary for the requested old snapshot.
4. Complete authorized evidence document/passage reads, resource provenance and validation/evaluation report discovery under role/rights policy. Return permitted excerpts and safe locators; viewer access to a summary does not grant raw note, linkage or private rejected-output access. Evaluation responses include protocol/version, denominators, failures and scope, not invented confidence badges.
5. Generate consumer clients/examples and integrate the thin interpretation panel's request/status/source paths. Escape output text, restrict links to verified safe references and handle unknown future enum values safely. Persisted IDs, not model-generated URLs, drive citation navigation.

Make the next right action easy
Show whether the result is live-model, local-template or saved, and why an output was withheld or narrowed. Let viewers inspect the exact permitted support for each finding and understand evaluation limitations without opening raw internal logs.

Acceptance checks
Test policy refusal with zero transmission, grounded success, insufficient evidence, failed validation, fallback mode, stale hash and cross-patient citation IDs. Verify unpublished/rejected candidates never reach viewers, restricted passages stay redacted and evaluation reads cannot conceal failed/abstained cases. Verify the relevant project/patient/branch authorization and happy/error paths against actual implementation.

Completion evidence
- Deliver applicable code, migrations, versioned configuration/prompts/schemas, generated contracts/clients, focused tests and a short runbook with actual commands. Use no protected identifiers or credentials in examples.
- Run relevant checks and report real results, denominators, failures and limits. Distinguish mocks/fixtures, live provider verification, real-data evaluation and qualified scientific review. Skipped mandatory checks are not passes.
- Update traceability, task ledger, contract decisions and release gates. Record what is implemented, what is blocked and the next recommended action. Creating a prompt or passing JSON validation is not completed scientific validation.
- Final response: behavior delivered; key files/contracts; commands/results; material limitation/dependency. Keep it concise; provide rationale and evidence, not hidden internal reasoning.
```

### COS-071 — Authentication, authorization, request validation and API contract testing

```text
Task: COS-071 — Authentication, authorization, request validation and API contract testing
Priority: P0 | Workstream: 09
Prerequisites: COS-008, COS-014, COS-015, COS-057, COS-064, COS-065, COS-066, COS-067, COS-068, COS-069, COS-070; inherited Phase 1–3 governance/security/contracts apply.
Expert perspectives: Application security, API conformance, integration QA and release engineering.
Read: SPEC-008 HTTP/roles/errors/concurrency; SPEC-010/011; audit C01–C05/D03–D05; relevant repository code/contracts and actual prerequisite evidence.

You are the CancerOS Principal Research Engineering Lead, following COS-000 and repository AGENTS.md. Apply the listed expert perspectives with top-tier research-engineering rigor. Do not claim company affiliation, clinical credentials, independent specialist review or approval you do not have. If working alone, label the review as self-review; do not assume subagents or special Muse Spark tools.

Execute this single task in the existing repository. Inspect instructions, relevant specifications, COS-AUD-001 adoption/decisions, current code/contracts and actual prerequisite evidence first. Preserve the modular FastAPI/Next.js/PostgreSQL/private-artifact/CPU-worker architecture. Reuse existing services and the canonical /api/v1/projects/{project_id} API, with documented health/identity exceptions. Add missing contracts through versioned decisions and regenerate OpenAPI/clients/examples together; do not rewrite twelve source documents or create competing routes.

Prioritize correct working behavior, clear choices, easy next actions and complete error/recovery paths. Preserve exact patient/branch/time context, unknown values, units and immutable source/history. Keep OBSERVED/SYNTHETIC context separate from item provenance, review, availability and publication; synthetic descendants remain SYNTHETIC_GENERATED. Authorization and safe validation apply now, not only at COS-071. No unrestricted SQL/tools, unapproved data exports or paid compute.

Proceed with authorized reversible implementation. When actual provider/data/review evidence is missing, complete independent code and conspicuously synthetic fixture checks, disable the affected capability and record the exact dependency/owner. Never invent model capabilities, source rights, clinical claims or evaluation results. Use typed statuses/errors/actions and runnable examples for backend tasks; build only the requested thin integration into existing screens. Do not expose placeholders as functioning controls.

Outcome
Prove the entire API layer enforces the adopted contracts and security controls already required in every preceding task.

Implement
1. Inventory every route, role, patient/project/branch constraint, request/response schema, async command and asset/evidence access path. Close gaps in the actual Phase 1 identity/session integration; do not add a second auth system or postpone protection until this task. Verify trusted claims, session expiry/revocation, cookie CSRF/origin checks where used, bearer handling and no production mock-identity bypass.
2. Enforce independent authorization of every nested ID and idempotency replay. Apply 401 unauthenticated, 404 inaccessible patient resources, and 403 forbidden visible operations consistently. Viewer/editor/admin policy and job-scoped workers must match the contract; untrusted body fields never grant ownership, provenance, publication or privileged status.
3. Verify common HTTP behavior: strict requests/unknown filters, nullable versus omitted draft fields, decimal-string quantities, supported time unions, bounded body/list/upload sizes, signed snapshot cursors, no-store private responses, 201/Location creation, 202/Location/Retry-After job acceptance, 428/412 preconditions and atomic idempotency under concurrency. Preserve the canonical error envelope with safe field details, reason codes, request ID and retry guidance; redact internals.
4. Freeze one OpenAPI contract and regenerated TypeScript client; detect schema drift in CI and exercise real endpoint behavior against the specification. Require route-level positive/negative tests plus persistence/worker/object-store integration. No skipped mandatory test is a pass. Use isolated synthetic fixtures and verify logs/artifacts contain no secrets, source maps or signed grants.
5. Produce a compact Phase 4 evidence matrix mapping COS-057–071 and audit closures to implemented behavior, actual tests, real/live provider evidence, review-pending and blocked scope. Run focused end-to-end journeys for observation correction, approved imaging asset, simulation publication and validated interpretation/fallback. Keep deployment/public release a separate evidenced decision; passing API tests does not prove clinical suitability.

Make the next right action easy
Ensure every meaningful failure has a stable readable explanation and a valid next action, while private resource errors avoid existence disclosure. Frontend clients must handle expiry, conflict, retryable job failure and unavailable capabilities without losing user input or creating duplicate writes.

Acceptance checks
Run cross-project/patient/branch ID-swapping, role escalation, mass assignment, CSRF, expired sessions/grants, cursor tampering, idempotency races, stale ETags and malformed/oversized payload tests. Verify safe output escaping, prompt-injection nonexecution and denied egress. Report actual conformance/security failures and block affected exposure until fixed; do not claim penetration testing or certification from these checks. Verify the relevant project/patient/branch authorization and happy/error paths against actual implementation.

Completion evidence
- Deliver applicable code, migrations, versioned configuration/prompts/schemas, generated contracts/clients, focused tests and a short runbook with actual commands. Use no protected identifiers or credentials in examples.
- Run relevant checks and report real results, denominators, failures and limits. Distinguish mocks/fixtures, live provider verification, real-data evaluation and qualified scientific review. Skipped mandatory checks are not passes.
- Update traceability, task ledger, contract decisions and release gates. Record what is implemented, what is blocked and the next recommended action. Creating a prompt or passing JSON validation is not completed scientific validation.
- Final response: behavior delivered; key files/contracts; commands/results; material limitation/dependency. Keep it concise; provide rationale and evidence, not hidden internal reasoning.
```

