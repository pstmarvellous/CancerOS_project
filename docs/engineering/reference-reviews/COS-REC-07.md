# COS-REC-07 reference context

Scope: assigned implementation task; specialist self-review through architecture,
data-integrity/security and verification perspectives; no independent clinical review.

Queries executed: interpretation, explanation, grounding against capability, academic and repository/scientific maps.
Exact commands, output, IDs and incoming/outgoing dependency/guard/verification edges:
[COS-REC-07.json](COS-REC-07.json). Unmatched queries are gaps, not successful source reviews.

Original specification sections inspected: prompt_8 AI interpretation; SPEC-006 intelligence; SPEC-007 architecture; SPEC-008 contracts.
Agent guidance: COS-000 sections 3–8/11; repository instructions sections 2–8;
COS-REF-001 sections 2–3/15–23; COS-HACK-001 sections 2–3/9/11/17.

## COS-REC-07 implementation update (2026-11-09)

Scope: workspace-connected research interpretation on existing services.
Specialist self-review: AI infrastructure, backend integration, application
security, UX. No independent clinical review.

### Capability map (Knowlage_map_1)

Queries `interpretation`, `explanation`, `grounding`: 8 capability nodes,
73 adjacent edges; exact output in [COS-REC-07.json](COS-REC-07.json).

### Academic behaviors

40 matched behaviors (pointers only). Principle applied: deterministic
templates over verified context; numeric fidelity checked by the grounding
gate; no LLM arithmetic.

### Repository/scientific maps

No upstream adapter adopted. No new checkpoint, dataset, license or code.

### Governing specifications inspected

COS-SPEC-006 (AI & Multimodal Intelligence), COS-SPEC-007, COS-SPEC-008,
COS-SPEC-009, COS-SPEC-010 (SAFE invariants), COS-PRD-001; module boundaries,
authority-and-scope, reference-consultation-policy, data-and-ai-safety-rules.

### Findings (verified, not assumed)

- Context/interpret/ground/save contracts match the Next.js proxy payloads;
  no request/schema mismatch on those paths.
- External candidates are denied server-side (`external_candidate` → 409);
  provider contract pins `external_model_available: False`; live enablement
  verified closed in this environment (`EXTERNAL_INFERENCE_ENABLED=false`,
  no export policy → `read_policy` raises `EXTERNAL_PROCESSING_NOT_ALLOWED`).
- Save persists only grounded `published` reports; otherwise 422. The
  grounding/save panel only renders for non-template reports, which the
  server cannot currently produce — fail-closed by construction.
- No manual UUID entry: branch/state pickers only, UUID validation of
  picker values, workspace selection from URL/session.

### Changes (surgical, no second gateway, no backend changes)

- Timeline selected-state section: "Explain this state in Insights →" deep
  link carrying project/patient/branch/state; InsightsExplorer preselects the
  linked branch and loads the linked state one-shot (no UUID copying).
- New project-scoped `api/provider-capabilities` proxy (`ai/capabilities`);
  the insights panel renders verified live status (blocked with the exact
  server `external_status`, or unverifiable) next to the deterministic local
  path instead of a hardcoded claim.
- Tests: 4 workspace-connection, 4 proxy, 1 deep-link tests (all pass).

### Blocked

Live Meta verification beyond the closed gate (no export authorization,
policy, or access) and real-browser evidence in this session; reported
separately from the passed local path.

### Hackathon Compliance Impact

Preservation, source privacy, truthful contribution records. No external
model request authorized or sent. Architecture preserved; changed files and
checks in the task ledger (COS-REC-07).

## Hackathon Compliance Impact

Applies to preservation, source privacy and truthful contribution records. No external
model request is authorized by this task record. Models/rules/access remain unverified.
Architecture is preserved; refer to the task ledger for changed files and actual checks.
