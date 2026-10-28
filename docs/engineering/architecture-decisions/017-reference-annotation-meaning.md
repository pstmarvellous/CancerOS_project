# ADR-017: per-label reference import with explicit annotation meaning

COS-029, 2026-10-28. SPEC-003 4.6/5.3, SPEC-005 section 7, SPEC-008 section 7
and SPEC-010 source/provenance rules govern the annotation-meaning/1 extension.

Import only a passing, owned image/mask alignment. Preserve source version, study,
source image, original/aligned mask, geometry, authorship category, method category
and source annotation evidence hash. Missing authorship/method evidence stays unknown.
There is no unverified annotator name or guessed model version in browser metadata.
Each positive label needs one unambiguous dictionary entry and receives a distinct
immutable segmentation UUID. Retries retain those IDs. No patient lesion identity
across visits is inferred; COS-038 owns reviewed correspondence.

Classify anatomical tumor contour, model proposal, functional enhancement region,
bounding box, approximate/illustrative region and unknown separately. Class-specific
dictionary meanings are validated; proposals require algorithmic authorship/source
method. The declared class is not review evidence. A functional analysis region or
bounding region cannot become an anatomical contour through successful alignment,
positive voxels or a generic review flag. Original masks and prior metadata remain
unchanged; revised classification creates another immutable import/version.

Owned capability policy separates preview, technical QC, numerical region volume,
anatomical volume/mesh and publication. Anatomical claims require appropriate class,
qualified review, technical pass, actual source permissions and authentic origin.
Publication adds explicit authority/review. Engineering fixtures cannot satisfy
authentic anatomical claims. Imported objects remain draft with technical/scientific
review pending. No HTTP field can assert qualified review, QC success or publication.

Source rights/withdrawals are checked before import, including replay, and before
actual mask use. Composite foreign keys bind batch, alignment and mask to one patient;
metadata/report/lineage hashes and immutable triggers retain history. A label-specific
internal reader selects only that label and never merges every positive voxel.

Evidence: annotation-import.json, contract policy fixtures plus PostgreSQL/S3/HTTP
ownership, invalid labels, failed alignment, meaning versioning and client-review
rejection. Pure tests of a hypothetical qualified contour are policy tests, not an
actual reviewer signature. Real source rights, independent annotation suitability and
qualified review remain open under D01. COS-030 is optional/deferred; continue COS-031.
