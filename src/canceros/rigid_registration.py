"""Engineering-only physical landmark fitting; no examination or anatomical acceptance.

SciPy Kabsch maps centered moving vectors (b) to fixed vectors (a). Its rssd
is not RMS: residual RMS is calculated independently on physical points below.
The review_* arguments are held-out numerical points, not qualified review.
Frozen limits are fixture engineering bounds, never clinical thresholds.
"""

from typing import Literal

import numpy as np
from numpy.typing import ArrayLike
from scipy.spatial.transform import Rotation

from canceros.contracts import Contract
from canceros.imaging_geometry import Matrix

POLICY = "rigid-landmarks/1"
MAX_RMS_MM = 1.0
MAX_RESIDUAL_MM = 2.0
MAX_ROTATION_DEGREES = 60.0
MAX_TRANSLATION_MM = 150.0
ROUNDTRIP_TOLERANCE_MM = 1e-5
RIGID_TOLERANCE = 1e-9
MAX_ABS_COORDINATE_MM = 1e7


class RegistrationError(ValueError):
    """Static safe reason; no supplied points are included in errors or logs."""


class RigidRegistrationReport(Contract):
    policy: Literal["rigid-landmarks/1"] = "rigid-landmarks/1"
    algorithm: Literal["scipy-1.17.1-centered-kabsch/1", "provided-proper-rigid/1"]
    status: Literal["pass", "fail"]
    reasons: tuple[str, ...]
    moving_to_fixed_world: Matrix
    fixed_to_moving_world: Matrix
    direction: Literal["moving_RAS_mm_to_fixed_RAS_mm"] = "moving_RAS_mm_to_fixed_RAS_mm"
    fit_point_count: int
    review_point_count: int
    fit_rms_mm: float
    fit_max_mm: float
    review_rms_mm: float | None
    review_max_mm: float | None
    roundtrip_max_mm: float
    determinant: float
    rotation_degrees: float
    translation_norm_mm: float
    review_meaning: Literal["held_out_numerical_points_not_qualified_anatomical_review"] = (
        "held_out_numerical_points_not_qualified_anatomical_review"
    )
    acceptance_scope: Literal["engineering_numerical_only"] = "engineering_numerical_only"


def _points(value: ArrayLike, minimum: int) -> np.ndarray:
    try:
        supplied = np.asarray(value)
        if supplied.dtype.kind not in "iuf":
            raise RegistrationError("finite_numeric_RAS_mm_points_required")
        points = supplied.astype(np.float64, copy=True)
        if (
            points.ndim != 2
            or points.shape[1:] != (3,)
            or not minimum <= len(points) <= 32
            or not np.isfinite(points).all()
            or np.max(np.abs(points)) > MAX_ABS_COORDINATE_MM
        ):
            raise RegistrationError("bounded_three_dimensional_landmark_set_required")
        if len(np.unique(points, axis=0)) != len(points):
            raise RegistrationError("duplicate_landmark_coordinates")
        return points
    except RegistrationError:
        raise
    except (TypeError, ValueError, OverflowError):
        raise RegistrationError("unreadable_landmark_set") from None


def _fit_points(moving, fixed):
    moving, fixed = _points(moving, 4), _points(fixed, 4)
    if moving.shape != fixed.shape:
        raise RegistrationError("paired_landmark_counts_must_match")
    for points in (moving, fixed):
        singular = np.linalg.svd(points - points.mean(axis=0), compute_uv=False)
        if singular[-1] < max(1e-4, singular[0] * 1e-6):
            raise RegistrationError("full_rank_well_conditioned_3D_fit_landmarks_required")
    return moving, fixed


def _review_points(moving, fixed, review_moving, review_fixed):
    if review_moving is None and review_fixed is None:
        return None, None
    if review_moving is None or review_fixed is None:
        raise RegistrationError("both_held_out_landmark_sets_required")
    review_moving, review_fixed = _points(review_moving, 1), _points(review_fixed, 1)
    if review_moving.shape != review_fixed.shape:
        raise RegistrationError("paired_held_out_landmark_counts_must_match")
    for fit, review in ((moving, review_moving), (fixed, review_fixed)):
        if any(np.any(np.linalg.norm(fit - point, axis=1) <= 1e-6) for point in review):
            raise RegistrationError("held_out_landmarks_must_not_reuse_fit_coordinates")
    return review_moving, review_fixed


def _matrix(value) -> Matrix:
    return tuple(tuple(float(x) for x in row) for row in value)  # type: ignore[return-value]


