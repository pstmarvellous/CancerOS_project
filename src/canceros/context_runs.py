"""Snapshot-bound immutable interpretation context; no generation or export."""

import hashlib
import json
from uuid import UUID

from fastapi import HTTPException

from canceros.context_contracts import (
    ContextAssertion,
    ContextBuildInput,
    ContextMeasurement,
    ContextPassage,
    InterpretationContext,
)
from canceros.evidence_runs import read_current_corpus, read_passage
from canceros.identity import authorize_project
from canceros.note_extraction import protected_fact_text
from canceros.note_runs import _load_input, read_extraction
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import canonical_bytes, science_hash
from canceros.state_fusion import FusionMember, fuse_state
from canceros.temporal_trends import PointComparison
from canceros.twin_states import read_state

CONTEXT_VERSION: str = "interpretation-context/1"
LOCAL_ONLY_FIELDS = (
    "source maps",
    "signed URLs",
    "storage credentials",
    "restricted note text",
    "private linkage keys",
)


def _measurement(member: FusionMember) -> ContextMeasurement | None:
    if member.numeric_result is None or member.numeric_result.form != "exact":
        return None
    quantity = member.numeric_result.quantity
    return ContextMeasurement(
        reference_id=member.id,
        metric_code=member.metric_definition or member.concept,
        value=quantity.value,
        unit=quantity.unit,
        member_time=member.time.reference.model_dump(mode="json").get("basis", "unknown")
        if member.time is not None
        else "unknown",
        origin=str(member.origin.value if hasattr(member.origin, "value") else member.origin),
        context=str(member.context.value if hasattr(member.context, "value") else member.context),
    )


