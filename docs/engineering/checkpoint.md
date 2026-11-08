# Execution checkpoint

Phase4 owner-authorized2026-10-30; prompt-by-prompt implementation continues.
COS-057–061 implemented with synthetic engineering verification; task statuses
remain implemented_unverified for real/live/scientific review.

- COS-057:76 provider/identity/settings checks; external inference/publication closed.
- COS-058:122 parser/private-note SQL/S3/HTTP checks; no observation promotion.
- COS-059:64 source-linked relationship/SQL/private-imaging/HTTP checks; no causality.
- COS-060:100 metadata/private corpus/FTS/S3/HTTP checks; no genuine corpus ingested.
- COS-062:6 snapshot-bound context checks; local/export views separate, no
  generation or export, deterministic hashes.

Ruff/mypy/generated contracts and seven governance checks passed for completed
slices. The COS-060 stale generated enum failed drift once; regeneration and a
focused retry passed, with the attempt preserved. COS-061/062 stale openapi/api.ts
were regenerated to include implemented retrieval/context routes, then green.
Private original-object retention requires separate review; removing search text
does not claim complete erasure. See phase-4-execution.md, ADR043–047 and
task-specific evidence/runbooks.

Current: COS-071 final authentication/authorization/validation conformance gate.
COS-056 optional/deferred. Phase3 code was committed/pushed at77eb4fe; Phase4 is
local/uncommitted. No live provider, authentic notes, qualified scientific review,
Phase4 browser verification or new publication performed. D01–D06 remain open;
forecasts abstain and synthetic descendants remain synthetic.


## 2026-11-05 — COS-UX-RECOVERY-001

Verified for the bounded local synthetic UX workflow. Homepage launch enters a
read-only token-free demonstration without manual UUIDs or credentials. Existing
backend engines produced five families, a shared 216 mm3 phantom baseline and
three mask-realized follow-ups per family. Backend authorization is unchanged.
Final production build, typecheck, lint, contract drift and Ruff passed; 77 frontend
tests passed in the standard thread pool and 3 Chromium journey/security checks
passed on the final build. Seven working screenshots were visually inspected.
See testing/ux-recovery/RECOVERY-REPORT.md and browser-evidence.json.

Local demo left running at http://127.0.0.1:3000 via npm run demo. Bundle expires
after seven days and requires explicit re-preparation. Every observation and mesh
is synthetic; the baseline is a geometric phantom. Insights are a local template,
not live Meta output. Authentic-source, scientific-review, provider and publication
gates remain separate. Nothing pushed, deployed or submitted.

## 2026-11-05 — COS-UX-RECOVERY-002

Resumed bounded implementation after UX recovery: versioned the prepared synthetic
demo bundle, bound meshes to exact point/state/patient/branch/run/result identities,
and rejected inconsistent chart/context/source references before session loading.
Actual five-family pipeline preparation succeeded with external inference disabled.
113 frontend tests across 18 files (including 39 adapter checks), 3 Chromium checks,
production build, typecheck, focused ESLint and preparation-script Ruff passed.
Stopped local data services were restarted without a reset after the first failed
preparation attempt. No backend or scientific contract changed. See
testing/ux-recovery/INTEGRITY-CONTINUATION.md for the version 2 migration and evidence.

The older COS-071 line above is historical; phase-4-execution.md and the task ledger
already record later implemented slices. Their authentic-source, scientific,
live-provider and release dependencies remain unverified. Current continuation is
verified only for the local synthetic workflow. Demo remains on loopback port 3000;
no commit, push, deployment, patient-source transmission or live inference occurred.


## 2026-11-06 — independent COS-REVIEW-003

Fresh review completed without relying on previous review conclusions. See
[review package](reviews/COS-REVIEW-003/README.md). Original twelve source texts,
current code, fresh build/browser and bounded contract/geometry checks inspected.
Product acceptance rejected: partial artificial clinical workflow and prepared phantom
demo exist; authentic onboarding and ordinary scenario/insight integration incomplete.
Review verification does not change previous phase statuses or close scientific,
source-rights, provider, operations or publication gates. No application source changed.
Next action: owner-assigned bounded recovery from the prioritized plan.

## 2026-11-06 - COS-REC-00 security and recovery baseline

