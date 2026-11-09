# COS-REC-00-REVERIFY reference context

Scope: assigned implementation task; specialist self-review through architecture,
data-integrity/security and verification perspectives; no independent clinical review.

Queries executed: authorization, security against capability, academic and repository/scientific maps.
Exact commands, output, IDs and incoming/outgoing dependency/guard/verification edges:
[COS-REC-00-REVERIFY.json](COS-REC-00-REVERIFY.json). Unmatched queries are gaps, not successful source reviews.

Original sources inspected: COS-SPEC-008 v1.0 (22 October 2026), sections 3 and 5 (PDF pages 2–3), section 12 (page 9), and interpretation/artifact contracts (page 12); COS-SPEC-010 v1.0 (22 October 2026), sections 7–9 (page 4). Both documents identify proposed baseline/control status, not certification. Read-only pypdf extraction used; source PDFs unchanged. An initial extraction stopped on console encoding; UTF-8 retry read the security sections.
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

## Actual learning and bounded decision

- Capability refresh found D.INFRA; direct second-hop inspection read INF.API, INF.DB and INF.CI and their three IMPLEMENTS edges. No adjacent CONSTRAINS/GUARDS/EXCLUDES/VERIFIES/WORKFLOW_PRECEDES edges existed for these nodes. Academic and repository/scientific authorization/security searches returned no matching behaviors; this is an unmapped security task.
- OWASP Cheat Sheet Series, Authorization Cheat Sheet, sections “Validate the Permissions on Every Request”, “Verify that Authorization Checks are Performed in the Right Location” and “Create Unit and Integration Test Cases for Authorization Logic”: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html (accessed 2026-11-08). Principle applied: validate current patient access at the service boundary and verify the real HTTP adapter separately. Failure mode: a previously authorized context can outlive its grant.
- OWASP HTML5 Security Cheat Sheet, Storage APIs / Local Storage: https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html (accessed 2026-11-08). Principle applied: browser storage does not establish authorization or confidentiality. The repository's stricter no-storage-write gate is preserved; case IDs moved to the already existing server session, with URL navigation and backend reauthorization on restore.
- No academic textbook section or empirical clinical paper was retrieved for this unmapped security behavior. These categories remain unavailable/not applicable to clinical efficacy; artificial access-control tests provide engineering evidence only.
- Implementation reference: existing CancerOS authorize_patient, RS256/SQL memberships, saved API and research-session proxy at starting commit 12b9502. No upstream code copied or dependency adopted. Locked FastAPI/Pydantic/SQLAlchemy APIs inspected locally; no new library, model, data or license adopted.
- Three-source note: current-permission security principle → existing patient authorization and server-session implementations → artificial SQL/HTTP/browser negative and positive evidence → recheck reuse grants and restore selection without persistent browser IDs. Clinical empirical support is not claimed or needed to establish these access-control invariants.
- Critical self-review covered guessed result IDs, URL/stored patient mismatch even with both grants, direct Patient-B URL without grant, missing authentication, removed project membership, revoked patient grants, cookie/bearer separation, private no-store responses, and denial-body minimization. This is specialist self-review, not independent expert approval.
- Existing Python static-check errors were repaired through an explicitly TYPE_CHECKING-only view of generated Pydantic input types, a discriminant-based branch and explicit SecretStr construction. Runtime generated schemas remain unchanged; contract drift and case regression checks were executed.

See [recovery report](../testing/rec00-reverify/RECOVERY-REPORT.md) for exact changed files, commands, counts, failed attempts, evidence limitations and the acceptance decision. New `/api/research-selection` is an internal Next.js session adapter returning only `{project, patient}` after backend authorization; no FastAPI wire contract or generated client changed.

## Hackathon Compliance Impact

Applies to preservation, source privacy and truthful contribution records. No external
model request is authorized by this task record. Models/rules/access remain unverified.
Architecture is preserved; refer to the task ledger for changed files and actual checks.
