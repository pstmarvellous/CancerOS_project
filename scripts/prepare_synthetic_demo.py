"""Prepare token-free, synthetic-only read-only demo data via the existing pipeline.

Uses the explicitly disposable test database and private object store. No external
inference, API credentials, clinical source data or runtime authorization bypass.
The fixture transaction rolls back; embedded meshes are copied into an ignored,
expiring local presentation bundle. Source specifications and algorithms are unchanged.

Modes: default ensures a valid bundle (skips rebuild when the present bundle is
valid with more than 24h remaining); --check validates only and reports actionable
failures; --force rebuilds unconditionally.
"""

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = ROOT / ".local" / "synthetic-demo.json"
FRESHNESS_SKIP = timedelta(hours=24)

ROOT = Path(__file__).resolve().parents[1]
# This process prepares local fixtures only, regardless of development .env.
os.environ["EXTERNAL_INFERENCE_ENABLED"] = "false"
sys.path.insert(0, str(ROOT / "tests"))

from simulation_fixtures import setup_simulation_baseline  # noqa: E402
from test_imaging_ingestion import imaging_db  # noqa: E402
from test_simulation_execution import command, freeze, publication_value  # noqa: E402
from test_simulation_runs import TEST  # noqa: E402
from test_source_registry import registry_db  # noqa: E402

from canceros.annotation_import import load_annotation_mask  # noqa: E402
from canceros.mesh_quality import validate_surface  # noqa: E402
from canceros.mesh_reconstruction import reconstruct  # noqa: E402
from canceros.simulation_execution import complete_run, publish_completion  # noqa: E402
from canceros.synthetic_geometry import read_generated_mesh  # noqa: E402
from canceros.temporal_timeline import TimelineScope, TimelineWindow  # noqa: E402
from canceros.timeline_runs import TimelineQuery, query_timeline  # noqa: E402
from canceros.trend_runs import TrendQuery, query_trends  # noqa: E402

FAMILIES = {
    "SC-01": ("Sustained shrinkage", "A hypothetical decrease in region volume over time."),
    "SC-02": ("Modest change or stability", "A hypothetical near-stable region volume."),
    "SC-03": ("Progressive growth", "A hypothetical increase in region volume over time."),
    "SC-04": ("Shrinkage then regrowth", "A hypothetical decrease followed by renewed growth."),
    "SC-05": (
        "Stable volume, changing symptoms",
        "Similar region volume with a separate hypothetical symptom course.",
    ),
}


def surface_digest(surface):
    """Match demo-integrity.ts binary encoding; avoid JSON float normalization."""
    digest = hashlib.sha256(b"canceros-demo-surface/1\n")
    digest.update(
        json.dumps(
            [
                surface[k]
                for k in (
                    "frame",
                    "unit",
                    "algorithm",
                    "surface_convention",
                    "measurement_authority",
                )
            ],
            separators=(",", ":"),
        ).encode()
        + b"\n"
    )
    digest.update(
        struct.pack("<III", *(len(surface[k]) for k in ("vertices", "triangles", "normals")))
    )
    for field, format in (("vertices", "<3d"), ("triangles", "<3I"), ("normals", "<3d")):
        for row in surface[field]:
            digest.update(struct.pack(format, *row))
    for field in ("bounds_min_mm", "bounds_max_mm"):
        digest.update(struct.pack("<3d", *surface[field]))
    for field in ("display_to_patient", "patient_to_display"):
        for row in surface[field]:
            digest.update(struct.pack("<4d", *row))
    return digest.hexdigest()


def bundle_status(path=None):
    """Validate the present bundle without touching services or the database."""
    node = shutil.which("node")
    if not node:
        return ("invalid", "Node runtime is required for the shared serving validator.")
    try:
        result = subprocess.run(
            [node, str(ROOT / "scripts/serve_synthetic_demo.mjs"),
             "--validate-bundle", str(path or BUNDLE_PATH)],
            cwd=ROOT, capture_output=True, text=True, timeout=60, check=False,
        )
        report = json.loads(result.stdout)
        if report["state"] == "valid" and result.returncode == 0:
            return ("valid", "Bundle passed the shared serving validator.")
        if report["state"] == "missing":
            return ("missing", "Prepared bundle is missing; prepare again.")
        if report["state"] == "expired":
            return ("expired", "Bundle expired; prepare again to refresh the 7-day window.")
        return ("invalid", "Bundle failed serving validation; prepare again. Run npm ci if validation dependencies are absent.")
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        return ("invalid", "Shared validator unavailable; verify Node and run npm ci, then prepare again.")


def check():
    state, message = bundle_status()
    print(f"Demo bundle state: {state}. {message}")
    if state != "valid":
        print("Action: ensure disposable PostgreSQL, storage and queue are running, then run:")
        print("  uv run python scripts/prepare_synthetic_demo.py")
        raise SystemExit(1)
    print("PASS existing synthetic demo bundle is valid; rebuild skipped")


