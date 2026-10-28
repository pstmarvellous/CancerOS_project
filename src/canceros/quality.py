"""Capability-specific completeness; one failed modality cannot erase valid clinical data."""

from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import Field
from sqlalchemy import text

from canceros.clinical_ingestion import BatchCommand, BatchReport, validate_batch
from canceros.contracts import Contract
from canceros.identity import authorize_project
from canceros.lineage import get_resource, lock_lineage, resource_restrictions
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import load_revision, science_hash
from canceros.source_registry import SourceAction


class CapabilityQuality(Contract):
    capability: Literal[
        "clinical_display",
        "physical_measurement",
        "anatomical_mesh",
        "real_temporal_comparison",
        "synthetic_baseline",
    ]
    status: Literal["usable", "missing", "unavailable", "pending_review", "invalid", "quarantined"]
    satisfied_count: int
    required_count: int
    missing_requirements: list[str]
    resource_ids: list[UUID]
    next_action: str


class QualityRequest(Contract):
    expected_revision: Annotated[int, Field(strict=True, ge=1)]


class QualitySnapshot(Contract):
    id: UUID
    rule_version: Literal["capability-quality/1"] = "capability-quality/1"
    patient_id: UUID
    data_revision: int
    capabilities: list[CapabilityQuality]
    missing_numeric_results: int
    clinical_record_count: int
    quarantined_artifact_ids: list[UUID]
    source_revalidation: BatchReport | None = None
    scope: Literal["engineering_evidence; real_source_and_scientific_review_not_established"] = (
        "engineering_evidence; real_source_and_scientific_review_not_established"
    )


class QualityView(Contract):
    report: QualitySnapshot
    stale: bool
    next_action: str


class ReportReference(Contract):
    id: UUID


def record_technical_validation(
    connection, identity, project, patient, resource_id, status, rule_version, checks
):
    """Internal validator entry point only; no HTTP command can assert QC success."""
    authorize_patient(connection, identity, project, patient, edit=True)
    get_resource(connection, identity, project, patient, resource_id)
    validation_id = uuid4()
    import json

    connection.execute(
        text(
            "INSERT INTO source.technical_validations(id,project_id,patient_id,resource_id,status,rule_version,checks,checks_hash) VALUES(:id,:p,:u,:r,:status,:version,CAST(:checks AS jsonb),:hash)"
        ),
        {
            "id": validation_id,
            "p": project,
            "u": patient,
            "r": resource_id,
            "status": status,
            "version": rule_version,
            "checks": json.dumps(checks),
            "hash": science_hash(checks),
        },
    )
    return validation_id


