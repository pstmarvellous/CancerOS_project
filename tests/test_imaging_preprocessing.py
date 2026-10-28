"""Artificial arrays verify numerical preprocessing, not MRI suitability."""

import hashlib

import numpy as np
import pytest
from pydantic import ValidationError

from canceros.imaging_geometry import canonical_geometry
from canceros.imaging_preprocessing import (
    PhaseSelection,
    PreprocessingConfig,
    PreprocessingError,
    preprocess,
)


def config(method="identity", **kwargs):
    return PreprocessingConfig(method=method, expected_sequence="t1", **kwargs)


def test_identity_preserves_source_geometry_flags_and_deterministic_pixel_bytes():
    source = np.arange(24, dtype=np.int16).reshape(2, 3, 4)
    original = source.copy()
    geometry = canonical_geometry(
        source.shape, [[-2, 0.5, 0, 10], [0, 3, 0, 20], [0, 0, 4, 30], [0, 0, 0, 1]]
    )
    first = preprocess(source, geometry, config(), "t1")
    second = preprocess(source, geometry, config(), "t1")
    np.testing.assert_array_equal(first.array, original)
    np.testing.assert_array_equal(source, original)
    assert source.flags.writeable and not first.array.flags.writeable
    assert not np.shares_memory(first.array, source)
    assert first.geometry == geometry
    assert first.report == second.report
    expected_hash = hashlib.sha256(original.astype("<f8").tobytes(order="C")).hexdigest()
    assert first.report.source_array_sha256 == expected_hash
    assert first.report.output_array_sha256 == expected_hash
    assert (
        first.report.interpretation
        == "numerical_only_not_calibrated_perfusion_or_biological_response"
    )
    assert first.report.statistics_fit_scope == "selected_volume_only_no_cohort_fit"


def test_population_zscore_matches_independent_small_volume_calculation():
    # Mean=2.5; squared deviations sum=5; population variance=5/4.
    source = np.array([1.0, 2.0, 3.0, 4.0]).reshape(1, 2, 2)
    geometry = canonical_geometry(source.shape, np.diag([2, 3, 4, 1]))
    result = preprocess(source, geometry, config("per_volume_zscore"), "t1")
    expected = np.array([-1.5, -0.5, 0.5, 1.5]).reshape(source.shape) / np.sqrt(1.25)
    np.testing.assert_allclose(result.array, expected, atol=1e-14, rtol=0)
    assert result.report.numerical_mean == 2.5
    assert result.report.numerical_standard_deviation == np.sqrt(1.25)
    assert result.geometry == geometry
    np.testing.assert_array_equal(source.ravel(), [1, 2, 3, 4])
    assert abs(float(result.array.mean())) < 1e-14
    assert abs(float(result.array.std()) - 1) < 1e-14


@pytest.mark.parametrize("value", [0.0, 7.0, -3.0])
def test_constant_images_preserved_by_identity_and_normalization_blocked(value):
    source = np.full((2, 3, 4), value)
    geometry = canonical_geometry(source.shape, np.eye(4))
    result = preprocess(source, geometry, config(), "t1")
    np.testing.assert_array_equal(result.array, source)
    assert result.report.numerical_standard_deviation == 0
    assert "constant_volume_preserved_without_invented_contrast" in result.report.warnings
    with pytest.raises(PreprocessingError, match="cannot be z-score"):
        preprocess(source, geometry, config("per_volume_zscore"), "t1")


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf, 1e13])
def test_invalid_intensities_reject_instead_of_impute(value):
    source = np.arange(24, dtype=float).reshape(2, 3, 4)
    source[0, 0, 0] = value
    geometry = canonical_geometry(source.shape, np.eye(4))
    with pytest.raises(PreprocessingError, match="intensity range"):
        preprocess(source, geometry, config(), "t1")


def phase_selection(index=1, role="postcontrast", offsets=("0", "30", "60")):
    return PhaseSelection(
        index=index, role=role, acquisition_offsets_seconds=offsets, evidence_sha256="f" * 64
    )


