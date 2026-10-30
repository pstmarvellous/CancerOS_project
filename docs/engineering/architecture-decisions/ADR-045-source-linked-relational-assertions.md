# ADR-045: source-linked relational assertions

COS-059 implements SPEC-006 section9 with PostgreSQL tables and the existing
canonical identities. Patient, lesion, clinical observation, physical measurement,
branch/state and note extraction IDs resolve through their actual domain readers
and current lineage/rights controls. There is no duplicate patient graph, graph
database, causal model or automatic clinical truth promotion.

The initial enabled relationships are ownership/source links, extracted symptom
assertions about local vocabulary concepts, explicit hypothetical baseline links,
unreviewed associations and proposed lexical concept relationships. General
concept links are project-only and cannot establish patient facts. Publications,
evidence statements, outcomes and treatment-exposure edges remain reserved and
disabled until their canonical evidence/clinical backing is implemented. This
dependency is explicit rather than represented by fabricated functioning records.

Entity kind, owned canonical row, registry kind, project/patient, exact branch,
current rights and source supports are independently checked. Supports in this
initial slice must be endpoint records, with an explicit matched lesion-association
event exception for HAS_MEASUREMENT. Third-branch support cannot bypass isolation.
The only branch-to-unbranched boundary exception is GENERATED_FROM_BASELINE with
an actual branch record naming the exact baseline measurement. The engineering
branch still reports observed_baseline_verified=false; no authentic baseline proof
is created by a structurally correct link.

ABOUT_CONCEPT binds an exact extraction/fact UUID to the same supported concept
code. Negated, possible, planned and family assertions keep their original note
fact; they never become accepted observations. Source and target/support provenance
determine the link origin. Synthetic support makes the relationship synthetic.
Model proposals remain unverified; no CAUSES, resistance, efficacy or prescription
edge is available. “Source linked” means referenced, not scientifically reviewed.

Migration0042 adds local vocabulary versions, relationship events and explicit
support foreign keys. Endpoint resource/concept FKs and kind checks prevent
dangling or cross-patient links. Correction triggers enforce root/version and exact
patient/branch continuity; each correction appends and concurrent successors cannot
silently fork the same version. Original events remain exact historical reads.
The ordinary relationship table permits concept cycles. The existing provenance
graph keeps its separate acyclic semantics and is not populated with concept edges.

Traversal checks the starting resource and every returned edge, with depth1–3,
page1–100 and a500-candidate scope ceiling. Exceeding the ceiling returns an
explicit budget refusal rather than unbounded recursive work. Deterministic order
and a snapshot hash pin eligible events and filters; supplied mismatched hashes
return409, including current-rights changes. No arbitrary SQL/URL or unrestricted
patient traversal is exposed. General literature retrieval and signed-cursor API
conformance remain separate later tasks.

Project concepts/lexical links and patient relationships use separate canonical
route scopes within the existing API. Admin writes and editor/patient-authorized
reads use existing identity, scoped idempotency, private/no-store responses and
generated contracts. Clients must render labels/statements as escaped text and
use persisted IDs for source navigation. No raw note, private object path or signed
grant appears in relationship content.
