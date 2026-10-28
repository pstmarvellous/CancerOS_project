"""Bounded, private in-memory readers; successful parsing is not imaging readiness.

Only flat classic MR Part-10 files and single-file NIfTI-1 are supported. These
engineering limits deliberately reject many otherwise valid medical images.
"""

from __future__ import annotations

import gzip
import io
import logging
import math
import struct
import threading
import warnings
from collections.abc import Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Literal

import nibabel as nib
import numpy as np
import pydicom
from numpy.typing import NDArray

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_SERIES_BYTES = 32 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 32 * 1024 * 1024
MAX_VOXELS = 2_000_000
MAX_SLICES = 256
MAX_PHASES = 16
PARSER_VERSION = "bounded-imaging/1"
GEOMETRY_ATOL_MM = 1e-4  # Engineering representation tolerance, not a clinical threshold.

# pydicom 3.0.2 logs source-bearing warnings before raising Python warnings. Filters
# remain installed but deny records only in this parsing context, preserving logs
# in unrelated threads. Names were checked in the pinned package's source; review
# this list on upgrade. Python 3.12 warning filters are global, so serialize our
# readers while they temporarily promote warnings to exceptions.
_PARSING_PRIVATE_DICOM: ContextVar[bool] = ContextVar("private_dicom_parsing", default=False)
_WARNING_FILTER_LOCK = threading.RLock()


class _PrivateDicomLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not _PARSING_PRIVATE_DICOM.get()


for _logger_name in (
    "pydicom",
    "pydicom.pixels.utils",
    "pydicom.pixels.decoders.base",
    "pydicom.pixels.encoders.base",
):
    logging.getLogger(_logger_name).addFilter(_PrivateDicomLogFilter())


@contextmanager
def _private_reader_context():
    token = _PARSING_PRIVATE_DICOM.set(True)
    try:
        with _WARNING_FILTER_LOCK, warnings.catch_warnings():
            warnings.simplefilter("error")
            yield
    finally:
        _PARSING_PRIVATE_DICOM.reset(token)


class ImagingFormatError(ValueError):
    """Static safe error; source values and upstream exception text are never exposed."""


@dataclass(frozen=True, repr=False)
class ParsedVolume:
    array: NDArray[Any] = field(repr=False)
    affine_ras_mm: NDArray[np.float64] = field(repr=False)
    format: Literal["dicom", "nifti"]
    private_metadata: dict[str, Any] = field(repr=False)
    header_bytes: tuple[bytes, ...] = field(repr=False)
    source_order: tuple[int, ...]
    warnings: tuple[str, ...] = ("privacy_review_required", "geometry_qc_pending")

    def safe_summary(self) -> dict[str, Any]:
        return {"format": self.format, "shape": list(self.array.shape), "parser": PARSER_VERSION}


def _bounded_bytes(payload: bytes) -> None:
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_FILE_BYTES:
        raise ImagingFormatError("File is empty or exceeds the supported byte limit")
    if payload.startswith((b"PK", b"7z\xbc\xaf\x27\x1c", b"Rar!", b"BZh")) or (
        len(payload) > 262 and payload[257:262] == b"ustar"
    ):
        raise ImagingFormatError("Archives are unsupported; upload individual imaging files")


def _check_affine(affine: NDArray[Any]) -> NDArray[np.float64]:
    value = np.asarray(affine, dtype=np.float64)
    if (
        value.shape != (4, 4)
        or not np.isfinite(value).all()
        or not np.allclose(value[3], [0, 0, 0, 1], atol=1e-8, rtol=0)
        or abs(float(np.linalg.det(value[:3, :3]))) < 1e-12
    ):
        raise ImagingFormatError("Missing or invalid spatial transform; geometry review required")
    return value


