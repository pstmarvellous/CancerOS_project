"""Deterministic region arithmetic; anatomical meaning belongs to separate evidence gates."""

from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Annotated, Literal, TypedDict

import numpy as np
from pydantic import Field

from canceros.contracts import Contract, DecimalString
from canceros.imaging_geometry import CanonicalGeometry, index_to_world

CalculationDecimal = Annotated[str, Field(max_length=180, pattern=r"^-?(0|[1-9]\d*)(\.\d+)?$")]


class SelectionArguments(TypedDict):
    selected_labels: tuple[int, ...]


def decimal_text(value):
    value = Decimal(value)
    if not value.is_finite() or abs(value) >= Decimal("1e15"):
        raise ValueError("Unrepresentable physical quantity")
    return (
        "0"
        if not value
        else format(value, "f").rstrip("0").rstrip(".")
        if value.as_tuple().exponent < 0
        else str(value)
    )


def quantity(value):
    return decimal_text(Decimal(value).quantize(Decimal("0.000000001"), rounding=ROUND_HALF_EVEN))


def exact_voxel_volume(geometry):
    """Determinant of the stored affine decimal coefficients; no rounded spacing product."""
    with localcontext() as context:
        context.prec = 80
        a = [[Decimal(str(v)) for v in row[:3]] for row in geometry.affine_ras_mm[:3]]
        return abs(
            a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
            - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
            + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0])
        )


class RegionMeasurement(Contract):
    version: Literal["physical-measurements/1"] = "physical-measurements/1"
    availability: Literal[
        "available", "unavailable", "invalid", "confirmed_absent", "configured_simulated_absent"
    ]
    reason: str
    selected_labels: tuple[int, ...]
    voxel_count: int | None = None
    voxel_volume_mm3: DecimalString | None = None
    volume_mm3: DecimalString | None = None
    volume_cm3: DecimalString | None = None
    exact_voxel_volume_mm3: CalculationDecimal | None = None
    exact_volume_mm3: CalculationDecimal | None = None
    exact_volume_cm3: CalculationDecimal | None = None
    centroid_ras_mm: tuple[DecimalString, DecimalString, DecimalString] | None = None
    world_axis_aligned_bounds_mm: (
        tuple[
            tuple[DecimalString, DecimalString, DecimalString],
            tuple[DecimalString, DecimalString, DecimalString],
        ]
        | None
    ) = None
    world_axis_aligned_box_extent_mm: tuple[DecimalString, DecimalString, DecimalString] | None = (
        None
    )
    extent_definition: Literal["world_axis_aligned_voxel_cell_support_box_not_RECIST_diameter"] = (
        "world_axis_aligned_voxel_cell_support_box_not_RECIST_diameter"
    )
    calculation_precision: Literal[
        "Decimal80_from_stored_affine_coefficients; coordinate_bounds_float64; standard_quantities_half_even_9dp"
    ] = "Decimal80_from_stored_affine_coefficients; coordinate_bounds_float64; standard_quantities_half_even_9dp"
    uncertainty: Literal["not_established"] = "not_established"


def measure_region(
    mask, geometry: CanonicalGeometry, selected_labels=(1,), *, verified_absence=False
):
    labels = tuple(selected_labels)
    if (
        not labels
        or len(labels) > 32
        or len(set(labels)) != len(labels)
        or any(type(v) is not int or not 1 <= v <= 65535 for v in labels)
    ):
        raise ValueError("Explicit distinct positive label selection required")
    empty: SelectionArguments = {"selected_labels": labels}
    if mask is None:
        return RegionMeasurement(availability="unavailable", reason="mask_missing", **empty)
    geometry = CanonicalGeometry.model_validate(geometry.model_dump())
    array = np.asarray(mask)
    if (
        array.shape != geometry.shape_xyz
        or geometry.phase_count is not None
        or array.dtype.kind not in "biuf"
        or not np.isfinite(array).all()
        or np.any(array < 0)
        or np.any(array > 65535)
        or np.any(array != np.floor(array))
    ):
        return RegionMeasurement(
            availability="invalid", reason="invalid_label_mask_or_grid", **empty
        )
    selected = np.isin(array, labels)
    count = int(selected.sum())
    if not count:
        if type(verified_absence) is not bool or not verified_absence:
            return RegionMeasurement(
                availability="invalid", reason="empty_selection_absence_not_verified", **empty
            )
        return RegionMeasurement(
            availability="confirmed_absent",
            reason="explicit_verified_absence_evidence_required_by_caller",
            voxel_count=0,
            volume_mm3="0",
            volume_cm3="0",
            exact_volume_mm3="0",
            exact_volume_cm3="0",
            **empty,
        )
    if any(not np.any(array == label) for label in labels):
        return RegionMeasurement(availability="invalid", reason="selected_label_missing", **empty)
    indices = np.argwhere(selected)
    with localcontext() as context:
        context.prec = 80
        voxel = exact_voxel_volume(geometry)
        volume = voxel * count
        means = [Decimal(int(v)) / count for v in indices.sum(axis=0, dtype=np.int64)]
        centroid = [
            sum(Decimal(str(geometry.affine_ras_mm[i][j])) * means[j] for j in range(3))
            + Decimal(str(geometry.affine_ras_mm[i][3]))
            for i in range(3)
        ]
        low, high = np.full(3, np.inf), np.full(3, -np.inf)
        for start in range(0, len(indices), 50000):
            world = index_to_world(geometry, indices[start : start + 50000])
            low, high = np.minimum(low, world.min(axis=0)), np.maximum(high, world.max(axis=0))
        half_cell = np.abs(np.asarray(geometry.affine_ras_mm)[:3, :3]).sum(axis=1) / 2
        low, high = low - half_cell, high + half_cell
        try:
            return RegionMeasurement(
                availability="available",
                reason="explicit_label_union_voxel_accounting",
                voxel_count=count,
                voxel_volume_mm3=quantity(voxel),
                volume_mm3=quantity(volume),
                volume_cm3=quantity(volume / 1000),
                exact_voxel_volume_mm3=decimal_text(voxel),
                exact_volume_mm3=decimal_text(volume),
                exact_volume_cm3=decimal_text(volume / 1000),
                centroid_ras_mm=tuple(quantity(v) for v in centroid),
                world_axis_aligned_bounds_mm=(
                    tuple(quantity(str(v)) for v in low),
                    tuple(quantity(str(v)) for v in high),
                ),
                world_axis_aligned_box_extent_mm=tuple(quantity(str(v)) for v in high - low),
                **empty,
            )
        except ValueError:
            return RegionMeasurement(
                availability="invalid", reason="quantity_outside_supported_numeric_range", **empty
            )


def relative_volume_change(current, baseline):
    if current is None or baseline is None:
        return None
    with localcontext() as context:
        context.prec = 80
        current, baseline = Decimal(current), Decimal(baseline)
        if not current.is_finite() or not baseline.is_finite() or current < 0 or baseline <= 0:
            return None
        return quantity(100 * (current - baseline) / baseline)
