# Phase 1 verification report

2026-10-27. **Foundation acceptance passed locally.** COS-001 through COS-015 were
executed in order. COS-011 remained implemented/unverified while its install checks
finished; independent COS-012 work proceeded, and the frontend was verified before
Phase1 closure. No routine approval pause, publication, paid model request or source
specification/knowledge-map rewrite occurred.

## Verified now

| Criterion | Result / actual evidence |
| --- | --- |
| Locked installation | Passed: isolated noneditable Python wheel import outside source directory; clean npm ci. [Record](evidence/locked-install.json) |
| Backend | 44 Python tests passed, Ruff lint/format, mypy, locked sync and schema checks. [Commands/output](evidence/backend.json) |
| Frontend | 10 component tests passed; ESLint, strict TypeScript, production build and generated-client drift checks passed. [Commands/output](evidence/frontend.json) |
| Browser | Chromium155.0.8059.86, 1280×900 and390×844; keyboard focus, API connection and no narrow overflow. Desktop/mobile PNGs visually inspected. [Record](evidence/frontend-browser.json) |
| Native startup | API/web/private dependencies reachable; authenticated readiness200, anonymous readiness/identity401. [Record](evidence/final-startup.json) |
| PostgreSQL | Three numbered migrations, repeated upgrade, invalid ownership/origin rejection, append-only revision history, N afterN+1, rollback and immutable synthetic artifact identity. [Suite](evidence/backend.json) |
| Private S3 service | Real versioned write/read/hash, quarantine/verified separation, wrong project/hash rejection, anonymous denial and short-lived authorized grant. [Record](evidence/persistence.json) |
| Queue/worker | Real Redis transport, durable SQL request/outbox/result and private artifact; separate bounded worker process; duplicate/cancellation/outage/abandoned-delivery tests. [Record](evidence/worker.json) |
| Restart | Owned PostgreSQL/storage/queue restart retained completed SQL results, exact object version and queue marker. This is not production backup restoration. [Record](evidence/restart-smoke.json) |
| Configuration/security | RS256 issuer/audience/time checks, database memberships, role/project denial, safe errors/settings, disabled unapproved export with zero outbound calls. [Record](evidence/security.json) |
| Governance/maps/hygiene | Source hashes,840 trace rows/CSV synchronization, negative validation fixtures, both original map queries, reference registers, boundaries, known local secret/ignore checks. [Record](evidence/governance.json) |

The 840 rows are named-ID/normative-keyword extraction plus audit/task coverage,
not a full manually adjudicated product compliance percentage. Table/implicit-clause
extraction gaps are explicit in requirements-traceability.json. All18 A/C/D audit
items remain accounted for. The twelve audited input PDFs, audit and supplemental
schedule have reproducible hashes. No SPEC-002 was invented. RA-001 is advisory and
its unestablished version remains null.

## Implementation and contract handoff

API: minimal health, identity and scoped foundation-status handlers; no fake clinical
success endpoints. Central Pydantic sources generate separate runtime OpenAPI3.1.1
and foundation JSON Schema, then TypeScript. API/web startup needs no GPU/provider.
Patient/scenario/evaluation routes remain planned, not working handlers.

C01: discovery design recorded; domain handlers future. C02: durable revision/input
manifest primitives verified; complete observation-head/state-builder integration future.
C03: independent patient time-origin/relative root verified; full branch/state anchors
future. C04: exact-membership/1 design recorded; clinical assembly/conflict/historical
imaging implementation future. C05: foundation bearer/membership/config path verified;
actual deployment issuer enrollment, patient-specific grants and restricted runtime SQL
roles remain deployment/domain gates. C06: reviewed clinical/simulation dictionaries future.

D01–D06 remain unverified for real baseline, genuine longitudinal case, source rights,
external inference, scientific evaluation and deployment/demo readiness. Formal project-owner
adoption of the supplied audit is not separately evidenced; no approval was invented.
This does not block the authorized reversible foundation work.

No authentic MRI, clinical dictionary, five-family simulator, patient-specific prediction,
Meta research agent, clinical accuracy or finalized hackathon submission is established
by this phase. Source/segmentation/model experiments remain future work. Specialist
reviews here were engineering self-review, not independent clinician approval.

## Runtime, CI and limitations

Tested on native Windows, Python3.12.14, Node22.14.0, uv0.12.5, PostgreSQL15.4,
SeaweedFS4.51 and Redis Windows8.10.3. Exact Python dependencies and all check outputs
are in [the summary](evidence/phase-1-summary.json) and lockfiles. [Measured memory](evidence/final-memory.json)
is point-in-time process-family RSS; host usable RAM measured about5.9GiB. PostgreSQL
processes and scientific workload peaks are not included in those service-family totals.
No claim that the full scientific suite fits8GB is made.

A GitHub Actions candidate workflow and equivalent fail-fast local commands exist.
Remote CI/container alternatives were **not_run**: no remote host or Docker runtime
was configured. Local mandatory integration used real native services. Worker tests
cover the named engineering cases, not complete distributed publication/cancellation
race or production reliability. A full backup/restore rehearsal remains future.

ESLint9.39.5 is pinned because the current Next plugin peers reject ESLint10; npm
marks that lint version deprecated. OpenAPI generation requires TypeScript5, so5.9.3
is pinned instead of incompatible TypeScript7. Starlette currently warns that its
httpx test client path is deprecated; tests pass. These are recorded toolchain limits,
not concealed skipped checks. Source/patient/model/asset redistribution review and a
project-owner license decision are still required before public release.

Git was initialized locally. Nothing was staged, committed, pushed or deployed;
there is no commit SHA to report. Existing system PostgreSQL and private Data_folder
were preserved. Local credentials, data volumes and downloaded binaries remain ignored.

## Hackathon Compliance Impact

Applies to preserved architecture/maps, contribution attribution, model configuration,
export denial and truthful demonstration claims. Official Meta model/quickstart docs
were read and match the configured target; authenticated model access, data-use terms,
export permission and organizer rules were not verified. HACK-TEST-001/002 and complete
research-agent/demo checks remain not_run/future. Foundation export-denial and hygiene
checks are a subset of safeguards, not overall hackathon compliance.

References: [Meta models](https://dev.meta.ai/docs/models),
[Meta quickstart](https://dev.meta.ai/docs/quickstart),
[contribution record](../hackathon/HACKATHON-CONTRIBUTIONS.md).

## Resume

Use [the task ledger](task-ledger.json), [the runbook](../../infrastructure/README.md)
and root AGENTS.md. Local workspace: http://127.0.0.1:3000. Stop only owned services
with `uv run python scripts/dev.py stop foundation`; data remains.
The next domain prompt is COS-016 (source registry/licenses) in Phase2. It was not
executed under this Phase1 request. Do not reopen completed foundation tasks without
new changes/failures; carry forward the named C/D gates and source-reading obligations.
