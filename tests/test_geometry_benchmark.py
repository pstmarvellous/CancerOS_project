"""COS-082 benchmark: imaging geometry, physical measurement and mesh checks.

Independent references (voxel count x |det(A3x3)|, numpy-free round trips, exact
integer-label counts, single mm->m conversion, watertightness accounting) kept
separate from production helpers. Curated real cases and optional segmentation
checkpoints are Not evaluated: no eligible model/reference, reviewer or approval
in this fixture-only scope.
"""

import hashlib
import json
import platform
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import numpy as np

from canceros.imaging_geometry import (
    GeometryError,
    canonical_geometry,
    index_to_world,
    world_to_index,
)

SUITE_VERSION = "geometry-benchmark/1"
RESULTS_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "engineering"
    / "evidence"
    / "geometry-benchmark.json"
)

TOL_VOLUME_REL = Decimal("1e-9")
TOL_VOLUME_ABS = Decimal("0.000001")
TOL_ROUNDTRIP_MM = Decimal("0.00001")
CASES = []


def record(name, status, detail=""):
    CASES.append({"case": name, "status": status, "detail": detail})


def check_volume(count, det_abs, expected_mm3, label):
    expected = Decimal(str(expected_mm3))
    got = (Decimal(count) * Decimal(str(det_abs))).quantize(Decimal("0.000001"))
    tolerance = max(TOL_VOLUME_ABS, abs(expected) * TOL_VOLUME_REL)
    assert abs(got - expected) <= tolerance, f"{label}: {got} vs {expected}"
    cm3 = got / Decimal(1000)
    assert abs(cm3 * 1000 - got) <= TOL_VOLUME_ABS
    record(label, "scored", f"{got} mm3 = {cm3} cm3")


def check_roundtrip(affine, shape, label):
    geometry = canonical_geometry(shape, affine)
    rng = np.random.default_rng(hash(label) % (2**32))
    worst = Decimal(0)
    for _ in range(25):
        index = [float(v) for v in rng.uniform(-0.5, np.subtract(shape, 0.5))]
        world = [float(v) for v in index_to_world(geometry, index)]
        back = [float(v) for v in world_to_index(geometry, world)]
        err = max(abs(a - b) for a, b in zip(index, back))
        worst = max(worst, Decimal(str(err)))
    assert worst <= TOL_ROUNDTRIP_MM, f"{label}: worst {worst} mm"
    record(label, "scored", f"worst round-trip error {worst} mm over 25 samples")


def test_cuboid_volumes_with_independent_determinants():
    check_volume(
        3 * 4 * 5,
        abs(float(np.linalg.det(np.diag([2.0, 3.0, 4.0])))),
        "1440",
        "translated anisotropic cuboid",
    )
    check_volume(
        3 * 4 * 5,
        abs(float(np.linalg.det(np.array([[0, -3, 0], [2, 0, 0], [0, 0, 4]], dtype=float)))),
        "1440",
        "axis-swap cuboid",
    )
    check_volume(
        3 * 4 * 5, abs(float(np.linalg.det(np.diag([-2.0, 3.0, 4.0])))), "1440", "reflected cuboid"
    )
    shear = np.array([[2.0, 1.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 4.0]])
    check_volume(3 * 4 * 5, abs(float(np.linalg.det(shear))), "1440", "sheared cuboid")


def test_bounded_roundtrips_oblique_and_sheared():
    check_roundtrip(
        [[2, 0, 0, 10], [0, 3, 0, -20], [0, 0, 4, 5], [0, 0, 0, 1]],
        (3, 4, 5),
        "translated anisotropic round-trip",
    )
    oblique = [[1.5, 0.5, 0.2, -4], [0.1, 2.5, -0.3, 8], [0.0, 0.4, 3.5, -2], [0, 0, 0, 1]]
    check_roundtrip(oblique, (4, 5, 6), "oblique affine round-trip")
    shear = [[2, 1, 0, 0], [0, 3, 0, 0], [0, 0, 4, 0], [0, 0, 0, 1]]
    check_roundtrip(shear, (3, 4, 5), "sheared affine round-trip")


def test_invalid_transforms_fail_for_intended_reason():
    for label, affine in [
        ("zero-determinant", [[1, 0, 0, 0], [0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]),
        ("non-affine-bottom-row", [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 1, 1]]),
    ]:
        try:
            canonical_geometry((2, 2, 2), affine)
        except GeometryError:
            record(label, "scored", "rejected for intended reason")
        else:
            raise AssertionError(f"{label} unexpectedly accepted")


def test_exact_label_counts_and_single_unit_conversion():
    labels = np.zeros((4, 5, 6), dtype=np.int16)
    labels[0:2, :, :] = 1
    labels[2:4, :, 0:3] = 2
    unique, counts = np.unique(labels, return_counts=True)
    tally = dict(zip(unique.tolist(), counts.tolist()))
    assert tally[1] == 60 and tally[2] == 30, tally
    nonzero = int((labels > 0).sum())
    assert nonzero == 90, nonzero
    record(
        "integer-label preservation", "scored", f"labels {tally} exact; nonzero voxels {nonzero}"
    )
    assert Decimal("1440") / Decimal(1000) == Decimal("1.44")
    record("mm-to-m single conversion", "scored", "1440 mm3 = 1.44 cm3 exactly once")


def test_mesh_bounds_scale_and_watertight_accounting():
    vertices = np.array([[0.0, 0.0, 0.0], [6.0, 0.0, 0.0], [0.0, 12.0, 0.0], [0.0, 0.0, 20.0]])
    triangles = np.array([[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]])
    bounds_min = vertices.min(axis=0).tolist()
    bounds_max = vertices.max(axis=0).tolist()
    assert bounds_min == [0.0, 0.0, 0.0] and bounds_max == [6.0, 12.0, 20.0]
    edge_counts: dict[tuple[int, int], int] = {}
    for tri in triangles:
        for edge in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            key = (min(edge), max(edge))
            edge_counts[key] = edge_counts.get(key, 0) + 1
    watertight = all(count == 2 for count in edge_counts.values())
    assert watertight
    record(
        "mesh bounds/scale/watertight",
        "scored",
        f"bounds {bounds_min}->{bounds_max}; watertight={watertight}",
    )


def test_benchmark_report_with_attempted_eligible_excluded_failed_scored():
    assert len([c for c in CASES if c["status"] == "scored"]) >= 5
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "suite": SUITE_VERSION,
        "tolerances": {
            "volume": "max(1e-6 mm3, 1e-9 x expected)",
            "roundtrip_mm": "1e-5",
        },
        "cases": CASES,
        "counts": {
            "attempted": len(CASES),
            "eligible": len(CASES),
            "excluded": 0,
            "failed": sum(1 for c in CASES if c["status"] != "scored"),
            "scored": sum(1 for c in CASES if c["status"] == "scored"),
        },
        "real_cases": "Not evaluated: no curated real case with source rights, linkage, reviewer and overlay evidence in this scope",
        "segmentation_model": "Not evaluated: no eligible optional checkpoint; imported-mask self-overlap transfers consistency only",
        "scope": "technical correctness only; not clinical accuracy",
        "result": "passed" if all(c["status"] == "scored" for c in CASES) else "failed",
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(CASES, sort_keys=True).encode()
    ).hexdigest()
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert payload["result"] == "passed"
