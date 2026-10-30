"""Grant-scoped patient/visit/observation reads and source-backed diagnosis."""

from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import Field
from sqlalchemy import text

from canceros.contracts import Contract, Hash
from canceros.identity import authorize_project
from canceros.patient_linkage import authorize_patient
from canceros.persistence import science_hash

PATIENT_PAGE_LIMIT: int = 25
OBSERVATION_PAGE_LIMIT: int = 25


class PatientSummary(Contract):
    patient_id: UUID
    display_code: str
    data_revision: int


class PatientPage(Contract):
    items: tuple[PatientSummary, ...]
    cursor: str | None = None
    next_action: str = "select_patient_for_observation_review"


class PatientDetail(Contract):
    patient_id: UUID
    display_code: str
    data_revision: int
    observation_count: int
    visit_count: int
    next_action: str = "review_observations_or_stage_source_update"


class VisitSummary(Contract):
    visit_id: UUID
    time_basis: str
    observation_count: int


class VisitPage(Contract):
    items: tuple[VisitSummary, ...]
    next_action: str = "select_visit_for_filtered_observations"


class ObservationFilter(Contract):
    kind: Literal["laboratory", "vital", "diagnosis", "treatment", "symptom", "visit", "note"] | None = None
    concept: str | None = Field(default=None, max_length=120)
    visit_id: UUID | None = None
    limit: int = Field(default=OBSERVATION_PAGE_LIMIT, strict=True, ge=1, le=100)
    cursor: str | None = None


class ObservationSummary(Contract):
    record_id: UUID
    kind: str
    concept: str
    source_hash: Hash
    superseded: bool


class ObservationPage(Contract):
    items: tuple[ObservationSummary, ...]
    snapshot_cursor: Hash
    next_action: str = "open_exact_observation_or_stage_correction"


def _grant_clause(admin: bool) -> str:
    if admin:
        return "SELECT p.id FROM source.research_patients p WHERE p.project_id=:p"
    return """SELECT g.patient_id AS id FROM access.patient_grants g
      JOIN source.research_patients p ON (p.project_id,p.id)=(g.project_id,g.patient_id)
      WHERE g.project_id=:p AND g.user_id=:u"""


def list_patients(c, i, p: UUID, limit: int = PATIENT_PAGE_LIMIT, cursor: str | None = None) -> PatientPage:
    authorize_project(i, p, "viewer")
    admin = i.memberships[p] == "admin"
    rows = (
        c.execute(
            text(
                f"SELECT p.id,p.display_code,p.data_revision FROM ({_grant_clause(admin)}) g "
                "JOIN source.research_patients p ON (p.project_id,p.id)=(:p,g.id) "
                "ORDER BY p.display_code LIMIT :limit"
            ),
            {"p": p, "u": i.user_id, "limit": max(1, min(limit, 100))},
        )
        .mappings()
        .all()
    )
    _ = cursor
    return PatientPage(
        items=tuple(
            PatientSummary(
                patient_id=r["id"], display_code=r["display_code"], data_revision=r["data_revision"]
            )
            for r in rows
        )
    )


def patient_detail(c, i, p: UUID, u: UUID) -> PatientDetail:
    authorize_patient(c, i, p, u)
    row = (
        c.execute(
            text(
                "SELECT display_code,data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"
            ),
            {"p": p, "u": u},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404)
    counts = c.execute(
        text(
            "SELECT COUNT(*) FILTER (WHERE payload->'item'->>'kind'<>'visit') AS obs, "
            "COUNT(*) FILTER (WHERE payload->'item'->>'kind'='visit') AS visits "
            "FROM clinical.observations WHERE project_id=:p AND patient_id=:u"
        ),
        {"p": p, "u": u},
    ).mappings().one()
    return PatientDetail(
        patient_id=u,
        display_code=row["display_code"],
        data_revision=row["data_revision"],
        observation_count=counts["obs"],
        visit_count=counts["visits"],
    )


def list_visits(c, i, p: UUID, u: UUID) -> VisitPage:
    authorize_patient(c, i, p, u)
    rows = (
        c.execute(
            text(
                "SELECT o.id,(o.payload->'item'->'time'->'reference'->>'basis') AS basis,"
                "(SELECT COUNT(*) FROM clinical.observations m WHERE m.project_id=:p AND m.patient_id=:u "
                "AND m.payload->'item'->>'visit_id'=o.id::text) AS n "
                "FROM clinical.observations o WHERE o.project_id=:p AND o.patient_id=:u "
                "AND o.payload->'item'->>'kind'='visit' ORDER BY o.id"
            ),
            {"p": p, "u": u},
        )
        .mappings()
        .all()
    )
    return VisitPage(
        items=tuple(
            VisitSummary(visit_id=r["id"], time_basis=r["basis"] or "unknown", observation_count=r["n"])
            for r in rows
        )
    )


def query_observations(
    c, i, p: UUID, u: UUID, filt: ObservationFilter
) -> ObservationPage:
    authorize_patient(c, i, p, u)
    clauses = ["o.project_id=:p", "o.patient_id=:u"]
    params: dict = {"p": p, "u": u, "limit": filt.limit}
    if filt.kind:
        clauses.append("o.payload->'item'->>'kind'=:kind")
        params["kind"] = filt.kind
    if filt.concept:
        clauses.append("o.payload->'item'->>'concept'=:concept")
        params["concept"] = filt.concept
    if filt.visit_id:
        clauses.append("o.payload->'item'->>'visit_id'=:visit")
        params["visit"] = str(filt.visit_id)
    rows = (
        c.execute(
            text(
                "SELECT o.id,o.payload->'item'->>'kind' AS kind,o.payload->'item'->>'concept' AS concept,"
                "o.payload_hash AS h,(o.supersedes_id IS NOT NULL) AS s FROM clinical.observations o "
                f"WHERE {' AND '.join(clauses)} ORDER BY o.id LIMIT :limit"
            ),
            params,
        )
        .mappings()
        .all()
    )
    cursor = science_hash(
        {"patient": str(u), "filter": filt.model_dump(mode="json"), "ids": sorted(str(r["id"]) for r in rows)}
    )
    return ObservationPage(
        items=tuple(
            ObservationSummary(
                record_id=r["id"],
                kind=r["kind"] or "unknown",
                concept=r["concept"] or "unknown",
                source_hash=r["h"],
                superseded=bool(r["s"]),
            )
            for r in rows
        ),
        snapshot_cursor=cursor,
    )


def create_source_diagnosis(c, i, p: UUID, u: UUID, record_id: UUID) -> dict:
    from canceros.clinical_ingestion import read_record

    record = read_record(c, i, p, u, record_id)
    if record.item.kind != "diagnosis":
        raise HTTPException(422)
    return {
        "record_id": record.id,
        "kind": "diagnosis",
        "source_backed": True,
        "next_action": "diagnosis_is_source_backed_observation_no_parallel_store",
    }


def observation_cursor(c, i, p: UUID, u: UUID) -> Hash:
    authorize_patient(c, i, p, u)
    revision = c.execute(
        text("SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"),
        {"p": p, "u": u},
    ).scalar_one()
    return science_hash({"patient": str(u), "data_revision": revision})
