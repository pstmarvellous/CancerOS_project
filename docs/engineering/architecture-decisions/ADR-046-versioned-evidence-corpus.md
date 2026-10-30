# ADR-046: versioned evidence corpus and removable search projection

COS-060 implements SPEC-006 section10 and SPEC-008 evidence tables in the existing
PostgreSQL/private-object architecture. No URL fetcher, PDF/OCR pipeline, embeddings
or vector service is introduced. Admin curators supply bounded plain UTF-8 text
from separately recorded source versions; unsupported formats fail schema checks.
Metadata-only registration contains no source bytes, passages or search entries.

The manifest records actual title/publisher/authors when known, canonical URL/DOI,
source publication/update dates or explicit unknown reasons, retrieval/version,
topic/subtype/setting, attribution and component-specific license/review references.
Declarations do not authorize processing. Source registry INTERNAL, DERIVATIVE
and PUBLIC action permissions gate excerpt import/indexing; real sources require
documented review rather than engineering-fixture approval. External inference
remains independently denied. A public URL or PubMed identifier is not permission.

Approved original bytes go to verified versioned private storage. Original and NFC
hashes are distinct. Passage IDs bind project/document fingerprint, exact normalized
code-point span and text hash. Only complete paragraphs are indexed; long or binary
input is refused rather than silently splitting numerical context. Immutable rows
hold descriptors/hashes and document/corpus membership; text and generated English
tsvector live in a removable PostgreSQL projection with a GIN index. No passage
text appears in ordinary import receipts, metadata history or application logs.

Corpora freeze sorted documents and passage hashes plus index version/configuration.
Build and activation validate current rights/retraction and actual projection hashes.
Activation appends history and atomically changes a project head with expected-head
comparison. HTTP activation requires a strong If-Match from current-head ETag:
missing428, mismatch412. Existing scoped idempotency replays before stale-head
handling, while current source rights are rechecked. CORS permits/exposes these
headers for existing authorized clients. Exact historical corpora remain separate.

Restriction events append and remove the document's current search text/lexemes;
old immutable hashes are preserved. All current reads, imports/replays, builds and
activations reject restricted/retracted sources or missing/corrupt projection.
Unknown retraction status remains needs_review and cannot enter an active corpus.
Upstream source-policy withdrawal immediately denies service access; explicit curator
restriction removes stored index content. No unfiltered search endpoint is exposed.

Private original object copies/versioning require a separate retention/deletion
decision. This task does not claim complete deletion or indefinite retention rights.
The restriction receipt explicitly reports original-object retention review required;
restricted-corpus enablement remains gated on that review. Citation resolution and
lexical ranking do not prove semantic support; COS-061/064 govern those boundaries.

NCI text-reuse and the selected Breast Cancer Treatment PDQ metadata were inspected
as a candidate, with attribution/trademark/image restrictions recorded. No NCI full
text, graphics or source excerpt was ingested by this implementation. Actual tests
use wholly artificial corpus text and isolated private storage/SQL identities.
