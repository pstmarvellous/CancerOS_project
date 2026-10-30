"""Bounded job orchestration: context, template, gate, persist, fallback."""

from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from canceros.context_contracts import ContextBuildInput
from canceros.context_runs import build_context, record_context_build
from canceros.grounding_runs import validate_publication
from canceros.interpretation_contracts import InterpretationInput
from canceros.interpretation_jobs_contracts import InterpretationJob, InterpretationJobInput
from canceros.interpretation_runs import build_interpretation
from canceros.patient_linkage import authorize_patient
from canceros.saved_runs import fallback_label, persist_validated

JOB_VERSION: str = "interpretation-job/1"


def submit_job(c, i, p: UUID, u: UUID, value: InterpretationJobInput, key: str) -> InterpretationJob:
    authorize_patient(c, i, p, u, edit=True)
    context = build_context(
        c, i, p, u, ContextBuildInput(patient_id=u, snapshot_id=value.state_id, purpose=value.purpose)
    )
    record_context_build(c, p, context)
    if value.expected_snapshot_hash is not None and value.expected_snapshot_hash != context.snapshot_hash:
        raise HTTPException(409)
    report = build_interpretation(
        context,
        InterpretationInput(
            context_snapshot_id=context.snapshot_id,
            expected_context_hash=context.context_hash,
            mode=value.mode,
        ),
    )
    grounded = validate_publication(context, report)
    known = c.execute(
        text("SELECT id FROM intelligence.interpretation_jobs WHERE project_id=:p AND idempotency_key=:k"),
        {"p": p, "k": f"interpretation-job:{key}"},
    ).scalar_one_or_none()
    if known:
        return read_job(c, i, p, u, known)
    identifier = uuid4()
    status = (
        "validated_ready"
        if grounded.verdict == "published"
        else ("withheld_insufficient_evidence" if grounded.verdict == "withheld_insufficient_evidence" else "failed_grounding")
    )
    saved_id = None
    fallback = None
    if grounded.verdict == "published":
        saved = persist_validated(c, i, p, context, report, f"job-{key}")
        saved_id = saved.id
    else:
        fallback = fallback_label(context, "outage")["label"]
    c.execute(
        text("""INSERT INTO intelligence.interpretation_jobs(
      id,project_id,patient_id,context_snapshot_id,context_hash,snapshot_hash,
      execution_mode,visibility,status,reason_codes,finding_count,saved_id,idempotency_key)
      VALUES(:id,:p,:u,:s,:ch,:sh,:m,:v,:st,:r,:n,:saved,:k)"""),
        {
            "id": identifier,
            "p": p,
            "u": u,
            "s": context.snapshot_id,
            "ch": context.context_hash,
            "sh": context.snapshot_hash,
            "m": report.execution_mode,
            "v": report.visibility,
            "st": status,
            "r": list(grounded.reason_codes),
            "n": len(report.findings),
            "saved": saved_id,
            "k": f"interpretation-job:{key}",
        },
    )
    return InterpretationJob(
        id=identifier,
        context_snapshot_id=context.snapshot_id,
        context_hash=context.context_hash,
        snapshot_hash=context.snapshot_hash,
        execution_mode=report.execution_mode,
        visibility=report.visibility,
        status=status,  # type: ignore[arg-type]
        reason_codes=tuple(grounded.reason_codes),
        finding_count=len(report.findings),
        saved_id=saved_id,
        fallback_label=fallback,
        next_action="inspect_saved_result_or_narrow_scope"
        if status == "validated_ready"
        else grounded.next_action,
    )


def read_job(c, i, p: UUID, u: UUID, identifier: UUID) -> InterpretationJob:
    authorize_patient(c, i, p, u)
    row = (
        c.execute(
            text("SELECT * FROM intelligence.interpretation_jobs WHERE project_id=:p AND id=:id"),
            {"p": p, "id": identifier},
        )
        .mappings()
        .one_or_none()
    )
    if row is None or row["patient_id"] != u:
        raise HTTPException(404)
    return InterpretationJob(
        id=row["id"],
        context_snapshot_id=row["context_snapshot_id"],
        context_hash=row["context_hash"],
        snapshot_hash=row["snapshot_hash"],
        execution_mode=row["execution_mode"],
        visibility=row["visibility"],
        status=row["status"],
        reason_codes=tuple(row["reason_codes"] or ()),
        finding_count=row["finding_count"],
        saved_id=row["saved_id"],
        fallback_label=None,
        next_action="inspect_saved_result_or_narrow_scope"
        if row["status"] == "validated_ready"
        else "narrow_scope_or_request_curator_review",
    )


def list_jobs(c, i, p: UUID, u: UUID) -> list[InterpretationJob]:
    authorize_patient(c, i, p, u)
    ids = (
        c.execute(
            text(
                "SELECT id FROM intelligence.interpretation_jobs WHERE project_id=:p AND patient_id=:u ORDER BY id"
            ),
            {"p": p, "u": u},
        )
        .scalars()
        .all()
    )
    return [read_job(c, i, p, u, identifier) for identifier in ids]
