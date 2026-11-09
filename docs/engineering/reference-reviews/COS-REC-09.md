# COS-REC-09 reference context

Scope: assigned implementation task; specialist self-review through architecture,
data-integrity/security and verification perspectives; no independent clinical review.

Queries executed: acceptance, verification, journeys against capability, academic and repository/scientific maps.
Exact commands, output, IDs and incoming/outgoing dependency/guard/verification edges:
[COS-REC-09.json](COS-REC-09.json). Unmatched queries are gaps, not successful source reviews.

Original specification sections inspected: prompt_10 independent acceptance; SPEC-011 evaluation; authority-and-scope.
Agent guidance: COS-000 sections 3–8/11; repository instructions sections 2–8;
COS-REF-001 sections 2–3/15–23; COS-HACK-001 sections 2–3/9/11/17.

## COS-REC-09 implementation update (2026-11-09)

Scope: independent acceptance across journeys A–E with separate verdicts; no
combined score claimed. Specialist self-review: senior QA, product acceptance,
UX. No independent clinical review; no authentic data exists here.

### Capability map (Knowlage_map_1)

Queries `acceptance`, `verification`, `journeys`: 121 capability nodes,
40 academic behaviors, 269 adjacent edges; exact output in
[COS-REC-09.json](COS-REC-09.json). Map entries are pointers only.

### Governing sources inspected

Prompt 10; COS-SPEC-011 (evaluation); authority-and-scope;
reference-consultation-policy. Prior REC-00–08 evidence re-executed where
cited, never taken on trust: Journeys A/B/C re-driven in a real browser on a
fresh disposable stack; backend suites re-run in-session.

### Verdicts (evidence in docs/engineering/testing/rec09-acceptance/)

- A synthetic demo: PASS (fresh browser, 5 scenarios, Day 37 = 64 mm³, 390px clean, zero errors).
- B case management: PASS (create/observe/reopen/correct/chart/navigate/isolate/sign-out).
- C imaging: PARTIAL — study→provenance→geometry→no-mask→refresh PASS; full chain APIs PASS (48 mm³, validated mesh-QC, lesion); case 3D viewer FAIL (defect D-01).
- D simulation: branch creation via API PASS; engine suites PASS; browser generation BLOCKED.
- E interpretation: local PASS (demo + re-run suites); live BLOCKED-and-closed (verified); case-on-generated-state BLOCKED.
- Authorization: viewer-create 403, outsider 404, cross-patient 403 (exact codes probed).
- Portfolio demo: NOT YET (A+B ready; C/D not end-to-end). Clinical release: NOT ASSESSED.

### Acceptance defects found (not just reported)

- D-01 (Major, open): LesionViewer geometry lookup probes only mesh-qc IDs equal to lesion/segmentation IDs, which can never match uuid4 reports (API-proven 404/404/200). Viewer unusable for genuine backend data.
- D-02 (Major, fixed in-session): lesion-viewer geometry branch dropped cookie-session auth (401 for all browser users); fixed with `researchAuthorization`; verified by 401→409 progression; full suite green.
- D-03/D-04: stale ux-recovery selectors; deferred browser-driven simulation/insight states.

### Hackathon Compliance Impact

Preservation, source privacy, truthful contribution records. Synthetic-only
evidence; no external inference; no authentic-data claims. Architecture
preserved except the D-02 session-auth fix; changed files and checks in the
task ledger (COS-REC-09).

## Hackathon Compliance Impact

Applies to preservation, source privacy and truthful contribution records. No external
model request is authorized by this task record. Models/rules/access remain unverified.
Architecture is preserved; refer to the task ledger for changed files and actual checks.
