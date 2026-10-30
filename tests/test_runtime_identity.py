"""Frozen run identity covers transitive scientific code, independently of worker dispatch."""

from pathlib import Path

import pytest

from canceros.simulation_runs import runtime_identity


@pytest.mark.parametrize(
    "name",
    [
        "contracts.py",
        "clinical_contracts.py",
        "imaging_geometry.py",
        "physical_measurements.py",
        "measurement_runs.py",
        "mesh_reconstruction.py",
        "mesh_quality.py",
    ],
)
def test_scientific_dependency_change_invalidates_frozen_environment(monkeypatch, name):
    before = runtime_identity()
    original = Path.read_bytes

    def changed(path):
        content = original(path)
        return content + b"\n# isolated hash mutation fixture\n" if path.name == name else content

    monkeypatch.setattr(Path, "read_bytes", changed)
    assert runtime_identity().code_hash != before.code_hash
