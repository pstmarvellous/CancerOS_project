# COS-REC-06 reference context

Scope: assigned implementation task; specialist self-review through architecture,
data-integrity/security and verification perspectives; no independent clinical review.

Queries executed: imaging, segmentation, geometry against capability, academic and repository/scientific maps.
Exact commands, output, IDs and incoming/outgoing dependency/guard/verification edges:
[COS-REC-06.json](COS-REC-06.json). Unmatched queries are gaps, not successful source reviews.

Original specification sections inspected: prompt_7 imaging import reconstruction; SPEC-005 imaging; SPEC-007 architecture; SPEC-008 contracts.
Agent guidance: COS-000 sections 3–8/11; repository instructions sections 2–8;
COS-REF-001 sections 2–3/15–23; COS-HACK-001 sections 2–3/9/11/17.

## COS-REC-06 implementation update (2026-11-08)

Scope: guided case-bound Imaging → Add Imaging Study workflow on existing services.
Specialist self-review: architecture, medical imaging computation,
data-integrity/security and verification. No independent clinical review.

### Capability map (Knowlage_map_1)

Queries `imaging`, `segmentation`, `geometry`: 27 capability nodes, 123 adjacent
edges; exact output in [COS-REC-06.json](COS-REC-06.json). Task-relevant nodes:
IMG.INGEST, IMG.VOL, IMG.MASK, IMG.PRE, IMG.MODEL, DATA.STUDY, DATA.SERIES,
DATA.SEG, INF.JOBS, UX.3D, TWIN.REAL. Guards honored: source rights,
de-identification, project/patient/branch ownership, REAL vs SYNTHETIC origin
separation, DCE-phase vs visit separation, geometry provenance, QC-before-measure.

### Academic behaviors

IMG.04, IMG.06, IMG.07, IMG.08, IMG.12, IMG.13, AI.04, EVAL.01 (pointers only).
Principles applied: voxel indices are not millimeters (affine/spacing/units
required before measurement); alignment resampling explicit with bounded volume
error; measurements deterministic and server-computed, never LLM arithmetic.

### Repository/scientific maps

No upstream adapter adopted (MAMA-MIA, nnU-Net v2, 3D Slicer, OHIF/Cornerstone3D,
IDC Index, MONAI unchanged). No new checkpoint, dataset, license or code.

### Governing specifications inspected

COS-SPEC-005 (Medical Imaging & Digital Twin v1.0), COS-SPEC-007, COS-SPEC-008,
COS-SPEC-009 (tab/workflow language), COS-SPEC-010 (SAFE invariants),
COS-PRD-001; docs/engineering module-boundaries, authority-and-scope,
reference-consultation-policy, data-and-ai-safety-rules.

### Three-Source Decision Note

Academic principle → existing owned services (imaging_ingestion, imaging_volumes,
alignment_runs, segmentation_reviews, measurement_runs, mesh_runs,
mesh_quality_runs, lesion_tracking, imaging_jobs) plus one read-only owned list
endpoint → synthetic-fixture empirical scope only → decision: guided case-bound
workflow surface (Next.js proxies + case-imaging-workflow panel) calling only
existing endpoints, surfacing real backend status, refusing simulated progress.
Blocked: authentic MRI rights/de-identification/geometry/annotation verification,
qualified review, longitudinal data (reported as blocked, not passed).

### Hackathon Compliance Impact

Preservation, source privacy, truthful contribution records. No external model
request authorized. Architecture preserved; changed files and checks in the task
ledger (COS-REC-06).

## Hackathon Compliance Impact

Applies to preservation, source privacy and truthful contribution records. No external
model request is authorized by this task record. Models/rules/access remain unverified.
Architecture is preserved; refer to the task ledger for changed files and actual checks.
