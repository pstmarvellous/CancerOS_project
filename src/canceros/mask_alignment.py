"""Explicit label-grid alignment with conservative clipping and volume checks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Annotated, Any, Literal

import numpy as np
import scipy
from numpy.typing import NDArray
from pydantic import Field, model_validator
from scipy import ndimage

from canceros.contracts import Contract, DecimalString, Hash
from canceros.imaging_geometry import CanonicalGeometry, Matrix

IDENTITY = ((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0))
INDEX_BOUNDARY_TOLERANCE = 1e-7


class MaskAlignmentError(ValueError):
    """Safe static validation error; patient/study authorization belongs to caller."""


class AlignmentConfig(Contract):
    expected_labels: Annotated[
        tuple[Annotated[int, Field(strict=True, ge=1, le=65535)], ...],
        Field(min_length=1, max_length=32),
    ]
    source_to_target_world: Matrix = IDENTITY
    transform_kind: Literal["identity", "rigid"] = "identity"
    mode: Literal["exact_grid", "nearest_neighbor"] = "exact_grid"
    max_relative_volume_error: DecimalString = "0.01"
    version: Literal["alignment/1"] = "alignment/1"

    @model_validator(mode="after")
    def valid_policy_and_transform(self):
        if len(set(self.expected_labels)) != len(self.expected_labels):
            raise MaskAlignmentError("Expected labels must be distinct positive integers")
        if not 0 <= Decimal(self.max_relative_volume_error) <= Decimal("0.01"):
            raise MaskAlignmentError(
                "Volume-error policy must be between zero and the frozen one-percent ceiling"
            )
        transform = np.asarray(self.source_to_target_world)
        if not np.isfinite(transform).all() or not np.array_equal(transform[3], [0, 0, 0, 1]):
            raise MaskAlignmentError(
                "Provide a finite source-world to target-world spatial transform"
            )
        if np.max(np.abs(transform[:3, 3])) > 1e7:
            raise MaskAlignmentError("Transform translation exceeds supported physical bounds")
        linear = transform[:3, :3]
        if not np.allclose(linear.T @ linear, np.eye(3), atol=1e-9, rtol=0) or not np.isclose(
            np.linalg.det(linear), 1, atol=1e-9, rtol=0
        ):
            raise MaskAlignmentError(
                "Only proper rigid world transforms are supported; no scaling or reflection is inferred"
            )
        if self.transform_kind == "identity" and not np.array_equal(transform, np.eye(4)):
            raise MaskAlignmentError("Identity declaration disagrees with the supplied transform")
        return self


class LabelAlignmentStats(Contract):
    label: int
    source_voxels: int
    output_voxels: int
    source_volume_mm3: DecimalString
    output_volume_mm3: DecimalString
    absolute_volume_change_mm3: DecimalString
    allowed_volume_change_mm3: DecimalString
    source_components_6: int
    output_components_6: int


class AlignmentReport(Contract):
    version: Literal["alignment/1"] = "alignment/1"
    status: Literal["pass", "quarantined"]
    issues: tuple[str, ...]
    mode: Literal["exact_grid", "nearest_neighbor"]
    source_shape: tuple[int, int, int]
    target_shape: tuple[int, int, int]
    source_to_target_world: Matrix
    transform_direction: Literal["source_RAS_mm_to_target_RAS_mm"] = (
        "source_RAS_mm_to_target_RAS_mm"
    )
    pull_target_index_to_source_index: Matrix
    interpolation: Literal["none", "nearest_neighbor_order_0"]
    boundary_policy: Literal["grid_constant_background_0_no_clipping_allowed"] = (
        "grid_constant_background_0_no_clipping_allowed"
    )
    source_labels: tuple[int, ...]
    output_labels: tuple[int, ...]
    per_label: tuple[LabelAlignmentStats, ...]
    source_foreground_inside_target_fraction: DecimalString
    coverage_meaning: Literal["fraction_source_foreground_voxel_cells_fully_contained_not_Dice"] = (
        "fraction_source_foreground_voxel_cells_fully_contained_not_Dice"
    )
    source_array_sha256: Hash
    output_array_sha256: Hash | None
    hash_encoding: Literal["C_order_little_endian_uint16_pixel_bytes"] = (
        "C_order_little_endian_uint16_pixel_bytes"
    )
    software: str
    reviewer_acceptance: Literal["pending"] = "pending"
    anatomical_alignment: Literal["not_established"] = "not_established"
    measurement_readiness: Literal["not_established"] = "not_established"


@dataclass(frozen=True, repr=False)
class MaskAlignmentResult:
    array: NDArray[np.uint16] | None = field(repr=False)
    report: AlignmentReport


def _quantity(number: Decimal | float) -> str:
    number = Decimal(str(number)).quantize(Decimal("0.000000001"), rounding=ROUND_HALF_EVEN)
    return "0" if not number else format(number, "f").rstrip("0").rstrip(".")


def _hash(array: NDArray[Any]) -> str:
    return hashlib.sha256(np.asarray(array, dtype="<u2", order="C").tobytes(order="C")).hexdigest()


def _matrix(value: NDArray[Any]) -> Matrix:
    return tuple(tuple(float(v) for v in row) for row in value)  # type: ignore[return-value]


def _coverage(source, forward, target_shape) -> tuple[int, int]:
    # An affine maps each voxel cell to a parallelepiped. Half the row-wise sum
    # of absolute linear coefficients gives its exact axis-aligned support radius
    # in target index space. Checking every cell's support catches partial clipping
    # even if its center survives nearest-neighbor interpolation.
    indices = np.argwhere(source != 0)
    radius = 0.5 * np.sum(np.abs(forward[:3, :3]), axis=1)
    lower = np.full(3, -0.5) - INDEX_BOUNDARY_TOLERANCE
    upper = np.asarray(target_shape) - 0.5 + INDEX_BOUNDARY_TOLERANCE
    inside = 0
    for start in range(0, len(indices), 32768):
        centers = indices[start : start + 32768] @ forward[:3, :3].T + forward[:3, 3]
        inside += int(
            np.count_nonzero(
                np.all((centers - radius >= lower) & (centers + radius <= upper), axis=1)
            )
        )
    return inside, len(indices)


def align_mask(
    array: NDArray[Any],
    source_geometry: CanonicalGeometry,
    target_geometry: CanonicalGeometry,
    config: AlignmentConfig,
) -> MaskAlignmentResult:
    """Return no output on failed numerical QC; originals are never modified."""
    if source_geometry.phase_count is not None or target_geometry.phase_count is not None:
        raise MaskAlignmentError(
            "Select one explicit three-dimensional acquisition before aligning labels"
        )
    source = np.asarray(array)
    if (
        source.shape != source_geometry.shape_xyz
        or source.dtype.kind not in "biuf"
        or not np.isfinite(source).all()
    ):
        raise MaskAlignmentError(
            "Mask must match validated source geometry and contain finite scalar labels"
        )
    if np.any(source < 0) or np.any(source > 65535) or not np.equal(source, np.floor(source)).all():
        raise MaskAlignmentError(
            "Mask labels must be nonnegative supported integers; intensity rounding is forbidden"
        )
    source = np.array(source, dtype="<u2", copy=True, order="C")
    source_affine = np.asarray(source_geometry.affine_ras_mm)
    target_affine = np.asarray(target_geometry.affine_ras_mm)
    transform = np.asarray(config.source_to_target_world)
    forward = np.linalg.inv(target_affine) @ transform @ source_affine
    pull = np.linalg.inv(source_affine) @ np.linalg.inv(transform) @ target_affine
    issues = []
    labels_before = tuple(int(n) for n in np.unique(source) if n != 0)
    if len(labels_before) > 32:
        raise MaskAlignmentError("Mask exceeds the supported distinct-label resource bound")
    if not labels_before:
        issues.append("EMPTY_MASK_NO_MEASUREMENT_READY_OUTPUT")
    if set(labels_before) != set(config.expected_labels):
        issues.append("SOURCE_LABELS_DISAGREE_WITH_DECLARED_LABELS")
    inside, total = _coverage(source, forward, target_geometry.shape_xyz)
    if inside != total:
        issues.append("SOURCE_FOREGROUND_PARTIALLY_OR_FULLY_OUTSIDE_TARGET")
    if config.mode == "exact_grid":
        if source_geometry.shape_xyz != target_geometry.shape_xyz or not np.allclose(
            pull, np.eye(4), atol=1e-9, rtol=0
        ):
            issues.append("EXACT_GRID_MISMATCH_EXPLICIT_RESAMPLING_REQUIRED")
        output = (
            np.zeros(target_geometry.shape_xyz, dtype=np.uint16)
            if "EXACT_GRID_MISMATCH_EXPLICIT_RESAMPLING_REQUIRED" in issues
            else source.copy()
        )
    else:
        output = ndimage.affine_transform(
            source,
            pull,
            output_shape=target_geometry.shape_xyz,
            output=np.uint16,
            order=0,
            prefilter=False,
            mode="grid-constant",
            cval=0,
        )
    labels_after = tuple(int(n) for n in np.unique(output) if n != 0)
    if set(labels_after) - set(labels_before):
        issues.append("RESAMPLING_CREATED_NEW_LABELS")
    if set(labels_before) - set(labels_after):
        issues.append("RESAMPLING_LOST_LABELS")
    structure = ndimage.generate_binary_structure(3, 1)
    stats = []
    for value in sorted(set(labels_before) | set(labels_after) | set(config.expected_labels)):
        source_label, output_label = source == value, output == value
        count_before, count_after = (
            int(np.count_nonzero(source_label)),
            int(np.count_nonzero(output_label)),
        )
        # Round physical totals only after multiplying the full affine determinant;
        # rounding each tiny voxel first can accumulate an avoidable volume error.
        source_voxel = Decimal(str(abs(float(np.linalg.det(source_affine[:3, :3])))))
        target_voxel = Decimal(str(abs(float(np.linalg.det(target_affine[:3, :3])))))
        volume_before = source_voxel * count_before
        volume_after = target_voxel * count_after
        difference = abs(volume_after - volume_before)
        tolerance = max(
            source_voxel,
            target_voxel,
            volume_before * Decimal(config.max_relative_volume_error),
        )
        components_before = int(ndimage.label(source_label, structure)[1])
        components_after = int(ndimage.label(output_label, structure)[1])
        if difference > tolerance:
            issues.append("LABEL_VOLUME_CHANGE_EXCEEDS_ENGINEERING_TOLERANCE")
        if components_before != components_after:
            issues.append("LABEL_COMPONENT_COUNT_CHANGED_REVIEW_REQUIRED")
        stats.append(
            LabelAlignmentStats(
                label=value,
                source_voxels=count_before,
                output_voxels=count_after,
                source_volume_mm3=_quantity(volume_before),
                output_volume_mm3=_quantity(volume_after),
                absolute_volume_change_mm3=_quantity(difference),
                allowed_volume_change_mm3=_quantity(tolerance),
                source_components_6=components_before,
                output_components_6=components_after,
            )
        )
    issues = sorted(set(issues))
    report = AlignmentReport(
        status="quarantined" if issues else "pass",
        issues=tuple(issues),
        mode=config.mode,
        source_shape=source_geometry.shape_xyz,
        target_shape=target_geometry.shape_xyz,
        source_to_target_world=config.source_to_target_world,
        pull_target_index_to_source_index=_matrix(pull),
        interpolation="none" if config.mode == "exact_grid" else "nearest_neighbor_order_0",
        source_labels=labels_before,
        output_labels=labels_after,
        per_label=tuple(stats),
        source_foreground_inside_target_fraction=_quantity(
            Decimal(inside) / total if total else Decimal(0)
        ),
        source_array_sha256=_hash(source),
        output_array_sha256=None if issues else _hash(output),
        software=f"scipy/{scipy.__version__};numpy/{np.__version__}",
    )
    if issues:
        return MaskAlignmentResult(None, report)
    output.setflags(write=False)
    return MaskAlignmentResult(output, report)
