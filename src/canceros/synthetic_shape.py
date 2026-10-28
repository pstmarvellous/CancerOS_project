"""Deterministic hypothetical volume realization on the unchanged baseline grid."""

from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Annotated, Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import Field, TypeAdapter
from scipy import ndimage

from canceros.contracts import Contract, DecimalString
from canceros.imaging_geometry import CanonicalGeometry, Matrix, Point
from canceros.physical_measurements import (
    RegionMeasurement,
    decimal_text,
    exact_voxel_volume,
    measure_region,
    quantity,
)


class ShapeError(ValueError):
    """Static input error without source identifiers or patient content."""


class ShapeConfig(Contract):
    version: Literal["isotropic-fixed-grid/1"] = "isotropic-fixed-grid/1"
    seed: Annotated[int, Field(strict=True, ge=0, le=4294967295)]


class ShapeReport(Contract):
    version: Literal["isotropic-fixed-grid/1"] = "isotropic-fixed-grid/1"
    seed: Annotated[int, Field(strict=True, ge=0, le=4294967295)]
    shape_class: Literal["hypothetical"] = "hypothetical"
    status: Literal["ready", "zero", "blocked"]
    baseline_values: RegionMeasurement
    realized_values: RegionMeasurement | None
    target_mm3: DecimalString
    tolerance_mm3: DecimalString
    scale_factor: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    center_ras_mm: Point
    baseline_to_synthetic_world: Matrix | None
    reasons: list[str]


@dataclass(frozen=True)
class SyntheticShapeResult:
    array: NDArray[np.uint8] | None
    report: ShapeReport


def generate_shape(
    mask, geometry: CanonicalGeometry, target_mm3: str, config: ShapeConfig
) -> SyntheticShapeResult:
    """Scale voxel-cell support around the physical centroid, without biological inference.

    Seed is recorded for reproducibility; version 1 uses no random perturbations.
    Tolerance is frozen at max(one determinant voxel, 1% target), in mm³.
    """
    try:
        config = ShapeConfig.model_validate(config.model_dump())
        geometry = CanonicalGeometry.model_validate(geometry.model_dump())
        target_mm3 = TypeAdapter(DecimalString).validate_python(target_mm3)
        target = Decimal(target_mm3)
        if target < 0:
            raise ValueError
        source = np.asarray(mask)
        if (
            source.shape != geometry.shape_xyz
            or geometry.phase_count is not None
            or source.dtype.kind not in "biuf"
            or not np.isfinite(source).all()
            or not np.isin(source, (0, 1)).all()
            or not np.any(source)
        ):
            raise ValueError
        baseline = measure_region(source, geometry)
        if baseline.availability != "available":
            raise ValueError
    except (ValueError, TypeError, AttributeError, OverflowError):
        raise ShapeError(
            "Provide valid nonempty binary baseline, geometry, target and config"
        ) from None

    indices = np.argwhere(source == 1)
    center_index = indices.mean(axis=0)
    affine = np.asarray(geometry.affine_ras_mm, dtype=np.float64)
    center = affine[:3, :3] @ center_index + affine[:3, 3]
    with localcontext() as context:
        context.prec = 80
        voxel_volume = exact_voxel_volume(geometry)
        base_volume = voxel_volume * len(indices)
        tolerance = max(voxel_volume, target * Decimal("0.01"))
        scale = float(np.cbrt(float(target / base_volume))) if target else 0.0

    def result(status, output, measured, reasons, transform):
        if output is not None:
            output.setflags(write=False)
        return SyntheticShapeResult(
            array=output,
            report=ShapeReport(
                seed=config.seed,
                status=status,
                baseline_values=baseline,
                realized_values=measured,
                target_mm3=target_mm3,
                tolerance_mm3=quantity(tolerance),
                scale_factor=scale,
                center_ras_mm=(float(center[0]), float(center[1]), float(center[2])),
                baseline_to_synthetic_world=transform,
                reasons=reasons,
            ),
        )

    if not target:
        output = np.zeros(geometry.shape_xyz, dtype=np.uint8)
        measured = measure_region(output, geometry, verified_absence=True)
        measured = RegionMeasurement.model_validate(
            measured.model_dump()
            | {
                "availability": "configured_simulated_absent",
                "reason": "hypothetical_zero_not_cure_or_surgery",
                "voxel_volume_mm3": quantity(voxel_volume),
                "exact_voxel_volume_mm3": decimal_text(voxel_volume),
            }
        )
        return result("zero", output, measured, ["configured_simulated_zero_endpoint"], None)

    world_scale = np.eye(4)
    world_scale[:3, :3] *= scale
    world_scale[:3, 3] = (1 - scale) * center
    transform = tuple(tuple(float(v) for v in row) for row in world_scale)
    # Scalar world scaling commutes with the complete affine. Check the selected
    # voxel CELLS, not centers, before nearest-neighbor sampling can hide clipping.
    low = center_index + scale * (indices.min(axis=0) - 0.5 - center_index)
    high = center_index + scale * (indices.max(axis=0) + 0.5 - center_index)
    if np.any(low < -0.5 - 1e-7) or np.any(high > np.array(source.shape) - 0.5 + 1e-7):
        return result(
            "blocked", None, None, ["scaled_voxel_cell_support_outside_fixed_grid"], transform
        )
    pull = np.linalg.inv(affine) @ np.linalg.inv(world_scale) @ affine
    output = ndimage.affine_transform(
        source.astype(np.uint8),
        pull[:3, :3],
        offset=pull[:3, 3],
        output_shape=geometry.shape_xyz,
        order=0,
        mode="grid-constant",
        cval=0,
        prefilter=False,
    )
    measured = measure_region(output, geometry)
    if not np.any(output):
        measured = measure_region(output, geometry, verified_absence=True)
        measured = RegionMeasurement.model_validate(
            measured.model_dump()
            | {"availability": "invalid", "reason": "nonzero_target_resampled_to_empty"}
        )
        return result("blocked", None, measured, ["nonzero_target_resampled_to_empty"], transform)
    if measured.availability != "available":
        return result("blocked", None, measured, ["realized_measurement_invalid"], transform)
    with localcontext() as context:
        context.prec = 80
        difference = abs(Decimal(measured.exact_volume_mm3) - target)
    if difference > tolerance:
        return result(
            "blocked", None, measured, ["realized_volume_outside_frozen_tolerance"], transform
        )
    return result("ready", output, measured, [], transform)
