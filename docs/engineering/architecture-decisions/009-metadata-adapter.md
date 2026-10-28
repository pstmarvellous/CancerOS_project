# ADR-009: fixture adapter before actual cohort enablement

COS-021, 2026-10-27. Only engineering-clinical-csv/1 is enabled. Actual I-SPY/Duke/
processed-breast adapters remain disabled until exact releases, dictionaries, rights,
linkage and annotation evidence are reviewed. No source fields are invented from
filenames. A safe aggregate inventory found five Data_folder files: one each gz,
PDF, CSV, Markdown and incomplete crdownload. File contents were not inspected and
no approved release or patient association was inferred.

The adapter protocol takes pinned source version, patient mapping, explicit origin,
input checksum and private bytes. It returns version/dictionary hash, deterministic
canonical source output, row findings, capability limitations and private raw/derived
artifact IDs. The exact column order is versioned in metadata_adapters.DICTIONARY.
The committed CSV is wholly synthetic; it is not an empirical cohort dictionary.
Missing results need an explicit reason; absent relative time remains unknown.
Units/qualifiers/source terms survive mapping. Duplicate record identity quarantines
the input. Nothing infers pathology, laboratory values or visits from image names.

Both internal-processing and derivative-creation permissions are required. The
private raw artifact, pinned source/release and derived artifact association are
recorded in immutable adapter_runs. Output uses the existing staged clinical service;
mapping success does not accept or publish records. A bad row/schema retains private
raw bytes and report but produces no usable output. Exact retries replay the same run.
COS-022 expands general DAG/withdrawal handling; this run preserves mandatory input
and output source-parent identity in the interim.

POST patient-scoped `/metadata-adapter-runs` and GET returned Location are actual
authenticated handlers; output_artifact_id feeds observation-batches/validations and
acceptance. No remote URL fetch, cohort download, general filesystem path API or
public dataset export exists. See tests/test_metadata_adapters.py for complete
request assembly and source/rights setup. Evidence: metadata-adapters.json.

Status: fixture-tested; real-data validation and qualified source dictionary review
blocked D01/D03. No complete breast MRI or longitudinal import claim is made.
