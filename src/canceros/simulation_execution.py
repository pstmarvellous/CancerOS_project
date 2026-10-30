"""Compose private engineering runs on existing workers and atomically publish complete manifests."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import AwareDatetime
from sqlalchemy import text

from canceros.clinical_generation_runs import (
    ClinicalGenerationInput,
    materialize_clinical,
    read_clinical_batch,
)
from canceros.contracts import Contract, Hash, RelativeTime
from canceros.eligibility_checks import evaluate_config
from canceros.measurement_runs import load_usable_measurement
from canceros.simulation_runs import (
    _prior,
    _read,
    _store,
    _usable,
    _write,
    read_run,
    read_run_sampling,
    read_run_targets,
    runtime_identity,
)
from canceros.simulation_validation import (
    CompleteValidationReport,
    RealizedGeometryEvidence,
    validate_complete_run,
)
from canceros.synthetic_geometry import GeometryInput, generate_geometry, read_geometry_result
from canceros.twin_states import (
    GeneratedClinicalMember,
    GeneratedGeometryMember,
    ImagingMember,
    StateBuildInput,
    build_state,
    publish_complete_run_states,
    read_branch,
    read_state,
)

CompletionStage = Literal[
    "eligibility", "sampling", "clinical", "geometry", "states", "validation", "complete"
]


class CompleteRunInput(ClinicalGenerationInput):
    pass


class CompletionReport(Contract):
    id: UUID
    branch_id: UUID
    run_id: UUID
    config_hash: Hash
    input_revision: int
    association_head: int
    baseline_measurement_id: UUID
    baseline_state_id: UUID | None
    status: Literal["ready", "blocked"]
    stage: CompletionStage
    failure_reason: str | None
    clinical_batch_id: UUID | None
    geometry_result_ids: list[UUID]
    state_ids: list[UUID]
    validation: CompleteValidationReport | None
    started_at: AwareDatetime
    completed_at: AwareDatetime
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    scientific_review: Literal["pending"] = "pending"
    publication: Literal["draft"] = "draft"
    next_action: str


class PublishRunInput(Contract):
    expected_config_hash: Hash
    expected_patient_revision: int
    expected_association_head: int
    expected_current_run_id: UUID | None
    engineering_attestation_sha256: Hash


class RunPublication(Contract):
    id: UUID
    branch_id: UUID
    run_id: UUID
    completion_id: UUID
    input: PublishRunInput
    state_publication_ids: list[UUID]
    recorded_at: AwareDatetime
    scope: Literal["private_engineering_fixture"] = "private_engineering_fixture"
    scientific_review: Literal["pending"] = "pending"


class CurrentRunView(Contract):
    branch_id: UUID
    publication: RunPublication | None
    current_use_allowed: bool
    restrictions: list[str]
    next_action: str


def utc_now():
    return datetime.now(timezone.utc)


def read_completion(c, i, p, u, identifier):
    _write(c, i, p, u)
    report = _read(c, i, p, u, "simulation_completions", identifier, CompletionReport)
    _usable(c, i, p, u, report.id)
    return report


def _current_pins(c, p, u):
    revision = c.execute(
        text("SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"),
        {"p": p, "u": u},
    ).scalar_one()
    head = c.execute(
        text(
            "SELECT COALESCE(max(sequence),0) FROM imaging.lesion_association_events WHERE project_id=:p AND patient_id=:u"
        ),
        {"p": p, "u": u},
    ).scalar_one()
    return revision, head


def _geometry_evidence(c, i, p, u, run, sampling, results):
    if run.config.geometry_policy == "none":
        if results:
            raise HTTPException(409, detail="measurement_only_run_cannot_claim_geometry")
        return []
    evidence = []
    for point, result in zip(sampling.tumor_targets, results, strict=True):
        g = result.geometry
        for resource in [result.id, g.mask_artifact_id, g.mesh_artifact_id]:
            if resource:
                _usable(c, i, p, u, resource)
        measured = g.shape.realized_values
        if result.status not in ("ready", "zero") or measured is None:
            raise HTTPException(409, detail="geometry_realization_or_mesh_qc_failed")
        mask_hash = c.execute(
            text(
                "SELECT sha256 FROM ops.artifacts WHERE project_id=:p AND patient_id=:u AND id=:id"
            ),
            {"p": p, "u": u, "id": g.mask_artifact_id},
        ).scalar_one()
        evidence.append(
            RealizedGeometryEvidence(
                slot_id=point.slot_id,
                branch_id=run.branch_id,
                relative_day=g.time.value,
                geometry_id=g.id,
                mask_sha256=mask_hash,
                actual_mm3=measured.exact_volume_mm3,
                target_mm3=g.shape.target_mm3,
                voxel_mm3=g.grid_geometry.voxel_volume_mm3,
                technical_qc_valid=result.status == "zero"
                or bool(g.mesh_qc and g.mesh_qc.display_allowed),
            )
        )
    return evidence


def complete_run(c, i, p, u, value, storage, key, settings):
    _write(c, i, p, u)
    if settings.mode != "test":
        raise HTTPException(409, detail="authentic_baseline_and_reviewed_policy_required")
    prior, fingerprint = _prior(c, i, p, u, "simulation_completions", key, value, CompletionReport)
    if prior:
        return prior
    run = read_run(c, i, p, u, value.run_id)
    _usable(c, i, p, u, run.id)
    if run.config_hash != value.expected_config_hash or run.environment != runtime_identity():
        raise HTTPException(409, detail="frozen_config_or_environment_changed")
    branch = read_branch(c, i, p, u, run.branch_id)
    started = utc_now()
    stage: CompletionStage = "eligibility"
    batch, geometry, states, validation, failure = None, [], [], None, None
    try:
        with c.begin_nested():
            if _current_pins(c, p, u) != (run.input_revision, run.association_head):
                raise HTTPException(409, detail="captured_revision_or_association_head_changed")
            # The isolated engineering authority does not change this negative scientific gate.
            evaluate_config(c, i, p, u, run.config, config_id=run.config_id)
            output = read_run_targets(c, i, p, u, run.id).output
            stage = "sampling"
            sampling = read_run_sampling(c, i, p, u, run.id)
            stage = "clinical"
            clinical_input = ClinicalGenerationInput(
                run_id=run.id,
                expected_config_hash=run.config_hash,
                include_tumor_observations=run.config.geometry_policy == "none",
            )
            batch = materialize_clinical(
                c, i, p, u, clinical_input, storage, "complete-clinical-" + str(run.id), settings
            )
            stage = "geometry"
            if run.config.geometry_policy != "none":
                for index in range(len(sampling.tumor_targets)):
                    result = generate_geometry(
                        c,
                        i,
                        p,
                        u,
                        GeometryInput(
                            run_id=run.id, baseline_hash=branch.baseline_hash, target_index=index
                        ),
                        storage,
                        f"complete-geometry-{run.id}-{index}",
                        settings,
                    )
                    geometry.append(result)
                    if result.status == "blocked":
                        raise HTTPException(409, detail="geometry_realization_or_mesh_qc_failed")
            stage = "states"
            geometry_days = {
                Decimal(result.geometry.time.value): result.geometry.id for result in geometry
            }
            event_days = {Decimal(event.relative_day) for event in batch.batch.events}
            days = sorted({Decimal(0), *geometry_days, *event_days})
            for day in days:
                selected = [
                    event.event_id
                    for event in batch.batch.events
                    if Decimal(event.relative_day) == day
                ]
                snapshot = build_state(
                    c,
                    i,
                    p,
                    u,
                    StateBuildInput(
                        target_revision=run.input_revision,
                        association_head=run.association_head,
                        branch_id=branch.id,
                        time=RelativeTime(
                            basis="relative_day",
                            value=format(day, "f"),
                            time_domain="simulation",
                            timeline_origin_id=branch.input.timeline_origin_id,
                        ),
                        imaging_members=[
                            ImagingMember(
                                measurement_id=branch.input.baseline_measurement_id,
                                role="historical_context",
                                reason="Shared engineering baseline measurement; source exam time is not invented",
                            )
                        ]
                        if day == 0
                        else [],
                        generated_geometry_members=[
                            GeneratedGeometryMember(geometry_id=geometry_days[day])
                        ]
                        if day in geometry_days
                        else [],
                        generated_clinical_members=[
                            GeneratedClinicalMember(batch_id=batch.id, event_ids=selected)
                        ]
                        if selected
                        else [],
                    ),
                    storage,
                    f"complete-state-{run.id}-{format(day, 'f')}",
                )
                states.append(snapshot.id)
            stage = "validation"
            measurement = load_usable_measurement(c, i, p, u, branch.input.baseline_measurement_id)
            validation = validate_complete_run(
                run.config,
                output,
                sampling,
                batch.batch,
                Decimal(measurement.values.exact_volume_mm3),
                _geometry_evidence(c, i, p, u, run, sampling, geometry),
            )
            if validation.status != "engineering_passed":
                raise HTTPException(409, detail="complete_run_validation_failed")
            stage = "complete"
    except (HTTPException, ValueError, LookupError) as error:
        failure = (
            error.detail
            if isinstance(error, HTTPException) and isinstance(error.detail, str)
            else "stage_input_or_validation_rejected"
        )
        # No partial derived records survive the savepoint. Private orphan objects remain unexposed.
        batch, geometry, states = None, [], []
    report = CompletionReport(
        id=uuid4(),
        branch_id=run.branch_id,
        run_id=run.id,
        config_hash=run.config_hash,
        input_revision=run.input_revision,
        association_head=run.association_head or 0,
        baseline_measurement_id=branch.input.baseline_measurement_id,
        baseline_state_id=run.config.baseline_state_id,
        status="blocked" if failure else "ready",
        stage=stage,
        failure_reason=failure,
        clinical_batch_id=batch.id if batch else None,
        geometry_result_ids=[result.id for result in geometry],
        state_ids=states,
        validation=validation,
        started_at=started,
        completed_at=utc_now(),
        next_action="Inspect the failed stage; correct the draft or dependency, then create a new attempt"
        if failure
        else "Review the complete engineering manifest and explicitly publish; scientific review remains pending",
    )
    _store(
        c,
        i,
        p,
        u,
        "simulation_completions",
        report,
        key,
        fingerprint,
        [run.id] + ([batch.id] if batch else []) + [result.id for result in geometry] + states,
        {"run_id": run.id},
    )
    return report


class _PublicationCommand(Contract):
    completion_id: UUID
    input: PublishRunInput


def publish_completion(c, i, p, u, identifier, value, storage, key, settings):
    _write(c, i, p, u)
    if settings.mode != "test":
        raise HTTPException(409, detail="authentic_baseline_and_reviewed_policy_required")
    prior, fingerprint = _prior(
        c,
        i,
        p,
        u,
        "simulation_publications",
        key,
        _PublicationCommand(completion_id=identifier, input=value),
        RunPublication,
    )
    if prior:
        return prior
    completion = read_completion(c, i, p, u, identifier)
    run = read_run(c, i, p, u, completion.run_id)
    if (
        completion.status != "ready"
        or not completion.validation
        or completion.validation.status != "engineering_passed"
        or completion.config_hash != value.expected_config_hash
        or run.environment != runtime_identity()
        or _current_pins(c, p, u)
        != (value.expected_patient_revision, value.expected_association_head)
        or (completion.input_revision, completion.association_head) != _current_pins(c, p, u)
    ):
        raise HTTPException(409, detail="complete_publication_preconditions_changed")
    current = c.execute(
        text(
            "SELECT run_id FROM imaging.simulation_current_runs WHERE project_id=:p AND patient_id=:u AND branch_id=:b FOR UPDATE"
        ),
        {"p": p, "u": u, "b": run.branch_id},
    ).scalar_one_or_none()
    if current != value.expected_current_run_id:
        raise HTTPException(409, detail="current_run_changed_reload_before_publication")
    evaluate_config(c, i, p, u, run.config, config_id=run.config_id)
    output = read_run_targets(c, i, p, u, run.id).output
    sampling = read_run_sampling(c, i, p, u, run.id)
    batch = read_clinical_batch(c, i, p, u, completion.clinical_batch_id)
    geometry = [read_geometry_result(c, i, p, u, r) for r in completion.geometry_result_ids]
    measurement = load_usable_measurement(c, i, p, u, completion.baseline_measurement_id)
    checked = validate_complete_run(
        run.config,
        output,
        sampling,
        batch.batch,
        Decimal(measurement.values.exact_volume_mm3),
        _geometry_evidence(c, i, p, u, run, sampling, geometry),
    )
    if checked != completion.validation or any(
        not read_state(c, i, p, u, s).current_use_allowed for s in completion.state_ids
    ):
        raise HTTPException(409, detail="complete_manifest_no_longer_eligible")
    published = publish_complete_run_states(
        c,
        i,
        p,
        u,
        completion.state_ids,
        run.id,
        completion.input_revision,
        completion.association_head,
        "complete-publish-" + str(identifier),
        completion_id=identifier,
    )
    report = RunPublication(
        id=uuid4(),
        branch_id=run.branch_id,
        run_id=run.id,
        completion_id=identifier,
        input=value,
        state_publication_ids=[s.id for s in published],
        recorded_at=utc_now(),
    )
    _store(
        c,
        i,
        p,
        u,
        "simulation_publications",
        report,
        key,
        fingerprint,
        [completion.id],
        {"run_id": run.id, "completion_id": completion.id},
    )
    c.execute(
        text(
            "INSERT INTO imaging.simulation_current_runs VALUES(:p,:u,:b,:r,:pub) ON CONFLICT(project_id,patient_id,branch_id) DO UPDATE SET run_id=excluded.run_id,publication_id=excluded.publication_id"
        ),
        {"p": p, "u": u, "b": run.branch_id, "r": run.id, "pub": report.id},
    )
    return report


def read_current_run(c, i, p, u, branch_id):
    _write(c, i, p, u)
    read_branch(c, i, p, u, branch_id)
    identifier = c.execute(
        text(
            "SELECT publication_id FROM imaging.simulation_current_runs WHERE project_id=:p AND patient_id=:u AND branch_id=:b"
        ),
        {"p": p, "u": u, "b": branch_id},
    ).scalar_one_or_none()
    publication = (
        _read(c, i, p, u, "simulation_publications", identifier, RunPublication)
        if identifier
        else None
    )
    restrictions = []
    if publication:
        completion = read_completion(c, i, p, u, publication.completion_id)
        if _current_pins(c, p, u) != (completion.input_revision, completion.association_head):
            restrictions.append("captured_revision_or_association_head_changed")
        for state in completion.state_ids:
            restrictions.extend(read_state(c, i, p, u, state).restrictions)
    return CurrentRunView(
        branch_id=branch_id,
        publication=publication,
        current_use_allowed=bool(publication) and not restrictions,
        restrictions=sorted(set(restrictions)),
        next_action="Inspect the published complete engineering run"
        if publication and not restrictions
        else "Review current restrictions and explicitly publish a validated complete run",
    )
