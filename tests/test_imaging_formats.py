"""Wholly artificial pixels and identifiers, not medical-image validation."""

import gzip
import io
import logging
import struct
from concurrent.futures import ThreadPoolExecutor

import nibabel as nib
import numpy as np
import pytest
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, ImplicitVRLittleEndian, MRImageStorage

from canceros import imaging_formats as formats
from canceros.imaging_formats import ImagingFormatError, parse_dicom_series, parse_nifti


def nifti_bytes(shape=(3, 4, 2), affine=None):
    image = nib.Nifti1Image(
        np.arange(np.prod(shape), dtype=np.int16).reshape(shape),
        np.diag([2.0, 3.0, 4.0, 1.0]) if affine is None else affine,
    )
    image.header.set_xyzt_units("mm")
    return image.to_bytes()


def dicom_bytes(z, *, series="1.2.826.0.1.2", syntax=ExplicitVRLittleEndian, **changes):
    meta = FileMetaDataset()
    meta.TransferSyntaxUID = syntax
    meta.MediaStorageSOPClassUID = MRImageStorage
    meta.MediaStorageSOPInstanceUID = f"1.2.826.0.1.99.{z + 1}"
    dataset = FileDataset(None, {}, file_meta=meta, preamble=b"\0" * 128)
    dataset.SOPClassUID = MRImageStorage
    dataset.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    dataset.PatientID = "ARTIFICIAL-PARSER-ONLY"
    dataset.PatientName = "ARTIFICIAL^ONLY"
    dataset.StudyInstanceUID = "1.2.826.0.1.1"
    dataset.SeriesInstanceUID = series
    dataset.FrameOfReferenceUID = "1.2.826.0.1.3"
    dataset.Modality = "MR"
    dataset.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
    dataset.ImagePositionPatient = [10, 20, z * 4]
    dataset.PixelSpacing = [3, 2]
    dataset.Rows, dataset.Columns = 2, 3
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = "MONOCHROME2"
    dataset.BitsAllocated = dataset.BitsStored = 16
    dataset.HighBit = 15
    dataset.PixelRepresentation = 0
    dataset.BurnedInAnnotation = "NO"
    dataset.InstanceNumber = 100 - z  # Deliberately opposite to physical order.
    dataset.PixelData = np.full((2, 3), z, dtype="<u2").tobytes()
    for key, value in changes.items():
        setattr(dataset, key, value)
    stream = io.BytesIO()
    dataset.save_as(stream, enforce_file_format=True)
    return stream.getvalue()


def test_nifti_preserves_values_affine_header_and_private_summary():
    raw = nifti_bytes()
    result = parse_nifti(gzip.compress(raw))
    np.testing.assert_array_equal(result.array, np.arange(24).reshape(3, 4, 2))
    np.testing.assert_array_equal(result.affine_ras_mm, np.diag([2, 3, 4, 1]))
    assert result.header_bytes[0] == raw[:352]
    assert result.safe_summary() == {
        "format": "nifti",
        "shape": [3, 4, 2],
        "parser": "bounded-imaging/1",
    }
    assert "array" not in repr(result)
    assert "ARTIFICIAL" not in repr(result)
    assert not result.array.flags.writeable
    assert "privacy_review_required" in result.warnings


def test_nifti_fourth_axis_is_never_guessed_to_be_followup():
    raw = nifti_bytes((2, 3, 4, 2))
    with pytest.raises(ImagingFormatError, match="explicit bounded DCE"):
        parse_nifti(raw)
    result = parse_nifti(raw, fourth_axis="dce_phase")
    assert result.private_metadata["fourth_axis"] == "dce_phase"
    assert result.array.shape == (2, 3, 4, 2)
    with pytest.raises(ImagingFormatError, match="fourth axis"):
        parse_nifti(nifti_bytes(), fourth_axis="dce_phase")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda raw: raw[:-1],
        lambda raw: raw + b"unaccounted-trailing-bytes",
        lambda raw: b"not an image",
        lambda raw: raw[:348] + b"\1\0\0\0" + raw[352:],
    ],
)
def test_nifti_corruption_and_extensions_rejected_without_source_echo(mutate):
    with pytest.raises(ImagingFormatError) as caught:
        parse_nifti(mutate(nifti_bytes()))
    assert "unaccounted" not in str(caught.value)


def test_nifti_bombs_and_header_allocation_preflight(monkeypatch):
    monkeypatch.setattr(formats, "MAX_DECOMPRESSED_BYTES", 1024)
    with pytest.raises(ImagingFormatError, match="Decompressed"):
        parse_nifti(gzip.compress(b"x" * 1025))
    raw = bytearray(nifti_bytes())
    struct.pack_into("<hhhh", raw, 42, 1024, 1024, 1024, 1)
    with pytest.raises(ImagingFormatError, match="voxel resource"):
        parse_nifti(bytes(raw))


