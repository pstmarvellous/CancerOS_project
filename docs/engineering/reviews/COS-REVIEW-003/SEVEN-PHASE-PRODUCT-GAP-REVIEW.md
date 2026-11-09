# Seven-phase delivery versus usable product

This assessment uses original phase prompts, current implementation and fresh observations. Historical ledger fields are reported as metadata only. Previous review/audit/browser conclusions were excluded.

| Phase and assigned tasks | Intended contribution | Delivered implementation visible now | Did it reach a usable product? | Required closure |
| --- | --- | --- | --- | --- |
| 1 — COS-001–015 | Authority, contracts, modular API/web, private persistence, reproducible startup | Governance, generated contracts, Next shell, FastAPI/SQL/private local services | Foundation is usable; fresh build/start succeeds. It never established medical product completion. | Keep foundation; connect acceptance to original journeys instead of phase count. |
| 2 — COS-016–040; optional 030 | Source/patient/clinical acquisition, spatial imaging, masks, measurements, mesh, immutable histories | Substantial private fixture pipeline, geometry and measurement code, source/identity controls | Phantom geometry works; authentic staging/annotation/baseline remain code-restricted. Import UI absent. | Controlled authentic-source enablement plus administrator import/QC/publication journey and independent validation. |
| 3 — COS-041–056; optional 056 | Five families, eligibility, clinical generation, repeatability, temporal integration/updates | Five executable engines, test-mode generation, snapshot/fusion/update services; prepared demo | Demo playback is useful. Ordinary generation and state synchronization are not a usable research workflow. | Typed real API builder, branch/baseline creation, jobs, exact member/time synchronization and reviewed baseline. |
| 4 — COS-057–071 | Evidence/provider/interpretation and patient/imaging/simulation/timeline API closure | Context/template/grounding/saved modules, numerous APIs | API scope is substantial. Insights UI emits invalid bodies; live agent absent; saved read misses patient authorization. | Repair contracts/ownership; integrate fallback; separately satisfy live/provider/export evidence. |
| 5 — COS-072–080 | Coherent frontend, observation/correction/import, accessible viewer, charts, scenarios, insights, guide and evaluation | Actual case/profile/manual lab slice and phantom demo; many individual screens/components | Partially delivered. Clinical refresh hangs; primary nav loses case; scenario route unusable; admin/activity placeholders; report/guide static. | Complete the end-to-end UI acceptance journey and original UX-ID traceability. This is core assigned scope, not optional polish. |
| 6 — COS-081–098 | Scientific evaluation, operations/recovery, curated real demo, rehearsal and evidence | Test/evaluation/deployment artifacts and runbooks; no independently established release dataset/deployment | No full scientific/operational acceptance demonstrated here. Existing fixture tests cannot substitute for genuine follow-up or human review. | Actual authorized cases, independent methods/review, hardware measurements, recovery trial and preflighted real demo. |
| 7 — COS-099–104 | Final integration, bounded remediation, deployed verification and freeze | Later component changes and verification artifacts; current build passes | Product cannot be frozen as accepted while ordinary routes/contracts fail. No deployed acceptance established. | Reopen acceptance against observable tasks; freeze only after separate gates have evidence. |

## What the ledger actually records

| Phase | Status metadata at inspection |
| --- | --- |
| 1 | 15 verified |
| 2 | 24 implemented_unverified; COS-030 planned |
| 3 | 15 implemented_unverified; COS-056 planned |
| 4 | 15 implemented_unverified |
| 5 | 9 implemented_unverified |
| 6 | 11 implemented_unverified; 7 blocked |
| 7 | 4 implemented_unverified; 2 blocked |

Two additional UX recovery entries are marked verified. Their reports were not used. These fields do not say that all seven phases are independently verified complete; this review does not promote them. Read the [matrix](SPECIFICATION-COMPLIANCE-MATRIX.md) for actual observed scope.

## Where acceptance drift is visible

The phase prompts explicitly assigned observation corrections/retractions and limited import review to COS-074, and real API-connected workflows across Phase 5. The present admin/activity placeholders still refer to future task completion. These are unclosed assigned deliverables.

Current tests often mount components with preselected contexts and mock successful API bodies. Real route entry passes empty context or emits a different wire format. This is direct evidence of acceptance boundaries that were too local. It does not establish which previous reviewer noticed or missed the issue; their conclusions were excluded.

The scientific acceptance boundary also narrowed in implementation: many origins and execution paths remain fixed to synthetic test fixtures. That is honest engineering scope but insufficient product scope. Original SPEC-009 §19 asks for one approved real case early, then synchronized state/chart/evidence before broad polish. The current application has a better integrated artificial demo than authentic research workspace. Recovery should close that missing vertical slice, not restart all phases or count additional UI components as completion.
