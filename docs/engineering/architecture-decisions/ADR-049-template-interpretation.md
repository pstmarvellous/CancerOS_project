# ADR-049: deterministic template interpretation with private candidates

COS-063 implements SPEC-006 section 12, SPEC-008 section 13.6 and SPEC-010
SAFE-20/21 over the frozen COS-062 context and the COS-057 provider boundary.
No model arithmetic, no streaming, no novel prose and no publication path are
introduced. The only visible mode is a deterministic template; the external
candidate mode exists solely to fail closed until COS-064 validates it.

Template findings project verified context fields verbatim: observed
measurements carry metric code/value/unit from the context, background items
reference retained passage locators without asserting support, and gaps name
missing modalities. Numerical text is backend-rendered from verified fields
under the existing qualifier policy; no LLM computes, rounds or compares
values. Observed findings, synthetic scenario descriptions and general
background stay in separate kinds; no formal response grades, prognosis,
resistance, causality or treatment recommendations are emitted.

Every build revalidates the exact context snapshot and hash. Context
mismatch, stale hash or the external mode returns 409; nothing unpublished
becomes visible. The minimized provider export view reuses COS-062 codes and
excludes local-only fields. The thin state-view panel labels execution mode
prominently, expands each finding to its measurement/passage references and
discards results on selection change. Fixture denominators cover template
determinism and mode gating only; they are not clinical or safety validation.
