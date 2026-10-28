"""Technical label QC and explicitly eligible per-case metrics, never review signoff."""

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any, Literal

import numpy as np
import scipy
from numpy.typing import NDArray
from scipy import ndimage
from scipy.spatial import cKDTree

from canceros.contracts import Contract, DecimalString
from canceros.imaging_geometry import CanonicalGeometry

MAX_SURFACE_POINTS = 100_000
AbsenceSemantics = Literal[
    "not_recorded", "confirmed_absence", "missing_annotation", "processing_failure"
]
QCCase = Literal[
    "nonempty",
    "confirmed_absence",
    "missing_annotation",
    "processing_failure",
    "empty_unknown",
    "not_assessed",
]
MetricCase = Literal["nonempty", "both_empty", "candidate_empty", "reference_empty", "not_assessed"]


class LabelQC(Contract):
    label: int
    voxel_count: int
    components_6: int
    boundary_voxels: int


class TechnicalMaskQC(Contract):
    rule_version: Literal["segmentation-qc/1"] = "segmentation-qc/1"
    technical_status: Literal["pass", "fail"]
    geometry_valid: bool
    foreground_voxels: int | None
    labels: tuple[LabelQC, ...]
    empty_case: Literal[
        "nonempty",
        "confirmed_absence",
        "missing_annotation",
        "processing_failure",
        "empty_unknown",
        "not_assessed",
    ]
    issues: tuple[str, ...]
    warnings: tuple[str, ...]
    source_association: Literal["not_established_here"] = "not_established_here"
    scientific_review: Literal["pending"] = "pending"
    anatomical_validity: Literal["not_established"] = "not_established"


class SegmentationMetrics(Contract):
    metric_version: Literal["segmentation-metrics/1"] = "segmentation-metrics/1"
    status: Literal["eligible", "not_evaluated"]
    dice: DecimalString | None
    hd95_mm: DecimalString | None
    absolute_volume_error_mm3: DecimalString | None
    relative_volume_error: DecimalString | None
    empty_case: Literal[
        "nonempty", "both_empty", "candidate_empty", "reference_empty", "not_assessed"
    ]
    attempted_cases: Literal[1] = 1
    eligible_attempted_cases: int
    failed_cases: int
    scored_cases: int
    correct_absence_cases: int
    candidate_foreground_voxels: int | None = None
    reference_foreground_voxels: int | None = None
    intersection_voxels: int | None = None
    candidate_surface_points: int | None = None
    reference_surface_points: int | None = None
    exclusions: tuple[str, ...]
    distance_definition: Literal[
        "percentile95_linear_of_concatenated_bidirectional_nearest_six_connected_boundary_voxel_centers_RAS_mm"
    ] = "percentile95_linear_of_concatenated_bidirectional_nearest_six_connected_boundary_voxel_centers_RAS_mm"
    empty_policy: Literal[
        "both_empty_separate_correct_absence_Dice_null_one_empty_failure_Dice_zero_distances_null"
    ] = "both_empty_separate_correct_absence_Dice_null_one_empty_failure_Dice_zero_distances_null"
    clinical_acceptance: Literal["not_established_no_universal_threshold"] = (
        "not_established_no_universal_threshold"
    )
    software: str


def _quantity(number) -> str:
    value = Decimal(str(number)).quantize(Decimal("0.000000001"), rounding=ROUND_HALF_EVEN)
    return "0" if not value else format(value, "f").rstrip("0").rstrip(".")


def _geometry_valid(geometry) -> bool:
    try:
        CanonicalGeometry.model_validate(geometry.model_dump())
        return geometry.phase_count is None
    except Exception:
        return False


def _legal_mask(mask, geometry, *, binary=False):
    try:
        array = np.asarray(mask)
        if (
            array.shape != geometry.shape_xyz
            or array.dtype.kind not in "biuf"
            or not np.isfinite(array).all()
        ):
            return None
        if (
            np.any(array < 0)
            or np.any(array > (1 if binary else 65535))
            or not np.equal(array, np.floor(array)).all()
        ):
            return None
        if np.count_nonzero(np.unique(array)) > 32:
            return None
        return np.asarray(array, dtype=np.uint16)
    except Exception:
        return None