def build_context(
    c,
    i,
    p: UUID,
    u: UUID,
    value: ContextBuildInput,
    comparisons: list[PointComparison] | None = None,
    storage=None,
) -> InterpretationContext:
    authorize_project(i, p, "viewer")
    authorize_patient(c, i, p, u)
    if value.patient_id != u:
        raise HTTPException(404)
    view = read_state(c, i, p, u, value.snapshot_id)
    if value.expected_snapshot_hash is not None and value.expected_snapshot_hash != view.snapshot_hash:
        raise HTTPException(409)
    comparison_stale: bool | None = None
    if value.comparison_snapshot_id is not None:
        if value.comparison_snapshot_id == value.snapshot_id:
            raise HTTPException(422)
        comparison = read_state(c, i, p, u, value.comparison_snapshot_id)
        if comparison.snapshot.branch_id != view.snapshot.branch_id:
            raise HTTPException(409)
        comparison_stale = comparison.stale
    report = fuse_state(view, comparisons)
    measurements: list[ContextMeasurement] = []
    omitted: list[str] = []
    critical = [m for m in report.tumor_state + report.clinical_indicators if m.primary_for_display]
    for member in critical:
        projected = _measurement(member)
        if projected is not None:
            measurements.append(projected)
    budget = max(0, value.max_items)
    if len(measurements) > budget:
        raise HTTPException(409)
    assertions: list[ContextAssertion] = []
    for extraction_id in dict.fromkeys(value.note_extraction_ids):
        try:
            extraction = read_extraction(c, i, p, u, extraction_id)
            note = _load_input(c, i, p, u, extraction.report.note_id, storage)
        except HTTPException:
            raise HTTPException(409) from None
        for index, fact in enumerate(extraction.report.facts):
            if len(measurements) + len(assertions) + len(report.treatment_history) >= budget:
                omitted.append(f"note_extraction:{extraction_id}:fact:{index}:budget")
                continue
            try:
                _, assertion_text = protected_fact_text(note, fact)
            except ValueError:
                raise HTTPException(409) from None
            assertions.append(
                ContextAssertion(
                    reference_id=extraction_id,
                    concept=fact.concept,
                    excerpt=assertion_text[:1000],
                    certainty=fact.certainty,
                    negated=fact.negated,
                    source_note_id=extraction.report.note_id,
                    source_hash=extraction.report.normalized_text_sha256,
                )
            )
    passages: list[ContextPassage] = []
    corpus_id = value.retrieval_corpus_id
    if value.retrieval_passage_ids:
        if corpus_id is None:
            raise HTTPException(422)
        head = read_current_corpus(c, i, p)
        if head.status != "active" or head.corpus_id != corpus_id:
            raise HTTPException(409)
        for passage_id in dict.fromkeys(value.retrieval_passage_ids):
            try:
                passage = read_passage(c, i, p, corpus_id, passage_id)
            except HTTPException:
                raise HTTPException(409) from None
            if len(measurements) + len(assertions) + len(passages) >= budget:
                omitted.append(f"passage:{passage_id}:budget")
                continue
            passages.append(
                ContextPassage(
                    passage_id=passage.descriptor.id,
                    document_id=passage.document_id,
                    corpus_id=corpus_id,
                    excerpt=passage.excerpt,
                    locator=f"{passage.descriptor.locator_kind}:{passage.descriptor.span.start}-{passage.descriptor.span.end}:{passage.descriptor.text_sha256[:16]}",
                )
            )
    missing = list(dict.fromkeys([b.reasons for b in report.blocks for r in [b] for r in []])) or []
    missing_modalities = sorted(
        {reason for block in report.blocks for reason in block.reasons if "missing" in reason.lower()}
    )
    conflicts = sorted({conflict.reason for conflict in report.conflicts})
    payload = {
        "schema_version": CONTEXT_VERSION,
        "patient_id": str(u),
        "branch_id": str(view.snapshot.branch_id),
        "snapshot_id": str(value.snapshot_id),
        "snapshot_hash": view.snapshot_hash,
        "purpose": value.purpose,
        "comparison_snapshot_id": str(value.comparison_snapshot_id)
        if value.comparison_snapshot_id
        else None,
        "measurements": [m.model_dump(mode="json") for m in measurements],
        "assertions": [a.model_dump(mode="json") for a in assertions],
        "passages": [g.model_dump(mode="json") for g in passages],
        "omitted": sorted(omitted),
    }
    payload_hash = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    context_hash = science_hash(
        {
            "schema_version": CONTEXT_VERSION,
            "snapshot_hash": view.snapshot_hash,
            "comparison": payload["comparison_snapshot_id"],
            "measurement_ids": sorted(str(m.reference_id) for m in measurements),
            "assertion_refs": sorted(str(a.reference_id) for a in assertions),
            "passage_ids": sorted(str(g.passage_id) for g in passages),
        }
    )
    if critical and not measurements and not assertions and not passages:
        status_action = "narrow_scope_or_request_curator_review"
    elif omitted:
        status_action = "review_omissions_before_generation"
    else:
        status_action = "proceed_to_bounded_generation_review"
    _ = (missing, storage)
    return InterpretationContext(
        patient_id=u,
        branch_id=view.snapshot.branch_id,
        snapshot_id=value.snapshot_id,
        snapshot_hash=view.snapshot_hash,
        purpose=value.purpose,
        stale=view.stale,
        comparison_snapshot_id=value.comparison_snapshot_id,
        comparison_stale=comparison_stale,
        measurements=tuple(measurements),
        assertions=tuple(assertions),
        passages=tuple(passages),
        treatment_history=tuple(f"history:{m.concept}:{m.id}" for m in report.treatment_history[:10]),
        missing_modalities=tuple(missing_modalities[:20]),
        conflicts=tuple(conflicts[:20]),
        omitted=tuple(sorted(omitted)[:20]),
        context_hash=context_hash,
        payload_hash=payload_hash,
        exportable=False,
        next_action=status_action,
    )


def context_export_view(context: InterpretationContext) -> dict:
    return {
        "schema_version": "provider-input/1",
        "purpose": context.purpose,
        "input_snapshot_hash": context.snapshot_hash,
        "measurements": [
            {
                "reference_id": str(m.reference_id),
                "metric_code": m.metric_code,
                "value": m.value,
                "unit": m.unit,
                "provenance": "SYNTHETIC_GENERATED",
            }
            for m in context.measurements
        ],
        "missingness": list(context.missing_modalities),
        "evidence_ids": [str(g.passage_id) for g in context.passages],
        "excluded_local_only_fields": list(LOCAL_ONLY_FIELDS),
    }


def record_context_build(c, p: UUID, context: InterpretationContext) -> None:
    audit(c, p, context.snapshot_id, "INTERPRETATION_CONTEXT_BUILT")
    _ = json.dumps(context.model_dump(mode="json"), sort_keys=True)
