# Phase 4 execution

Owner authorization: begin Phase4 implementation,2026-10-30. Execute COS-057–071
sequentially using the original prompt series. Existing Phase1–3 evidence and open
D01–D06 gates remain applicable. COS-056 is optional/deferred, not a prerequisite.
No source specification/map edits, live provider calls, paid compute or new push
are authorized by this implementation request.

COS-057: provider-boundary/1 typed inputs, Meta Responses adapter, strict parsing,
per-attempt export/2 checks, private candidate handling, default-closed output gate,
local inventory template and project-authenticated capability discovery implemented.
Source PDF extracts and original guidance were read; reference context records
map edges, actual external documentation access and unavailable source categories.
Focused target passed76 tests, Ruff, mypy and generated contract drift; see
`evidence/provider-boundary.json`. No live provider or scientific evaluation ran. Runtime live processing
and candidate publication remain disabled, including in configured deployments.

Remaining ordered tasks: COS-058 note extraction,059 relational/source linkage,
060 approved corpus,061 retrieval,062 immutable context,063 generation,
064 grounding/safety,065 persistence/fallback,066–070 API closure,071 conformance.
These are planned, not completed by provider schema validation.

COS-058 implemented and fixture-verified:97 pure grammar/Unicode tests plus25
private PostgreSQL/S3/HTTP tests (122 total); mypy, Ruff and contract drift passed.
Migration0041 upgraded the disposable database twice. Four symptoms/twelve frames
remain the supported scope. Fixture entity precision48/48, supported recall48/48,
input coverage48/68, zero assertions from20 unsupported cases; numeric value
extraction denominator0, no real-note/model comparison or human review performed.
See ADR-044, note-extraction runbook and evidence/note-extraction.json.

COS-059 passed64 focused pure/SQL/private-imaging/HTTP tests plus migrations, Ruff,
mypy and contract drift. Lexical concept cycles remain unverified proposals;
source-linked relationships retain exact fact/branch/source context and do not
promote observations. See ADR-045 and evidence/knowledge-relationships.json.

COS-060 passed100 pure/private SQL/S3/HTTP checks, including real PostgreSQL FTS,
metadata-only isolation, corpus activation preconditions/replay, rights/retraction
refusals and removal of mutable search text. A stale generated enum failed drift;
regeneration and a focused drift retry passed, preserving actual prior test results
and failure history. No NCI text or genuine approved corpus was ingested; original
private-object retention remains review-required. Next COS-061.

COS-061 verified close-out: 35 focused real-PostgreSQL/HTTP checks passed
(fixture precision 4/4 on 2 answerable queries, fixture recall 4/4, unsupported
rate 0/4, correct no-match 3/3; strict bounds/injection/ownership/citation tests),
plus migrations, Ruff, mypy and regenerated contract drift (stale openapi/api.ts
regenerated, then green). See ADR-047, evidence-retrieval runbook and
evidence/evidence-retrieval.json. No genuine corpus, reviewed labels, live fetch
or SPEC-011 evaluation ran. Current: COS-062, then COS-063–071.

COS-062 implemented: snapshot-bound immutable interpretation context with separate local/export views. 6 focused checks passed (identity/hash/stale, same-branch comparison, over-budget 409, omission records, active-corpus passage inclusion with rights recheck, HTTP auth boundary); plus migrations, Ruff, mypy and regenerated contract drift (new context routes allowlisted, then green). Migration 0045 adds append-only context build audit. See ADR-048, interpretation-context runbook and evidence/interpretation-context.json. No generation, export, genuine curation or SPEC-011 evaluation ran. Current: COS-063, then COS-064-071.

