# ARCHITECTURE AND INTEGRATION REVIEW — COS-REVIEW-003

**Date:** 2026-11-05  
**Scope:** Backend/frontend integration, API contracts, DB models, imaging pipelines, simulation services, AI provider, auth, persistence, worker orchestration, provenance, error handling, complexity.

---

## 1. Backend/Frontend Integration

**Pattern:** Next.js `apps/web` proxies via `app/api/*` routes to FastAPI at `http://127.0.0.1:8000` (or env API_BASE_URL). Proxy in `research-session.ts` validates RS256, origin checks, secure transport (https or localhost only). Session cookie short-lived 30min, in-memory Map max 512.

Frontend fetches with `cache:no-store`, AbortController signal, `idempotency-key` header rotating on form change (crypto.randomUUID). Good idempotency practice.

Contract generation: `packages/contracts/generated/api.ts` + `openapi.json` via `scripts/generate_contracts.py` -> check_contract_drift guard.

**Integration gaps:**
- API base hard-coded fallback localhost — no discovery; for deployed demo, must supply env.
- `app/api/cases/route.ts` thin proxy over generated `PatientPage` contract but returns display_code + data_revision only, loses counts visible in `ResearchCases` composite (which uses `/api/research-cases` separate).
- Two different case listings: `/api/cases` vs `/api/research-cases` confusing.
- Many routes bypass proxy, directly call `API` constant `process.env.NEXT_PUBLIC_API_BASE_URL || http://127.0.0.1:8000` from browser (simulation-workflow). Cross-origin not allowed per `isSameResearchOrigin` else? Inconsistent.

**Recommendation:** Unify all research reads through same-origin `/api/*` proxies, preserve session cookie centrally, remove direct browser-to-API calls.

---

## 2. API Contracts

**Source:** `packages/contracts/` with `foundation.ts`, `clinical.ts`, `api.ts` generated.

**Strengths:**
- Typed FoundationEnvelope with origin enum, time basis (date/timestamp/relative_day/unknown), time_domain (source_calendar, simulation, source_shifted).
- Clinical contracts exhaustive: laboratory/vital with exact/censored/missing forms, units, original values preserved.
- Symptom with presence/reporter/severity/instrument.
- Treatment with event_type/exposure_status/regimen.
- Diagnosis with ER/PR/HER2/side/stage.

**Gaps:**
- Contract drift check exists (`scripts/check_contract_drift.py`) — green per phase execution notes but not re-verified this review.
- Frontend sometimes casts `components['schemas']['PatientSummary']` without null guard; backend returns `PatientPage` with items maybe outside type.

---

## 3. Database Models

**Foundational:** Migrations `0001_foundation.sql`, `env.py`, alembic. Models in `source` schema: patient_revisions with input_manifest jsonb + hash. Captures immutable revisions. Science hash verification `science_hash(manifest)!=hash → integrity failure`.

**Observations:** ObservationPage snapshot cursor for pagination. Good.

**Patient linkage:** Private versioned key ring, namespace/digest idempotent, confidence, review.

**Branch/Run:** Simulation configs versioned draft_revision, baseline_hash, config_version id. Expected draft revision optimistic concurrency (409). Good.

**Lesion:** Lesion identity persistent, UUID.

**Complexities:** Overly many run tables: preprocessing_runs, measurement_runs, mesh_runs, fusion_runs, timeline_runs, registration_runs, alignment_runs, simulation_runs, grounding_runs, evidence_runs, etc. Each with similar pattern — suggests need for general run framework but implemented as separate modules (code duplication). Could be simplified.

---

## 4. Imaging Pipeline

Flow: ingest → discovery → volumes → preprocessing → mask alignment → measurement → mesh → QC → lesion tracking → registration.

Modules tracked runs; each run produces report.

**Integration gap:**
- Imaging worker Dockerfiles exist `infrastructure/Dockerfile.api`, `Dockerfile.worker`, `Dockerfile.web` but orchestration local? `scripts/local_services.py`, `scripts/ci_services.py`.
- Imaging jobs `imaging_jobs.py` create durable jobs, but frontend `case-imaging.tsx` only displays results; upload workflow not visible.
- Mask types (analysis ROI vs anatomical contour vs bbox) distinguished in code but not in UI selector.

**Measurement correctness:**
- `physical_measurements.py` preserves origin, orientation, spacing, affine, units — correct per invariant.
- No voxel-mm confusion observed (verified earlier). Good.

---

## 5. Simulation Services

**Flow:** eligibility-checks (capability measurement vs anatomical_mesh) → config_version saved immutable → schedule preview (SampledObservations) → run creation (expect revision) → job polling (ImagingJobRecord) → completion report → separate private publication with attestation + review checkbox.

Plugins `simulation_plugins.py` likely strategy pattern per family.

**Eligibility:** `simulation_eligibility.py` separate engineering test permission vs clinical eligibility — good distinction but not explained UX.

**Publication gate:** `current-simulation` pointer + publication requires attestation text + reviewed flag — honest.

**Gap:** Publish separate private? Yet `/simulation` intro says "separate private publication". Means even after generation, run not automatically visible to evaluators — requires explicit publish action. But no UI indicating unpublished runs count.

**Branch ownership:** Enforced in backend `authorize_project` + branch_id check.