def _transform(value):
    try:
        supplied = np.asarray(value)
        if supplied.dtype.kind not in "iuf":
            raise RegistrationError("finite_proper_rigid_transform_required")
        transform = supplied.astype(np.float64, copy=True)
    except (TypeError, ValueError, OverflowError):
        raise RegistrationError("finite_proper_rigid_transform_required") from None
    if (
        transform.shape != (4, 4)
        or not np.isfinite(transform).all()
        or not np.array_equal(transform[3], [0, 0, 0, 1])
    ):
        raise RegistrationError("finite_spatial_four_by_four_transform_required")
    rotation = transform[:3, :3]
    if not np.allclose(
        rotation.T @ rotation, np.eye(3), atol=RIGID_TOLERANCE, rtol=0
    ) or not np.isclose(np.linalg.det(rotation), 1, atol=RIGID_TOLERANCE, rtol=0):
        raise RegistrationError("proper_rigid_transform_without_scale_or_reflection_required")
    if np.max(np.abs(transform[:3, 3])) > MAX_ABS_COORDINATE_MM:
        raise RegistrationError("transform_translation_outside_numeric_bounds")
    return transform.copy()


def _apply(transform, points):
    return points @ transform[:3, :3].T + transform[:3, 3]


def evaluate_rigid(
    transform,
    moving,
    fixed,
    *,
    review_moving=None,
    review_fixed=None,
) -> RigidRegistrationReport:
    """Check a declared moving→fixed transform; an inverted direction fails residual QC."""
    moving, fixed = _fit_points(moving, fixed)
    review_moving, review_fixed = _review_points(moving, fixed, review_moving, review_fixed)
    transform = _transform(transform)
    inverse = np.linalg.inv(transform)
    fit_errors = np.linalg.norm(_apply(transform, moving) - fixed, axis=1)
    fit_rms, fit_max = float(np.sqrt(np.mean(fit_errors**2))), float(fit_errors.max())
    review_rms = review_max = None
    roundtrip_points = moving
    reasons = []
    if fit_rms > MAX_RMS_MM or fit_max > MAX_RESIDUAL_MM:
        reasons.append("fit_landmark_residual_exceeds_engineering_limit")
    if review_moving is None:
        reasons.append("held_out_landmarks_required")
    else:
        errors = np.linalg.norm(_apply(transform, review_moving) - review_fixed, axis=1)
        review_rms, review_max = float(np.sqrt(np.mean(errors**2))), float(errors.max())
        roundtrip_points = np.vstack([moving, review_moving])
        if review_rms > MAX_RMS_MM or review_max > MAX_RESIDUAL_MM:
            reasons.append("held_out_landmark_residual_exceeds_engineering_limit")
    angle = float(np.degrees(Rotation.from_matrix(transform[:3, :3]).magnitude()))
    translation = float(np.linalg.norm(transform[:3, 3]))
    # This is the norm of the matrix translation at the declared RAS origin,
    # not a clinical limit on displacement at an anatomical center of rotation.
    if angle > MAX_ROTATION_DEGREES + 1e-9:
        reasons.append("rotation_exceeds_engineering_limit")
    if translation > MAX_TRANSLATION_MM:
        reasons.append("matrix_translation_exceeds_engineering_limit")
    roundtrip = float(
        np.linalg.norm(
            _apply(inverse, _apply(transform, roundtrip_points)) - roundtrip_points, axis=1
        ).max()
    )
    if roundtrip > ROUNDTRIP_TOLERANCE_MM:
        reasons.append("roundtrip_exceeds_engineering_limit")
    return RigidRegistrationReport(
        algorithm="provided-proper-rigid/1",
        status="fail" if reasons else "pass",
        reasons=tuple(reasons),
        moving_to_fixed_world=_matrix(transform),
        fixed_to_moving_world=_matrix(inverse),
        fit_point_count=len(moving),
        review_point_count=0 if review_moving is None else len(review_moving),
        fit_rms_mm=fit_rms,
        fit_max_mm=fit_max,
        review_rms_mm=review_rms,
        review_max_mm=review_max,
        roundtrip_max_mm=roundtrip,
        determinant=float(np.linalg.det(transform[:3, :3])),
        rotation_degrees=angle,
        translation_norm_mm=translation,
    )


def fit_rigid(
    moving,
    fixed,
    *,
    review_moving=None,
    review_fixed=None,
) -> RigidRegistrationReport:
    """Equal-weight paired-point least squares, centered first, with no scaling."""
    moving, fixed = _fit_points(moving, fixed)
    try:
        rotation, _ = Rotation.align_vectors(
            fixed - fixed.mean(axis=0), moving - moving.mean(axis=0)
        )
    except (ValueError, np.linalg.LinAlgError):
        raise RegistrationError("rigid_landmark_fit_failed") from None
    transform = np.eye(4)
    transform[:3, :3] = rotation.as_matrix()
    transform[:3, 3] = fixed.mean(axis=0) - rotation.apply(moving.mean(axis=0))
    report = evaluate_rigid(
        transform, moving, fixed, review_moving=review_moving, review_fixed=review_fixed
    )
    return report.model_copy(update={"algorithm": "scipy-1.17.1-centered-kabsch/1"})