def parse_nifti(payload: bytes, *, fourth_axis: Literal["dce_phase"] | None = None) -> ParsedVolume:
    """Association is deliberately absent: the caller must authorize an explicit manifest.

    A declared DCE axis is retained as phases within one examination, never visits.
    Source bytes, including potentially identifying header strings, stay private.
    """
    _bounded_bytes(payload)
    try:
        if payload.startswith(b"\x1f\x8b"):
            with gzip.GzipFile(fileobj=io.BytesIO(payload)) as stream:
                raw = stream.read(MAX_DECOMPRESSED_BYTES + 1)
            if len(raw) > MAX_DECOMPRESSED_BYTES:
                raise ImagingFormatError("Decompressed imaging exceeds the supported byte limit")
        else:
            raw = payload
        if len(raw) < 352 or raw[344:348] != b"n+1\0":
            raise ImagingFormatError("Only single-file NIfTI-1 images are supported")
        if raw[348:352] != b"\0\0\0\0":
            raise ImagingFormatError("NIfTI extensions require a separately reviewed adapter")
        with _private_reader_context():
            header = nib.Nifti1Header(raw[:348], check=False)
            if int(header["sizeof_hdr"]) != 348:
                raise ImagingFormatError("Invalid NIfTI header")
            shape = header.get_data_shape()
            if len(shape) not in (3, 4) or any(d <= 0 or d > 1024 for d in shape):
                raise ImagingFormatError(
                    "Only bounded three-dimensional images or DCE phases are supported"
                )
            if len(shape) == 4 and (fourth_axis != "dce_phase" or shape[3] > MAX_PHASES):
                raise ImagingFormatError(
                    "Four-dimensional input requires an explicit bounded DCE phase axis"
                )
            if len(shape) == 3 and fourth_axis is not None:
                raise ImagingFormatError("Declared fourth axis does not match the input dimensions")
            dtype = header.get_data_dtype()
            if dtype.kind not in "iuf" or dtype.itemsize > 8 or math.prod(shape) > MAX_VOXELS:
                raise ImagingFormatError("Unsupported voxel type or voxel resource limit exceeded")
            offset = float(header["vox_offset"])
            if not math.isfinite(offset) or offset != int(offset) or offset < 352:
                raise ImagingFormatError("Invalid NIfTI pixel offset")
            if int(offset) + math.prod(shape) * dtype.itemsize != len(raw):
                raise ImagingFormatError("Truncated or unexpected trailing NIfTI pixel data")
            if header.get_xyzt_units()[0] != "mm":
                raise ImagingFormatError("This adapter requires explicit millimeter spatial units")
            qform, qcode = header.get_qform(coded=True)
            sform, scode = header.get_sform(coded=True)
            if not qcode and not scode:
                raise ImagingFormatError(
                    "NIfTI requires a coded physical transform; no fallback is inferred"
                )
            if qcode and scode and not np.allclose(qform, sform, atol=GEOMETRY_ATOL_MM, rtol=0):
                raise ImagingFormatError("Conflicting NIfTI qform and sform require review")
            affine = _check_affine(sform if scode else qform)
            image = nib.Nifti1Image.from_bytes(raw)
            array = np.asarray(image.dataobj, dtype=np.float64)
            if not np.isfinite(array).all():
                raise ImagingFormatError("Nonfinite image intensities are unsupported")
            array.setflags(write=False)
            affine.setflags(write=False)
            return ParsedVolume(
                array,
                affine,
                "nifti",
                {
                    "spatial_units": "mm",
                    "fourth_axis": fourth_axis,
                    "qform_code": int(qcode),
                    "sform_code": int(scode),
                    "qform": None if qform is None else qform.tolist(),
                    "sform": None if sform is None else sform.tolist(),
                },
                (raw[: int(offset)],),
                (0,),
            )
    except ImagingFormatError:
        raise
    except Exception:
        raise ImagingFormatError("Unreadable or unsupported NIfTI image") from None


_LONG_VR = {b"OB", b"OD", b"OF", b"OL", b"OV", b"OW", b"SQ", b"UC", b"UR", b"UT", b"UN"}
_TRANSFER_SYNTAXES = {"1.2.840.10008.1.2.1", "1.2.840.10008.1.2"}
_MR_SOP_CLASS = "1.2.840.10008.5.1.4.1.1.4"
_TAGS = [
    "SOPClassUID",
    "SOPInstanceUID",
    "PatientID",
    "IssuerOfPatientID",
    "PatientName",
    "PatientBirthDate",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "FrameOfReferenceUID",
    "Modality",
    "ImageOrientationPatient",
    "ImagePositionPatient",
    "PixelSpacing",
    "Rows",
    "Columns",
    "SamplesPerPixel",
    "PhotometricInterpretation",
    "BitsAllocated",
    "BitsStored",
    "HighBit",
    "PixelRepresentation",
    "PixelData",
    "NumberOfFrames",
    "RescaleSlope",
    "RescaleIntercept",
    "BurnedInAnnotation",
    "AcquisitionDateTime",
    "AcquisitionDate",
    "AcquisitionTime",
    "SequenceName",
    "TemporalPositionIdentifier",
    "EchoNumbers",
    "ImageType",
    "AnatomicalOrientationType",
]