COS-063 implemented: deterministic template interpretation over frozen contexts with external candidates held private. 11 backend checks passed (5 interpretation + 6 context) plus 2 panel checks; template determinism, context/mode gating, minimized export, HTTP auth boundary and strict input schema verified. Migration 0046 adds append-only interpretation build audit. See ADR-049, interpretation-generation runbook and evidence/interpretation-generation.json. No model arithmetic, streaming, novel prose, publication, genuine curation or SPEC-011 evaluation ran. Current: COS-064, then COS-065-071.

COS-064 implemented: mandatory fail-closed grounding publication gate with frozen 60-case fixture suite (20 grounded, 20 edge, 20 adversarial). 6 focused checks passed; numeric/unit/reference/context fidelity, 8-class prohibited-claim policy, private-candidate gating and HTTP boundary verified. Gates on fixtures: 100% numeric/unit/origin fidelity on published (24/24), zero published critical prohibited claims (0/20 adversarial), correct abstention on predefined critical insufficient cases. Migration 0047 adds append-only grounding decision audit. See ADR-050, grounding-gate runbook and evidence/grounding-gate.json. No live model, genuine curation, qualified review or SPEC-011 evaluation ran. Current: COS-065, then COS-066-071.

COS-065 implemented: exact-context persistence of gate-published templates with revalidation on every reuse, immutable supersede records, labeled fallback and withdrawal propagation. 4 focused checks passed (idempotent persist/supersede, exact reuse with version-match and isolation, fallback labels with 403 preserved for refusals, HTTP persist/reuse/auth boundary). Migration 0048 adds the immutable saved_interpretations store. See ADR-051, saved-results runbook and evidence/saved-results.json. No cross-patient reuse, URL caching, live model or retention signoff ran. Current: COS-066, then COS-067-071.

COS-066 implemented: patient/diagnosis/observation API closure over existing services with no new persistence. 4 focused checks passed (grant-scoped list/detail without plaintext export, snapshot-stable filtered queries, source-backed diagnosis confirmation with kind gating, HTTP paths and auth boundary). No parallel diagnosis store or uncontrolled CRUD added; batches, corrections and retractions keep validated transactional semantics. See ADR-052, patient-closure runbook and evidence/patient-closure.json. No clinical validation ran. Current: COS-067, then COS-068-071.

COS-067 implemented: imaging/segmentation/geometry API closure with study, acquisition and segmentation discovery reads over existing services. 4 focused checks passed (owned stable discovery, QC-visible segmentation state, grant expiry/withdrawal honesty, HTTP paths and auth boundary). No new upload path, remote ingestion, public links or model routes; failed QC geometry never publishes. See ADR-053, imaging-closure runbook and evidence/imaging-closure.json. No clinical validation ran. Current: COS-068, then COS-069-071.

COS-068 implemented: simulation/branch API closure with five-family scenario discovery and owned branch listing over the existing engine. 3 focused checks passed (family discovery with versions, branch ownership isolation, HTTP paths and auth boundary). No duplicated simulation logic or destructive endpoints; lifecycle keeps existing transactional semantics. See ADR-054, simulation-closure runbook and evidence/simulation-closure.json. No engine validation ran. Current: COS-069, then COS-070-071.

COS-069 implemented: twin state/timeline/comparison closure with a selected-state manifest over owned assembly. 3 focused checks passed (manifest coherence with selection identity and isolation, comparison pair/scope rejection, HTTP manifest/timeline/trend paths). No reassembly, timeline or geometry changes; old states never rebuild from mutable heads. See ADR-055, twin-closure runbook and evidence/twin-closure.json. No temporal validation ran. Current: COS-070, then COS-071.

COS-070 implemented: interpretation-job orchestration closing context, template, gate and persistence into one bounded endpoint with discovery reads. 3 focused checks passed (submit/validate/persist/replay with isolation, external-mode and stale-hash closure, HTTP job paths and auth). Migration 0049 adds the append-only job ledger. No model proxy, tool gateway or free-form endpoint added. See ADR-056, ai-closure runbook and evidence/ai-closure.json. No live behavior or review ran. Current: COS-071 final conformance.