def prepare(*, force=False):
    if not force:
        state, message = bundle_status()
        if state == "valid":
            try:
                remaining = datetime.fromisoformat(
                    json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))["expiresAt"]
                ) - datetime.now(timezone.utc)
            except (OSError, ValueError, KeyError):
                remaining = timedelta(0)
            if remaining > FRESHNESS_SKIP:
                print(f"PASS {message} Rebuild skipped.")
                return
            print(f"{message} Refreshing within 24h of expiry.")
    if not __debug__:
        raise RuntimeError("Synthetic preparation requires Python fixture assertions enabled")
    fixture = registry_db.__wrapped__()
    try:
        data = imaging_db.__wrapped__(next(fixture))
        c, identity, project, patient, _, storage, _ = data
        measurement, origin, _ = setup_simulation_baseline(data)
        if measurement.origin != "SYNTHETIC_GENERATED":
            raise RuntimeError("Demo baseline must be synthetic")
        # The project was created in this uncommitted fixture transaction. Check
        # every source, rather than trusting a display label or synthetic descendant.
        sources = (
            c.execute(
                text("SELECT origin FROM source.registry_versions WHERE project_id=:p"),
                {"p": project},
            )
            .scalars()
            .all()
        )
        if not sources or set(sources) != {"synthetic_engineering_fixture"}:
            raise RuntimeError("Demo source registry contains non-fixture origins")
        annotation = measurement.selections[0].segmentation_id
        record, mask = load_annotation_mask(
            c, identity, project, patient.patient_id, annotation, storage
        )
        surface = reconstruct(mask, record.geometry)
        if not validate_surface(surface).display_allowed:
            raise RuntimeError("Demo baseline surface failed display validation")
        baseline_surface = surface.model_dump(mode="json")
        scenarios = {}
        for family, (label, description) in FAMILIES.items():
            print(f"Preparing {family}: {label}", flush=True)
            branch, _, run = freeze(data, measurement, origin, family)
            completion = complete_run(
                c,
                identity,
                project,
                patient.patient_id,
                command(run),
                storage,
                "demo-complete-" + family,
                TEST,
            )
            if completion.status != "ready":
                raise RuntimeError(f"Synthetic demo family {family} did not complete")
            publish_completion(
                c,
                identity,
                project,
                patient.patient_id,
                completion.id,
                publication_value(run),
                storage,
                "demo-publish-" + family,
                TEST,
            )
            query = TimelineQuery(
                window=TimelineWindow(
                    scope=TimelineScope(
                        mode="simulation",
                        data_revision=run.input_revision,
                        branch_id=branch.id,
                        run_id=run.id,
                    ),
                    knowledge_as_of=datetime.now(timezone.utc) + timedelta(minutes=1),
                ),
                completion_id=completion.id,
                limit=100,
            )
            page = query_timeline(c, identity, project, patient.patient_id, query)
            if page.next_cursor or any(p.origin.value != "SYNTHETIC_GENERATED" for p in page.items):
                raise RuntimeError("Demo timeline must be complete and exclusively synthetic")
            trends = query_trends(
                c, identity, project, patient.patient_id, TrendQuery(timeline=query)
            )
            points = [
                p
                for p in page.items
                if p.measurement_basis in ("baseline_reference", "mask_realized")
            ]
            if len(points) != 4:
                raise RuntimeError("Demo requires a baseline and three measured follow-ups")
            meshes = {}
            bindings = {}
            for point in points:
                if point.geometry_result_id:
                    mesh = read_generated_mesh(
                        c, identity, project, patient.patient_id, point.geometry_result_id, storage
                    )
                    if mesh.geometry_id != point.id or mesh.origin != "SYNTHETIC_GENERATED":
                        raise RuntimeError("Demo mesh identity or synthetic origin mismatch")
                    meshes[str(point.id)] = mesh.surface.model_dump(mode="json")
                else:
                    meshes[str(point.id)] = baseline_surface
                bindings[str(point.id)] = {
                    "point_id": str(point.id),
                    "patient_id": str(point.patient_id),
                    "branch_id": str(point.branch_id),
                    "run_id": str(point.run_id),
                    "state_ids": [str(s) for s in point.state_ids],
                    "geometry_result_id": str(point.geometry_result_id)
                    if point.geometry_result_id
                    else None,
                    "surface_sha256": surface_digest(meshes[str(point.id)]),
                }
            # Typed domain reports, with only synthetic identifiers and embedded
            # geometry. No Settings, storage metadata, JWTs or source-linkage rows.
            scenarios[family] = {
                "id": family,
                "label": label,
                "description": description,
                "timeline": page.model_dump(mode="json"),
                "trends": trends.model_dump(mode="json"),
                "meshes": meshes,
                "meshBindings": bindings,
            }
        now = datetime.now(timezone.utc)
        bundle = {
            "version": "synthetic-demo/2",
            "syntheticOnly": True,
            "sourceOrigin": "synthetic_engineering_fixture",
            "caseLabel": "Research Demo 01",
            "preparedAt": now.isoformat(),
            "expiresAt": (now + timedelta(days=7)).isoformat(),
            "scenarios": scenarios,
        }
        target = ROOT / ".local/synthetic-demo.json"
        target.parent.mkdir(exist_ok=True)
        temporary = target.with_suffix(".pending")
        temporary.write_text(json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
        state, _ = bundle_status(temporary)
        if state != "valid":
            temporary.unlink(missing_ok=True)
            raise RuntimeError("Generated demo failed the shared serving validator; previous bundle preserved")
        temporary.replace(target)
        print(
            "Prepared five synthetic scenarios, each with a shared phantom baseline and three measured follow-ups."
        )
        print("Local read-only bundle ready. No token or live-provider request created.")
    finally:
        fixture.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare or validate the synthetic demo bundle")
    parser.add_argument("--check", action="store_true", help="validate the present bundle only")
    parser.add_argument("--force", action="store_true", help="rebuild even when the bundle is fresh")
    args = parser.parse_args()
    try:
        if args.check:
            check()
        else:
            prepare(force=args.force)
    except Exception as error:
        # Dependency errors can contain connection strings: never print their
        # text or tracebacks in normal preparation output.
        print(f"Demo preparation failed ({type(error).__name__}). Previous bundle preserved.", file=sys.stderr)
        print("Verify npm ci and the foundation PostgreSQL/storage/queue services using infrastructure/README.md, then retry.", file=sys.stderr)
        raise SystemExit(1) from None
