"""Common configuration snapshots; scientific run authorization is not inferred from fixtures."""

import hashlib
import json
import platform
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import AwareDatetime, Field
from sqlalchemy import text

from canceros.contracts import Contract, Hash
from canceros.identity import authorize_project
from canceros.lineage import derive_resource, lock_lineage, processing_spec, require_resource_action
from canceros.measurement_runs import load_usable_measurement
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import load_revision, science_hash
from canceros.sampling import SampledObservations, sample_observations
from canceros.simulation_contracts import SimulationConfig
from canceros.simulation_eligibility import EligibilityResult
from canceros.simulation_plugins import PluginOutput
from canceros.source_registry import SourceAction
from canceros.twin_states import read_branch, read_state

Revision = Annotated[int, Field(strict=True, ge=0)]


class SaveConfigInput(Contract):
    expected_draft_revision: Revision
    config: SimulationConfig


class ConfigSummary(Contract):
    baseline: Literal["unverified_engineering_baseline"] = "unverified_engineering_baseline"
    disclosure: Literal["Hypothetical simulation; not a patient-specific prediction"] = (
        "Hypothetical simulation; not a patient-specific prediction"
    )
    available_actions: list[Literal["edit_draft", "inspect_baseline", "freeze_isolated_test_run"]]
    blocking_reasons: list[str]


class ConfigVersion(Contract):
    id: UUID
    branch_id: UUID
    draft_revision: Annotated[int, Field(strict=True, ge=1)]
    config: SimulationConfig
    config_hash: Hash
    summary: ConfigSummary


class QueueRunInput(Contract):
    config_id: UUID
    expected_draft_revision: Annotated[int, Field(strict=True, ge=1)]
    expected_config_hash: Hash


class RuntimeIdentity(Contract):
    python: str
    system: str
    machine: str
    numpy: str
    pydantic: str
    code_hash: Hash
    dependency_lock_hash: Hash


class SimulationRun(Contract):
    id: UUID
    branch_id: UUID
    config_id: UUID
    config: SimulationConfig
    config_hash: Hash
    input_revision: Annotated[int, Field(strict=True, ge=1)]
    input_manifest_hash: Hash
    association_head: Annotated[int, Field(strict=True, ge=0)] | None = None
    environment: RuntimeIdentity
    eligibility: EligibilityResult | None = None
    queued_at: AwareDatetime
    started_at: None = None
    completed_at: None = None
    validation_summary: None = None
    failure_reason: None = None
    status: Literal["queued"] = "queued"
    readiness: Literal[
        "blocked_pending_integration", "isolated_engineering_execution_available"
    ] = "isolated_engineering_execution_available"
    job_id: None = None
    authority: Literal["isolated_test_mock"] = "isolated_test_mock"
    baseline_observed_verified: Literal[False] = False
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    scientific_review: Literal["pending"] = "pending"
    publication: Literal["draft"] = "draft"
    next_action: str = "Queue complete-run engineering generation; inspect its completion before separate publication"


class RunTargetSummary(Contract):
    run_id: UUID
    baseline_hash: Hash
    baseline_measurement_id: UUID
    output: PluginOutput
    geometry_policy: Literal["none", "isotropic-fixed-grid/1"]
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    publication: Literal["draft"] = "draft"


def _write(c, i, p, u):
    authorize_project(i, p, "admin")
    authorize_patient(c, i, p, u, edit=True)
    lock_lineage(c, p, u)


def _usable(c, i, p, u, identifier):
    for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE):
        require_resource_action(c, i, p, u, identifier, action)


def _read(c, i, p, u, table, identifier, model):
    authorize_patient(c, i, p, u, edit=True)
    row = c.execute(
        text(
            f"SELECT report,report_hash FROM imaging.{table} WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": p, "u": u, "id": identifier},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.report) != row.report_hash:
        raise HTTPException(409, detail="simulation_snapshot_integrity_failure")
    return model.model_validate(row.report)


def read_config(c, i, p, u, identifier):
    return _read(c, i, p, u, "simulation_config_versions", identifier, ConfigVersion)


