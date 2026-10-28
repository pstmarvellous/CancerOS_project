"""Single-volume numerical preprocessing; no inference, cohort fit or phase fusion."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Annotated, Any, Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import Field, FiniteFloat, model_validator

from canceros.contracts import Contract, DecimalString, Hash
from canceros.imaging_geometry import CanonicalGeometry, canonical_geometry

Sequence = Literal["t1", "t2", "other_mr", "dce"]
MIN_NORMALIZATION_STD = 1e-12
MAX_ABS_INTENSITY = 1e12


class PreprocessingError(ValueError):
    """Static safe issue text; no source metadata is echoed."""


class PhaseSelection(Contract):
    index: Annotated[int, Field(strict=True, ge=0, le=15)]
    role: Literal["precontrast", "postcontrast", "unknown"]
    acquisition_offsets_seconds: Annotated[
        tuple[DecimalString, ...], Field(min_length=1, max_length=16)
    ]
    evidence_sha256: Hash

    @model_validator(mode="after")
    def ordered_acquisition_evidence(self):
        offsets = [Decimal(v) for v in self.acquisition_offsets_seconds]
        if any(right <= left for left, right in zip(offsets, offsets[1:])):
            raise PreprocessingError(
                "Phase acquisition order is ambiguous or misordered; review source evidence"
            )
        return self


class PreprocessingConfig(Contract):
    method: Literal["identity", "per_volume_zscore"] = "identity"
    expected_sequence: Sequence
    selected_phase: PhaseSelection | None = None
    version: Literal["preprocessing/1"] = "preprocessing/1"


class PreprocessingReport(Contract):
    version: Literal["preprocessing/1"] = "preprocessing/1"
    method: Literal["identity", "per_volume_zscore"]
    sequence: Sequence
    selected_phase: PhaseSelection | None
    source_shape: tuple[int, ...]
    output_shape: tuple[int, int, int]
    source_array_sha256: Hash
    output_array_sha256: Hash
    hash_encoding: Literal["C_order_little_endian_float64_pixel_bytes"] = (
        "C_order_little_endian_float64_pixel_bytes"
    )
    numerical_mean: FiniteFloat
    numerical_standard_deviation: FiniteFloat
    statistics_definition: Literal["all_selected_volume_voxels_population_ddof_0_float64"] = (
        "all_selected_volume_voxels_population_ddof_0_float64"
    )
    output_dtype: Literal["<f8"] = "<f8"
    parameters_precision: Literal["float64_numerical_metadata_not_clinical_quantities"] = (
        "float64_numerical_metadata_not_clinical_quantities"
    )
    statistics_fit_scope: Literal["selected_volume_only_no_cohort_fit"] = (
        "selected_volume_only_no_cohort_fit"
    )
    spatial_operation: Literal["none_original_voxel_centers_preserved"] = (
        "none_original_voxel_centers_preserved"
    )
    phase_correspondence: Literal["not_established_no_voxelwise_combination"] = (
        "not_established_no_voxelwise_combination"
    )
    interpretation: Literal["numerical_only_not_calibrated_perfusion_or_biological_response"] = (
        "numerical_only_not_calibrated_perfusion_or_biological_response"
    )
    software: str
    warnings: tuple[str, ...]


@dataclass(frozen=True, repr=False)
class PreprocessingResult:
    array: NDArray[np.float64] = field(repr=False)
    geometry: CanonicalGeometry
    report: PreprocessingReport


def _array_hash(array: NDArray[Any]) -> str:
    return hashlib.sha256(np.asarray(array, dtype="<f8", order="C").tobytes(order="C")).hexdigest()


def preprocess(
    array: NDArray[Any],
    geometry: CanonicalGeometry,
    config: PreprocessingConfig,
    source_sequence: str,
) -> PreprocessingResult:
    """Select at most one acquisition and optionally normalize that volume alone.

    Explicit phase evidence is an administrator-provided source claim, not proof
    of motion correction or specialist review. Unknown roles remain unknown.
    """
    if (
        source_sequence not in ("t1", "t2", "other_mr", "dce")
        or source_sequence != config.expected_sequence
    ):
        raise PreprocessingError(
            "Requested sequence is missing, unknown or inconsistent with the source"
        )
    try:
        source = np.asarray(array)
        expected_shape = geometry.shape_xyz + (
            (geometry.phase_count,) if geometry.phase_count else ()
        )
        if source.shape != expected_shape or source.dtype.kind not in "iuf":
            raise PreprocessingError(
                "Image shape or scalar channel type disagrees with validated geometry"
            )
        if (
            not np.isfinite(source).all()
            or np.max(np.abs(source.astype(np.float64))) > MAX_ABS_INTENSITY
        ):
            raise PreprocessingError(
                "Nonfinite or unsupported intensity range; review the preserved source"
            )
        source_hash = _array_hash(source)
        phase = config.selected_phase
        warnings = []
        if geometry.phase_count is not None:
            if source_sequence != "dce" or phase is None:
                raise PreprocessingError(
                    "A DCE phase must be explicitly selected with acquisition-order evidence"
                )
            if (
                len(phase.acquisition_offsets_seconds) != geometry.phase_count
                or phase.index >= geometry.phase_count
            ):
                raise PreprocessingError(
                    "Phase evidence or selected index disagrees with the source phase count"
                )
            selected = source[..., phase.index]
            if phase.role == "unknown":
                warnings.append("selected_phase_role_unknown_not_inferred")
        else:
            if phase is not None:
                raise PreprocessingError(
                    "Phase selection cannot be applied to a three-dimensional acquisition"
                )
            selected = source
            if source_sequence == "dce":
                warnings.append("single_dce_acquisition_phase_role_unknown")
        # Copy before any operation, even identity; source pixels and flags remain unchanged.
        output = np.array(selected, dtype="<f8", order="C", copy=True)
        mean = float(np.mean(output, dtype=np.float64))
        std = float(np.std(output, dtype=np.float64, ddof=0))
        if not np.isfinite([mean, std]).all():
            raise PreprocessingError("Normalization statistics are numerically unsupported")
        if std <= MIN_NORMALIZATION_STD:
            if config.method == "per_volume_zscore":
                raise PreprocessingError(
                    "Constant or numerically constant volume cannot be z-score normalized"
                )
            warnings.append("constant_volume_preserved_without_invented_contrast")
        if config.method == "per_volume_zscore":
            output = np.asarray((output - mean) / std, dtype="<f8", order="C")
        if not np.isfinite(output).all():
            raise PreprocessingError(
                "Processing produced invalid intensities; retain the source and review"
            )
        transform = geometry.source_transform
        output_geometry = canonical_geometry(
            geometry.shape_xyz,
            transform.original_affine,
            units=transform.source_unit,
            source_frame=transform.source_frame,
        )
        output.setflags(write=False)
        report = PreprocessingReport(
            method=config.method,
            sequence=source_sequence,
            selected_phase=phase,
            source_shape=tuple(source.shape),
            output_shape=geometry.shape_xyz,
            source_array_sha256=source_hash,
            output_array_sha256=_array_hash(output),
            numerical_mean=mean,
            numerical_standard_deviation=std,
            software=f"numpy/{np.__version__}",
            warnings=tuple(warnings),
        )
        return PreprocessingResult(output, output_geometry, report)
    except PreprocessingError:
        raise
    except Exception:
        raise PreprocessingError(
            "Unsupported preprocessing input; review the preserved acquisition"
        ) from None
