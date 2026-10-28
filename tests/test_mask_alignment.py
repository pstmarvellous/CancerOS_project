"""Artificial label geometry; numerical overlays are not anatomical review."""

import numpy as np
import pytest
from pydantic import ValidationError

from canceros.imaging_geometry import canonical_geometry
from canceros.mask_alignment import AlignmentConfig, MaskAlignmentError, align_mask


def test_exact_identity_preserves_labels_components_bytes_and_source():
    source = np.zeros((6, 7, 8), dtype=np.uint16)
    source[1:3, 2:4, 3:5] = 1
    source[4, 5, 6] = 7
    original = source.copy()
    geometry = canonical_geometry(source.shape, np.diag([2, 3, 4, 1]))
    result = align_mask(source, geometry, geometry, AlignmentConfig(expected_labels=(1, 7)))
    assert result.report.status == "pass"
    np.testing.assert_array_equal(result.array, source)
    np.testing.assert_array_equal(source, original)
    assert not np.shares_memory(result.array, source)
    assert not result.array.flags.writeable and source.flags.writeable
    assert result.report.source_array_sha256 == result.report.output_array_sha256
    assert result.report.source_foreground_inside_target_fraction == "1"
    assert result.report.per_label[0].source_voxels == 8
    assert result.report.per_label[0].source_volume_mm3 == "192"
    assert result.report.per_label[1].source_components_6 == 1
    assert result.report.measurement_readiness == "not_established"
    assert result.report.reviewer_acceptance == "pending"


def test_translated_source_affine_uses_pull_direction_and_correct_target_position():
    source = np.zeros((5, 5, 5), dtype=np.uint16)
    source[1, 2, 3] = 1
    source_geometry = canonical_geometry(
        source.shape, [[1, 0, 0, 1], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    )
    target_geometry = canonical_geometry(source.shape, np.eye(4))
    result = align_mask(
        source,
        source_geometry,
        target_geometry,
        AlignmentConfig(expected_labels=(1,), mode="nearest_neighbor"),
    )
    assert result.report.status == "pass"
    assert np.argwhere(result.array).tolist() == [[2, 2, 3]]
    assert result.report.pull_target_index_to_source_index[0][3] == -1
    assert result.report.per_label[0].absolute_volume_change_mm3 == "0"
    blocked = align_mask(
        source, source_geometry, target_geometry, AlignmentConfig(expected_labels=(1,))
    )
    assert blocked.array is None
    assert "EXACT_GRID_MISMATCH_EXPLICIT_RESAMPLING_REQUIRED" in blocked.report.issues


def test_explicit_world_translation_uses_inverse_not_forward_for_sampling():
    source = np.zeros((6, 6, 6), dtype=np.uint16)
    source[1:3, 1:3, 1:3] = 3
    geometry = canonical_geometry(source.shape, np.eye(4))
    transform = ((1, 0, 0, 2), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))
    result = align_mask(
        source,
        geometry,
        geometry,
        AlignmentConfig(
            expected_labels=(3,),
            mode="nearest_neighbor",
            transform_kind="rigid",
            source_to_target_world=transform,
        ),
    )
    expected = np.zeros_like(source)
    expected[3:5, 1:3, 1:3] = 3
    np.testing.assert_array_equal(result.array, expected)
    assert result.report.status == "pass"


