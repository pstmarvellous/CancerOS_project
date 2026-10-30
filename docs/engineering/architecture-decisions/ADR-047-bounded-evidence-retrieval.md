# ADR-047: bounded keyword retrieval and separate citation resolution

COS-061 implements SPEC-006 section 10 and SPEC-008 evidence/claim links on the
existing PostgreSQL plus private-object architecture. No vector service,
reranker, URL fetcher, DOI resolver or live external lookup is introduced.
Retrieval and citation are read-only over COS-060 corpora and activation heads;
ingestion rights, retraction handling and original-object retention stay under
ADR-046 and the source registry.

Retrieval accepts one bounded plain-text query and optional declared context
(concepts, topics, subtype, setting, publication/update floors, top_k 1-10).
Unknown subtype/setting is never invented: documents carrying specific
subtype/setting values only match an exactly equal request, while generic
documents match an undeclared request. Date floors compare exact calendar
dates; unknown dates fail a dated request. Duplicate or oversized filters,
blank/NUL/surrogate/oversized queries and unknown fields fail schema checks.

Ranking is PostgreSQL `plainto_tsquery`/`ts_rank` over the active corpus's
removable English projection, ordered by rank then document/passage identity;
no operator, URL, instruction or executable text is interpreted. The query is
normalized NFC and embedded as a bound parameter, combined only with requested
concepts as additional lexical tokens. A separate offline citation check
verifies exact corpus/document/passage membership, current rights, locator
integrity (optional expected text hash) and activation status. Verified
offline resolution never contacts a network; live URL status stays not_checked.

Every hit is labeled a lexical candidate only: `unreviewed_general_research`,
with patient-fact and individual-treatment-effect support permanently false.
Citation resolution and meaningful claim support remain distinct; general
research cannot establish an unrecorded patient fact or a personalized
treatment effect. Retracted, rights-withdrawn, incompatible-context or
hash-mismatched passages are refused, and stale activation expectations fail
closed. Empty eligibility or zero lexical matches return an explicit
no_suitable_evidence status rather than invented citations.

Frozen engineering fixture sets keep development queries disjoint from a final
evaluation set. Reported denominators cover only artificial passages with
fixture relevance labels; they are not scientific precision/recall and do not
replace SPEC-011's reviewed language suite or qualified human adjudication.
