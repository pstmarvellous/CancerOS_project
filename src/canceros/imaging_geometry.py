"""Canonical voxel-center geometry. Technical validity never establishes alignment."""

from __future__ import annotations

import itertools
import math
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Annotated, Any, Literal

import nibabel as nib
import numpy as np
from numpy.typing import ArrayLike, NDArray
from pydantic import Field, FiniteFloat, model_validator

from canceros.contracts import Contract, DecimalString
from canceros.imaging_formats import MAX_PHASES, MAX_VOXELS, ParsedVolume

GEOMETRY_VERSION = "geometry/1"
ROUNDTRIP_TOLERANCE_MM = 1e-5
MAX_CONDITION_NUMBER = 1e6
MIN_SPACING_MM = 0.001
MAX_SPACING_MM = 1000.0
MAX_ABS_COORDINATE_MM = 1e7
Frame = Literal["RAS", "LPS"]
Point = tuple[FiniteFloat, FiniteFloat, FiniteFloat]
Matrix = tuple[
    tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat],
    tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat],
    tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat],
    tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat],
]
Dimension = Annotated[int, Field(strict=True, ge=1, le=1024)]


class GeometryError(ValueError):
    """Static reader-independent error containing no source identifiers."""


def _quantity(number: float) -> str:
    value = Decimal(str(float(number))).quantize(Decimal("0.000000001"), rounding=ROUND_HALF_EVEN)
    return "0" if not value else format(value, "f").rstrip("0").rstrip(".")


def _matrix(value: NDArray[Any]) -> Matrix:
    return tuple(tuple(float(v) for v in row) for row in value)  # type: ignore[return-value]


def _valid_affine(affine: ArrayLike) -> NDArray[np.float64]:
    try:
        value = np.asarray(affine, dtype=np.float64)
        if value.shape != (4, 4) or not np.isfinite(value).all():
            raise GeometryError("Provide a finite four-by-four physical affine")
        if not np.allclose(value[3], [0, 0, 0, 1], atol=1e-12, rtol=0):
            raise GeometryError("Projective transforms are unsupported; provide a spatial affine")
        spacing = np.linalg.norm(value[:3, :3], axis=0)
        if np.any(spacing < MIN_SPACING_MM) or np.any(spacing > MAX_SPACING_MM):
            raise GeometryError("Spacing is zero or outside supported millimeter bounds")
        condition = float(np.linalg.cond(value[:3, :3]))
        if not math.isfinite(condition) or condition > MAX_CONDITION_NUMBER:
            raise GeometryError("Singular or ill-conditioned spatial affine requires review")
        if np.max(np.abs(value[:3, 3])) > MAX_ABS_COORDINATE_MM:
            raise GeometryError("Physical origin exceeds supported coordinate bounds")
        determinant = float(np.linalg.det(value[:3, :3]))
        if not math.isfinite(determinant) or abs(determinant) < 1e-9:
            raise GeometryError("Spatial voxel volume cannot be represented by this contract")
        return value
    except GeometryError:
        raise
    except Exception:
        raise GeometryError("Unreadable spatial affine; supply verified numeric geometry") from None


def convert_frame(
    affine: ArrayLike, source_frame: Frame, target_frame: Frame
) -> NDArray[np.float64]:
    """Change world coordinates by left multiplication, keeping XYZ indices unchanged."""
    if source_frame not in ("RAS", "LPS") or target_frame not in ("RAS", "LPS"):
        raise GeometryError("Only explicit RAS and LPS coordinate frames are supported")
    value = _valid_affine(affine)
    conversion = np.eye(4) if source_frame == target_frame else np.diag([-1.0, -1.0, 1.0, 1.0])
    return conversion @ value


class SourceGeometryTransform(Contract):
    source_frame: Frame
    source_unit: Literal["mm"]
    original_affine: Matrix
    source_to_ras_mm: Matrix
    conversion_direction: Literal["source_world_to_canonical_world"] = (
        "source_world_to_canonical_world"
    )


