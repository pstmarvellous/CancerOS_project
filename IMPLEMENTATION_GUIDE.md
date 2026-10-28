# CancerOS implementation reference guide

Created: 2026-10-27. Status: navigation and execution reference derived from four
instruction documents. This guide does not replace specifications, adopt unresolved
design proposals, or certify implementation, scientific validity, or hackathon eligibility.

## 1. Read the sources by responsibility

| Source | What to consult it for |
| --- | --- |
| [COS-000: agent persona](docs/agent_prompt/agent-persona.md) | Leadership, specialist perspectives, scientific judgement, task execution and honest reporting; especially sections 3–8 and 11. |
| [Repository instructions, v2](docs/agent_prompt/AGENTS.md) | Authority, dual-map refresh, invariants, architecture, evidence records and Phase 1 boundaries; sections 2–8. |
| [COS-HACK-001: hackathon directive](docs/agent_prompt/hackathon_compliance.md) | Competition-specific restrictions, Meta adapter, export controls, contribution records, demo and verification; sections 2–6 and 9–19. |
| [COS-REF-001: reference integration blueprint](docs/agent_prompt/Repository_usage_prompt.md) | Upstream investigation, licensing, adapters, canonical artifacts, vertical slice and integration acceptance; sections 2–3 and 14–23. |

Read the original section for consequential decisions. This summary is not a
substitute for source inspection.

## 2. Resolve authority before changing behavior

1. Follow higher-priority instructions and the current explicit user request.
2. Use the twelve governing source specifications and recorded adopted decisions
   for product contracts. Apply COS-AUD-001 as a reconciliation overlay only where
   its decisions are actually adopted.
3. Respect domain ownership: SPEC-008 for finalized API/wire contracts, SPEC-007
   for architecture, SPEC-009 for UI, SPEC-010 for safety, SPEC-011 for evaluation,
   and PRD/SPEC-003–006 for product and clinical meaning. Verify identities in the
   source documents; filenames alone do not establish document IDs or approval.
4. Apply COS-HACK-001 to competition constraints and Meta integration without
   replacing scientific or architectural contracts.
5. Use maps, academic sources, papers and repositories to inform implementation;
   they do not independently authorize scope or resolve an adopted-contract conflict.

Record real conflicts. Resolve routine reversible choices within scope. Ask for a
decision only when a material unresolved conflict affects scope, scientific meaning,
data rights, security or a major contract. Continue independent authorized work.
Do not rewrite specifications or map sources without explicit owner direction.

## 3. Product target and boundaries

The intended experience is:

**Authorized authentic breast MRI → verified lesion mask → deterministic physical
measurements and 3D mesh → immutable observed baseline → five explicitly hypothetical
scenario families → synchronized clinical timeline → evidence-linked research comparison.**

CancerOS is a research/hackathon prototype. It must not provide autonomous diagnosis,
staging, prescribing, individualized treatment ranking, or unsupported survival or
treatment-success predictions. Scenario curves are demonstrative hypotheses.

Prefer the established modular FastAPI backend, Next.js/TypeScript research web,
PostgreSQL, private object storage and optional CPU/GPU imaging worker. Use central
contracts and thin adapters. Additional infrastructure or models need a justified,
adopted scope decision. Accommodate the limited-memory development laptop.

## 4. Locate the maps and specifications

The paths below were found locally when this guide was created. Preserve their
existing spelling; do not create duplicate maps to match older example paths.

| Resource | Actual local location |
| --- | --- |
| Capability map and retrieval protocol | [Knowlage_map_1](docs/Agent_knowledge_map/Knowlage_map_1/), including `COS-KMAP-001.md`, `canceros-knowledge-graph.json`, `AGENT-KNOWLEDGE-REFRESH.md` |
| Academic map and reading protocol | [Knowlage_map_2](docs/Agent_knowledge_map/Knowlage_map_2/), including `COS-ACA-KMAP-002.md`, `knowledge-map.json`, `behavior-index.json`, `academic-source-register.json`, `AGENT-ACADEMIC-PROTOCOL.md` |
| Repository and scientific reference maps | [reference-maps](docs/Agent_knowledge_map/CancerOS_Repository_and_Scientific_Knowledge_Maps/reference-maps/), including repository/scientific registers and `shared/AGENT-DUAL-MAP-PROTOCOL.md` |
| Source specifications and audit | [docs](docs/); inspect PDF document identities and versions before assigning authority |
| Task prompt series | [agent_prompt](docs/agent_prompt/), including [Phase 1 v2](docs/agent_prompt/CancerOS_Phase_1_Prompt_Series_v2.md) and Phase 2–7 files |