def test_phase_selection_uses_exact_index_without_fusion_or_new_visits():
    source = np.zeros((2, 3, 4, 3))
    source[..., 0] = np.arange(24).reshape(2, 3, 4)
    source[..., 1] = np.arange(24).reshape(2, 3, 4) + 100
    source[..., 2] = np.arange(24).reshape(2, 3, 4) + 1000
    geometry = canonical_geometry(source.shape, np.diag([-2, -3, 4, 1]), fourth_axis="dce_phase")
    settings = PreprocessingConfig(expected_sequence="dce", selected_phase=phase_selection())
    result = preprocess(source, geometry, settings, "dce")
    np.testing.assert_array_equal(result.array, source[..., 1])
    assert result.geometry.shape_xyz == (2, 3, 4)
    assert result.geometry.phase_count is None and result.geometry.fourth_axis is None
    assert result.report.selected_phase.index == 1
    assert result.report.numerical_mean == 111.5
    assert result.report.phase_correspondence == "not_established_no_voxelwise_combination"
    np.testing.assert_array_equal(result.geometry.affine_ras_mm, geometry.affine_ras_mm)
    np.testing.assert_array_equal(
        result.geometry.source_transform.original_affine, geometry.source_transform.original_affine
    )


def test_unknown_phase_role_stays_unknown_for_independent_selection():
    source = np.arange(24.0).reshape(2, 2, 2, 3)
    geometry = canonical_geometry(source.shape, np.eye(4), fourth_axis="dce_phase")
    settings = PreprocessingConfig(
        expected_sequence="dce", selected_phase=phase_selection(role="unknown")
    )
    result = preprocess(source, geometry, settings, "dce")
    assert result.report.selected_phase.role == "unknown"
    assert "selected_phase_role_unknown_not_inferred" in result.report.warnings


@pytest.mark.parametrize("offsets", [("0", "60", "30"), ("0", "0", "30")])
def test_misordered_or_ambiguous_phase_evidence_cannot_be_configured(offsets):
    with pytest.raises(ValidationError, match="ambiguous or misordered"):
        phase_selection(offsets=offsets)


def test_missing_phase_missing_sequence_and_wrong_phase_counts_block():
    source = np.arange(24.0).reshape(2, 2, 2, 3)
    geometry = canonical_geometry(source.shape, np.eye(4), fourth_axis="dce_phase")
    with pytest.raises(PreprocessingError, match="explicitly selected"):
        preprocess(source, geometry, PreprocessingConfig(expected_sequence="dce"), "dce")
    for phase in (phase_selection(index=3), phase_selection(offsets=("0", "30"))):
        with pytest.raises(PreprocessingError, match="phase count"):
            preprocess(
                source,
                geometry,
                PreprocessingConfig(expected_sequence="dce", selected_phase=phase),
                "dce",
            )
    source = np.arange(24.0).reshape(2, 3, 4)
    geometry = canonical_geometry(source.shape, np.eye(4))
    for sequence in ("unknown", "", "t2"):
        with pytest.raises(PreprocessingError, match="sequence is missing"):
            preprocess(source, geometry, config(), sequence)
    with pytest.raises(PreprocessingError, match="three-dimensional"):
        preprocess(
            source,
            geometry,
            PreprocessingConfig(expected_sequence="dce", selected_phase=phase_selection()),
            "dce",
        )


def test_source_lps_conversion_is_not_applied_twice_after_phase_selection():
    source = np.arange(16.0).reshape(2, 2, 2, 2)
    geometry = canonical_geometry(
        source.shape,
        [[2, 0, 0, 10], [0, 3, 0, 20], [0, 0, 4, 30], [0, 0, 0, 1]],
        source_frame="LPS",
        fourth_axis="dce_phase",
    )
    settings = PreprocessingConfig(
        expected_sequence="dce", selected_phase=phase_selection(offsets=("0", "30"))
    )
    result = preprocess(source, geometry, settings, "dce")
    assert result.geometry.source_transform.source_frame == "LPS"
    np.testing.assert_array_equal(
        result.geometry.affine_ras_mm,
        [[-2, 0, 0, -10], [0, -3, 0, -20], [0, 0, 4, 30], [0, 0, 0, 1]],
    )


def test_unsupported_cohort_fit_resampling_and_fabricated_channels_reject():
    for extra in (
        {"cohort_fit": True},
        {"resample_spacing": [1, 1, 1]},
        {"fill_missing_channel": True},
    ):
        with pytest.raises(ValidationError):
            PreprocessingConfig(expected_sequence="t1", **extra)
    with pytest.raises(ValidationError):
        PreprocessingConfig(expected_sequence="t1", method="bias_correction")
    geometry = canonical_geometry((2, 3, 4), np.eye(4))
    with pytest.raises(PreprocessingError, match="shape or scalar channel"):
        preprocess(np.zeros((2, 3, 4, 2)), geometry, config(), "t1")
