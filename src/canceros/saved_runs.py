"""Exact-context reuse, revalidation, withdrawal and labeled fallback."""

import re
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from canceros.context_contracts import InterpretationContext
from canceros.grounding_runs import GATE_VERSION, validate_publication
from canceros.interpretation_contracts import InterpretationInput, InterpretationReport
from canceros.interpretation_runs import TEMPLATE_VERSION, build_interpretation
from canceros.saved_runs_contracts import PersistedInterpretation, SavedResultQuery

MODEL_IDENTIFIER: str = "local-template/1"
CORPUS_MANIFEST: str = "postgres-curated-corpus/active-head"

KEY_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def _row(c, p, u, identifier):
    row = (
        c.execute(
            text("SELECT * FROM intelligence.saved_interpretations "
                 "WHERE project_id=:p AND patient_id=:u AND id=:id"),
            {"p": p, "u": u, "id": identifier},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404)
    return row


def _view(row) -> PersistedInterpretation:
    return PersistedInterpretation.model_validate(
        {
            "id": row["id"],
            "project_id": row["project_id"],
            "patient_id": row["patient_id"],
            "context_snapshot_id": row["context_snapshot_id"],
            "context_hash": row["context_hash"],
            "execution_mode": row["execution_mode"],
            "visibility": row["visibility"],
            "model_identifier": row["model_identifier"],
            "model_revision": row["model_revision"],
            "prompt_version": row["prompt_version"],
            "validator_version": row["validator_version"],
            "corpus_manifest": row["corpus_manifest"],
            "finding_count": row["finding_count"],
            "usage_tokens": row["usage_tokens"],
            "failure_stage": row["failure_stage"],
            "status": row["status"],
            "superseded_by_id": row["superseded_by_id"],
            "next_action": "inspect_saved_result_history",
        }
    )


def persist_validated(
    c, i, p: UUID, context: InterpretationContext, report: InterpretationReport, key: str
) -> PersistedInterpretation:
    if not KEY_RE.fullmatch(key):
        raise HTTPException(422)
    from canceros.identity import authorize_project
    from canceros.patient_linkage import authorize_patient

    authorize_project(i, p, "viewer")
    authorize_patient(c, i, p, context.patient_id)
    if report.context_hash != context.context_hash:
        raise HTTPException(409)
    grounded = validate_publication(context, report)
    if grounded.verdict != "published":
        raise HTTPException(422)
    known = c.execute(
        text(
            "SELECT id FROM intelligence.saved_interpretations WHERE project_id=:p AND patient_id=:u AND idempotency_key=:k"
        ),
        {"p": p, "u": context.patient_id, "k": f"saved-interpretation:{key}"},
    ).scalar_one_or_none()
    if known:
        return read_saved(c, i, p, context.patient_id, known)
    identifier = uuid4()
    c.execute(
        text("""INSERT INTO intelligence.saved_interpretations(
      id,project_id,patient_id,context_snapshot_id,context_hash,execution_mode,visibility,
      model_identifier,model_revision,prompt_version,validator_version,corpus_manifest,
      finding_count,idempotency_key,status)
      VALUES(:id,:p,:u,:s,:h,:m,:v,:model,:rev,:prompt,:gate,:corpus,:n,:k,'validated_ready')"""),
        {
            "id": identifier,
            "p": p,
            "u": context.patient_id,
            "s": context.snapshot_id,
            "h": context.context_hash,
            "m": report.execution_mode,
            "v": report.visibility,
            "model": MODEL_IDENTIFIER,
            "rev": "unresolved",
            "prompt": TEMPLATE_VERSION,
            "gate": GATE_VERSION,
            "corpus": CORPUS_MANIFEST,
            "n": len(report.findings),
            "k": f"saved-interpretation:{key}",
        },
    )
    prior = c.execute(
        text("""SELECT * FROM intelligence.saved_interpretations
      WHERE project_id=:p AND patient_id=:u AND context_snapshot_id=:s AND id<>:new AND status='validated_ready'"""),
        {"p": p, "u": context.patient_id, "s": context.snapshot_id, "new": identifier},
    ).mappings().all()
    for old in prior:
        c.execute(
            text("""INSERT INTO intelligence.saved_interpretations(
        id,project_id,patient_id,context_snapshot_id,context_hash,execution_mode,visibility,
        model_identifier,model_revision,prompt_version,validator_version,corpus_manifest,
        finding_count,idempotency_key,status,superseded_by_id)
        VALUES(:id,:p,:u,:s,:h,:m,:v,:model,:rev,:prompt,:gate,:corpus,:n,:k,'superseded',:new)"""),
            {
                "id": uuid4(),
                "p": p,
                "u": old["patient_id"],
                "s": old["context_snapshot_id"],
                "h": old["context_hash"],
                "m": old["execution_mode"],
                "v": old["visibility"],
                "model": old["model_identifier"],
                "rev": old["model_revision"],
                "prompt": old["prompt_version"],
                "gate": old["validator_version"],
                "corpus": old["corpus_manifest"],
                "n": old["finding_count"],
                "k": old["idempotency_key"] + ":superseded:" + str(identifier),
                "new": identifier,
            },
        )
    return read_saved(c, i, p, context.patient_id, identifier)


def read_saved(c, i, p: UUID, u: UUID, identifier: UUID) -> PersistedInterpretation:
    from canceros.identity import authorize_project
    from canceros.patient_linkage import authorize_patient

    authorize_project(i, p, "viewer")
    authorize_patient(c, i, p, u)
    row = _row(c, p, u, identifier)
    return _view(row)


def reuse_exact(
    c, i, p: UUID, context: InterpretationContext, query: SavedResultQuery
) -> PersistedInterpretation:
    from canceros.identity import authorize_project
    from canceros.patient_linkage import authorize_patient

    authorize_project(i, p, "viewer")
    authorize_patient(c, i, p, context.patient_id)
    if query.context_snapshot_id != context.snapshot_id:
        raise HTTPException(409)
    if query.expected_context_hash is not None and query.expected_context_hash != context.context_hash:
        raise HTTPException(409)
    row = (
        c.execute(
            text("""SELECT * FROM intelligence.saved_interpretations
        WHERE project_id=:p AND patient_id=:u AND context_snapshot_id=:s AND context_hash=:h
        AND status='validated_ready' ORDER BY built_at DESC LIMIT 1"""),
            {
                "p": p,
                "u": context.patient_id,
                "s": context.snapshot_id,
                "h": context.context_hash,
            },
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404)
    if (
        row["execution_mode"] != "rule_based_summary"
        or row["prompt_version"] != TEMPLATE_VERSION
        or row["validator_version"] != GATE_VERSION
        or row["model_identifier"] != MODEL_IDENTIFIER
    ):
        raise HTTPException(409)
    report = build_interpretation(
        context, InterpretationInput(context_snapshot_id=context.snapshot_id, mode="template")
    )
    grounded = validate_publication(context, report)
    if grounded.verdict != "published":
        raise HTTPException(409)
    return _view(row)


def fallback_label(context: InterpretationContext, reason: str) -> dict:
    if reason == "policy_refusal":
        return {
            "status": 403,
            "label": "External processing not allowed",
            "next_action": "use_local_template_or_request_policy_review",
        }
    return {
        "label": "Saved result for this snapshot"
        if reason == "exact_reuse"
        else "Rule-based fallback",
        "snapshot_hash": context.snapshot_hash,
        "stale": context.stale,
        "next_action": "retry_template_generation_or_inspect_measurements",
    }