def _part10_preflight(raw: bytes) -> None:
    """Reject deflate/undefined lengths before the library can decompress or recurse."""
    if len(raw) < 144 or raw[128:132] != b"DICM":
        raise ImagingFormatError("DICOM Part-10 preamble and file metadata are required")
    offset, syntax, elements = 132, None, 0
    while offset < len(raw):
        if offset + 8 > len(raw):
            raise ImagingFormatError("Truncated DICOM element")
        group, element = struct.unpack_from("<HH", raw, offset)
        explicit = group == 2 or syntax != "1.2.840.10008.1.2"
        if group != 2 and syntax not in _TRANSFER_SYNTAXES:
            raise ImagingFormatError(
                "Only uncompressed little-endian classic MR DICOM is supported"
            )
        if explicit:
            vr = raw[offset + 4 : offset + 6]
            if vr == b"SQ":
                raise ImagingFormatError(
                    "Sequence-bearing DICOM requires a separately reviewed adapter"
                )
            if vr in _LONG_VR:
                if offset + 12 > len(raw):
                    raise ImagingFormatError("Truncated DICOM element")
                length = struct.unpack_from("<I", raw, offset + 8)[0]
                start = offset + 12
            else:
                if len(vr) != 2 or not vr.isalpha() or vr != vr.upper():
                    raise ImagingFormatError("Invalid DICOM value representation")
                length = struct.unpack_from("<H", raw, offset + 6)[0]
                start = offset + 8
        else:
            length = struct.unpack_from("<I", raw, offset + 4)[0]
            start = offset + 8
        if length == 0xFFFFFFFF or start + length > len(raw) or length % 2:
            raise ImagingFormatError("Undefined-length or truncated DICOM elements are unsupported")
        if group == 2 and element == 0x10:
            syntax = raw[start : start + length].rstrip(b"\0 ").decode("ascii")
            if syntax not in _TRANSFER_SYNTAXES:
                raise ImagingFormatError(
                    "Only uncompressed little-endian classic MR DICOM is supported"
                )
        offset = start + length
        elements += 1
        if elements > 10000:
            raise ImagingFormatError("DICOM metadata element limit exceeded")


