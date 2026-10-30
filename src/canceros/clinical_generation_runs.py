"""Private immutable generated records; source patient revisions are never edited."""

from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from canceros.clinical_generation import (
    ClinicalBatch,
    generate_clinical,
    materialize_measurement_only,
)
from canceros.contracts import Contract, Hash
from canceros.identity import authorize_project
from canceros.lineage import lock_lineage
from canceros.patient_linkage import authorize_patient
from canceros.simulation_runs import _prior, _read, _store, _usable, read_run, read_run_targets


class ClinicalGenerationInput(Contract):
    run_id: UUID
    expected_config_hash: Hash
    include_tumor_observations: bool = False


class ClinicalGenerationReport(Contract):
    id: UUID
    branch_id: UUID
    run_id: UUID
    config_hash: Hash
    input_revision: int
    batch: ClinicalBatch
    status: Literal["ready"] = "ready"
    scientific_review: Literal["pending"] = "pending"
    publication: Literal["draft"] = "draft"
    baseline_values: Literal["unchanged_unavailable_values_remain_unknown"] = (
        "unchanged_unavailable_values_remain_unknown"
    )
    next_action: str = (
        "Validate the complete run; generated records are hypothetical research observations"
    )


def read_clinical_batch(c, i, p, u, identifier):
    authorize_project(i, p, "admin")
    report = _read(c, i, p, u, "generated_clinical_batches", identifier, ClinicalGenerationReport)
    _usable(c, i, p, u, report.id)
    return report


def materialize_clinical(c, i, p, u, value, storage, key, settings):
    authorize_project(i, p, "admin")
    authorize_patient(c, i, p, u, edit=True)
    lock_lineage(c, p, u)
    if settings.mode != "test":
        raise HTTPException(409, detail="authentic_baseline_and_reviewed_policy_required")
    prior, fingerprint = _prior(
        c, i, p, u, "generated_clinical_batches", key, value, ClinicalGenerationReport
    )
    if prior:
        return prior
    run = read_run(c, i, p, u, value.run_id)
    _usable(c, i, p, u, run.id)
    if run.config_hash != value.expected_config_hash:
        raise HTTPException(409, detail="frozen_config_hash_mismatch")
    existing = c.execute(
        text(
            "SELECT id FROM imaging.generated_clinical_batches WHERE project_id=:p AND patient_id=:u AND run_id=:r"
        ),
        {"p": p, "u": u, "r": run.id},
    ).scalar_one_or_none()
    if existing:
        return read_clinical_batch(c, i, p, u, existing)
    target = read_run_targets(c, i, p, u, run.id)
    try:
        generator = (
            materialize_measurement_only if value.include_tumor_observations else generate_clinical
        )
        batch = generator(run.config, target.output, run.id)
    except ValueError as error:
        raise HTTPException(409, detail=str(error)) from None
    report = ClinicalGenerationReport(
        id=uuid4(),
        branch_id=run.branch_id,
        run_id=run.id,
        config_hash=run.config_hash,
        input_revision=run.input_revision,
        batch=batch,
    )
    _store(
        c,
        i,
        p,
        u,
        "generated_clinical_batches",
        report,
        key,
        fingerprint,
        [run.id, run.config_id],
        {"run_id": run.id},
    )
    return report
