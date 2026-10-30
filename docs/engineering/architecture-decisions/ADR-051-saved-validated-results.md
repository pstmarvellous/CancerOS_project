# ADR-051: exact-context result persistence with revalidation and fallback

COS-065 implements SPEC-008 intelligence freshness, SPEC-010 retention and
SPEC-011 resilience over frozen contexts, templates and the grounding gate.
No new public exposure, no cross-patient reuse and no signed-URL caching are
introduced. Only gate-published template reports persist as validated_ready;
private candidates never enter the saved store.

Persistence records the full reproduction identity: project/patient/snapshot,
context hash, execution mode, visibility, model identifier with explicitly
unresolved revision, template/prompt, gate validator and corpus versions,
finding count and idempotency key. Raw prompts and responses are minimized
by construction; routine logs carry no sensitive copies. Rows are immutable;
a source correction creates a new validated row while prior rows stand as
superseded records of their exact historical inputs — hashes are preserved,
never rewritten.

Reuse is keyed by exact project/patient/snapshot/context hash plus matching
model/prompt/validator versions, with current authorization rechecked and a
fresh template-plus-gate pass on every hit. Version, state or corpus drift
misses rather than serving a stale "similar" answer. Private application
state never authorizes shared HTTP/browser caching of patient data.
Outage fallback stays labeled: exact reuse after revalidation reads as a
saved result, otherwise a rule-based fallback; policy refusal remains 403
and is never disguised as an outage. Measurements and trends stay available
even when generation fails. Withdrawal propagates by declining new reuse
while retained history keeps its hashes.
