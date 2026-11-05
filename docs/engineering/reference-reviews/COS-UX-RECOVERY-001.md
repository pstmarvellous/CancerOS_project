# COS-UX-RECOVERY-001 reference context

Scope: assigned implementation task; specialist self-review through architecture,
data-integrity/security and verification perspectives; no independent clinical review.

Queries executed: viewer, timeline, authorization against capability, academic and repository/scientific maps.
Exact commands, output, IDs and incoming/outgoing dependency/guard/verification edges:
[COS-UX-RECOVERY-001.json](COS-UX-RECOVERY-001.json). Unmatched queries are gaps, not successful source reviews.

Original specification sections inspected: COS-SPEC-009 v1.0 sections 1–4.3,
4.5, 4.7–4.9, 11–12; COS-SPEC-008 v1.0 sections 13.3–13.6, 17, 19;
COS-SPEC-010 v1.0 sections 2, 7. Original PDFs text-extracted using pypdf.
Agent guidance: COS-000 sections 3–8/11; repository instructions sections 2–8;
COS-REF-001 sections 2–3/15–23; COS-HACK-001 sections 2–3/9/11/17.

## Source Learning Record and Three-Source Decision Note

Map source IDs are retrieved pointers only. Academic text, upstream interfaces and
empirical papers are NOT claimed read or reproduced by this refresh. Append actual
source learning, pinned interface inspection and empirical scope below before
enabling consequential scientific or security behavior. Medical reading exemptions
must be justified for the actual task; this refresh grants no exemption.
Missing academic/repository/empirical categories remain unverified for future domain
enablement. No weights, datasets or upstream code are adopted by a lookup.

Decision: preserve scoped specifications and keep unsupported capabilities disabled.
Verification: task-specific evidence and ledger, not map
existence. Failure fallback: disable affected domain/provider capability. Map drift
is recorded separately; original maps are unchanged.

## Hackathon Compliance Impact

Applies to preservation, source privacy and truthful contribution records. No external
model request is authorized by this task record. Models/rules/access remain unverified.
Architecture is preserved; refer to the task ledger for changed files and actual checks.

## Scoped source learning and integration decision

The capability lookup returned IMG.VIEW, REF.OHIF, D.TWIN, D.UX, TWIN.TIME,
UX.TIMELINE and EVAL.E2E; academic behaviors IMG.04, IMG.12 and TWIN.02.
The saved JSON contains 30 adjacent edges, including GOV.PROV constraining the
timeline. `authorization` returned no matches in all three query packages; the
actual identity, patient-linkage and timeline/mesh readers supplied that context.

UI source learning: SPEC-009 places context above the viewer, timeline below it,
and measurements beside it; URL selection must survive refresh/Back. Snapshot and
per-observation time are distinct. Missing modalities stay empty, and unavailable
model output must not prevent geometry navigation. SPEC-008 distinguishes viewer
reads from administrative simulation operations; source permissions remain separate
from technical QC. SPEC-010 requires persistent synthetic labeling and no secrets
in the browser. These are inspected local requirements, not new clinical findings.

Medical academic reading and empirical cohort research are not applicable to this
bounded presentation adapter: no clinical algorithm, geometry computation,
inference integration or clinical meaning is changed. Mapped books/papers remain
pointers, not claimed readings. No independent clinician participated.

Three-source decision: preserve provenance/missingness principles in the inspected
specifications → reuse local MeshRenderer/OrbitControls, TimelinePoint/TrendReport,
pointValue, TrendView and the existing fixture/domain pipeline → verify only on the
artificial engineering phantom. No empirical real-patient support exists for this
demonstration. Therefore choose a token-free synthetic snapshot adapter rather
than weakening the admin-only readers or retaining an administrator JWT. The
operator prepares the snapshot in a disposable test transaction; strict expiring
server sessions expose its read-only scenario payloads. Runtime performs no
backend request and no external inference. Failure closes access with a recovery
action; it does not substitute data or geometry.

Local implementation inspection: tests/simulation_fixtures.py,
test_simulation_execution.freeze/complete_run/publish_completion,
timeline_runs.query_timeline, trend_runs.query_trends,
synthetic_geometry.read_generated_mesh, mesh_reconstruction.reconstruct and
mesh_quality.validate_surface. Existing pinned Three.js 0.186.1 renderer APIs are
reused; no upstream source, weight, dataset, package or license is newly adopted.
The baseline is the existing 24³ artificial grid with a 6³ region mask (216 mm³).
It is not patient anatomy. Follow-up volumes and clinical records remain synthetic.

Separate agent security review identified and removed the unfinished adapter's
broad JWT, configurable backend proxy and expiry hazards. It also recommended
explicit source checks and rejection of optimized Python execution; both were
implemented. This is an engineering code review, not scientific certification.

Contracts: FastAPI/OpenAPI/database contracts and generated clients are unchanged.
New internal Next routes are POST /api/demo-session and GET /api/demo[?scenario].
The shared local TypeScript contract is demo-contracts.ts. Regression, failure
attempts, screenshots and final status are recorded in the recovery report and
task ledger. Public publication, provider access and D01–D06 are unchanged.