def parse_dicom_series(payloads: Sequence[bytes]) -> ParsedVolume:
    """Build XYZ voxels by physical position, retaining source bytes/order privately."""
    if not 2 <= len(payloads) <= MAX_SLICES or sum(map(len, payloads)) > MAX_SERIES_BYTES:
        raise ImagingFormatError("A bounded series of two or more slices is required")
    try:
        datasets = []
        with _private_reader_context():
            for raw in payloads:
                _bounded_bytes(raw)
                _part10_preflight(raw)
                ds = pydicom.dcmread(io.BytesIO(raw), force=False, specific_tags=_TAGS)
                if str(ds.SOPClassUID) != _MR_SOP_CLASS or str(ds.Modality) != "MR":
                    raise ImagingFormatError("Only classic single-frame MR images are supported")
                if "NumberOfFrames" in ds:
                    raise ImagingFormatError("Enhanced or multiframe DICOM is unsupported")
                if str(ds.get("AnatomicalOrientationType", "BIPED")) != "BIPED":
                    raise ImagingFormatError("Only biped patient coordinates are supported")
                if (
                    int(ds.SamplesPerPixel) != 1
                    or str(ds.PhotometricInterpretation) != "MONOCHROME2"
                ):
                    raise ImagingFormatError("Only monochrome scalar MR pixels are supported")
                if int(ds.BitsAllocated) not in (8, 16, 32):
                    raise ImagingFormatError("Unsupported DICOM pixel representation")
                datasets.append(ds)
            first = datasets[0]
            consistency = [
                "PatientID",
                "IssuerOfPatientID",
                "StudyInstanceUID",
                "SeriesInstanceUID",
                "FrameOfReferenceUID",
                "TemporalPositionIdentifier",
                "EchoNumbers",
                "ImageType",
            ]
            required = [
                "PatientID",
                "StudyInstanceUID",
                "SeriesInstanceUID",
                "FrameOfReferenceUID",
                "SOPInstanceUID",
            ]
            for ds in datasets:
                if any(not str(ds.get(name, "")).strip() for name in required):
                    raise ImagingFormatError(
                        "Essential patient, study, series or frame identity is missing"
                    )
                if any(str(ds.get(name, "")) != str(first.get(name, "")) for name in consistency):
                    raise ImagingFormatError(
                        "Mixed patient, study, series, frame or sequence dimensions"
                    )
            if len({str(ds.SOPInstanceUID) for ds in datasets}) != len(datasets):
                raise ImagingFormatError("Duplicate DICOM instances are unsupported")
            orientation = np.asarray(first.ImageOrientationPatient, dtype=float)
            spacing = np.asarray(first.PixelSpacing, dtype=float)
            if (
                orientation.shape != (6,)
                or spacing.shape != (2,)
                or not np.isfinite(orientation).all()
                or not np.isfinite(spacing).all()
                or np.any(spacing <= 0)
            ):
                raise ImagingFormatError("Invalid DICOM orientation or pixel spacing")
            row, column = orientation[:3], orientation[3:]
            if not np.allclose(
                [np.linalg.norm(row), np.linalg.norm(column), np.dot(row, column)],
                [1, 1, 0],
                atol=1e-5,
                rtol=0,
            ):
                raise ImagingFormatError(
                    "DICOM orientation must contain orthonormal direction cosines"
                )
            normal = np.cross(row, column)
            positions = np.asarray([ds.ImagePositionPatient for ds in datasets], dtype=float)
            if positions.shape != (len(datasets), 3) or not np.isfinite(positions).all():
                raise ImagingFormatError("Invalid DICOM physical slice positions")
            order = np.argsort(positions @ normal, kind="stable")
            sorted_positions = positions[order]
            distances = np.diff(sorted_positions @ normal)
            if np.any(distances <= GEOMETRY_ATOL_MM):
                raise ImagingFormatError("Duplicate or ambiguous physical slice positions")
            step = sorted_positions[1] - sorted_positions[0]
            if not np.allclose(
                np.diff(sorted_positions, axis=0), step, atol=GEOMETRY_ATOL_MM, rtol=0
            ):
                raise ImagingFormatError("Irregular DICOM slice sampling requires review")
            shape = (int(first.Columns), int(first.Rows), len(datasets))
            if min(shape) <= 0 or max(shape) > 1024 or math.prod(shape) > MAX_VOXELS:
                raise ImagingFormatError("DICOM voxel resource limit exceeded")
            slices = []
            for index in order:
                ds = datasets[int(index)]
                if (
                    (int(ds.Columns), int(ds.Rows)) != shape[:2]
                    or not np.allclose(ds.ImageOrientationPatient, orientation, atol=1e-5, rtol=0)
                    or not np.allclose(ds.PixelSpacing, spacing, atol=1e-5, rtol=0)
                ):
                    raise ImagingFormatError("Inconsistent DICOM slice grid")
                expected_bytes = shape[0] * shape[1] * int(ds.BitsAllocated) // 8
                if len(ds.PixelData) != expected_bytes + expected_bytes % 2:
                    raise ImagingFormatError("Truncated or unexpected DICOM pixel bytes")
                values = np.asarray(ds.pixel_array, dtype=np.float64).T
                values = values * float(ds.get("RescaleSlope", 1)) + float(
                    ds.get("RescaleIntercept", 0)
                )
                if not np.isfinite(values).all():
                    raise ImagingFormatError("Nonfinite DICOM pixel data or scaling")
                slices.append(values)
            lps = np.eye(4)
            lps[:3, 0], lps[:3, 1], lps[:3, 2], lps[:3, 3] = (
                row * spacing[1],
                column * spacing[0],
                step,
                sorted_positions[0],
            )
            affine = _check_affine(np.diag([-1.0, -1.0, 1.0, 1.0]) @ lps)
            array = np.stack(slices, axis=2)
            array.setflags(write=False)
            affine.setflags(write=False)
            private: dict[str, Any] = {
                "patient_id": str(first.PatientID),
                "issuer_of_patient_id": str(first.get("IssuerOfPatientID", "")),
                "study_uid": str(first.StudyInstanceUID),
                "series_uid": str(first.SeriesInstanceUID),
                "frame_of_reference_uid": str(first.FrameOfReferenceUID),
                "acquisition": {
                    name: str(first.get(name, ""))
                    for name in [
                        "AcquisitionDateTime",
                        "AcquisitionDate",
                        "AcquisitionTime",
                        "SequenceName",
                        "TemporalPositionIdentifier",
                        "EchoNumbers",
                        "ImageType",
                    ]
                },
                "deidentification_evidence": "not_established_by_parser",
            }
            private["sop_instance_uids"] = [str(datasets[int(i)].SOPInstanceUID) for i in order]
            private["identifying_tags_present"] = any(
                name in ds
                for ds in datasets
                for name in ["PatientID", "PatientName", "PatientBirthDate"]
            )
            private["burned_in_annotation"] = sorted(
                {str(ds.get("BurnedInAnnotation", "UNKNOWN")) for ds in datasets}
            )
            private["original_affine_lps_mm"] = lps.tolist()
            return ParsedVolume(array, affine, "dicom", private, (), tuple(int(i) for i in order))
    except ImagingFormatError:
        raise
    except Exception:
        raise ImagingFormatError("Unreadable or unsupported DICOM series") from None