From the workspace root, after inspecting the scripts, replace `segmentation` with
the assigned task's terms or exact node/behavior ID:

```powershell
python -X utf8 docs/Agent_knowledge_map/Knowlage_map_1/query_map.py segmentation
python -X utf8 docs/Agent_knowledge_map/Knowlage_map_2/query_academic_map.py segmentation
python -X utf8 docs/Agent_knowledge_map/CancerOS_Repository_and_Scientific_Knowledge_Maps/reference-maps/shared/query_references.py segmentation
```

These are usage examples, not recorded successful query results. A map entry is a
pointer, not proof that its book was read, repository reproduced, or paper verified.

## 5. Apply this workflow to each assigned implementation task

1. **Inspect:** current instructions, working tree, existing code, task ledger,
   adopted decisions, requirement IDs and applicable specification sections.
   Preserve user changes. Check Git availability rather than assuming it exists.
2. **Bound:** state deliverables, dependencies, acceptance conditions and relevant
   specialist perspectives. Use actual delegated review only when appropriate;
   otherwise describe specialist self-review accurately.
3. **Refresh:** query both core maps and relevant repository/scientific maps.
   Record exact node/behavior IDs. Expand dependencies and incoming/outgoing
   `CONSTRAINS`, `GUARDS`, `EXCLUDES`, `VERIFIES`, `WORKFLOW_PRECEDES` edges.
4. **Learn:** read applicable mapped academic sections, inspect upstream APIs at
   pinned versions, and check empirical population/modality/endpoint support.
   Record inaccessible material and absent evidence. Domain reading may be marked
   not applicable with a reason for routine styling/build work.
5. **Decide:** define owned input/output contracts, provenance, algorithm/interface,
   alternatives, missingness, error handling, negative tests and acceptance limits.
6. **Implement:** make minimal integrated changes within the established architecture.
   Do not automatically execute other COS tasks or add upstream features.
7. **Review and verify:** explicitly examine clinical meaning, privacy, physical
   geometry and scientific claims where relevant. Run meaningful checks on approved
   fixtures, record exact commands and outcomes, and distinguish mocks from real data.
8. **Record and report:** update implementation status separately from original maps.
   Describe implemented/verified, implemented/unverified, blocked, deferred and
   not-evaluated items accurately, with the next dependency.

For substantial changes, use `docs/engineering/reference-reviews/<TASK-ID>.md`.
Include scope; requirement and map IDs; queries/edges; Source Learning Record
(author, title, verified edition/section, principle, assumptions, failures, relevance,
link); upstream SHA/release, inspected APIs and separate licenses; experiment outcome;
empirical scope; Three-Source Decision Note; changed files; tests; gaps; next action.
The decision note connects academic principle → candidate implementation → empirical
support → CancerOS decision → verification. Explicitly mark missing categories.

Use the task ledger/checkpoints when established. Source instructions name
`docs/engineering/task-ledger.json`; do not invent completed entries. Distinguish
`planned`, `in_progress`, `blocked`, `implemented_unverified` and `verified`.

## 6. Enforce these invariants throughout

- Keep `REAL_OBSERVED`, `REAL_DERIVED`, `SYNTHETIC_GENERATED`, `INTERPOLATED` and
  `MODEL_PREDICTED` distinct. Derived computations on synthetic branches retain
  synthetic origin. Preserve source history through immutable records or explicit revisions.
- Enforce project/patient/visit/lesion/branch ownership in backend and database
  controls. The viewer does not own authoritative state.
- Preserve origin, orientation, spacing, affine transforms and units. Voxel indices
  are not millimeters; mesh coordinates need defined physical transforms.
- DCE phases are not follow-up visits. Functional enhancement masks, bounding boxes
  and anatomical lesion contours are not interchangeable. Tumor volume is not a
  clinical response classification.
- Keep missing values missing. Preserve original times, synthetic-relative time,
  actual units and source quality. Never invent biomarkers, stage, dates or laboratory values.
- Compute measurements and trends outside the LLM. Ground numerical claims in
  returned observations and citations in evidence actually supporting the claim.
- Deny external source-data export by default until permissions, minimization,
  credentials and policy gates are verified. Keep secrets, restricted data,
  unauthorized weights and signed artifact links out of public artifacts.
- Keep deterministic measurements, source-mask import and core twin workflows usable
  when optional segmentation inference or external LLM services fail.
- Do not equate passing mocks, valid JSON, completed jobs or a running app with
  real-data performance, published results, clinical validation or release readiness.

## 7. Reuse upstream components through owned contracts