Branch cos-rec-00-security-recovery already active; uncommitted review work left
untouched. Root cause: saved-interpretation retrieval ignored patient ownership -
saved_api.saved_detail discarded the URL patient_id and read_saved checked only
project membership; a viewer granted Patient A could read Patient B's result.
Reproduced with artificial Patients A/B in the disposable test database at both
service and HTTP layers before fixing.

Fix (src/canceros/saved_runs.py, src/canceros/saved_api.py): read_saved now takes
the URL patient, enforces authorize_patient (project/patient/role/grant) and binds
the stored row's patient_id to it; persist_validated enforces authorize_patient and
scopes idempotency lookup by patient; route passes patient_id through.
Positive authorized retrieval unchanged; denials return 404/403 with no content.

Tests: tests/test_saved_runs.py 6 passed (2 new REC-00: service-level denial plus
positive retrieval; HTTP-route denial without content leak plus 200 for own
result). Adjacent: test_patient_linkage, test_api, hardening secrets/egress checks
(3 passed; pre-existing frontend localStorage boundary failure unrelated),
test_interpretation_runs, test_context_runs, test_imaging_ingestion (18 passed),
demo/case suites (20 passed). Full startup verified via scripts/dev.py foundation
(API 200, web 200), then stopped. Remaining risk: pre-existing frontend
localStorage usage flagged by hardening test; no real patient data involved.

## 2026-11-08 - COS-REC-01 unified navigation and case context

Branch cos-rec-01-navigation-context (from REC-00 recovery); all prior uncommitted
work preserved. Single authoritative selection added in apps/web/lib/case-selection.ts
(URL first, validated last_case fallback, no second store); app-shell preserves it on
every case route; twin/charts/simulation/insights/states/timeline restore it with a
synchronous history update and server-authorized re-reads. Clinical Records permissions
now load at workspace level (use-case-permissions) independent of mounted tabs.
Insights bodies corrected to canonical ContextBuildInput/InterpretationInput/
GroundingCheckInput/InterpretationPersistInput (patient+snapshot binding, template mode,
sanitized idempotency key); external candidate visibly gate-closed. Simulation preview
corrected to GET schedule-preview; observation timeline bound to a new session proxy
with project/patient from selection and explicit advanced-tool labeling; no raw tokens
or UUID paste in normal journeys. Sign-out clears selection and reloads into gated states.

Proof: Playwright rec01-navigation (11 steps incl. refresh, back, sign-out, cross-case
isolation, stale-state and viewer-denied negatives, 8 screenshots, evidence JSON) passed
on real RS256/SQL/storage services with artificial records only. Python negatives for
inaccessible cases (3 passed). Full frontend suite 175 passed; backend auth/workspace
suites 40+47 passed; typecheck/lint/build/ruff clean. Remaining risk: viewer role
cannot list cases (pre-existing editor-gate, surfaced honestly); no real patient data.

## 2026-11-08 - COS-REC-02 first-time experience and reliable demo launch

Branch cos-rec-02-demo-launch (from REC-01 recovery); all prior uncommitted work
preserved. Root causes of "Synthetic demo is not ready": 7-day bundle expiry with no
refresh path; CANCEROS_SYNTHETIC_DEMO flag missing from normal startup; bundle lookup
assumed the serve-script cwd so foundation-launched web never found the file; homepage
advertised unconditionally (including a statically prerendered verdict).

Fix: bundle lookup probes both launcher layouts (plus explicit override); web process
gets the demo flag at normal startup; prepare script gains --check, skip-when-fresh
ensure and --force with actionable output; dev.py foundation/data migrates the
disposable DB and ensures the bundle before API/web; homepage rewritten to the required
plain-language headline, one primary CTA (honestly gated per request via force-dynamic)
plus research-case entry, three capabilities and a subdued synthetic disclosure; demo
session/API/workspace errors give visitor recovery plus the operator check command.

Proof: full stop then dev.py start foundation from cold, then fresh-session Playwright
journey (homepage, launch, canvas rotate with pixel-diff, SC-03, follow-up, refresh;
5 screenshots, evidence JSON, zero console errors) plus shell spec. Full frontend suite
175 passed; backend spot suites 12 passed; typecheck/lint/build/ruff clean. Remaining
risk: none blocking; bundle naturally expires 7 days after preparation (startup
refreshes it automatically).