def _boundary(mask):
    return mask & ~ndimage.binary_erosion(
        mask, structure=ndimage.generate_binary_structure(3, 1), border_value=0
    )


def inspect_mask(
    mask: NDArray[Any],
    geometry: CanonicalGeometry,
    absence_semantics: AbsenceSemantics = "not_recorded",
) -> TechnicalMaskQC:
    """Do not discard components or infer whether an empty mask means absence."""
    if absence_semantics not in (
        "not_recorded",
        "confirmed_absence",
        "missing_annotation",
        "processing_failure",
    ):
        raise ValueError("Unsupported absence semantics; preserve missing evidence")
    if not _geometry_valid(geometry):
        return TechnicalMaskQC(
            technical_status="fail",
            geometry_valid=False,
            foreground_voxels=None,
            labels=(),
            empty_case="not_assessed",
            issues=("INVALID_GEOMETRY",),
            warnings=(),
        )
    array = _legal_mask(mask, geometry)
    if array is None:
        return TechnicalMaskQC(
            technical_status="fail",
            geometry_valid=True,
            foreground_voxels=None,
            labels=(),
            empty_case="not_assessed",
            issues=("INVALID_LABELS_SHAPE_OR_NONFINITE_DATA",),
            warnings=(),
        )
    foreground = int(np.count_nonzero(array))
    issues, warnings, labels = [], [], []
    empty_case: QCCase = "nonempty"
    if not foreground:
        empty_case = "empty_unknown" if absence_semantics == "not_recorded" else absence_semantics
        if absence_semantics != "confirmed_absence":
            issues.append("EMPTY_MASK_REQUIRES_EXPLICIT_ABSENCE_OR_FAILURE_RESOLUTION")
        else:
            warnings.append("CONFIRMED_ABSENCE_REQUIRES_CALLER_VERIFIED_EVIDENCE")
    elif absence_semantics in ("confirmed_absence", "missing_annotation", "processing_failure"):
        issues.append("NONEMPTY_MASK_CONFLICTS_WITH_DECLARED_ABSENCE_OR_FAILURE")
    faces = np.zeros(array.shape, dtype=bool)
    faces[0, :, :] = faces[-1, :, :] = True
    faces[:, 0, :] = faces[:, -1, :] = True
    faces[:, :, 0] = faces[:, :, -1] = True
    for value in np.unique(array):
        if not value:
            continue
        selected = array == value
        components = int(ndimage.label(selected, ndimage.generate_binary_structure(3, 1))[1])
        boundary = int(np.count_nonzero(selected & faces))
        if components > 1:
            warnings.append("MULTIPLE_COMPONENTS_RETAINED_MAY_REPRESENT_MULTIFOCAL_REGIONS")
        if boundary:
            warnings.append("FOREGROUND_TOUCHES_IMAGE_BOUNDARY_EXTENT_REVIEW_REQUIRED")
        labels.append(
            LabelQC(
                label=int(value),
                voxel_count=int(np.count_nonzero(selected)),
                components_6=components,
                boundary_voxels=boundary,
            )
        )
    return TechnicalMaskQC(
        technical_status="fail" if issues else "pass",
        geometry_valid=True,
        foreground_voxels=foreground,
        labels=tuple(labels),
        empty_case=empty_case,
        issues=tuple(issues),
        warnings=tuple(sorted(set(warnings))),
    )


def _not_evaluated(exclusions, *, eligible=0, failed=0):
    return SegmentationMetrics(
        status="not_evaluated",
        dice=None,
        hd95_mm=None,
        absolute_volume_error_mm3=None,
        relative_volume_error=None,
        empty_case="not_assessed",
        eligible_attempted_cases=eligible,
        failed_cases=failed,
        scored_cases=0,
        correct_absence_cases=0,
        exclusions=tuple(exclusions),
        software=f"scipy/{scipy.__version__};numpy/{np.__version__}",
    )


