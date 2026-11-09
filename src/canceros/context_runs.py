"""Snapshot-bound immutable interpretation context; no generation or export."""

import hashlib
import json
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException

from canceros.context_contracts import (
    MAX_TEXT_BYTES,
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
from canceros.simulation_runs import _usable
from canceros.state_fusion import FusionMember, fuse_state
from canceros.temporal_trends import PointComparison
from canceros.twin_states import read_state

CONTEXT_VERSION: str = "interpretation-context/1"
ASSEMBLY_VERSION: str = "interpretation-context-assembly/2"
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
        member_time=_member_time(member),
        origin=str(member.origin.value if hasattr(member.origin, "value") else member.origin),
        context=str(member.context.value if hasattr(member.context, "value") else member.context),
    )


def _member_time(member: FusionMember) -> str:
    reference = member.original_time or (member.time.reference if member.time else None)
    if reference is None or reference.basis == "unknown":
        return "Unknown time"
    if reference.basis == "relative_day":
        return f"Day {reference.value} ({reference.time_domain})"
    return f"{reference.value.isoformat()} ({reference.time_domain}; {reference.basis})"


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
    _usable(c, i, p, u, value.snapshot_id)
    if (
        value.expected_snapshot_hash is not None
        and value.expected_snapshot_hash != view.snapshot_hash
    ):
        raise HTTPException(409)
    comparison_stale: bool | None = None
    comparison_measurements: list[ContextMeasurement] = []
    if value.comparison_snapshot_id is not None:
        if value.comparison_snapshot_id == value.snapshot_id:
            raise HTTPException(422)
        comparison = read_state(c, i, p, u, value.comparison_snapshot_id)
        _usable(c, i, p, u, value.comparison_snapshot_id)
        before, selected = comparison.snapshot, view.snapshot
        if (
            before.branch_id != selected.branch_id
            or before.input_revision != selected.input_revision
            or before.time.timeline_origin_id != selected.time.timeline_origin_id
            or before.time.anchor_state_id != selected.time.anchor_state_id
            or before.time.time_domain != selected.time.time_domain
            or Decimal(before.time.value) >= Decimal(selected.time.value)
        ):
            raise HTTPException(409)
        comparison_stale = comparison.stale
        previous = fuse_state(comparison)
        comparison_measurements = [
            projected
            for member in previous.tumor_state + previous.clinical_indicators
            if member.primary_for_display
            for projected in [_measurement(member)]
            if projected is not None
        ]
    report = fuse_state(view, comparisons)
    measurements: list[ContextMeasurement] = []
    omitted: list[str] = []
    critical = [m for m in report.tumor_state + report.clinical_indicators if m.primary_for_display]
    for member in critical:
        projected = _measurement(member)
        if projected is not None:
            measurements.append(projected)
    for member in report.tumor_state + report.clinical_indicators:
        if member.numeric_result is not None and (
            not member.primary_for_display or member.numeric_result.form != "exact"
        ):
            omitted.append(f"member:{member.id}:quality_time_conflict_or_nonexact_excluded")
    budget = max(0, value.max_items)
    if len(measurements) + len(comparison_measurements) > budget:
        raise HTTPException(409)
    budget -= len(comparison_measurements)
    history_budget = min(10, max(0, budget - len(measurements)))
    history = report.treatment_history[:history_budget]
    omitted.extend(
        f"treatment:{member.id}:budget" for member in report.treatment_history[history_budget:]
    )
    budget -= len(history)
    assertions: list[ContextAssertion] = []
    for extraction_id in dict.fromkeys(value.note_extraction_ids):
        try:
            extraction = read_extraction(c, i, p, u, extraction_id)
            retained_notes = {
                member.record.item.note_document_id
                for member in view.snapshot.clinical_members
                if member.record.item.kind == "note"
            }
            if extraction.report.note_id not in retained_notes:
                raise HTTPException(409)
            note = _load_input(c, i, p, u, extraction.report.note_id, storage)
            if note.branch_id is not None and note.branch_id != view.snapshot.branch_id:
                raise HTTPException(409)
        except HTTPException:
            raise HTTPException(409) from None
        for index, fact in enumerate(extraction.report.facts):
            if len(measurements) + len(assertions) >= budget:
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
        {
            reason
            for block in report.blocks
            for reason in block.reasons
            if "missing" in reason.lower()
        }
    )
    conflicts = sorted({conflict.reason for conflict in report.conflicts})
    payload = {
        "schema_version": CONTEXT_VERSION,
        "assembly_version": ASSEMBLY_VERSION,
        "patient_id": str(u),
        "branch_id": str(view.snapshot.branch_id),
        "snapshot_id": str(value.snapshot_id),
        "snapshot_hash": view.snapshot_hash,
        "purpose": value.purpose,
        "comparison_snapshot_id": str(value.comparison_snapshot_id)
        if value.comparison_snapshot_id
        else None,
        "measurements": [m.model_dump(mode="json") for m in measurements],
        "comparison_measurements": [m.model_dump(mode="json") for m in comparison_measurements],
        "assertions": [a.model_dump(mode="json") for a in assertions],
        "passages": [g.model_dump(mode="json") for g in passages],
        "treatment_history": [f"history:{m.concept}:{m.id}" for m in history],
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
            "payload_hash": payload_hash,
        }
    )
    if not measurements and not assertions and not passages:
        status_action = "narrow_scope_or_request_curator_review"
    elif omitted:
        status_action = "review_omissions_before_generation"
    else:
        status_action = "proceed_to_bounded_generation_review"
    _ = (missing, storage)
    context = InterpretationContext(
        patient_id=u,
        branch_id=view.snapshot.branch_id,
        snapshot_id=value.snapshot_id,
        snapshot_hash=view.snapshot_hash,
        purpose=value.purpose,
        stale=view.stale,
        comparison_snapshot_id=value.comparison_snapshot_id,
        comparison_stale=comparison_stale,
        measurements=tuple(measurements),
        comparison_measurements=tuple(comparison_measurements),
        assertions=tuple(assertions),
        passages=tuple(passages),
        treatment_history=tuple(f"history:{m.concept}:{m.id}" for m in history),
        missing_modalities=tuple(missing_modalities[:20]),
        conflicts=tuple(conflicts[:20]),
        omitted=tuple(sorted(omitted))
        if len(omitted) <= 20
        else tuple(sorted(omitted)[:19]) + (f"additional_omission_records:{len(omitted) - 19}",),
        context_hash=context_hash,
        payload_hash=payload_hash,
        exportable=False,
        next_action=status_action,
    )
    if len(canonical_bytes(context.model_dump(mode="json"))) > MAX_TEXT_BYTES:
        raise HTTPException(409, detail="interpretation_context_budget_exceeded_narrow_scope")
    return context


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
