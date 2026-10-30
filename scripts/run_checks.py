"""Fail-fast local checks with actual redacted outputs; no unconditional successes."""

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
TARGETS = {
    "forecast-baselines": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_forecast_baselines.py",
            "tests/test_forecast_runs.py",
            "--tb=line",
        ],
        [
            PY,
            "scripts/evaluate_forecast_baselines.py",
            "--output",
            "docs/engineering/evidence/forecast-baseline-metrics.json",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "dependent-updates": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_dependent_updates.py",
            "tests/test_clinical_ingestion.py::test_concurrent_corrections_only_one_revision_wins",
            "tests/test_imaging_jobs.py",
            "tests/test_state_jobs.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "state-fusion": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_state_fusion.py",
            "tests/test_fusion_runs.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "deterministic-trends": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_temporal_trends.py",
            "tests/test_trend_runs.py",
            "tests/test_timeline_runs.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "observation-timeline": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_temporal_timeline.py",
            "tests/test_timeline_source.py",
            "tests/test_timeline_runs.py",
            "tests/test_generated_clinical_states.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "simulation-pins": [
        [PY, "-m", "pytest", "tests/test_runtime_identity.py", "--tb=line"],
        [PY, "-m", "mypy"],
    ],
    "simulation-publication-scope": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_simulation_execution.py::test_all_five_families_have_actual_complete_geometry_and_atomic_publication",
            "tests/test_simulation_execution.py::test_concurrent_publication_cas_and_withdrawal",
            "--tb=line",
        ],
    ],
    "simulation-complete": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_simulation_validation.py",
            "tests/test_simulation_regression.py",
            "tests/test_simulation_execution.py",
            "tests/test_generated_clinical_states.py",
            "tests/test_imaging_jobs.py",
            "tests/test_simulation_runs.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "simulation-sampling": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_sampling.py",
            "tests/test_sampling_runs.py",
            "tests/test_clinical_generation.py",
            "tests/test_clinical_generation_runs.py",
            "tests/test_scenario_geometry.py",
            "tests/test_simulation_runs.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "clinical-generation": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_clinical_generation.py",
            "tests/test_clinical_generation_runs.py",
            "tests/test_simulation_contracts.py",
            "tests/test_scenario_sc05.py",
            "tests/test_state_jobs.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "scenario-sc05": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_scenario_sc05.py",
            "tests/test_scenario_sc04.py",
            "tests/test_scenario_families.py",
            "tests/test_scenario_sc02.py",
            "tests/test_scenario_sc03.py",
            "tests/test_scenario_geometry.py",
            "tests/test_simulation_contracts.py",
            "tests/test_simulation_runs.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "scenario-sc04": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_scenario_sc04.py",
            "tests/test_scenario_families.py",
            "tests/test_scenario_sc02.py",
            "tests/test_scenario_sc03.py",
            "tests/test_scenario_geometry.py",
            "tests/test_simulation_contracts.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "scenario-sc03": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_scenario_sc03.py",
            "tests/test_synthetic_shape.py",
            "tests/test_scenario_families.py",
            "tests/test_scenario_sc02.py",
            "tests/test_scenario_geometry.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "scenario-sc02": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_scenario_sc02.py",
            "tests/test_simulation_runs.py",
            "tests/test_scenario_families.py",
            "tests/test_scenario_geometry.py",
            "tests/test_simulation_contracts.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "scenario-sc01": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_scenario_families.py",
            "tests/test_scenario_geometry.py",
            "tests/test_synthetic_geometry.py",
            "tests/test_twin_states.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "simulation-eligibility": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_simulation_eligibility.py",
            "tests/test_eligibility_checks.py",
            "tests/test_simulation_runs.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "simulation-configs": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_simulation_contracts.py",
            "tests/test_simulation_runs.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "synthetic-geometry": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_synthetic_shape.py",
            "tests/test_synthetic_geometry.py",
            "tests/test_twin_states.py",
            "tests/test_imaging_jobs.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "twin-states": [
        [PY, "scripts/migrate_test.py"],
        [PY, "-m", "pytest", "tests/test_twin_states.py", "tests/test_state_jobs.py", "--tb=line"],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "lesion-tracking": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_temporal_measurements.py",
            "tests/test_lesion_tracking.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "registration": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_rigid_registration.py",
            "tests/test_registration_runs.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "mesh-preview": [
        [PY, "scripts/verify_mesh_browser.py"],
    ],
    "mesh-quality": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_mesh_quality.py",
            "tests/test_mesh_quality_runs.py",
            "tests/test_mesh_runs.py",
            "--tb=line",
        ],
        [PY, "scripts/measure_mesh.py"],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "mesh-reconstruction": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_mesh_reconstruction.py",
            "tests/test_mesh_runs.py",
            "tests/test_imaging_jobs.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "physical-measurements": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_physical_measurements.py",
            "tests/test_measurement_runs.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "imaging-worker": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_imaging_jobs.py",
            "tests/test_imaging_worker_cli.py",
            "tests/test_imaging_storage.py",
            "tests/test_imaging_jobs_http.py",
            "tests/test_jobs.py",
            "--tb=line",
        ],
        [PY, "scripts/measure_imaging_worker.py"],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "segmentation-qc": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_segmentation_qc.py",
            "tests/test_segmentation_reviews.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "annotation-import": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_annotation_contracts.py",
            "tests/test_annotation_import.py",
            "tests/test_alignment_runs.py",
            "tests/test_preprocessing_runs.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "mask-alignment": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_mask_alignment.py",
            "tests/test_alignment_runs.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "imaging-preprocessing": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_imaging_preprocessing.py",
            "tests/test_preprocessing_runs.py",
            "tests/test_imaging_ingestion.py",
            "tests/test_evaluation_splits.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "imaging-geometry": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_imaging_geometry.py",
            "tests/test_imaging_volumes.py",
            "tests/test_imaging_ingestion.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "imaging-ingestion": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_imaging_formats.py",
            "tests/test_imaging_ingestion.py",
            "--tb=line",
        ],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "evaluation-splits": [
        [PY, "scripts/migrate_test.py"],
        [PY, "-m", "pytest", "tests/test_evaluation_splits.py", "--tb=line"],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "quality": [
        [PY, "scripts/migrate_test.py"],
        [PY, "-m", "pytest", "tests/test_quality.py", "--tb=line"],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "lineage": [
        [PY, "scripts/migrate_test.py"],
        [
            PY,
            "-m",
            "pytest",
            "tests/test_lineage.py",
            "tests/test_metadata_adapters.py",
            "tests/test_clinical_ingestion.py",
            "--tb=line",
        ],
        [PY, "scripts/clinical_fixture.py"],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "metadata-adapters": [
        [PY, "scripts/migrate_test.py"],
        [PY, "-m", "pytest", "tests/test_metadata_adapters.py", "--tb=line"],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "clinical-validation": [
        [PY, "scripts/migrate_test.py"],
        [PY, "-m", "pytest", "tests/test_clinical_validation.py", "--tb=line"],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "clinical-ingestion": [
        [PY, "scripts/migrate_test.py"],
        [PY, "-m", "pytest", "tests/test_clinical_ingestion.py", "--tb=line"],
        [PY, "scripts/clinical_fixture.py"],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "clinical-contracts": [
        [PY, "-m", "pytest", "tests/test_clinical_contracts.py", "--tb=line"],
        [PY, "-m", "mypy"],
        [PY, "scripts/check_contract_drift.py"],
    ],
    "patient-linkage": [
        [PY, "scripts/migrate_test.py"],
        [PY, "-m", "pytest", "tests/test_patient_linkage.py", "--tb=line"],
        [PY, "-m", "mypy"],
        [PY, "scripts/generate_contracts.py", "--check"],
    ],
    "source-registry": [
        [PY, "scripts/migrate_test.py"],
        [PY, "-m", "pytest", "tests/test_source_registry.py", "--tb=line"],
        [PY, "-m", "mypy"],
        [PY, "scripts/generate_contracts.py", "--check"],
    ],
    "security": [
        [
            PY,
            "-m",
            "pytest",
            "tests/test_identity_export.py",
            "tests/test_identity_db.py",
            "tests/test_settings.py",
            "--tb=line",
        ],
    ],
    "frontend": [
        ["npm.cmd" if sys.platform == "win32" else "npm", "run", command]
        for command in ("lint", "typecheck", "test", "build", "contracts:check")
    ],
    "worker": [
        [PY, "scripts/migrate_test.py"],
        [PY, "-m", "pytest", "tests/test_jobs.py", "--tb=line"],
        [PY, "scripts/worker_smoke.py"],
    ],
    "persistence": [
        [PY, "scripts/migrate_test.py"],
        [PY, "-m", "pytest", "tests/test_persistence.py", "tests/test_storage.py", "--tb=line"],
    ],
    "backend": [
        ["uv", "sync", "--locked"],
        [PY, "-m", "ruff", "check", "src", "tests", "scripts", "workers", "migrations"],
        [PY, "-m", "ruff", "format", "--check", "src", "tests", "scripts", "workers", "migrations"],
        [PY, "-m", "mypy"],
        [
            PY,
            "-m",
            "pytest",
            "--tb=line",
        ],
        [PY, "scripts/generate_contracts.py", "--check"],
    ],
    "governance": [
        [PY, "scripts/check_foundation_docs.py"],
        [PY, "scripts/check_governance.py", "--self-test"],
        [PY, "scripts/check_reference_maps.py"],
        [PY, "scripts/check_structure.py"],
        [PY, "scripts/check_boundaries.py"],
        [PY, "scripts/check_hygiene.py"],
        [PY, "scripts/check_evidence.py"],
    ],
}


def run(target):
    directory = ROOT / "docs/engineering/evidence"
    directory.mkdir(parents=True, exist_ok=True)
    records = []
    for command in TARGETS[target]:
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        records.append(
            {
                "command": command,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        print(
            "PASS" if result.returncode == 0 else "FAIL",
            " ".join(command[1:] if command[0] == PY else command),
        )
        if result.returncode:
            break
    payload = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "scope": target + " engineering verification only; no real-data or qualified review claim",
        "input_hash": hashlib.sha256((ROOT / "pyproject.toml").read_bytes()).hexdigest(),
        "checks": records,
        "result": "passed" if all(r["exit_code"] == 0 for r in records) else "failed",
    }
    (directory / f"{target}.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    if payload["result"] == "failed":
        print(records[-1]["stdout"], records[-1]["stderr"])
        raise SystemExit(1)


if __name__ == "__main__":
    run(sys.argv[1])
