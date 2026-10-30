"""Server-resolved eligibility evidence. Submitted pathology/review assertions are never accepted."""

from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from canceros.annotation_import import read_annotation
from canceros.contracts import Contract, Hash
from canceros.identity import authorize_project
from canceros.lineage import lock_lineage, resource_restrictions
from canceros.measurement_runs import load_usable_measurement, read_measurement
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import science_hash
from canceros.simulation_eligibility import (
    EligibilityResult,
    PathologyFact,
    PureBaselineFacts,
    evaluate,
)
from canceros.source_registry import SourceAction
from canceros.twin_states import read_branch, read_state


class EligibilityCheckInput(Contract):
    config_id: UUID
    capability: Literal["measurement", "anatomical_mesh"] = "measurement"


class EligibilityReport(Contract):
    id: UUID
    config_id: UUID
    baseline_hash: Hash
    input_revision: int
    current_patient_revision: int
    result: EligibilityResult
    scope: Literal["immutable_audit_snapshot_recheck_before_execution_or_publication"] = (
        "immutable_audit_snapshot_recheck_before_execution_or_publication"
    )


def evaluate_config(c, i, p, u, config, capability="measurement", config_id=None):
    authorize_project(i, p, "admin")
    authorize_patient(c, i, p, u, edit=True)
    lock_lineage(c, p, u)
    branch = read_branch(c, i, p, u, config.branch_id)
    measurement = read_measurement(c, i, p, u, branch.input.baseline_measurement_id)
    evidence = [branch.id, measurement.id] + ([config_id] if config_id else [])
    restrictions = []
    for identifier in evidence:
        for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE):
            restrictions.extend(resource_restrictions(c, i, p, u, identifier, action))
    numeric = False
    anatomy = False
    metric = False
    try:
        usable = load_usable_measurement(c, i, p, u, measurement.id)
        metric = usable.values.availability == "available" and bool(usable.selections)
        annotations = [read_annotation(c, i, p, u, s.segmentation_id) for s in usable.selections]
        evidence.extend(annotation.id for annotation in annotations)
        numeric = all(a.capabilities.numerical_region_volume_allowed for a in annotations)
        anatomy = all(a.capabilities.anatomical_mesh_allowed for a in annotations)
    except HTTPException as error:
        if error.status_code not in (403, 409):
            raise
    revision = c.execute(
        text("SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"),
        {"p": p, "u": u},
    ).scalar_one()
    pathology: list[PathologyFact] = []
    baseline_published = False
    baseline_current = config.input_revision == revision
    if config.baseline_state_id:
        baseline = read_state(c, i, p, u, config.baseline_state_id)
        evidence.append(baseline.snapshot.id)
        restrictions.extend(baseline.restrictions)
        baseline_current = baseline_current and not baseline.stale
        # Current runtime states are engineering-only. Their private administrator
        # publication is never qualified observed-baseline scientific approval.
        for member in baseline.snapshot.clinical_members:
            record = member.record
            item = record.item
            if item.kind != "diagnosis" or member.membership.role != "current":
                continue
            evidence.append(record.id)
            if (
                record.availability != "available"
                or record.scientific_review != "approved"
                or item.certainty != "documented"
                or item.negation != "affirmed"
            ):
                continue
            pathology.extend(
                PathologyFact.model_validate(
                    {
                        "source_id": record.id,
                        "field": field,
                        "status": status,
                        "origin": record.origin,
                    }
                )
                for field, status in (
                    ("er", item.er_status),
                    ("pr", item.pr_status),
                    ("her2", item.her2_status),
                )
            )
    facts = PureBaselineFacts(
        baseline_hash=config.baseline_hash,
        observed_baseline_verified=branch.observed_baseline_verified,
        published_baseline_verified=baseline_published,
        source_rights_allowed=not restrictions,
        patient_ownership_verified=True,
        revision_current=baseline_current and config.baseline_hash == branch.baseline_hash,
        metric_valid=metric,
        annotation_numeric_eligible=numeric,
        anatomy_eligible=anatomy,
        pathology=pathology,
        evidence_ids=sorted(set(evidence), key=str),
    )
    result = evaluate(facts, config.treatment, capability=capability)
    return result, sorted(set(evidence), key=str), revision


def check_eligibility(c, i, p, u, value):
    from canceros.simulation_runs import read_config

    draft = read_config(c, i, p, u, value.config_id)
    result, _, revision = evaluate_config(c, i, p, u, draft.config, value.capability, draft.id)
    report = EligibilityReport(
        id=uuid4(),
        config_id=draft.id,
        baseline_hash=draft.config.baseline_hash,
        input_revision=draft.config.input_revision,
        current_patient_revision=revision,
        result=result,
    )
    c.execute(
        text(
            "INSERT INTO imaging.simulation_eligibility_checks(id,project_id,patient_id,config_id,actor_id,report,report_hash) VALUES(:id,:p,:u,:config,:actor,CAST(:report AS jsonb),:hash)"
        ),
        {
            "id": report.id,
            "p": p,
            "u": u,
            "config": draft.id,
            "actor": i.user_id,
            "report": report.model_dump_json(),
            "hash": science_hash(report.model_dump(mode="json")),
        },
    )
    audit(c, p, report.id, "SIMULATION_ELIGIBILITY_EVALUATED")
    return report


def read_eligibility(c, i, p, u, identifier):
    authorize_project(i, p, "admin")
    authorize_patient(c, i, p, u, edit=True)
    row = c.execute(
        text(
            "SELECT report,report_hash FROM imaging.simulation_eligibility_checks WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": p, "u": u, "id": identifier},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.report) != row.report_hash:
        raise HTTPException(409)
    return EligibilityReport.model_validate(row.report)