def evaluate_masks(
    candidate: NDArray[Any],
    reference: NDArray[Any] | None,
    geometry: CanonicalGeometry,
    *,
    independent_reference: bool,
    self_comparison: bool,
) -> SegmentationMetrics:
    """Per-label binary metrics only after caller verifies independent reference evidence.

    The two masks must already share this explicitly validated grid. This function
    never registers, resamples or supplies missing reference approvals.
    """
    if type(independent_reference) is not bool or type(self_comparison) is not bool:
        raise ValueError("Explicit server-owned reference eligibility flags required")
    exclusions = []
    if reference is None:
        exclusions.append("MISSING_REFERENCE")
    if not independent_reference:
        exclusions.append("INDEPENDENT_SUITABLE_REFERENCE_NOT_ESTABLISHED")
    if self_comparison or reference is candidate:
        exclusions.append("SELF_COMPARISON_EXCLUDED_FROM_ACCURACY")
    if exclusions:
        return _not_evaluated(exclusions)
    if not _geometry_valid(geometry):
        return _not_evaluated(["INVALID_GEOMETRY"], eligible=1, failed=1)
    predicted = _legal_mask(candidate, geometry, binary=True)
    truth = _legal_mask(reference, geometry, binary=True)
    if predicted is None or truth is None:
        return _not_evaluated(["INVALID_CANDIDATE_OR_REFERENCE"], eligible=1, failed=1)
    predicted, truth = predicted.astype(bool), truth.astype(bool)
    count, reference_count = int(np.count_nonzero(predicted)), int(np.count_nonzero(truth))
    empty_case: MetricCase = (
        "nonempty"
        if count and reference_count
        else "both_empty"
        if not count and not reference_count
        else "candidate_empty"
        if not count
        else "reference_empty"
    )
    voxel_volume = Decimal(
        str(abs(float(np.linalg.det(np.asarray(geometry.affine_ras_mm)[:3, :3]))))
    )
    absolute = voxel_volume * abs(count - reference_count)
    if absolute >= Decimal("1000000000000000"):
        return _not_evaluated(["PHYSICAL_VOLUME_OUTSIDE_QUANTITY_RANGE"], eligible=1, failed=1)
    relative = Decimal(abs(count - reference_count)) / reference_count if reference_count else None
    dice = (
        None
        if not count and not reference_count
        else Decimal(2 * int(np.count_nonzero(predicted & truth))) / (count + reference_count)
    )
    hd95 = None
    surface_counts: tuple[int | None, int | None] = (
        0 if not count else None,
        0 if not reference_count else None,
    )
    if count and reference_count:
        source_points = np.argwhere(_boundary(predicted))
        reference_points = np.argwhere(_boundary(truth))
        surface_counts = (len(source_points), len(reference_points))
        if max(len(source_points), len(reference_points)) > MAX_SURFACE_POINTS:
            return _not_evaluated(["SURFACE_POINT_RESOURCE_LIMIT"], eligible=1, failed=1)
        affine = np.asarray(geometry.affine_ras_mm)
        source_world = source_points @ affine[:3, :3].T + affine[:3, 3]
        reference_world = reference_points @ affine[:3, :3].T + affine[:3, 3]
        forward = cKDTree(reference_world).query(source_world, k=1, p=2, eps=0, workers=1)[0]
        backward = cKDTree(source_world).query(reference_world, k=1, p=2, eps=0, workers=1)[0]
        hd95 = float(np.percentile(np.concatenate([forward, backward]), 95, method="linear"))
        if not np.isfinite(hd95):
            return _not_evaluated(["INVALID_SURFACE_DISTANCE"], eligible=1, failed=1)
    return SegmentationMetrics(
        status="eligible",
        dice=None if dice is None else _quantity(dice),
        hd95_mm=None if hd95 is None else _quantity(hd95),
        absolute_volume_error_mm3=_quantity(absolute),
        relative_volume_error=None if relative is None else _quantity(relative),
        empty_case=empty_case,
        eligible_attempted_cases=1,
        failed_cases=int(empty_case in ("candidate_empty", "reference_empty")),
        scored_cases=int(empty_case == "nonempty"),
        correct_absence_cases=int(empty_case == "both_empty"),
        candidate_foreground_voxels=count,
        reference_foreground_voxels=reference_count,
        intersection_voxels=int(np.count_nonzero(predicted & truth)),
        candidate_surface_points=surface_counts[0],
        reference_surface_points=surface_counts[1],
        exclusions=(),
        software=f"scipy/{scipy.__version__};numpy/{np.__version__}",
    )