Prioritize investigation of MAMA-MIA, nnU-Net v2, 3D Slicer geometry workflows,
OHIF/Cornerstone3D, IDC Index and relevant MONAI modules. Consult COS-REF-001 for
each repository's experiments and acceptance criteria. dcmqi, MONAI Label/Deploy,
radiomics and alternative segmentation are conditional or optional as specified.

For adoption: inspect actual code; pin SHA/release; check code, checkpoint, dataset
and annotation rights separately; reproduce a minimal compatible example; measure
resources; validate geometry; choose adopt/adapt/study/reference/defer/reject.
Use approved reference masks if inference is unavailable. Do not assume checkpoints
exist or published benchmarks transfer to CancerOS.

Finalize canonical contracts under SPEC-008: `ImagingVolumeArtifact`,
`SegmentationArtifact`, `TumorGeometryArtifact`, `TwinState`, `ModelInferenceResult`
and `ClinicalInterpretation`. The blueprint's field lists require reconciliation
with the adopted wire contract; they are not evidence of existing runtime schemas.

As relevant work proceeds, maintain `research/reference-audits/<repository-name>.md`
and the reference compatibility matrix, license/model registers, reproduction ledger
and integration backlog named in COS-REF-001 sections 17–18.

## 8. Follow dependency gates

| Gate | Required result before proceeding |
| --- | --- |
| Assigned Phase 1 governance, COS-001–008 | Authority, reconciliation, traceability, standards, safety, change control, verification and integration contracts addressed under their individual prompts. |
| Assigned Phase 1 foundation, COS-009–015 | Lightweight coordinated repository, backend, frontend, persistence, startup, configuration and CI verified for their actual scope. Plumbing does not establish medical capabilities. |
| Upstream verification and first imaging slice | Authorized MRI/mask, correct physical measurements and browser mesh, with comparison to an independent reference. |
| `VERTICAL-REF-001` | One authentic baseline plus one synthetic follow-up, distinct IDs, synchronized clinical records, correct provenance, evidence-linked interpretation and repeatable execution. Pass before expanding all five scenarios. |
| Scenario and intelligence expansion | Reproducible branches, clinical synchronization, grounded comparisons, failure handling and appropriate evaluation under governing specifications. |
| Demo/release | Functional integrated workflow, meaningful tests, scientific/privacy safeguards, attribution and competition requirements actually checked. |

Consult each prompt's exact dependencies. Do not treat this table as authorization
to execute all phases or as evidence that any gate has passed.

## 9. Apply the hackathon overlay selectively

COS-HACK-001 specifies substantive Meta use for a bounded, tool-grounded research
agent. Preserve the provider-neutral interface and deterministic source of truth.
Allow approved read-only tools, validate CancerOS schemas, enforce export policy,
bound retries/timeouts and costs, and record actual model identity.

The directive names `https://api.meta.ai/v1`, `muse-spark-1.3`, `MODEL_API_KEY` and a
preferred Responses API. These are document-stated targets, not verified provider
capabilities. Before implementation, verify official documentation, authenticated
model availability, access, terms and competition eligibility. Optional models
must not delay the core vertical slice or replace specialist imaging without evidence.

Maintain compact implementation records in `docs/hackathon/`, including
`HACKATHON-CONTRIBUTIONS.md` when contributions exist. Preserve true dates/history
and attribute reused work. The directive calls for a public repository and a maximum
three-minute functioning demo; publication/submission remain separate actions.
Verify official schedules and rules before release rather than treating this guide
as current organizer confirmation.

Track HACK-TEST-001–010: API connectivity, actual model identity, authorized tools,
numerical grounding, synthetic provenance, medical-advice restrictions, outage
handling, export controls, repository hygiene and reproducible demonstration.
Report each real result; one passing check does not establish overall compliance.
For affected implementation reports, include the source-required **Hackathon
Compliance Impact**: applicability, model/rule, changed files, contract impact,
passed checks and remaining blocked/unverified requirements.

## 10. Baseline limits and maintenance

At creation, the workspace contained `docs/` and `Data_folder/`; no application
implementation or task ledger was found in the inspected file inventory, and
`git status --short` reported that the workspace was not a Git repository.
These are dated observations, not permanent assumptions; inspect again per task.

This guide was derived from the four Markdown documents, with supporting local
path and query-script inspection. The source PDFs were not substantively reviewed,
external models/rules were not verified, and no scientific experiments or product
tests were run to create it. Academic/repository/empirical design records are not
applicable to this documentation-only consolidation; future engineering decisions
still require the process above.

Keep this guide concise and update navigation when local paths or adopted sources
change. Preserve original specification/map content. Do not claim COS-001 or any
implementation phase completed merely because this guide and entry point exist.
