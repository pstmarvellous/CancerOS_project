"""Actual isolated synthetic CPU fixture timing/RSS; no representative device claim."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psutil

from canceros.imaging_geometry import canonical_geometry
from canceros.mesh_quality import simplify_convex, validate_surface
from canceros.mesh_reconstruction import reconstruct
from canceros.persistence import canonical_bytes

start = time.perf_counter()
mask = np.ones((3, 4, 2), dtype=np.uint8)
surface = reconstruct(mask, canonical_geometry(mask.shape, np.diag([2.0, 3.0, 4.0, 1.0])))
quality = validate_surface(surface)
lod, comparison = simplify_convex(surface)
assert quality.display_allowed and comparison.accepted and lod is not None
raw, reduced = (canonical_bytes(s.model_dump(mode="json")) for s in (surface, lod))
elapsed = time.perf_counter() - start
start = time.perf_counter()
json.loads(reduced)
decode_seconds = time.perf_counter() - start
payload = {
    "recorded_at": datetime.now(timezone.utc).isoformat(),
    "scope": "artificial_3x4x2_cpu_fixture_only_not_browser_or_clinical",
    "original_vertices": len(surface.vertices),
    "original_triangles": len(surface.triangles),
    "lod_vertices": len(lod.vertices),
    "lod_triangles": len(lod.triangles),
    "original_bytes": len(raw),
    "lod_bytes": len(reduced),
    "cpu_total_seconds": elapsed,
    "json_decode_seconds": decode_seconds,
    "process_rss_after_bytes": psutil.Process().memory_info().rss,
    "peak_rss": "not_measured",
    "browser_load": "not_measured",
    "target_laptop": "not_measured",
}
Path("docs/engineering/evidence/mesh-fixture-measurement.json").write_text(
    json.dumps(payload, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(payload))
