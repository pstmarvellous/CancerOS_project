# ADR-001: scoped foundation contracts

Task COS-008; version1; status: selected for reversible Phase 1 implementation under
the user's sequential execution authorization. Not a claim of formal baseline approval.
Capabilities/academic IDs and edges: ../reference-reviews/COS-008.json.

Decision: single installed Python src package, central Pydantic schemas, separate
runtime OpenAPI/design JSON Schema, generated TypeScript. Append-only revision journal
plus immutable job input. Patient-owned relative-time origins independent of state.
Exact-membership/1 assembly semantics and future C01 project-scoped discovery reads.
Alternative rejected: reconstruct history from mutable heads; invent baseline dates;
duplicate API catalogs; force graph-path copies; include planned endpoints as runtime.

Standards inspected: PostgreSQL18 documentation 5.5 (CHECK/not-null/unique/FK; cross-row
constraints require proper FK/triggers), RFC9457 July2023 sections3/5 (typed safe
Problem Details), ITK Software Guide online Book1 chapter4.1 (image representation;
no numerical algorithm implemented). Online edition numbers not established beyond
the visible chapter; no invented edition/page. Links:
https://www.postgresql.org/docs/18/ddl-constraints.html
https://www.rfc-editor.org/rfc/rfc9457.html
https://itk.org/ITKSoftwareGuide/html/Book1/ITKSoftwareGuide-Book1ch4.html

Three-source note: engineering standards support explicit contracts and constraints;
candidate upstream Pydantic/FastAPI interfaces will be inspected/tested at resolved
installed versions in COS-010; empirical clinical evidence is not applicable to this
foundation design and remains absent for scientific enablement. No clinical license,
dataset right or model entitlement inferred. No upstream source copied.

Test contracts: decimal/time malformed input rejection; schema/client drift; N after
N+1 reconstruction; cross-patient origin rejection; append-only SQL; lab-only fixture
has no current mesh; project/role denials; configured private transport/storage smoke.
Design closure is separate from implementation and runtime verification.