def quality_inputs(connection, identity, project, patient):
    authorize_project(identity, project, "editor")
    authorize_patient(connection, identity, project, patient)
    revision = connection.execute(
        text("SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:id"),
        {"p": project, "id": patient},
    ).scalar_one()
    manifest = load_revision(connection, project, patient, revision)
    records = []
    for record_id in manifest.get("members", []):
        row = connection.execute(
            text(
                "SELECT payload,payload_hash FROM clinical.observations WHERE project_id=:p AND patient_id=:u AND id=:id"
            ),
            {"p": project, "u": patient, "id": UUID(record_id)},
        ).one_or_none()
        if row is None or science_hash(row.payload) != row.payload_hash:
            raise HTTPException(409)
        records.append(row.payload)
    resources = (
        connection.execute(
            text(
                "SELECT id,kind,origin FROM ops.resource_registry WHERE project_id=:p AND patient_id=:u ORDER BY id"
            ),
            {"p": project, "u": patient},
        )
        .mappings()
        .all()
    )
    facts = []
    for resource in resources:
        latest = (
            connection.execute(
                text(
                    "SELECT id,status,rule_version,checks,checks_hash FROM source.technical_validations WHERE project_id=:p AND patient_id=:u AND resource_id=:id ORDER BY sequence DESC LIMIT 1"
                ),
                {"p": project, "u": patient, "id": resource["id"]},
            )
            .mappings()
            .one_or_none()
        )
        if latest and science_hash(latest["checks"]) != latest["checks_hash"]:
            raise HTTPException(409)
        restrictions = resource_restrictions(
            connection, identity, project, patient, resource["id"], SourceAction.INTERNAL
        )
        qc_evidence = latest["checks"].get("qc_report_id") if latest else None
        if qc_evidence:
            restrictions.extend(
                "QC_EVIDENCE:" + reason
                for reason in resource_restrictions(
                    connection, identity, project, patient, UUID(qc_evidence), SourceAction.INTERNAL
                )
            )
        facts.append(
            {
                "id": str(resource["id"]),
                "kind": resource["kind"],
                "origin": resource["origin"],
                "qc": latest["status"] if latest else "pending",
                "validation_id": str(latest["id"]) if latest else None,
                "rule_version": latest["rule_version"] if latest else None,
                "qc_evidence_id": qc_evidence,
                "restrictions": restrictions,
            }
        )
    quarantine = (
        connection.execute(
            text(
                "SELECT DISTINCT artifact_id FROM source.ingestion_results WHERE project_id=:p AND patient_id=:u AND report->>'status'='quarantined' ORDER BY artifact_id"
            ),
            {"p": project, "u": patient},
        )
        .scalars()
        .all()
    )
    adapter_quarantine = (
        connection.execute(
            text(
                "SELECT input_artifact_id FROM source.adapter_runs WHERE project_id=:p AND patient_id=:u AND report->>'status'='quarantined' ORDER BY input_artifact_id"
            ),
            {"p": project, "u": patient},
        )
        .scalars()
        .all()
    )
    data = {
        "rule_version": "capability-quality/1",
        "revision": revision,
        "manifest": manifest,
        "facts": facts,
        "quarantine": sorted(str(v) for v in set(quarantine) | set(adapter_quarantine)),
    }
    return data, records


def evaluate_capabilities(patient, inputs, records):
    facts = inputs["facts"]
    member_ids = set(inputs["manifest"].get("members", []))
    clinical_facts = [
        fact
        for fact in facts
        if fact["id"] in member_ids and fact["kind"] == "clinical_observation"
    ]
    display_allowed = any(not fact["restrictions"] for fact in clinical_facts)
    clinical_missing = []
    if not records:
        clinical_missing.append("accepted_clinical_records")
    if not display_allowed:
        clinical_missing.append("current_source_access")
    capabilities = [
        CapabilityQuality(
            capability="clinical_display",
            status="usable"
            if not clinical_missing
            else "quarantined"
            if not records and inputs["quarantine"]
            else "missing"
            if not records
            else "unavailable",
            satisfied_count=2 - len(clinical_missing),
            required_count=2,
            missing_requirements=clinical_missing,
            resource_ids=[UUID(fact["id"]) for fact in clinical_facts if not fact["restrictions"]],
            next_action="Display available engineering records with source/missingness labels; publication stays separate"
            if not clinical_missing
            else "Accept source-supported records and resolve current source permissions",
        )
    ]
    definitions = [
        (
            "physical_measurement",
            ["imaging_volume", "segmentation"],
            ["validated_physical_grid", "validated_label_mask", "annotation_meaning_review"],
        ),
        (
            "anatomical_mesh",
            ["physical_measurement", "mesh"],
            ["eligible_anatomical_measurement", "validated_mesh", "anatomical_annotation_review"],
        ),
        (
            "real_temporal_comparison",
            ["imaging_volume"],
            ["two_genuine_exams", "reviewed_lesion_correspondence", "comparable_definitions"],
        ),
        (
            "synthetic_baseline",
            ["segmentation"],
            [
                "immutable_observed_baseline",
                "eligible_anatomical_mask",
                "reviewed_source_derivative_rights",
            ],
        ),
    ]
    for capability_name, kinds, requirements in definitions:
        relevant = [fact for fact in facts if fact["kind"] in kinds]
        failed = [fact for fact in relevant if fact["qc"] == "fail"]
        restricted = [fact for fact in relevant if fact["restrictions"]]
        status = (
            "invalid"
            if failed
            else "unavailable"
            if restricted
            else "pending_review"
            if relevant
            else "missing"
        )

        # Later domain validators supply technical facts; no unimplemented clinical review can be inferred here.
        def passed(kind):
            prefixes = {
                "imaging_volume": "geometry/",
                "segmentation": "segmentation-qc/",
                "physical_measurement": "physical-measurements/",
                "mesh": "mesh-qc/",
            }
            return any(
                fact["kind"] == kind
                and fact["qc"] == "pass"
                and not fact["restrictions"]
                and (fact["rule_version"] or "").startswith(prefixes[kind])
                for fact in relevant
            )

        predicates = {
            "physical_measurement": [passed("imaging_volume"), passed("segmentation"), False],
            "anatomical_mesh": [passed("physical_measurement"), passed("mesh"), False],
            "real_temporal_comparison": [False, False, False],
            "synthetic_baseline": [False, passed("segmentation"), False],
        }[capability_name]
        satisfied = sum(predicates)
        capabilities.append(
            CapabilityQuality.model_validate(
                {
                    "capability": capability_name,
                    "status": status,
                    "satisfied_count": satisfied,
                    "required_count": len(requirements),
                    "missing_requirements": [
                        requirement
                        for requirement, complete in zip(requirements, predicates)
                        if not complete
                    ],
                    "resource_ids": [fact["id"] for fact in relevant],
                    "next_action": "Resolve failed artifact QC; valid clinical records remain independently usable"
                    if failed
                    else "Supply the named source/domain evidence and qualified review before enabling this capability",
                }
            )
        )
    return capabilities


