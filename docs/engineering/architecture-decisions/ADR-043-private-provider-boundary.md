# ADR-043: private provider boundary and closed live enablement

COS-057 implements the provider boundary inside the existing FastAPI application.
SPEC-006 sections6/12–16, SPEC-008 section13.6, SPEC-010 SAFE-19–21 and audit
A04/D04 govern it. Phase4 execution was owner-authorized on2026-10-30; that does
not authorize external processing, paid calls or scientific publication.

The documented Meta Responses protocol is implemented through a single bounded
HTTP transport. Endpoint/model remain server configuration; endpoint is limited to
the documented HTTPS host/path, redirects and environment proxies are disabled.
No SDK, additional provider, tool executor or raw model proxy is introduced. The
existing pinned httpx dependency becomes a runtime dependency; its BSD license is
retained by the distribution. No vendor code, weights or data were copied.

`export/1` remains a legacy deny guard and cannot authorize runtime transmissions.
`export/2` adds purpose, account/region, retention/training/onward-use declarations,
hashed permission/source-rights evidence, expiry/revocation, field/data-class
allowlisting and exact minimized-input and complete-wire approval hashes. Evidence
files and matching configuration are necessary checks, not proof of legal approval.
Current snapshot/source authorization is rechecked before every attempt. There is
no production caller until the context/rights integration and COS-064 gate exist.
Both the gateway and actual HTTP transport block all non-test modes, regardless
of an environment flag. The concrete HTTP transport additionally requires an
injected httpx.MockTransport even in test mode, preventing real network access. No live call was made or authorized.

The initial typed payload supports only bounded structured measurements, missing
category codes and evidence IDs. Raw DICOM, note text, identity mappings, arbitrary
metadata, signed links and tools are absent. Note extraction is explicitly
unavailable; a purpose enum does not imply that its note payload is implemented.
Request count (maximum3), input/response bytes, per-attempt timeout (maximum30s)
and output-token ceiling are bounded. Without verified pricing/billing approval,
monetary budgets and account-wide rate accounting remain enablement dependencies.

Native schema constraints supplement strict local JSON parsing: reject duplicate
keys, nonfinite values, extra candidate fields, oversized/truncated bodies, wrong
snapshot/model/reference IDs and unsupported response forms. Candidate content is
excluded from ordinary result serialization and remains private even if its schema
passes. The default output validator always refuses publication until COS-064.
Model revision stays null when the provider supplies no immutable revision.

`GET /api/v1/projects/{project_id}/ai/capabilities` is the sole new HTTP route. It
authenticates project membership, has no patient inputs, returns no credentials or
account metadata, and truthfully reports local inventory support and blocked
external/extraction/publication paths. A local template inventories already-owned
inputs without inventing findings; full patient summaries arrive in COS-062/063.
Typed provider refusals preserve403 EXTERNAL_PROCESSING_NOT_ALLOWED; arbitrary
provider text is never a public error. Existing domain history is unchanged.
