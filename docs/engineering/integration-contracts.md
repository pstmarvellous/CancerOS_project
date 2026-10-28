# Integration contracts v1

COS-008. Source: SPEC-008; audit C01–C06; SPEC-009 section17. Reversible foundation
design choices are recorded in ADR-001. Formal audit adoption remains unevidenced.
No schema/example below claims a working clinical endpoint.

## Canonical ownership and generation

Installed `src/canceros/contracts.py` owns Python contract sources under the logical
packages/contracts boundary. Pydantic emits versioned JSON Schema; FastAPI emits
only implemented handlers to packages/contracts/generated/openapi.json, pinned to
OpenAPI 3.1.1. Design-only foundation schemas are separate from runtime OpenAPI.
openapi-typescript consumes runtime OpenAPI and json-schema-to-typescript consumes
foundation schema; generated TypeScript is never hand-edited. `scripts/generate_contracts.py`
and root npm generation/check commands must be deterministic and fail on drift.

One modular FastAPI backend; workers call shared services; persistence/storage and
inference are adapters. Only health and identity routes are project-base exceptions.
REST base: `/api/v1/projects/{project_id}`. No `/api/imaging`, `/api/ai` or `/cases`
parallel catalogs. Patient resources require route ownership and project membership.
Viewer reads published approved data; editor commands require write scope; admin
controls rights/config/imports. Readiness is deployment-monitor-only.

## C01 discovery design (future handlers)

| Relative path | Minimum response and authorization |
| --- | --- |
| GET /capabilities | Feature/action codes, dictionary versions, supported units/limits; project membership; no inferred eligibility/secrets |
| GET /dictionaries/{code}/versions/{version} | Exact reviewed immutable coding/unit version; project viewer; no invented conversions |
| GET /patients/{p}/branches | Published-only viewer list; editor drafts scoped to patient; cursor envelope |
| GET /patients/{p}/observations/{o} | Exact authorized revision, time/subtype and safe source references |
| GET /patients/{p}/interpretations | state_id/snapshot_hash filters, execution mode, freshness/publication |
| GET /evaluations and /evaluations/{id} | Approved redacted versioned report, cohort/method/real-synthetic separation; project viewer |

These are recorded contract extensions, not claims that SPEC-008 originally supplied
the paths. Activity/job-list is deferred: Phase 1 has no Activity view, and known job IDs
are sufficient. Every future list uses items/next_cursor/snapshot_revision; the signed
cursor binds actor-authorized project/context/filter/order/revision and has expiry.
Wrong scope is denied and cursor expiry returns 409. No frontend feature calls a
planned route before its handler/schema/access tests exist.

## C02 durable history

Persist append-only patient revision entries with exact immutable membership payload
and input hash; enqueue copies/captures an immutable input manifest at that revision.
Later workers resolve the stored revision, never mutable current heads. Lists pin
the patient data_revision on the first page and retain it across pages; corrections
create N+1. Older snapshots and science fingerprints do not change. Durable history
requires both SQL immutability and N-after-N+1 regression tests, not MVCC alone.

## C03 relative-time root

Persist patient-owned `timeline_origins` independent of state creation: identity,
project/patient, reference meaning, time_domain, no invented calendar date. Version
the wire TimeReference extension as `foundation/1`: relative_day has exactly one
of anchor_state_id (existing state API) or timeline_origin_id (relative-only root).
Both resolve to authorized patient-owned persisted anchors. Never self-reference a
baseline; no cyclic time anchors. Branch simulation times must use the approved
observed-baseline link; arbitrary cross-branch anchors are rejected.

Time bases: offset timestamp, date, relative_day decimal string, unknown with reason.
Domains: source_calendar, source_shifted, source_relative, simulation. Timestamp/date
never silently converted across domains. Unknown has no value and cannot order a state.
This wire extension is a recorded implementation decision, not an edit to the PDF.

## C04 assembly policy `exact-membership/1`

Resolve exact accepted source members at the captured revision. Use explicit event
membership at the selected anchor; do not infer windows, impute or carry forward.
Conflicting same-concept assertions remain conflicts unless explicit source correction
links resolve them; deterministic ID ordering does not imply medical precedence.
Late source data produces new revision/snapshots, never rewrites old ones. A lab-only
state has lab members; earlier imaging may be returned only as historical_context
with its original source time, never asserted current. Store policy version, member
IDs, input hash and absence/conflict reasons. No clinical state builder is implemented
in Phase 1; its full late/same-day/conflict tests remain domain enablement gates.

## Execution versus publication

At-least-once transport; durable SQL jobs/outbox are authoritative. Request input is
immutable. Lease token, max three attempts, cancellation guard and unique job-output
identity prevent duplicate result commits where implemented. Job success means durable
result, not user publication. Scenario ready→published remains an explicit authorized
command. No clinical publication endpoint is scaffolded as fake success. Phase 1
harmless digest job tests plumbing only; broader retry/cancellation/publication races
need dedicated later tests. Outbox recovery must survive transport outage.

## Drift and handoff

No new platform, duplicate origin enums, browser measurements, unversioned wire
changes, source-to-synthetic mixing or UI-only access controls. COS-010 implements
types/generation; COS-011 consumes generated contracts; COS-012 proves durable history
and origins in SQL; COS-014 selects identity/config; COS-015 checks drift. Clinical
dictionaries C06 and complete C04 runtime enforcement stay explicitly open.