---

## 6. AI Provider Architecture

`provider_api.py` routes, `provider_gateway.py` handles Meta API `https://api.meta.ai/v1` per spec but actual provider not verified here (requires MODEL_API_KEY). Gateway likely wraps model identity check, tool grounding, export policy.

Also `knowledge_api.py`, `knowledge_runs.py`, `evidence_api.py` for curated retrieval.

Grounding API `grounding_api.py` returns GroundingReport with reason, evidence spans.

**Strengths:** Provider-neutral interface, deterministic source-of-truth flag, export denials respected.

**Gaps:**
- No frontend display of actual model identity or cost.
- `interpretation_job_api.py` vs `interpretation_api.py` duplication?
- Rate limit/timeout/bound not visible.

---

## 7. Patient & Case Authorization

`identity.py`: authenticate JWT RS256, issuer/audience/time claims, memberships. `authorize_project` role check.

`patient_api.py`: list/detail scoped to project. `context_api.py` likely similar.

`research_api.py`: research cases view requires project membership; source eligibility.

Frontend `ResearchSessionPanel` signs in via POST `/api/research-session` which calls `checkResearchWorkspace` to `/api/v1/workspace` on backend; returns projects[]. Then stores in-memory session Map, returns cookie.

**Integration:** Secure transport check only allows https or localhost loopback (`secureResearchTransport`). Good security.

**UX implication:** Because session stored in server memory (Node process), restart loses sessions; no DB persistence. Acceptable for dev but not for deployment with multiple replicas. Should be Redis? However out of scope for this review.

**Missing:** No project creation API exposed to UI; admin must use backend directly or bootstrap script.

---

## 8. Worker Orchestration

`jobs.py` central job framework; `workers/` directory. `infrastructure/compose.yaml` + `compose.staging.yaml`. Workers likely process preprocessing, segmentation QC, simulation, interpretation, grounding.

Modules: `imaging_jobs.py`, `interpretation_jobs.py`, `forecast_runs.py`, `evaluation_splits.py`, `temporal_timeline.py`, etc.

**Gap:** Job status polling loop in frontend `simulation-workflow.tsx` uses request per polling? Implementation shows `act` single request pattern, not automatic polling loop described; likely run polling requires manual refresh or effect not seen due to truncation.

---

## 9. Provenance & Lineage

`lineage.py`, `source_registry.py`, `persistence.py` provide `REAL_OBSERVED`, `REAL_DERIVED`, `SYNTHETIC_GENERATED`, `INTERPOLATED`, `MODEL_PREDICTED` distinctions.

Frontend `ProvenanceBadge` renders symbol + label + kind (observed/derived/simulated/warning). Time label shows basis. Good.

**Gap:** Badge color-only complement with symbols — symbols help but need explicit legend page. `ResearchCases` card uses badge but not full legend.

---

## 10. Error Handling

Thorough 401/403/404/409/412/422 explanations per component (`explain` functions per file). Messages tailored: "Sign in with an authorized session", "This project restricted for your role", "Record unavailable in this context", "Current QC or source permission blocks display", "Record or revision changed — reload", "Configuration rejected".

Idempotency key per request prevents double-save.

**Gap:** Errors pessimistic, not corrective enough (do not say how to obtain token or create source). Retry buttons exist but limited.

---

## 11. Essential vs Excessive Complexity Classification

| Item | Classification | Justification |
|---|---|---|
| RS256 JWT + session + secure transport + same-origin check | Essential | Safety requirement |
| Provenance five kinds + immutable revision + hash | Essential | Scientific integrity |
| Treatment assumption gate blocked | Essential (with poor UX) | Prevents unsupported claims |
| Separate private publication with attestation | Essential (with poor UX) | Evaluation integrity |
| UUIDs in UI under details | Unnecessary complexity — should be hidden | Leaks internal IDs |
| Two timeline routes `/timeline` vs `/states` | Unnecessary duplication | Should merge |
| Many run tables without generic framework | Unnecessary complexity | Framework would simplify |
| Manual UUID inputs in `/simulation` | Missing workflow integration, not essential complexity | Should be picker |
| Direct browser-to-API calls alongside same-origin proxies | Unnecessary complexity | Unify proxy |
| `preserveSelection` trying to keep 6 query params across nav | Necessary but fragile | Better single workspace route |
| Multiple button classes without design system | Unnecessary complexity | Tokenize |
| Case library inside `<details>` collapsed even after auth | Missing integration — not intentional | Should auto-open |

---

## 12. Recommended Architectural Changes (Minimal Effective)

1. **Single workspace route** `/workspace?project=&patient=` rendering tabs instead of separate top pages; reduce preserveSelection fragility.
2. **Proxy unification:** All API reads via `/api/*` same-origin, delete direct `NEXT_PUBLIC_API_BASE_URL` usage from client.
3. **Run framework abstraction:** Generic `run_record` table + typed payload, reduce duplication.
4. **Project/source bootstrap UI:** Add `/admin` page features to create source, invite token generation (dev only) — even if admin-only.
5. **3D viewer prominence:** Make viewer component accept `className` 65% viewport, measurement badge inside.
6. **Scenario builder:** Replace JSON draft with form: family select → assumption cards → schedule preview → eligibility → freeze.