class CanonicalGeometry(Contract):
    shape_xyz: tuple[Dimension, Dimension, Dimension]
    phase_count: Annotated[int, Field(strict=True, ge=1, le=MAX_PHASES)] | None
    fourth_axis: Literal["dce_phase"] | None
    affine_ras_mm: Matrix
    coordinate_frame: Literal["RAS"] = "RAS"
    physical_unit: Literal["mm"] = "mm"
    voxel_center_convention: Literal["integer_indices_are_centers"] = "integer_indices_are_centers"
    orientation_axis_codes: tuple[str, str, str]
    orientation_meaning: Literal["nearest_cardinal_axes_not_resampling"] = (
        "nearest_cardinal_axes_not_resampling"
    )
    spacing_mm: tuple[DecimalString, DecimalString, DecimalString]
    origin_mm: Point
    voxel_volume_mm3: DecimalString
    handedness: Literal["right", "left"]
    source_transform: SourceGeometryTransform
    validation_version: Literal["geometry/1"] = "geometry/1"
    max_roundtrip_error_mm: DecimalString
    longitudinal_alignment: Literal["not_established"] = "not_established"

    @model_validator(mode="after")
    def consistent_geometry(self):
        if (self.phase_count is None) != (self.fourth_axis is None):
            raise GeometryError("Phase count and explicit fourth-axis meaning must agree")
        if math.prod(self.shape_xyz) * (self.phase_count or 1) > MAX_VOXELS:
            raise GeometryError("Geometry exceeds supported voxel resource bounds")
        affine = _valid_affine(self.affine_ras_mm)
        source = self.source_transform
        expected_conversion = (
            np.eye(4) if source.source_frame == "RAS" else np.diag([-1.0, -1.0, 1.0, 1.0])
        )
        if not np.array_equal(source.source_to_ras_mm, expected_conversion):
            raise GeometryError("Source conversion matrix disagrees with the declared frames")
        original = _valid_affine(source.original_affine)
        if not np.allclose(expected_conversion @ original, affine, atol=1e-9, rtol=0):
            raise GeometryError("Canonical affine disagrees with the retained source transform")
        determinant = float(np.linalg.det(affine[:3, :3]))
        expected_spacing = tuple(_quantity(v) for v in np.linalg.norm(affine[:3, :3], axis=0))
        if self.spacing_mm != expected_spacing or self.voxel_volume_mm3 != _quantity(
            abs(determinant)
        ):
            raise GeometryError("Derived spacing or determinant volume disagrees with the affine")
        if self.handedness != ("right" if determinant > 0 else "left"):
            raise GeometryError("Handedness disagrees with the affine determinant")
        if self.origin_mm != tuple(affine[:3, 3]):
            raise GeometryError("Origin disagrees with the affine translation")
        if self.orientation_axis_codes != tuple(nib.aff2axcodes(affine)):
            raise GeometryError("Orientation axis labels disagree with the affine")
        measured = _roundtrip_error(affine, self.shape_xyz)
        if measured > ROUNDTRIP_TOLERANCE_MM or self.max_roundtrip_error_mm != _quantity(measured):
            raise GeometryError("Coordinate round trip exceeds the engineering tolerance")
        return self


def _roundtrip_error(affine: NDArray[Any], shape) -> float:
    # Include support boundaries and interior fractions: integer indices denote
    # centers; outer faces occur at -.5 and dimension-.5, not zero/dimension.
    corners = list(itertools.product(*[(-0.5, float(n) - 0.5) for n in shape]))
    points = np.asarray(corners + [[(n - 1) / 2 for n in shape], [0.123, 0.456, 0.789]])
    world = points @ affine[:3, :3].T + affine[:3, 3]
    inverse = np.linalg.inv(affine)
    recovered = world @ inverse[:3, :3].T + inverse[:3, 3]
    rebuilt = recovered @ affine[:3, :3].T + affine[:3, 3]
    return float(np.max(np.linalg.norm(rebuilt - world, axis=1)))


