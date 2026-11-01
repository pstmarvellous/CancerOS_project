# COS-AUDIT-002 Remediation Backlog

**Run:** `cos-audit-002-arch-001` · **Candidate:** `bd7b2c2`
Ordered by risk. Every entry names files, changes, tests and regression risk. No broad refactor is authorized by this audit; each item needs a separately identified remediation task.

## Critical correctness and security — none found

No secret exposure, identity corruption, false provenance, destructive operation, or core-workflow breakage was found in the sampled paths. If a later pass finds one, it outranks everything below and must restrict the affected path within existing authorization.

## Scientific integrity

1. **Keep D02 blocked until a real two-exam case lands** — `tests/test_longitudinal_gate.py`, `tests/test_demo_case_longitudinal.py`, COS-083/095 evidence. Change: none to code; curate case with rights/linkage/reviewer/demo use. Tests: longitudinal gate. Risk: none. Owner: data/rights.
2. **Retain synthetic/real separation in all new UI copy** — components under `apps/web/components/`. Change: reviewer check per screen, no logic change. Tests: existing component tests. Risk: none.

## Broken integration — none found

Conformance, lineage and denial paths verified via frozen evidence; full live rerun recorded as exceeding the audit budget, not as a failure. Next scheduled rerun belongs to COS-103 on a named candidate with a live target.

## Clean-code refactoring

3. **Split oversized route/job functions** (CC-01, MEDIUM) — `imaging_api.py`, `clinical_api.py`, `twin_states.py`, `imaging_jobs.py::_process_locked`. Change: extract per-resource builders and per-stage processors; no behavior change. Tests: contract + imaging suites. Risk: low. Effort: M.
4. **Consolidate FastAPI dependency helpers** (CC-02, MEDIUM) — one tested helper module for session/auth dependencies. Tests: conformance suite. Risk: low. Effort: S–M.
5. **Narrow broad exception handlers** (CC-04, MEDIUM) — 17 sites listed in CLEAN-CODE-AUDIT. Change: per-call-site exception types, one site per commit with its negative test. Tests: existing negative tests. Risk: low–medium. Effort: M.
6. **Run `ruff format` on 20 listed files** (CC-03, LOW) — formatter only. Tests: none needed beyond gates. Risk: none. Effort: S.
7. **Extract frontend sub-panels on next touch** (CC-05, LOW–MEDIUM) — four components >340 lines. Tests: component tests. Risk: low. Effort: M.

## Missing verification

8. **Run dependency CVE scan with reliable advisory data** — record results, upgrade only with compatibility/regression notes. Owner: platform.
9. **Rerun full DB-backed conformance/lineage on a live disposable instance** — the audit reused frozen evidence after a 240 s timeout; rerun before any release claim. Owner: QA/platform.
10. **Declared-device trials** (3D, assistive tech, performance p95/mesh/frame) — retain slow/failing trials. Owner: QA.
11. **Live Model API smoke gate** (explicitly authorized session + verified export policy) — record identity, tokens, verdict, cost; never infer from authentic-session access. Owner: platform/safety.
12. **Isolated restore with RPO/RTO measurement** — inherits COS-089/093/103. Owner: platform.

## Optional improvements

- Mermaid architecture visual already in `docs/PHASE-6-EVIDENCE-PACKAGE.md`; regenerate only if topology changes.
- No dependency upgrades, schema changes, or new infrastructure in this backlog.
