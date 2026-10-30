# ADR-056: interpretation job orchestration with closed external mode

COS-070 implements SPEC-008 interpretation/evidence/provenance/validation
routes and SPEC-010/011 over the COS-057–065 services and the C01/C03/C04
decisions. No free-form model endpoint, no patient-data tool gateway and no
raw model proxy are introduced. Job submission orchestrates one bounded
sequence: patient-authorized state read, frozen context build with purpose,
template interpretation, grounding validation and validated persistence —
202 acceptance apart, nothing validates on submission alone.

Exact state_id, snapshot hash, purpose, mode and optional comparison ride
the canonical job input; stale or mismatched context fails closed and
external mode stays 409 until the COS-064 gate path authorizes it.
Disallowed export returns 403 with zero transmission; outages may yield
only the labeled deterministic fallback; unsupported claims fail with
FAILED_GROUNDING. Jobs are idempotent by key and replay the original
receipt; results expose execution mode, model identity when available,
corpus version, record/measurement/passage references, limitations and
freshness. Current-for-snapshot and superseded-for-timeline meanings are
preserved; a latest-state summary never substitutes for an old snapshot.
Evidence, provenance and evaluation reads reuse role/rights policy with
permitted excerpts and safe locators; denominators, failures and scope are
reported without invented confidence. Fixture denominators cover job
gating and viewer isolation — live behavior and review remain open.