def test_nifti_unknown_units_conflicting_geometry_nonfinite_and_no_fallback():
    image = nib.Nifti1Image.from_bytes(nifti_bytes())
    image.header.set_xyzt_units("unknown")
    with pytest.raises(ImagingFormatError, match="millimeter"):
        parse_nifti(image.to_bytes())
    image.header.set_xyzt_units("mm")
    image.set_qform(np.diag([3, 3, 4, 1]), code=1)
    with pytest.raises(ImagingFormatError, match="Conflicting"):
        parse_nifti(image.to_bytes())
    uncoded = bytearray(image.to_bytes())
    struct.pack_into("<hh", uncoded, 252, 0, 0)
    with pytest.raises(ImagingFormatError, match="no fallback"):
        parse_nifti(bytes(uncoded))
    image = nib.Nifti1Image(np.full((2, 2, 2), np.nan), np.eye(4))
    image.header.set_xyzt_units("mm")
    with pytest.raises(ImagingFormatError, match="Nonfinite"):
        parse_nifti(image.to_bytes())


@pytest.mark.parametrize("syntax", [ExplicitVRLittleEndian, ImplicitVRLittleEndian])
def test_dicom_shuffled_files_and_instance_numbers_use_physical_sorting(syntax):
    result = parse_dicom_series(
        [
            dicom_bytes(2, syntax=syntax),
            dicom_bytes(0, syntax=syntax),
            dicom_bytes(1, syntax=syntax),
        ]
    )
    assert result.source_order == (1, 2, 0)
    assert result.array.shape == (3, 2, 3)
    np.testing.assert_array_equal(result.array[0, 0], [0, 1, 2])
    np.testing.assert_array_equal(
        result.affine_ras_mm, [[-2, 0, 0, -10], [0, -3, 0, -20], [0, 0, 4, 0], [0, 0, 0, 1]]
    )
    assert result.private_metadata["patient_id"] == "ARTIFICIAL-PARSER-ONLY"
    assert result.private_metadata["burned_in_annotation"] == ["NO"]
    assert "ARTIFICIAL" not in str(result.safe_summary())
    assert "ARTIFICIAL" not in repr(result)


@pytest.mark.parametrize(
    "changes",
    [
        {"PatientID": "OTHER-PRIVATE-IDENTITY"},
        {"IssuerOfPatientID": "OTHER-ISSUER"},
        {"StudyInstanceUID": "1.2.333"},
        {"SeriesInstanceUID": "1.2.444"},
        {"FrameOfReferenceUID": "1.2.555"},
        {"TemporalPositionIdentifier": 2},
        {"EchoNumbers": 2},
    ],
)
def test_dicom_mixed_dimensions_and_identity_reject_without_echo(changes):
    with pytest.raises(ImagingFormatError, match="Mixed") as caught:
        parse_dicom_series([dicom_bytes(0), dicom_bytes(1, **changes)])
    assert "OTHER" not in str(caught.value)


def test_dicom_duplicates_irregular_grid_and_multiframe_policy():
    with pytest.raises(ImagingFormatError, match="Duplicate DICOM"):
        parse_dicom_series([dicom_bytes(0), dicom_bytes(0)])
    with pytest.raises(ImagingFormatError, match="Duplicate or ambiguous"):
        parse_dicom_series([dicom_bytes(0), dicom_bytes(1, ImagePositionPatient=[10, 20, 0])])
    with pytest.raises(ImagingFormatError, match="Irregular"):
        parse_dicom_series([dicom_bytes(0), dicom_bytes(1), dicom_bytes(3)])
    with pytest.raises(ImagingFormatError, match="multiframe"):
        parse_dicom_series([dicom_bytes(0), dicom_bytes(1, NumberOfFrames=1)])
    with pytest.raises(ImagingFormatError, match="Inconsistent"):
        parse_dicom_series([dicom_bytes(0), dicom_bytes(1, PixelSpacing=[2, 2])])


def test_dicom_truncation_compression_and_undefined_lengths_rejected_before_decode():
    raw = dicom_bytes(0)
    with pytest.raises(ImagingFormatError, match="truncated"):
        parse_dicom_series([raw[:-1], dicom_bytes(1)])
    compressed_syntax = raw.replace(b"1.2.840.10008.1.2.1\0", b"1.2.840.10008.1.2.5\0")
    with pytest.raises(ImagingFormatError, match="uncompressed"):
        parse_dicom_series([compressed_syntax, dicom_bytes(1)])
    malformed = raw + struct.pack("<HH2s2sI", 0x7777, 1, b"UN", b"\0\0", 0xFFFFFFFF)
    with pytest.raises(ImagingFormatError, match="Undefined-length"):
        parse_dicom_series([malformed, dicom_bytes(1)])


