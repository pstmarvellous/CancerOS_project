# COS-029 annotation meaning and capability evidence

Scope: delegated annotation input/dictionary contracts and pure capability guards.
Read the exact COS-029 prompt, [task-local context](COS-029.md), original capability,
academic and repository/scientific query outputs, SPEC-003 4.6, SPEC-005 segmentation
modes/QC and SPEC-008 section 7. Relevant nodes: DATA.SEG, IMG.MASK, IMG.MODEL and
EVAL.SEG; annotation-term map misses are retained in the parent context. No source
specification/map modifications or model inference. This is AI engineering review,
not radiologist or qualified scientific review.

## Actual source learning

- TCIA/UCSF, *I SPY-1 DCE MRI Data Sharing DICOM Dictionary*, last modified by
  David Newitt **2016-08-31**, [DICOM Objects, Tumor Analysis VOI and Appendix A](https://wiki.cancerimagingarchive.net/pages/viewpage.action?pageId=20643847):
  read distinctions among original acquisitions, derived PE/SER maps, rectangular
  operator VOI and semi-automatically derived FTV. FTV depends on enhancement maps,
  filtering and exclusions inside a VOI. Therefore its region is neither simply
  the enclosing box nor automatically an anatomical contour. These are collection-
  specific definitions, not a universal FTV algorithm or permission to implement
  clinical response calculations. No source thresholds copied into CancerOS.
- Mapped **R01/P01 MAMA-MIA**, Garrucho et al., repository
  [README](https://github.com/LidiaGarrucho/MAMA-MIA/blob/e05e12a98e5772fce4caeb4f77dc17211873f202/README.md)
  pinned to **e05e12a98e5772fce4caeb4f77dc17211873f202**, verified using actual
  `git ls-remote ... refs/heads/main`. Read dataset/expert-segmentation description,
  inference distinction, citations and access/preprocessing notes. The repository
  describes 1,506 multicenter breast DCE-MRI cases and expert segmentations; an
  automatic proposal and an expert annotation are separate evidence categories.
  No inference code adopted/reproduced and no benchmark transfer claimed.
- Pinned MAMA-MIA root LICENSE is **CC BY-NC 4.0**; README also lists source
  collection licenses separately. These observations do not establish CancerOS's
  specific data/annotation/checkpoint rights or hackathon redistribution permission.
  No code, model, image or mask downloaded or copied.
- Garrucho et al., *A large-scale multicenter breast cancer DCE-MRI benchmark dataset
  with expert segmentations*, **Scientific Data 12:453 (2025)**, DOI
  `10.1038/s41597-025-04707-4`: publication metadata was accessible through PMC;
  subsequent full-text section requests hit a browser challenge and Nature redirected
  to an inaccessible authorization page. Do not claim methods/full-paper review.
  I-SPY2 collection fetch returned HTTP 500; the accessible I-SPY1 dictionary above
  informs annotation semantics, not I-SPY2 source compatibility or rights.

Mapped segmentation lectures/textbooks were not newly read for these categorical
guards. No segmentation algorithm is implemented here. Governing source semantics
and the actual collection dictionary constrain classification; missing academic/full
empirical review remains explicit and anatomical capabilities stay gated.

## Three-source decision

Source annotation meaning → owned, class-specific label dictionary and capability
truth table; MAMA-MIA source documentation studied rather than adopted → no qualified
review or authentic mask reproduction available → retain previews and technical QC
while anatomical claims/publication require independent evidence → assert categorical
negative tests for functional regions, bounding boxes, proposals and unknown masks.
Self-overlap or a passing alignment report cannot supply that evidence.

Each distinct positive label has one dictionary entry; no all-positive union or
client-supplied lesion identity is accepted. Parent assigns stable annotation UUIDs
per label. Labels are strict integers 1–65535, at most 32 distinct entries. Meaning
must match class. Authorship remains human/algorithm/unknown separately from class;
model proposals require algorithmic authorship and an explicit method category.
Method categories are controlled codes, not URLs, free-text patient metadata,
verified concrete algorithm identities or inferred model versions. Missing method
and source-annotation evidence remain null. Import input cannot assert scientific
review, technical pass, reviewer identity or publication.

The pure guard consumes **server-owned** review/QC/alignment/rights/publication
states. Defaults deny uses. Passing alignment plus source permission permits
numerical previews and entry into technical QC; technical pass permits explicitly
labelled region arithmetic for known classes. Functional and bounding regions never
pass anatomical guards even with hypothetical qualified review. Only a nonfixture
anatomical contour with qualified review, technical pass, alignment and current
source permission can pass anatomical volume/mesh guards; publication additionally
requires explicit publication authority. The current parent fixture workflow supplies
pending review and fixture origin, so it enables no authentic anatomical claim.
Pure truth-table tests do not create or certify review records.

## Actual checks and gaps

Executed `uv run pytest tests/test_annotation_contracts.py -q`: **16 passed**.
Tests cover distinct labels, unknown authorship/method, duplicates and invalid labels,
meaning mismatches, rejected client review/QC/publication assertions, controlled
method categories, model authorship, fail-closed defaults, nonanatomical classes,
hypothetical reviewed-contour entry into QC, fixture restrictions, revoked rights,
failed alignment and rejected review. Ruff check/format and focused mypy passed.

Parent owns immutable records, current-rights checks, wrong-study/alignment refusal,
stable UUID persistence and generated clients. Real source rights, qualified review,
source-specific annotation evidence and independent validation remain missing.
Hackathon impact: preserves annotation truth and immutable source meaning; no model
access, publication, clinical validation or competition eligibility established.