def read_latest_config(c, i, p, u, branch_id):
    authorize_project(i, p, "admin")
    branch = read_branch(c, i, p, u, branch_id)
    _usable(c, i, p, u, branch.id)
    identifier = c.execute(
        text(
            "SELECT id FROM imaging.simulation_config_versions WHERE project_id=:p AND patient_id=:u AND branch_id=:b ORDER BY draft_revision DESC LIMIT 1"
        ),
        {"p": p, "u": u, "b": branch_id},
    ).scalar_one_or_none()
    if identifier is None:
        return None
    _usable(c, i, p, u, identifier)
    return read_config(c, i, p, u, identifier)


def read_run(c, i, p, u, identifier):
    return _read(c, i, p, u, "simulation_runs", identifier, SimulationRun)


def read_run_targets(c, i, p, u, identifier):
    from decimal import Decimal

    from canceros.scenario_families import build_registry

    authorize_project(i, p, "admin")
    run = read_run(c, i, p, u, identifier)
    _usable(c, i, p, u, run.id)
    if run.environment != runtime_identity():
        raise HTTPException(409, detail="frozen_simulator_environment_changed_create_new_run")
    branch = read_branch(c, i, p, u, run.branch_id)
    measurement = load_usable_measurement(c, i, p, u, branch.input.baseline_measurement_id)
    try:
        output = build_registry().generate(run.config, Decimal(measurement.values.exact_volume_mm3))
    except ValueError as error:
        raise HTTPException(409, detail=str(error)) from None
    return RunTargetSummary(
        run_id=run.id,
        baseline_hash=run.config.baseline_hash,
        baseline_measurement_id=measurement.id,
        output=output,
        geometry_policy=run.config.geometry_policy,
    )


def read_run_sampling(c, i, p, u, identifier):
    run = read_run(c, i, p, u, identifier)
    target = read_run_targets(c, i, p, u, identifier)
    return _sample(run.config, target.output)


def read_run_geometry_targets(c, i, p, u, identifier):
    from decimal import Decimal

    from canceros.scenario_families import check_family_realized
    from canceros.simulation_plugins import TumorTarget

    run = read_run(c, i, p, u, identifier)
    target = read_run_targets(c, i, p, u, identifier)
    observed = _sample(run.config, target.output)
    if any(point.target_mm3 is None for point in observed.tumor_targets):
        raise HTTPException(409, detail="required_tumor_sample_missing_anatomical_run_blocked")
    measurement = load_usable_measurement(c, i, p, u, target.baseline_measurement_id)
    checked = check_family_realized(
        run.config,
        target.output.tumor_targets,
        [
            Decimal(point.target_mm3) if point.target_mm3 is not None else None
            for point in observed.tumor_targets
        ],
        Decimal(measurement.values.exact_volume_mm3),
    )
    if not checked.ordering_valid:
        raise HTTPException(409, detail="sampled_tumor_course_violates_family_revise_sampling")
    targets = []
    for point in observed.tumor_targets:
        assert point.target_mm3 is not None
        targets.append(
            TumorTarget(
                slot_id=point.slot_id, relative_day=point.relative_day, target_mm3=point.target_mm3
            )
        )
    return targets


def preview_config_schedule(c, i, p, u, identifier):
    from decimal import Decimal

    from canceros.scenario_families import build_registry

    authorize_project(i, p, "admin")
    draft = read_config(c, i, p, u, identifier)
    _usable(c, i, p, u, draft.id)
    branch = read_branch(c, i, p, u, draft.branch_id)
    measurement = load_usable_measurement(c, i, p, u, branch.input.baseline_measurement_id)
    try:
        output = build_registry().generate(
            draft.config, Decimal(measurement.values.exact_volume_mm3)
        )
    except ValueError as error:
        raise HTTPException(409, detail=str(error)) from None
    return _sample(draft.config, output)


def _sample(config, output) -> SampledObservations:
    try:
        return sample_observations(config, output)
    except ValueError as error:
        raise HTTPException(409, detail=str(error)) from None