def test_rotation_and_reflected_grids_keep_label_semantics():
    source = np.zeros((5, 5, 5), dtype=np.uint16)
    source[1, 2, 3] = 4
    target = canonical_geometry(source.shape, np.eye(4))
    rotation = canonical_geometry(
        source.shape, [[0, -1, 0, 4], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    )
    result = align_mask(
        source, rotation, target, AlignmentConfig(expected_labels=(4,), mode="nearest_neighbor")
    )
    assert result.report.status == "pass"
    assert np.argwhere(result.array).tolist() == [[2, 1, 3]]
    reflection = canonical_geometry(
        source.shape, [[-1, 0, 0, 4], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    )
    reflected = align_mask(
        source, reflection, target, AlignmentConfig(expected_labels=(4,), mode="nearest_neighbor")
    )
    assert reflected.report.status == "pass"
    assert np.argwhere(reflected.array).tolist() == [[3, 2, 3]]


def test_anisotropic_resampling_reports_exact_physical_volume_not_raw_count():
    source = np.zeros((4, 4, 4), dtype=np.uint16)
    source[1:3, 1:3, 1:3] = 1
    # Source X centers map to target X indices 1,3,5,7; target cells 0..7
    # exactly tile its source support, avoiding half-cell-boundary ambiguity.
    source_grid = canonical_geometry(
        source.shape, [[2, 0, 0, 0.5], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    )
    target_grid = canonical_geometry((8, 4, 4), np.eye(4))
    result = align_mask(
        source,
        source_grid,
        target_grid,
        AlignmentConfig(expected_labels=(1,), mode="nearest_neighbor"),
    )
    assert result.report.status == "pass"
    stats = result.report.per_label[0]
    assert stats.source_voxels == 8 and stats.output_voxels == 16
    assert stats.source_volume_mm3 == stats.output_volume_mm3 == "16"


def test_partial_voxel_clipping_blocks_even_when_label_count_unchanged():
    source = np.zeros((4, 4, 4), dtype=np.uint16)
    source[0, 1, 1] = 1
    shifted = canonical_geometry(
        source.shape, [[1, 0, 0, -0.1], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    )
    target = canonical_geometry(source.shape, np.eye(4))
    result = align_mask(
        source, shifted, target, AlignmentConfig(expected_labels=(1,), mode="nearest_neighbor")
    )
    assert result.array is None and result.report.status == "quarantined"
    assert result.report.per_label[0].source_voxels == result.report.per_label[0].output_voxels == 1
    assert "SOURCE_FOREGROUND_PARTIALLY_OR_FULLY_OUTSIDE_TARGET" in result.report.issues
    assert result.report.output_array_sha256 is None


def test_large_shift_empty_mask_unexpected_and_lost_labels_quarantine():
    source = np.zeros((4, 4, 4), dtype=np.uint16)
    source[1, 1, 1] = 1
    target = canonical_geometry(source.shape, np.eye(4))
    source_grid = canonical_geometry(
        source.shape, [[1, 0, 0, 100], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    )
    result = align_mask(
        source, source_grid, target, AlignmentConfig(expected_labels=(1,), mode="nearest_neighbor")
    )
    assert result.array is None
    assert "RESAMPLING_LOST_LABELS" in result.report.issues
    assert result.report.source_foreground_inside_target_fraction == "0"
    empty = align_mask(np.zeros_like(source), target, target, AlignmentConfig(expected_labels=(1,)))
    assert empty.array is None
    assert "EMPTY_MASK_NO_MEASUREMENT_READY_OUTPUT" in empty.report.issues
    wrong = align_mask(source, target, target, AlignmentConfig(expected_labels=(2,)))
    assert wrong.array is None
    assert "SOURCE_LABELS_DISAGREE_WITH_DECLARED_LABELS" in wrong.report.issues


@pytest.mark.parametrize("value", [-1, 0.5, np.nan, np.inf, 65536])
def test_invalid_labels_never_interpolate_and_round(value):
    source = np.zeros((2, 3, 4))
    source[0, 0, 0] = value
    geometry = canonical_geometry(source.shape, np.eye(4))
    with pytest.raises(MaskAlignmentError):
        align_mask(source, geometry, geometry, AlignmentConfig(expected_labels=(1,)))


def test_only_declared_proper_rigid_world_transforms_and_frozen_tolerance_allowed():
    for transform in (
        ((2, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)),
        ((-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)),
    ):
        with pytest.raises(ValidationError, match="proper rigid"):
            AlignmentConfig(
                expected_labels=(1,), source_to_target_world=transform, transform_kind="rigid"
            )
    with pytest.raises(ValidationError, match="Identity declaration"):
        AlignmentConfig(
            expected_labels=(1,),
            source_to_target_world=((1, 0, 0, 1), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)),
        )
    with pytest.raises(ValidationError):
        AlignmentConfig(expected_labels=(1,), max_relative_volume_error="0.1")


def test_fourth_axis_must_be_explicitly_selected_and_no_shape_resize():
    geometry = canonical_geometry((2, 3, 4, 2), np.eye(4), fourth_axis="dce_phase")
    with pytest.raises(MaskAlignmentError, match="three-dimensional"):
        align_mask(
            np.zeros((2, 3, 4, 2)), geometry, geometry, AlignmentConfig(expected_labels=(1,))
        )
    target = canonical_geometry((2, 3, 4), np.eye(4))
    with pytest.raises(MaskAlignmentError, match="match validated"):
        align_mask(np.zeros((2, 3, 5)), target, target, AlignmentConfig(expected_labels=(1,)))


def test_coarse_grid_volume_error_and_component_merging_quarantine():
    source = np.zeros((8, 8, 8), dtype=np.uint16)
    source[2:5, 2:5, 2:5] = 1
    source_grid = canonical_geometry(source.shape, np.eye(4))
    target_grid = canonical_geometry(
        (4, 4, 4), [[2, 0, 0, 0.5], [0, 2, 0, 0.5], [0, 0, 2, 0.5], [0, 0, 0, 1]]
    )
    result = align_mask(
        source,
        source_grid,
        target_grid,
        AlignmentConfig(expected_labels=(1,), mode="nearest_neighbor"),
    )
    assert result.array is None
    assert "LABEL_VOLUME_CHANGE_EXCEEDS_ENGINEERING_TOLERANCE" in result.report.issues
    source = np.zeros((7, 7, 7), dtype=np.uint16)
    source[2, 2, 2] = source[4, 2, 2] = 1
    result = align_mask(
        source,
        canonical_geometry(source.shape, np.eye(4)),
        canonical_geometry((4, 4, 4), np.diag([2, 2, 2, 1])),
        AlignmentConfig(expected_labels=(1,), mode="nearest_neighbor"),
    )
    assert result.array is None
    assert "LABEL_COMPONENT_COUNT_CHANGED_REVIEW_REQUIRED" in result.report.issues
    assert result.report.per_label[0].source_components_6 == 2
    assert result.report.per_label[0].output_components_6 == 1


def test_unexpected_label_cardinality_cannot_expand_component_work_unboundedly():
    source = np.arange(64, dtype=np.uint16).reshape(4, 4, 4)
    geometry = canonical_geometry(source.shape, np.eye(4))
    with pytest.raises(MaskAlignmentError, match="distinct-label resource"):
        align_mask(source, geometry, geometry, AlignmentConfig(expected_labels=(1,)))
