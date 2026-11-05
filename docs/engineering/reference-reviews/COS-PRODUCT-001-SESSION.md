# COS-PRODUCT-001-SESSION reference context

Scope: assigned implementation task; specialist self-review through architecture,
data-integrity/security and verification perspectives; no independent clinical review.

Queries executed: privacy, access against capability, academic and repository/scientific maps.
Exact commands, output, IDs and incoming/outgoing dependency/guard/verification edges:
[COS-PRODUCT-001-SESSION.json](COS-PRODUCT-001-SESSION.json). Unmatched queries are gaps, not successful source reviews.

Original specification sections inspected: COS-PRODUCT-001 sections 4, 6, 9, 10, 14; source specifications to inspect; current case-proxy implementation inspected.
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

## Bounded session implementation, 2026-11-05

Delegated ownership: web research-session route, session memory, research-session
panel, case proxy integration and focused authentication tests. Parent owns case
forms and orchestration; backend agent owns the workspace membership endpoint.
No database edits, patient observations, provider requests or authentication bypasses
were introduced by this subtask.

Capability nodes: `GOV.PRIV`, `UX.CASE`, `DATA.ARTIFACT`, `IMG.INGEST`; 18 adjacent
edges are captured in the JSON. Academic and repository/scientific searches for
privacy/access yielded no directly mapped session behavior; this is an unmapped
plumbing task. No textbook, cohort evidence or upstream code adoption is claimed.

Source Learning Record: COS-SPEC-008 version 1.0, 22 October 2026, proposed
implementation baseline, PDF pages 8–9 section 11 and start of section 12 inspected.
It requires authenticated sessions or bearers, explicit origin protection for
cookie writes, private/no-store responses, independent session expiry and preserved
ETag/idempotency semantics. The source's broader scientific gates remain unchanged.
COS-SPEC-010 identity/version front matter inspected; this record does not claim a
full rereading of its controls. Existing local `src/canceros/identity.py` independently
verifies RS256 signature, issuer, audience, time claims and current database
memberships. The web layer does not duplicate that authority.

Security source reading: OWASP Cheat Sheet Series, current retrieved edition,
[Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html),
sections Session ID Content, Server-Side Session Token Storage, Secure/HttpOnly/
SameSite cookie attributes; and [CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html),
Using Standard Headers to Verify Origin (source/target origin and missing-origin
failure). Reviewed 2026-11-05. Decision: opaque CSPRNG cookie, memory-only bearer,
exact browser origin checks, no forwarded-host trust, no browser web storage or
credential URLs. SameSite alone is not the write authorization mechanism.

Three-Source Decision Note: governing security principle → existing database-backed
identity service plus installed Node crypto and NextResponse cookie APIs → no
medical empirical evidence applicable to this session plumbing → thin session
adapter validated by focused negative tests. The inspected local base is Git
`9221233` with substantial existing uncommitted work preserved. No copied upstream
implementation, model, dataset or new dependency was adopted. OWASP guidance is
design support; the tests establish only the bounded implementation behavior.

Contract: POST `/api/research-session` accepts only `{token}` containing an existing
RS256 credential. The backend GET `/api/v1/workspace` must authorize it and return
current project memberships before session creation. Browser receives only safe
project names/IDs/roles, expiry and a random 256-bit HttpOnly SameSite Strict
host-only cookie. Bearer credentials stay in process memory for at most 30 minutes
and never beyond credential expiry. HTTPS is required outside loopback development;
HTTPS cookies are Secure. GET rechecks backend membership; DELETE requires the
same origin and invalidates both cookie and memory. Reauthentication rotates the
identifier. Restart/eviction requires signing in again; distributed deployment
sessions are outside this local prototype change.

Case proxy resolves explicit bearer headers or the separate research cookie,
rechecks API authorization on every request, preserves ETag/Location/Retry-After,
and forwards idempotency/precondition headers. Cookie mutations require exact
Origin; explicit non-browser bearer clients retain compatibility without an Origin.
Any supplied cross-origin Origin or cross-site Fetch Metadata is denied. Synthetic
demo cookies never grant research privileges. Upstream redirects are rejected.

Verification executed: `npx vitest run apps/web/lib/research-session.test.tsx
apps/web/components/research-session.test.tsx --maxWorkers=1`: **30 passed**, two
files. These mock backend/network responses; real RS256 authorization and browser
journeys remain parent integration checks. Focused ESLint passed after the final
TLS guard; `git diff --check` passed with line ending normalization warnings only.
`npm run typecheck` found no owned
session errors but failed on concurrent case/renderer/generated-contract edits;
not recorded as a pass. Parent was notified of exact failures.

Limitations: credential issuance remains an existing administrator/identity-provider
responsibility. This provides explicit credential sign-in, not an invented identity
provider or elevated role. Browser screenshots, persistence through the real API,
full build/regression and authorization integration are parent-owned checks. No
live Meta, source-rights, scientific-review or publication gate is changed.
