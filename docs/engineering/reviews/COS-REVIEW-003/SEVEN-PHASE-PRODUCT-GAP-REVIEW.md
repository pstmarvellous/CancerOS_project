# SEVEN PHASE PRODUCT GAP REVIEW — COS-REVIEW-003

**Review ID:** COS-REVIEW-003-D  
**Task ledger:** `docs/engineering/task-ledger.json` — 106 tasks total: 15 verified (Phase1), 78 implemented_unverified (2-7), 9 blocked, 2 planned.  
**Source:** phase-*-execution.md stubs, ledger, git composition.

---

## Phase 1: Governance (COS-001–008) — Verified

**Delivered:** authority-and-scope, reference-consultation-policy, standards, safety-invariants, change-control, verification-matrix, architecture decisions.  
**Status:** `verified` 8 tasks.

**Product translation:** None direct; governance docs exist but do not surface to user. Safety invariants (provenance five kinds, immutable history, missing stays missing, DCE≠visits) are implemented in backend and partly in UI, but not explained to researcher.

**Gap:** Safety as code checks, not as UX education. Product gap: researchers need plain-language safety banner + provenance legend beyond badge symbols.

---

## Phase 2: Foundation Storage & Ingestion (COS-016–029, 031–040)

From ledger: COS-016..029 implemented_unverified (14 tasks), COS-030 planned, COS-031..040 implemented_unverified (10 tasks). Covers? Likely: persistence foundation, source registry, imaging ingestion, preprocessing, mask alignment, measurement runs, mesh runs, patient linkage, clinical ingestion, annotation import etc.

Evidence in code:
- `persistence.py`, `source_registry.py`, `imaging_ingestion.py`, `imaging_discovery.py`, `imaging_storage.py`, `imaging_volumes.py`, `mask_alignment.py`, `mask_associations.py`, `measurement_runs.py`, `mesh_runs.py`, `mesh_reconstruction.py`, `patient_runs.py`, `patient_linkage.py`, `clinical_ingestion.py` etc.

**What became usable product:** Measurement reports (mm³) used by twin viewer — yes, surfacing. Mesh asset delivery for demo — yes. Imaging volumes — not surfaced beyond `/twin` guard. Clinical ingestion — observation intake form works.

**What didn't become usable:**
- Preprocessing runs tracked but no progress UI.
- Mask alignment runbook exists but no quality badge in twin view beyond "Retry 3D" fallback.
- Source registry commands present (`source_api.py`) but researcher never sees source registration UI.

**Root cause:** Phase delivered durable storage + contracts but deferred visualization and case workspace orchestration. Acceptance assumed "code exists" not "user can complete task".

---

## Phase 3: Simulation & Twin State (COS-041–055, 056 planned)

Tasks COS-041..055 — 15 tasks implemented_unverified per ledger.

Modules: `scenario_families.py` (SC-01..05 definitions), `scenario_geometry.py`, `synthetic_geometry.py`, `synthetic_shape.py`, `synthetic_contracts.py`, `simulation_contracts.py`, `simulation_execution.py`, `simulation_plugins.py`, `simulation_validation.py`, `simulation_eligibility.py`, `simulation_discovery.py`, `twin_states.py`, `state_fusion.py`, `state_manifest.py`, `temporal_timeline.py`, `timeline_runs.py`, `timeline_source.py`, `temporal_measurements.py`, `temporal_trends.py`, `fusion_runs.py`, etc.

**Product outcome:**
- Twin states + provenance + timeline + fusion reports implemented backend.
- Demo synthetic catalog precomputed scenario geometries and timeline points (baseline_reference + mask_realized) — fully usable.
- Research scenario GENERATION (new runs) only via `/simulation` engineering private page requiring UUID + hand JSON + admin token + attest reviewed.
- No researcher scenario builder (forms for treatment=no_specific_assumption).

**Gap:** Reproducible branches, clinical synchronization concept satisfied in backend, but user workflow to create branch from baseline state absent. Timeline sync implemented (demo-workspace sync state <-> measurement <-> chart) but only synthetic.

---

## Phase 4: Intelligence & Evidence (COS-057–071)

15 tasks implemented_unverified.

Modules: `interpretation_api.py`, `interpretation_jobs.py`, `interpretation_runs.py`, `grounding_api.py`, `grounding_runs.py`, `grounding_suite.py`, `evidence_api.py`, `evidence_retrieval.py`, `evidence_contracts.py`, `note_extraction.py`, `note_observation_adapter.py`, `knowledge_api.py`, `provider_api.py`, `provider_gateway.py`, `research_api.py`, `research_workspace.py`, etc.

**Product outcome:**
- Interpretation context binding snapshot_hash + context_hash + branch + state — rigorous.
- Rule-based summary + external_private Meta candidate separation correct.
- Grounding reports with exact evidence opening.
- But frontend requires branch/state context IDs manually.
- No AI progress streaming (design intends non-streaming per safety), but no UX loading cues.
- Research workspace APIs present but front-end `research-cases` sign-in friction high.

**Gap:** Intelligence reads as technical status dashboard, not as researcher helper. Evidence-linked insight is present but not compelling visually.

---

## Phase 5: UX Shell & Productization (COS-072–080)

From execution notes: COS-072 AppShell with URL-owned selection, primary/case nav, safety notice, capability states. COS-073 real API-connected case library over PatientPage. Remaining COS-074..080 noted as implemented_unverified (not detailed; likely: lesion viewer, state timeline, charts, insights, simulation, evaluation, guided demo).

Files delivered: `app-shell.tsx`, `research-cases.tsx`, `case-library.tsx`, `lesion-viewer.tsx`, `mesh-renderer.tsx`, `state-timeline-explorer`, `clinical-charts-explorer`, `insights-explorer`, `simulation-workflow`, `guided-demo`, `demo-workspace`.

**Product outcome:**
- `AppShell` provides header brand, selection under details, nav lists, case nav conditional. Good navigation ownership concept but leaks UUIDs under details.
- Case library real API-connected, role-aware, empty/failed/missing/empty states, retry. Best improvement.
- Lesion viewer functional but not prominent.
- Charts explorer correct scientific handling but hidden.
- Insights explorer correct provenance but technical.
- Simulation workflow manual JSON.
- Demo workspace polished — fully usable synthetic product.
- Guided demo text-list only.

**Gap:** Shell built late; did not retrofit all pages into single workspace; left two timeline routes; left simulation as engineer page; left visual design inconsistencies.

---

## Phase 6: Evidence & Hardening (per docs/PHASE-6-EVIDENCE-PACKAGE.md)

Evidence package indicates evaluation, contracts, implementation verification. But not product usability.

---

## Phase 7 (incomplete per schedule?)

Implementation roadmap mentions demo/video/submission.

**Overall drift analysis:** Each phase satisfied engineering acceptance (module exists, test passes, ledger entry implemented_unverified) but never validated end-to-end research journey by naive user. Ledger shows 78 implemented_unverified vs 15 verified — verification stopped after Phase1 foundation. No phase gate required browser journey without UUIDs. Demo became surrogate.

**Consequence:** Backend strong, demo usable, real research case workflow fragmented across query params.