def canonical_geometry(
    shape,
    affine: ArrayLike,
    *,
    units: str = "mm",
    source_frame: Frame = "RAS",
    fourth_axis: Literal["dce_phase"] | None = None,
) -> CanonicalGeometry:
    """Retain the grid; this neither reorients pixels nor invents missing metadata."""
    if units != "mm":
        raise GeometryError("Provide verified millimeter units; unit conversion is not inferred")
    try:
        shape = tuple(shape)
    except TypeError:
        raise GeometryError(
            "Provide three spatial dimensions and an optional explicit DCE axis"
        ) from None
    if len(shape) not in (3, 4) or any(type(n) is not int or not 1 <= n <= 1024 for n in shape):
        raise GeometryError(
            "Provide bounded integer XYZ dimensions and an optional DCE phase count"
        )
    if (len(shape) == 4) != (fourth_axis == "dce_phase"):
        raise GeometryError("Four-dimensional geometry requires explicit DCE phase meaning")
    original = _valid_affine(affine)
    ras = convert_frame(original, source_frame, "RAS")
    spacing = np.linalg.norm(ras[:3, :3], axis=0)
    determinant = float(np.linalg.det(ras[:3, :3]))
    return CanonicalGeometry(
        shape_xyz=shape[:3],
        phase_count=shape[3] if len(shape) == 4 else None,
        fourth_axis=fourth_axis,
        affine_ras_mm=_matrix(ras),
        orientation_axis_codes=tuple(nib.aff2axcodes(ras)),
        spacing_mm=(_quantity(spacing[0]), _quantity(spacing[1]), _quantity(spacing[2])),
        origin_mm=tuple(ras[:3, 3]),
        voxel_volume_mm3=_quantity(abs(determinant)),
        handedness="right" if determinant > 0 else "left",
        source_transform=SourceGeometryTransform(
            source_frame=source_frame,
            source_unit="mm",
            original_affine=_matrix(original),
            source_to_ras_mm=_matrix(
                np.eye(4) if source_frame == "RAS" else np.diag([-1.0, -1.0, 1.0, 1.0])
            ),
        ),
        max_roundtrip_error_mm=_quantity(_roundtrip_error(ras, shape[:3])),
    )


def geometry_for(parsed: ParsedVolume) -> CanonicalGeometry:
    if parsed.format == "dicom":
        if "original_affine_lps_mm" not in parsed.private_metadata:
            raise GeometryError("Original DICOM physical geometry is missing")
        result = canonical_geometry(
            parsed.array.shape,
            parsed.private_metadata["original_affine_lps_mm"],
            source_frame="LPS",
        )
    elif parsed.format == "nifti":
        result = canonical_geometry(
            parsed.array.shape,
            parsed.affine_ras_mm,
            units=parsed.private_metadata.get("spatial_units", "unknown"),
            fourth_axis=parsed.private_metadata.get("fourth_axis"),
        )
    else:
        raise GeometryError("Unsupported source geometry format")
    if not np.allclose(result.affine_ras_mm, parsed.affine_ras_mm, atol=1e-9, rtol=0):
        raise GeometryError("Retained source geometry disagrees with the decoded volume")
    return result


def _coordinates(coordinates: ArrayLike) -> NDArray[np.float64]:
    try:
        points = np.asarray(coordinates, dtype=np.float64)
        if (
            points.ndim not in (1, 2)
            or points.shape[-1] != 3
            or points.size == 0
            or points.size > 300_000
            or not np.isfinite(points).all()
            or np.max(np.abs(points)) > 1e12
        ):
            raise GeometryError("Provide a bounded finite XYZ coordinate or coordinate list")
        return points
    except GeometryError:
        raise
    except Exception:
        raise GeometryError("Unreadable coordinates; provide finite XYZ values") from None


def index_to_world(geometry: CanonicalGeometry, coordinates: ArrayLike) -> NDArray[np.float64]:
    points = _coordinates(coordinates)
    affine = np.asarray(geometry.affine_ras_mm)
    return points @ affine[:3, :3].T + affine[:3, 3]


def world_to_index(geometry: CanonicalGeometry, coordinates: ArrayLike) -> NDArray[np.float64]:
    points = _coordinates(coordinates)
    inverse = np.linalg.inv(np.asarray(geometry.affine_ras_mm))
    return points @ inverse[:3, :3].T + inverse[:3, 3]