@pytest.mark.parametrize(
    "archive", [b"PK\3\4../../patient.dcm", b"7z\xbc\xaf\x27\x1c", b"Rar!", b"BZh-bomb"]
)
def test_archives_never_extract_paths(archive):
    with pytest.raises(ImagingFormatError, match="Archives"):
        parse_nifti(archive)
    with pytest.raises(ImagingFormatError, match="Archives"):
        parse_dicom_series([archive, dicom_bytes(1)])


def test_file_and_series_bounds_precede_parsing(monkeypatch):
    monkeypatch.setattr(formats, "MAX_FILE_BYTES", 4)
    with pytest.raises(ImagingFormatError, match="byte limit"):
        parse_nifti(b"12345")
    with pytest.raises(ImagingFormatError, match="two or more"):
        parse_dicom_series([])


def test_nifti_shear_reflection_preserved_and_singular_rejected():
    affine = np.array([[-2.0, 0.3, 0, 10], [0, 3, 0.2, -8], [0, 0, 4, 2], [0, 0, 0, 1]])
    result = parse_nifti(nifti_bytes(affine=affine))
    np.testing.assert_allclose(result.affine_ras_mm, affine, atol=1e-6, rtol=0)
    raw = bytearray(nifti_bytes())
    # Replace the sform's first spatial row with zero, retaining the coded transform.
    struct.pack_into("<ffff", raw, 280, 0, 0, 0, 0)
    with pytest.raises(ImagingFormatError, match="invalid spatial transform"):
        parse_nifti(bytes(raw))


def test_dicom_invalid_orientation_and_nonfinite_positions_are_safe(caplog, capsys):
    first = dicom_bytes(0)
    with pytest.raises(ImagingFormatError, match="orthonormal"):
        parse_dicom_series(
            [dicom_bytes(0, ImageOrientationPatient=[1, 0, 0, 1, 0, 0]), dicom_bytes(1)]
        )
    with pytest.warns(UserWarning, match="Invalid value for VR DS"):
        nonfinite = dicom_bytes(1, ImagePositionPatient=[10, 20, "nan"])
    with pytest.raises(ImagingFormatError):
        parse_dicom_series([first, nonfinite])
    captured = capsys.readouterr()
    assert "ARTIFICIAL" not in captured.out + captured.err + caplog.text


def test_dicom_uniform_shear_keeps_full_physical_step():
    result = parse_dicom_series(
        [
            dicom_bytes(0),
            dicom_bytes(1, ImagePositionPatient=[10.5, 20, 4]),
            dicom_bytes(2, ImagePositionPatient=[11, 20, 8]),
        ]
    )
    np.testing.assert_array_equal(result.affine_ras_mm[:3, 2], [-0.5, 0, 4])


def test_nifti_truncated_gzip_has_static_error_without_private_header_echo():
    raw = bytearray(nifti_bytes())
    raw[148:169] = b"PRIVATE-HEADER-MARKER"
    with pytest.raises(ImagingFormatError) as caught:
        parse_nifti(gzip.compress(bytes(raw))[:-7])
    assert "PRIVATE" not in str(caught.value)


def test_malformed_dicom_values_never_reach_upstream_logs_or_stderr(caplog, capsys):
    raw = dicom_bytes(0)
    original = b"1.2.826.0.1.99.1"
    marker = b"PRIVATE-MARKER!!"
    assert len(original) == len(marker)
    # Modify bytes after fixture serialization to exercise the upstream reader's
    # source-bearing invalid-UID warning, rather than the fixture writer's warning.
    raw = raw.replace(original, marker)
    with pytest.raises(ImagingFormatError) as caught:
        parse_dicom_series([raw, dicom_bytes(1)])
    captured = capsys.readouterr()
    assert "PRIVATE-MARKER" not in caplog.text + captured.out + captured.err + str(caught.value)


def test_private_log_filter_does_not_suppress_other_threads_or_application_logs(caplog):
    def other_thread():
        logging.getLogger("pydicom").warning("unrelated-thread-event")

    with formats._private_reader_context():
        logging.getLogger("pydicom").warning("private-reader-event")
        logging.getLogger("canceros.test").warning("application-event")
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(other_thread).result()
    logging.getLogger("pydicom").warning("after-reader-event")
    assert "private-reader-event" not in caplog.text
    assert "application-event" in caplog.text
    assert "unrelated-thread-event" in caplog.text
    assert "after-reader-event" in caplog.text