def _prior(c, i, p, u, table, key, value, model):
    fingerprint = science_hash(value.model_dump(mode="json"))
    row = c.execute(
        text(
            f"SELECT id,input_hash,report FROM imaging.{table} WHERE project_id=:p AND patient_id=:u AND actor_id=:a AND command_key=:k"
        ),
        {"p": p, "u": u, "a": i.user_id, "k": key},
    ).one_or_none()
    if row:
        prior_report = _read(c, i, p, u, table, row.id, model)
        if row.input_hash != fingerprint:
            legacy_equal = (
                table == "simulation_config_versions"
                and value.expected_draft_revision == prior_report.draft_revision - 1
                and value.config == prior_report.config
                and science_hash(
                    {
                        "expected_draft_revision": prior_report.draft_revision - 1,
                        "config": row.report["config"],
                    }
                )
                == row.input_hash
                and science_hash(row.report["config"]) == prior_report.config_hash
            )
            if table == "generated_clinical_batches" and not value.include_tumor_observations:
                legacy_equal = (
                    value.run_id == prior_report.run_id
                    and value.expected_config_hash == prior_report.config_hash
                    and science_hash(
                        {
                            "run_id": str(value.run_id),
                            "expected_config_hash": value.expected_config_hash,
                        }
                    )
                    == row.input_hash
                )
            if not legacy_equal:
                raise HTTPException(409, detail="idempotency_key_payload_conflict")
        _usable(c, i, p, u, row.id)
        return prior_report, fingerprint
    return None, fingerprint


def _store(c, i, p, u, table, report, key, fingerprint, parents, extra):
    values = {
        "id": report.id,
        "project_id": p,
        "patient_id": u,
        "branch_id": report.branch_id,
        "actor_id": i.user_id,
        "command_key": key,
        "input_hash": fingerprint,
        "report": report.model_dump_json(),
        "report_hash": science_hash(report.model_dump(mode="json")),
        **extra,
    }
    c.execute(
        text(
            f"INSERT INTO imaging.{table}({','.join(values)}) VALUES({','.join('CAST(:' + k + ' AS jsonb)' if k in ('report', 'input_manifest') else ':' + k for k in values)})"
        ),
        values,
    )
    derive_resource(
        c,
        i,
        p,
        u,
        report.id,
        table,
        values["report_hash"],
        sorted(set(parents), key=str),
        processing_spec(
            __file__, "simulation-runs/1", "simulation-config/1", {"request_sha256": fingerprint}
        ),
    )
    audit(c, p, report.id, table.upper() + "_RECORDED")


def _baseline(c, i, p, u, value, storage):
    branch = read_branch(c, i, p, u, value.branch_id)
    _usable(c, i, p, u, branch.id)
    if value.baseline_hash != branch.baseline_hash:
        raise HTTPException(409, detail="branch_baseline_hash_mismatch")
    load_usable_measurement(c, i, p, u, branch.input.baseline_measurement_id)
    parents = [branch.id]
    if value.baseline_state_id:
        baseline = read_state(c, i, p, u, value.baseline_state_id)
        if (
            baseline.snapshot.branch_id != branch.id
            or baseline.snapshot.baseline_hash != branch.baseline_hash
            or baseline.snapshot.time.value != "0"
            or baseline.stale
        ):
            raise HTTPException(409, detail="baseline_state_pin_mismatch")
        _usable(c, i, p, u, baseline.snapshot.id)
        parents.append(baseline.snapshot.id)
    try:
        manifest = load_revision(c, p, u, value.input_revision)
    except (LookupError, ValueError):
        raise HTTPException(409, detail="simulation_input_revision_unavailable") from None
    return parents, manifest


def _head(c, p, u, branch):
    return c.execute(
        text(
            "SELECT COALESCE(max(draft_revision),0) FROM imaging.simulation_config_versions WHERE project_id=:p AND patient_id=:u AND branch_id=:b"
        ),
        {"p": p, "u": u, "b": branch},
    ).scalar_one()


def save_config(c, i, p, u, branch_id, value, storage, key, settings):
    _write(c, i, p, u)
    if value.config.branch_id != branch_id:
        raise HTTPException(409, detail="configuration_branch_mismatch")
    prior, fingerprint = _prior(c, i, p, u, "simulation_config_versions", key, value, ConfigVersion)
    if prior:
        return prior
    parents, _ = _baseline(c, i, p, u, value.config, storage)
    head = _head(c, p, u, branch_id)
    if head != value.expected_draft_revision:
        raise HTTPException(409, detail="simulation_draft_changed_reload_before_edit")
    actions: list[Literal["edit_draft", "inspect_baseline", "freeze_isolated_test_run"]] = [
        "edit_draft",
        "inspect_baseline",
    ]
    if settings.mode == "test":
        actions.append("freeze_isolated_test_run")
    report = ConfigVersion(
        id=uuid4(),
        branch_id=branch_id,
        draft_revision=head + 1,
        config=value.config,
        config_hash=science_hash(value.config.model_dump(mode="json")),
        summary=ConfigSummary(
            available_actions=actions,
            blocking_reasons=[
                "authentic_observed_baseline_review_missing",
                "reviewed_scientific_policy_missing",
            ],
        ),
    )
    _store(
        c,
        i,
        p,
        u,
        "simulation_config_versions",
        report,
        key,
        fingerprint,
        parents,
        {"draft_revision": report.draft_revision},
    )
    return report


