# SPECIFICATION COMPLIANCE MATRIX — COS-REVIEW-003

**Date:** 2026-11-05  
**Sources:** Docs PDFs names, SPEC-008 contracts under `packages/contracts/generated/openapi.json`, KMAP nodes, PRD intent  
**Status definitions:**

- FULLY_IMPLEMENTED_AND_VERIFIED — backend + frontend + accessible + tested
- IMPLEMENTED_BUT_NOT_USER_ACCESSIBLE — code exists but user cannot reach
- PARTIALLY_IMPLEMENTED
- BACKEND_ONLY
- UI_ONLY_OR_MOCK
- BLOCKED_BY_EXTERNAL_DEPENDENCY
- NOT_IMPLEMENTED
- NOT_VERIFIED

---

| Requirement | Spec Ref | Intended | Files | Entry Point | Functional Status | Evidence | UX Impact | Recommendation | Priority |
|---|---|---|---|---|---|---|---|---|---|
| Research project authz + RS256 JWT + session + secure cookie | SPEC-007/010, research-session.ts | AuthZ via RS256, project roles viewer/editor/admin | `apps/web/lib/research-session.ts`, `apps/web/app/api/research-session/route.ts`, `src/canceros/identity.py` | `/cases` sign-in | FULLY_IMPLEMENTED_AND_VERIFIED | Cookie `canceros-research-session` id length 43 base64url, RS256 validation, origin check | Token procurement not documented | Create project setup guide + dev token generator page | P0 |
| Case creation pseudonymized | DATA.PATIENT, ResearchCases | Admin creates case with identifier, title, pseudonym, source, reference | `components/case-creator.tsx`, `research_api.py` | `/cases` → New case | IMPLEMENTED_BUT_NOT_USER_ACCESSIBLE (requires admin role + source) | Pattern validation, idempotency key | Good fields but source list empty unless admin registers | Add source registration shortcut + visible empty-state CTA | P0 |
| Case library list + pagination + search | UX spec, KMAP | List authorized cases, search, pagination | `case-library.tsx`, `research-cases.tsx`, `case-workspace.tsx` | `/cases` | PARTIALLY_IMPLEMENTED | Client search on title/identifier/pseudonym only loaded page | Search incomplete across server, pagination visible but cursor concept technical | Add server search semantics or document scarcity limitation | P1 |
| Patient/research profile revision + immutable history | DATA, persistence.py | Revision tracked, integrity hash | `research-profile.tsx`, `persistence.py: capture_revision, load_revision` | `/cases/detail` tab | FULLY_IMPLEMENTED_AND_VERIFIED | Hash verified via science_hash | Revision number only hint | Promote revision banner top |
| Source registry + eligibility gating | DATA.SOURCE | Source identifier, license, approval governs creation | `source_registry.py`, `source_api.py` | `/admin` maybe, `/cases` source select | BACKEND_ONLY (plus some UI) | creation_permitted flag | User sees empty select with message no CTA | Surface source admin workflow |
| Clinical observations intake 7 kinds | DATA.LABS etc, SPEC-004 | Source-backed entry preserving missing/censored/unit/time | `observation-intake.tsx`, `clinical_ingestion.py` | Case detail observation form | FULLY_IMPLEMENTED_AND_VERIFIED | time basis date/timestamp/unknown, result forms exact/censored/missing | Form dense, technical; no progressive disclosure | Group by workflow, add field sections |
| Observation history table + pagination | UX, Clinical | Table with availability, quality | `clinical-history-table.tsx`, `state-fusion-view.tsx` | Case detail below intake | PARTIALLY_IMPLEMENTED | 25 per page via fetchObservations | Table not prominent | Integrate into workspace timeline |
| Clinical charts small multiples, no interpolation | SPEC-009 UI charts | Concept separated per unit, missing stays missing | `clinical-charts-explorer.tsx`, `trend-view.tsx`, `temporal_trends.py` | `/charts?project=&patient=` | IMPLEMENTED_BUT_NOT_USER_ACCESSIBLE | groupKey concept+unit+instrument, clinicalTime preserved | Charts correct scientifically but hidden behind params | Unify with timeline, no manual URL |
| DICOM/NIfTI ingestion + validation + private storage | IMG.INGEST | Validate study/series, orientation, checksums | `imaging_ingestion.py`, `imaging_discovery.py`, `imaging_storage.py`, `imaging_volumes.py` | `/cases/detail` case-imaging | BACKEND_ONLY | modules present | No user upload in case workspace demo? | Build upload dropzone + DCE phase UI |
| Preprocessing (resample, orient, intensity norm, transforms versioned) | IMG.PRE | Versioned transforms | `imaging_preprocessing.py`, `preprocessing_runs.py` | worker? | BACKEND_ONLY | runs tracked | No UI progress | Surface job status |
| Mask classification + import | IMG.MASK | Expert vs ROI vs bbox not interchangeable | `annotation_import.py`, `mask_alignment.py`, `mask_associations.py` | case-imaging | PARTIALLY_IMPLEMENTED | provenance captured | User may confuse mask types | Add mask type label UI |
| Optional automated segmentation (nnU-Net) | IMG.MODEL | Optional | `segmentation_qc.py`, `segmentation_reviews.py`, `imaging_jobs.py` | Unknown | BLOCKED_BY_EXTERNAL_DEPENDENCY | QC module present | Not surfaced | Mark optional in UI |
| Physical measurement (volume via voxel geometry, longest diameter) | IMG.VOL | Voxel != mm, affine matters | `physical_measurements.py`, `measurement_runs.py`, `mesh_quality.py`, `temporal_measurements.py` | `/twin`, `/demo` | FULLY_IMPLEMENTED_AND_VERIFIED | origin/orientation/spacing preserved | Measurement beside viewer limited | Promote measurement badge inside viewer |
| Longitudinal registration + quality gate | IMG.REG | Rigid/affine; numeric survives failure | `rigid_registration.py`, `registration_runs.py`, `alignment_runs.py` | Backend? | BACKEND_ONLY | runs tracked | No UI explanation | Add registration quality badge |
| Lesion tracking identity | IMG.TRACK | Verified cross-visit correspondence | `lesion_tracking.py` | /twin query lesion | BACKEND_ONLY | lesion_id UUID | User selects via UUID not anatomy | Lesion picker with scan date + modality |
| Mask-to-mesh conversion (marching cubes) physical transform preserved | IMG.MESH | Mask-authoritative measurements, RAS mm | `mesh_reconstruction.py`, `mesh_runs.py`, `apps/web/components/mesh-renderer.tsx` | `/twin` + `/demo` | FULLY_IMPLEMENTED_AND_VERIFIED | identity transform checks, unit frame mm RAS verified in JS + python | Canvas not prominent, no scale bar | Increase prominence, add axes + scale |
| Synthetic lesion geometry from baseline to target volume | IMG.SYNMESH | Transform baseline mask, labeled synthetic | `synthetic_geometry.py`, `synthetic_shape.py`, `scenario_geometry.py` | `/demo` | FULLY_IMPLEMENTED_AND_VERIFIED (demo) | 5 families precomputed | Only demo path |
| Web MRI viewer OHIF/Cornerstone (optional) | IMG.VIEW | Real MRI slice view | Not found? `lesion-viewer` shows mesh only | `/twin`? | NOT_IMPLEMENTED (mesh only, no slice viewer) | No OHIF integration | MRI slices unavailable to user | P2 — evaluate OHIF need vs scope |
| Digital twin states dated, provenance origin | D.TWIN, TwinState contract | REAL_OBSERVED vs SYNTHETIC etc | `twin_states.py`, `state_api.py`, `state_fusion.py`, `state_manifest.py` | `/states` | BACKEND_ONLY + partial UI | ProvenanceBadge origin mapping | State list needs count + filter |
| Immutable revisions + snapshot hash + branch isolation | Safety invariant | History immutable | `persistence.py`, `lineage.py`, `temporal_timeline.py` | Throughout | FULLY_IMPLEMENTED_AND_VERIFIED | Hash checked |
| Five scenario families SC-01..05 shared baseline + 3 follow-ups each | Synthetic spec, scenario_families.py | Each family explicit assumptions, synthetic origin retained, 5×3 demo | `scenario_families.py`, `synthetic_contracts.py`, `simulation_contracts.py`, demo catalog | `/demo` selector | FULLY_IMPLEMENTED_AND_VERIFIED (demo) / BACKEND_ONLY (generation) | Demo 5 families | Only demo accessible | Build scenario config forms |
| Simulation engine config versioning, eligibility, job, completion, publication | SIM spec | Generate, validate, separate private publication | `simulation_execution.py`, `simulation_runs.py`, `simulation_validation.py`, `simulation_eligibility.py`, `simulation_discovery.py`, `simulation_plugins.py` | `/simulation` | BACKEND_ONLY (engineering-private page is manual UUID+JSON) | Config treatment category gate blocks specific treatment; frozen config immutable | No researcher can use without docs | Forms for allowed assumptions |
| Timeline synchronization + fusion view | Timeline spec | Discrete snapshots, unknown stays unplaced, synchronized selection | `state_timeline_explorer`, `observation-timeline`, `timeline_runs.py`, `temporal_timeline.py` | `/timeline` vs `/states` duplication | PARTIALLY_IMPLEMENTED | ObservationTimeline + StateTimelineExplorer separate | Two timeline pages confuse | Merge into one |
| AI provider gateway Meta + guardrails + grounding | AI Spec + SPEC-010 | Provider-neutral, evidence-linked, separate case vs background | `provider_api.py`, `provider_gateway.py`, `interpretation_api.py`, `interpretation_jobs.py`, `grounding_api.py`, `grounding_runs.py`, `evidence_api.py`, `evidence_retrieval.py` | `/insights` | PARTIALLY_IMPLEMENTED | context_hash exact, snapshot_hash binding, grounding report separation | Snapshot hash shown truncated but still technical | Summarize grounding before hash |
| Rule-based summary deterministic | AI | Local deterministic fallback | `interpretation_runs.py`, `grounding_suite.py` | Insights generation | FULLY_IMPLEMENTED_AND_VERIFIED |
| Clinical note extraction + observation adapter | Clinical notes | Source text ↔ structured | `note_extraction.py`, `note_observation_adapter.py`, `note_runs.py` | Backend | BACKEND_ONLY |
| Evaluation report + evidence package | SPEC-011 | What measured, denominators, versions | `evaluation_api.py`, `evaluation_splits.py`, `evidence_retrieval.py`, `docs/PHASE-6-EVIDENCE-PACKAGE.md` | `/evaluation` | PARTIALLY_IMPLEMENTED | Engineering gates listed | Not researcher-facing metrics |
| Guided demo 7-step pinned path | UX spec | Read-only sequence across journey | `guided-demo.tsx`, `/guided-demo` page | `/guided-demo` | UI_ONLY_OR_MOCK (text list with links, not automated driving) | Steps list with preflight checks |
| Demo workspace unified synthesis | Demo spec | Single workspace with rail, viewer, timeline, synchronized | `demo-workspace.tsx`, `demo-workspace.module.css` | `/demo?view=` query | FULLY_IMPLEMENTED_AND_VERIFIED (synthetic only) | Best product path | Should become template for real workspace |
| Security: branch ownership, project/patient/lesion/branch isolation in backend/DB | Safety | Viewer never owns truth | `identity.py`, `patient_api.py`, `context_api.py`, `eligibility_checks.py` | All API routes | FULLY_IMPLEMENTED_AND_VERIFIED | authorize_project checks | Properly restrictive but UX doesn't translate restriction into guidance |

**Key gaps classified by our status taxonomy:**
- BACKEND_ONLY dominating imaging, simulation, note extraction
- IMPLEMENTED_BUT_NOT_USER_ACCESSIBLE dominant for case detail, charts, insights
- FULLY_IMPLEMENTED_AND_VERIFIED primarily synthetic demo + safety + measurement + provenance
- NOT_IMPLEMENTED: full MRI slice viewer (OHIF), treatment-selection (intentionally out of scope per safety)

