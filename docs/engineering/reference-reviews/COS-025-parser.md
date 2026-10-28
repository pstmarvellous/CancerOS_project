# COS-025 bounded reader source learning

Scope: delegated implementation of `imaging_formats.py` and its artificial unit
fixtures only. Parent task context is [COS-025](COS-025.md), including exact dual-map
queries and edges. Relevant retrieved nodes are IMG.INGEST, DATA.ARTIFACT, IMG.01,
A16, A05, A03, R06 and R07. Original source specifications remain unchanged.
Read SPEC-003 sections 4.5 and 5.1–5.2 and SPEC-005 IMG-001–008 / P-01–04 from
the existing extracted source texts. Reviewed implementation guide and original
persona/team, repository, reference-integration and hackathon guidance.

## Actual learning and inspection

- DICOM Standards Committee, PS3.3 **2026d**, C.7.6.2 and C.7.6.2.1.1,
  [Image Plane Module](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.7.6.2.html):
  pixel spacing is row then column; image position locates the first voxel center;
  orientation has two direction vectors. Slice thickness is not interslice center
  distance. Biped coordinates are LPS. Decision: XYZ array axes use original column,
  row and physically sorted slice order, with an explicitly converted RAS-mm affine.
  Uniform sheared steps retain the full displacement. No filename or instance-number
  ordering and no inferred spacing for single slices.
- pydicom **3.0.2**: inspected official `dcmread` documentation, tagged
  [filereader.py](https://github.com/pydicom/pydicom/blob/v3.0.2/src/pydicom/filereader.py)
  entry points and defined/undefined value-length behavior, plus tagged pixel utilities.
  Used public `dcmread(force=False, specific_tags=...)` and `Dataset.pixel_array`.
  File-meta transfer syntax is checked before invoking the reader, denying deflate
  and compressed syntax. Flat element boundaries are bounded first; undefined-length
  elements and explicit sequences are rejected. This narrow supported subset avoids
  a claim of comprehensive DICOM validation or arbitrary nested-dataset support.
- NiBabel **5.4.2**: inspected tagged
  [nifti1.py](https://github.com/nipy/nibabel/blob/5.4.2/nibabel/nifti1.py)
  header fields and transform access, and `SerializableImage.from_bytes` in tagged
  [filebasedimages.py](https://github.com/nipy/nibabel/blob/5.4.2/nibabel/filebasedimages.py).
  Public `Nifti1Header`, coded qform/sform, `get_xyzt_units` and
  `Nifti1Image.from_bytes` are exercised by fixtures. The live documentation labels
  itself a development build; tagged source and installed 5.4.2 are the pinned basis.
  Shape, scalar dtype, offset and payload length are checked before decoding pixels.
  Unknown units, uncoded geometry and conflicting transforms are rejected, retaining
  original header bytes privately. Only explicit millimeter NIfTI-1 is supported.
- Licenses inspected: pydicom tagged LICENSE is MIT with GDCM private-dictionary
  BSD conditions; NiBabel tagged COPYING is MIT with listed third-party licenses;
  NumPy 2.4.6 LICENSE is BSD-3-Clause. These software licenses grant no medical
  dataset, annotation or model rights. No checkpoints or external images downloaded.

Mapped ITK guide/MIT lecture chapters were not read for this bounded reader change;
normative DICOM spatial text was read. No empirical breast-MRI dataset or paper was
evaluated. Artificial round trips establish deterministic representation behavior,
not real-cohort compatibility, privacy clearance or clinical correctness.

## Three-source decision and review

Normative spatial principle → public pinned pydicom/NiBabel readers behind byte,
dimension, syntax and transform preflight → no authentic cohort evidence available →
enable only this narrow reader subset behind the parent's privacy/rights/linkage
gates → independently asserted artificial pixel order and physical coordinates.
No inferred patient association is possible inside this module. NIfTI association
authorization belongs to its caller; DICOM source identifiers remain private.
Header strings and even a `BurnedInAnnotation=NO` value never certify anonymization.
Any parsed volume still requires privacy review and geometry QC; parsing publishes
nothing. Critical self-review covered physical axes, decompression allocation,
unknown phase meaning, private exception text and immutable source preservation.

## Limits and checks

Engineering bounds: 8 MiB/file, 32 MiB series/decompressed NIfTI, 2 million scalar
voxels, 256 DICOM slices, 16 explicitly declared DCE phases, axes at most 1024.
No archive extraction, NIfTI-2/extensions, enhanced multiframe, compressed DICOM,
quadruped coordinates, non-MONOCHROME2 pixels, singleton DICOM series or irregular
slice grids. Tolerance 1e-4 mm is a representation threshold, not clinical QC.

Executed `uv run pytest tests/test_imaging_formats.py -q`: 30 artificial cases
passed after correcting a fixture which NiBabel recoded on serialization. Executed
Ruff check/format and `uv run mypy src/canceros/imaging_formats.py` successfully.
Tests cover shuffled input order, independent affine arithmetic, both supported
transfer syntaxes, mixed patient/study/series/frame/sequence, duplicate instances
and positions, irregular geometry, shear/reflection preservation, malformed lengths,
unsupported compression, multiframe, archives, gzip limits/truncation, NIfTI unknown
axes/units/conflicts/singular transforms/nonfinite pixels, resource caps and safe
summary/error behavior. Parent integration owns persisted-byte, authorization,
normal-log and API payload tests. No authentic patient data were inspected.

Critical follow-up found that pydicom 3.0.2 `misc.warn_and_log` sends a log record
before raising a Python warning. An actual malformed artificial UID initially reached
the logger despite warning-to-error handling. Fixed with context-variable filters
on the logger names inspected in the pinned package; unrelated threads/application
logs remain visible. A shared reader lock serializes temporary Python 3.12 warning
filter changes. New negative coverage asserts the malformed marker reaches neither
normal logs nor stderr, and checks context restoration and other-thread logging.
This filter-name inventory must be reviewed when upgrading pydicom. All 30 cases,
Ruff and focused mypy passed after the fix.

Hackathon compliance impact: private deterministic imaging only; no external model
call, source publication, competition eligibility or scientific validation claimed.
