# ADR-044: scoped private note assertions

COS-058 follows the fixture-verified COS-057 boundary. SPEC-006 section6,
SPEC-008 extracted_facts/span conventions and SPEC-010 govern this implementation.
No live model or broad clinical extractor is enabled. A small deterministic English
grammar recognizes explicit standalone assertions for fatigue, pain, nausea and
swelling. Unsupported clauses are counted and abstained. Numerical severity/labs,
receptor status, staging, treatment and recommendations are outside this version.
Documented recommendations remain original source text; no new advice is produced.
Model comparison is unavailable because live processing remains denied.

The parser accepts exact NFC-normalized UTF-8 text, its SHA256 and owned immutable
note/version/project/patient/branch context. It preserves mention and assertion
code-point spans (zero-based/end-exclusive), original time qualifiers, certainty,
negation, experiencer and provenance. UTF-16 conversion explicitly rejects offsets
inside surrogate pairs. Source text is excluded from reports, representations and
validation-error strings. Fact IDs are deterministic for note/hash/span/extractor.
NFC changes no clinical values; original object bytes/version/hash are retained.

Date resolution needs an explicit verified anchor. Unanchored times and “last
visit” stay unresolved; precision, shift basis and uncertainty are retained.
Pure real-source parser output is REAL_DERIVED, while synthetic stays synthetic.
The runtime registration service currently accepts only approved synthetic
engineering note artifacts. Authentic note onboarding/privacy/source-rights and
qualified clinical NLP review remain open. A user-supplied anchor is only a
declared simulation coordinate, not proof of a genuine note date.

The privileged upstream ingestion process must first create an immutable verified
private artifact and register its source lineage as `note_source_artifact`. The
note API accepts only that artifact ID, never raw text, object keys, credentials or
arbitrary uploads. Registration checks internal and derivative rights before reading
bytes; note and extraction reads recheck inherited rights/withdrawals. Admins may
register/extract; editors with patient access may inspect assertions and supporting
spans. Viewer state access alone grants neither. Protected span responses are JSON
text; consumers must render text nodes and never execute or inject HTML.

Migration0041 adds append-only note_documents and note_extractions with owned
artifact/branch/note/registry foreign keys and mutation-rejection triggers. Note
corrections append a new version linked to its predecessor; conflicting evidence
and old exact spans remain available when rights permit. No source observation,
patient revision, eligibility rule or published state is changed by extraction.
These staging resources precede canonical observation promotion/review contracts;
they cannot masquerade as accepted clinical.note_documents observations. Task059
will link assertions without making their symptom/temporal relationships causal.

Canonical project/patient routes expose metadata, scoped extraction and a separate
protected source-span read. Append-only POSTs use existing scoped idempotency with
authorization and current-rights checks before returning replay. No mutable
aggregate is updated, so If-Match is not applicable. OpenAPI/TypeScript are
regenerated together. No trained model, new service or graph database is added.
