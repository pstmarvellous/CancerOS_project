"""Known physical transforms and failed QC; fixtures do not establish anatomical review."""

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from canceros.rigid_registration import RegistrationError, evaluate_rigid, fit_rigid


def points():
    return np.array([[0.0, 0, 0], [20, 0, 0], [0, 30, 0], [0, 0, 40], [15, 20, 25]])


def known(angle=25, translation=(12, -8, 5)):
    transform = np.eye(4)
    transform[:3, :3] = Rotation.from_euler("z", angle, degrees=True).as_matrix()
    transform[:3, 3] = translation
    moving = points()
    fixed = moving @ transform[:3, :3].T + transform[:3, 3]
    review = np.array([[5.0, 5, 5], [10, 15, 20]])
    return moving, fixed, transform, review, review @ transform[:3, :3].T + transform[:3, 3]


def test_known_moving_to_fixed_transform_holdout_inverse_and_no_mutation():
    moving, fixed, transform, review_moving, review_fixed = known()
    before = [value.copy() for value in (moving, fixed, review_moving, review_fixed)]
    result = fit_rigid(moving, fixed, review_moving=review_moving, review_fixed=review_fixed)
    assert result.status == "pass" and not result.reasons
    np.testing.assert_allclose(result.moving_to_fixed_world, transform, atol=1e-12)
    np.testing.assert_allclose(
        np.array(result.fixed_to_moving_world) @ transform, np.eye(4), atol=1e-12
    )
    assert result.fit_rms_mm < 1e-12 and result.review_max_mm < 1e-12
    assert result.roundtrip_max_mm < 1e-12 and result.determinant == pytest.approx(1)
    assert result.rotation_degrees == pytest.approx(25)
    for supplied, original in zip((moving, fixed, review_moving, review_fixed), before):
        np.testing.assert_array_equal(supplied, original)


def test_inverse_direction_and_low_quality_holdout_fail_closed():
    moving, fixed, transform, rm, rf = known()
    inverted = evaluate_rigid(
        np.linalg.inv(transform), moving, fixed, review_moving=rm, review_fixed=rf
    )
    assert inverted.status == "fail" and inverted.fit_max_mm > 2
    rf[0] += [0, 0, 10]
    failed = fit_rigid(moving, fixed, review_moving=rm, review_fixed=rf)
    assert failed.status == "fail" and failed.fit_rms_mm < 1e-12
    assert "held_out_landmark_residual_exceeds_engineering_limit" in failed.reasons
    assert "held_out_landmarks_required" in fit_rigid(moving, fixed).reasons


@pytest.mark.parametrize(
    "angle,translation,reason",
    [
        (70, (0, 0, 0), "rotation_exceeds_engineering_limit"),
        (0, (151, 0, 0), "matrix_translation_exceeds_engineering_limit"),
    ],
)
def test_implausible_but_numerically_exact_transform_retains_failure(angle, translation, reason):
    moving, fixed, _, rm, rf = known(angle, translation)
    result = fit_rigid(moving, fixed, review_moving=rm, review_fixed=rf)
    assert result.status == "fail" and reason in result.reasons and result.fit_max_mm < 1e-12


@pytest.mark.parametrize(
    "kind",
    [
        "nan",
        "infinite",
        "collinear",
        "planar",
        "too_few",
        "too_many",
        "duplicate",
        "count",
        "string",
    ],
)
def test_invalid_landmarks_do_not_return_identity_success(kind):
    moving, fixed = points(), points()
    if kind == "nan":
        moving[0, 0] = np.nan
    if kind == "infinite":
        fixed[0, 0] = np.inf
    if kind == "collinear":
        moving = np.array([[i, i, i] for i in range(5)])
    if kind == "planar":
        moving[:, 2] = 0
    if kind == "too_few":
        moving = moving[:3]
    if kind == "too_many":
        moving = np.arange(99).reshape(33, 3)
    if kind == "duplicate":
        moving[1] = moving[0]
    if kind == "count":
        fixed = fixed[:4]
    if kind == "string":
        moving = moving.astype(str)
    with pytest.raises(RegistrationError):
        fit_rigid(moving, fixed)


@pytest.mark.parametrize("kind", ["singular", "reflection", "scaled", "nonfinite", "projective"])
def test_bad_provided_transforms_rejected(kind):
    transform = np.eye(4)
    if kind == "singular":
        transform[0, 0] = 0
    if kind == "reflection":
        transform[0, 0] = -1
    if kind == "scaled":
        transform[:3, :3] *= 2
    if kind == "nonfinite":
        transform[0, 3] = np.nan
    if kind == "projective":
        transform[3, 0] = 1
    with pytest.raises(RegistrationError):
        evaluate_rigid(transform, points(), points())


def test_fit_noise_is_measured_and_heldout_reuse_rejected():
    moving, fixed, _, rm, rf = known()
    fixed[0] += [4, 0, 0]
    result = fit_rigid(moving, fixed, review_moving=rm, review_fixed=rf)
    assert result.fit_rms_mm > 1 and result.status == "fail"
    with pytest.raises(RegistrationError, match="reuse"):
        fit_rigid(points(), points(), review_moving=points()[:1], review_fixed=points()[:1])