def create_quality_report(
    connection, identity, project, patient, expected_revision, source_validation=None
):
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    inputs, records = quality_inputs(connection, identity, project, patient)
    if inputs["revision"] != expected_revision:
        raise HTTPException(409)
    report = QualitySnapshot(
        id=uuid4(),
        patient_id=patient,
        data_revision=expected_revision,
        capabilities=evaluate_capabilities(patient, inputs, records),
        missing_numeric_results=sum(
            record["item"].get("result", {}).get("form") == "missing" for record in records
        ),
        clinical_record_count=len(records),
        quarantined_artifact_ids=[UUID(v) for v in inputs["quarantine"]],
        source_revalidation=source_validation,
    )
    connection.execute(
        text(
            "INSERT INTO source.quality_reports(id,project_id,patient_id,revision,input_hash,report,report_hash,recorded_by) VALUES(:id,:p,:u,:rev,:hash,CAST(:report AS jsonb),:rh,:actor)"
        ),
        {
            "id": report.id,
            "p": project,
            "u": patient,
            "rev": expected_revision,
            "hash": science_hash(inputs),
            "report": report.model_dump_json(),
            "rh": science_hash(report.model_dump(mode="json")),
            "actor": identity.user_id,
        },
    )
    audit(connection, project, report.id, "QUALITY_REVALIDATED")
    return ReportReference(id=report.id)


def revalidate_source(connection, identity, project, patient, command: BatchCommand, storage):
    report, _ = validate_batch(connection, identity, project, patient, command, storage)
    return create_quality_report(
        connection, identity, project, patient, command.expected_revision, report
    )


def read_quality_report(connection, identity, project, patient, report_id):
    inputs, _ = quality_inputs(connection, identity, project, patient)
    row = connection.execute(
        text(
            "SELECT input_hash,report,report_hash FROM source.quality_reports WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": report_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.report) != row.report_hash:
        raise HTTPException(409)
    stale = science_hash(inputs) != row.input_hash
    return QualityView(
        report=QualitySnapshot.model_validate(row.report),
        stale=stale,
        next_action="Run a new revalidation for changed source/QC/revision evidence"
        if stale
        else "Inspect capability-specific missing evidence; do not infer overall clinical readiness",
    )