def runtime_identity():
    root = Path(__file__).parent
    names = (
        "simulation_contracts.py",
        "simulation_plugins.py",
        "simulation_runs.py",
        "simulation_eligibility.py",
        "eligibility_checks.py",
        "scenario_families.py",
        "clinical_generation.py",
        "clinical_generation_runs.py",
        "clinical_validation.py",
        "sampling.py",
        "simulation_execution.py",
        "simulation_validation.py",
        "contracts.py",
        "clinical_contracts.py",
        "imaging_geometry.py",
        "physical_measurements.py",
        "measurement_runs.py",
        "mesh_reconstruction.py",
        "mesh_quality.py",
        "synthetic_geometry.py",
        "synthetic_shape.py",
        "twin_states.py",
    )
    digest = hashlib.sha256()
    for name in names:
        digest.update(name.encode())
        digest.update((root / name).read_bytes())
    return RuntimeIdentity(
        python=platform.python_version(),
        system=platform.system(),
        machine=platform.machine(),
        numpy=version("numpy"),
        pydantic=version("pydantic"),
        code_hash=digest.hexdigest(),
        dependency_lock_hash=hashlib.sha256((root.parents[1] / "uv.lock").read_bytes()).hexdigest(),
    )


def queue_run(c, i, p, u, branch_id, value, storage, key, settings):
    _write(c, i, p, u)
    if settings.mode != "test":
        raise HTTPException(409, detail="authentic_baseline_and_reviewed_policy_required")
    prior, fingerprint = _prior(c, i, p, u, "simulation_runs", key, value, SimulationRun)
    if prior:
        if prior.branch_id != branch_id:
            raise HTTPException(409)
        return prior
    draft = read_config(c, i, p, u, value.config_id)
    _usable(c, i, p, u, draft.id)
    if (
        draft.branch_id != branch_id
        or draft.config_hash != value.expected_config_hash
        or draft.draft_revision != value.expected_draft_revision
        or _head(c, p, u, branch_id) != value.expected_draft_revision
    ):
        raise HTTPException(409, detail="simulation_config_changed_reload_before_queue")
    revision = c.execute(
        text("SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"),
        {"p": p, "u": u},
    ).scalar_one()
    if revision != draft.config.input_revision:
        raise HTTPException(409, detail="patient_revision_changed_create_new_config_version")
    if science_hash(draft.config.model_dump(mode="json")) != draft.config_hash:
        raise HTTPException(409, detail="configuration_schema_changed_create_new_draft_version")
    parents, manifest = _baseline(c, i, p, u, draft.config, storage)
    from canceros.eligibility_checks import evaluate_config

    eligibility, _, _ = evaluate_config(c, i, p, u, draft.config, config_id=draft.id)
    report = SimulationRun(
        id=uuid4(),
        branch_id=branch_id,
        config_id=draft.id,
        config=draft.config,
        config_hash=draft.config_hash,
        input_revision=revision,
        input_manifest_hash=science_hash(manifest),
        association_head=c.execute(
            text(
                "SELECT COALESCE(max(sequence),0) FROM imaging.lesion_association_events WHERE project_id=:p AND patient_id=:u"
            ),
            {"p": p, "u": u},
        ).scalar_one(),
        environment=runtime_identity(),
        eligibility=eligibility,
        queued_at=datetime.now(timezone.utc),
    )
    _store(
        c,
        i,
        p,
        u,
        "simulation_runs",
        report,
        key,
        fingerprint,
        parents + [draft.id],
        {
            "config_id": draft.id,
            "input_revision": revision,
            "input_manifest": json.dumps(manifest),
            "input_manifest_hash": science_hash(manifest),
        },
    )
    return report
