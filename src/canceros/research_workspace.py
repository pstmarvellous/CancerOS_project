"""Research case metadata over existing identities and canonical clinical ingestion."""

import base64
import hashlib
import json
from datetime import date
from typing import Annotated, Literal, Union
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import AwareDatetime, Field, SecretStr, create_model, field_validator, model_validator
from sqlalchemy import text

from canceros.clinical_contracts import (
    ClinicalTime,
    DiagnosisInput,
    NumericInput,
    SymptomInput,
    TreatmentInput,
    VisitInput,
)
from canceros.clinical_ingestion import (
    BatchCommand,
    ClinicalSourceUpload,
    accept_batch,
    read_record,
    upload_source,
)
from canceros.contracts import Contract
from canceros.identity import authorize_project
from canceros.lineage import register_root
from canceros.patient_linkage import (
    LinkageInput,
    audit,
    authorize_patient,
    resolve_mapping,
)
from canceros.source_registry import (
    SourceAction,
    SourceVersionInput,
    add_source,
    capability,
    get_source,
    require_source_action,
)

ShortText = Annotated[str, Field(min_length=1, max_length=200)]


class ResearchProfileFields(Contract):
    case_identifier: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")]
    title: ShortText
    pseudonym: ShortText
    status: Literal["draft", "active", "archived"] = "draft"
    sex: Literal["female", "male", "intersex", "unknown", "not_recorded"] = "not_recorded"
    age_at_observation: int | None = Field(default=None, strict=True, ge=0, le=150)
    age_observed_on: date | None = None
    profile_source_reference: Annotated[str, Field(min_length=1, max_length=1000)]
    medical_history: Annotated[str, Field(min_length=1, max_length=4000)] | None = None

    @field_validator("title", "pseudonym", "profile_source_reference", "medical_history")
    @classmethod
    def clean_text(cls, value):
        if value is not None and (
            not value.strip()
            or value != value.strip()
            or any(ord(c) < 32 and c not in "\n\t" for c in value)
        ):
            raise ValueError("Nonempty trimmed research text required")
        return value

    @model_validator(mode="after")
    def age_context(self):
        if (self.age_at_observation is None) != (self.age_observed_on is None):
            raise ValueError("Source age requires its observation date")
        if self.age_observed_on and self.age_observed_on > date.today():
            raise ValueError("Age observation date cannot be future dated")
        return self


class ResearchCaseInput(ResearchProfileFields):
    source_version_id: UUID


class ResearchProfileUpdate(ResearchProfileFields):
    expected_profile_revision: int = Field(strict=True, ge=1)


class ResearchCaseView(ResearchCaseInput):
    patient_id: UUID
    project_id: UUID
    profile_revision: int
    data_revision: int
    origin: Literal["real_source", "synthetic_engineering_fixture"]
    created_at: AwareDatetime
    updated_at: AwareDatetime
    observation_count: int
    imaging_count: int


class ResearchCasePage(Contract):
    items: list[ResearchCaseView]
    next_cursor: UUID | None = None


class ResearchCaseSource(Contract):
    source_version_id: UUID
    title: str
    origin: Literal["real_source", "synthetic_engineering_fixture"]
    creation_permitted: bool
    clinical_entry_permitted: bool
    reason: str


class ResearchCaseSources(Contract):
    items: list[ResearchCaseSource]
    next_action: str = "An administrator must register source evidence and current action-specific reviews; no source or permission is created automatically"


class WorkspaceProject(Contract):
    project_id: UUID
    name: str
    role: Literal["viewer", "editor", "admin"]


class WorkspaceView(Contract):
    user_id: UUID
    projects: list[WorkspaceProject]


def workspace(c, i):
    projects = c.execute(
        text("SELECT id,name FROM access.projects WHERE id=ANY(:ids) ORDER BY name,id"),
        {"ids": list(i.memberships)},
    ).all()
    return WorkspaceView(
        user_id=i.user_id,
        projects=[
            WorkspaceProject(project_id=r.id, name=r.name, role=i.memberships[r.id])
            for r in projects
        ],
    )


def case_sources(c, i, p, settings):
    authorize_project(i, p)
    rows = c.execute(
        text(
            "SELECT id FROM source.registry_versions WHERE project_id=:p AND kind='artifact_source' AND record_key NOT LIKE 'manual-%' ORDER BY recorded_at DESC,id"
        ),
        {"p": p},
    ).all()
    items = []
    for row in rows:
        source = get_source(c, i, p, row.id)
        internal = capability(c, i, p, row.id, SourceAction.INTERNAL).permitted
        privacy = (
            source.origin == "synthetic_engineering_fixture"
            or capability(c, i, p, row.id, SourceAction.PATIENT).permitted
        )
        create = (
            internal
            and privacy
            and bool(settings.linkage_active_key)
            and i.memberships[p] == "admin"
        )
        clinical = create and capability(c, i, p, row.id, SourceAction.DERIVATIVE).permitted
        reason = (
            "available"
            if create
            else "administrator_role_required"
            if i.memberships[p] != "admin"
            else "private_linkage_key_required"
            if not settings.linkage_active_key
            else "current_internal_rights_and_privacy_linkage_reviews_required"
        )
        items.append(
            ResearchCaseSource(
                source_version_id=row.id,
                title=source.title,
                origin=source.origin,
                creation_permitted=create,
                clinical_entry_permitted=clinical,
                reason=reason,
            )
        )
    return ResearchCaseSources(items=items)


def _creation_gate(c, i, p, source_id):
    authorize_project(i, p, "admin")
    source = get_source(c, i, p, source_id)
    if source.kind != "artifact_source":
        raise HTTPException(422)
    require_source_action(c, i, p, source_id, SourceAction.INTERNAL)
    if source.origin == "real_source":
        require_source_action(c, i, p, source_id, SourceAction.PATIENT, real_data=True)
    return source


def research_profile(c, i, p, u):
    authorize_project(i, p, "editor")
    authorize_patient(c, i, p, u)
    row = (
        c.execute(
            text(
                "SELECT r.payload,r.profile_revision,r.source_version_id,r.recorded_at,p.data_revision, (SELECT min(recorded_at) FROM source.research_profile_revisions WHERE project_id=:p AND patient_id=:u) AS created_at, (SELECT count(*) FROM clinical.observations WHERE project_id=:p AND patient_id=:u) AS observations, (SELECT count(*) FROM imaging.studies WHERE project_id=:p AND patient_id=:u) AS imaging FROM source.research_profile_revisions r JOIN source.research_patients p ON (p.project_id,p.id)=(r.project_id,r.patient_id) WHERE r.project_id=:p AND r.patient_id=:u ORDER BY r.profile_revision DESC LIMIT 1"
            ),
            {"p": p, "u": u},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404)
    source = get_source(c, i, p, row["source_version_id"])
    return ResearchCaseView(
        **row["payload"],
        patient_id=u,
        project_id=p,
        profile_revision=row["profile_revision"],
        data_revision=row["data_revision"],
        origin=source.origin,
        created_at=row["created_at"],
        updated_at=row["recorded_at"],
        observation_count=row["observations"],
        imaging_count=row["imaging"],
    )


def research_cases(c, i, p, search="", limit=25, cursor=None):
    authorize_project(i, p, "editor")
    rows = c.execute(
        text(
            "SELECT k.patient_id FROM source.research_case_identifiers k JOIN LATERAL (SELECT payload FROM source.research_profile_revisions WHERE project_id=k.project_id AND patient_id=k.patient_id ORDER BY profile_revision DESC LIMIT 1) r ON true WHERE k.project_id=:p AND (:admin OR EXISTS(SELECT 1 FROM access.patient_grants g WHERE g.project_id=k.project_id AND g.patient_id=k.patient_id AND g.user_id=:actor)) AND (CAST(:cursor AS uuid) IS NULL OR k.patient_id>CAST(:cursor AS uuid)) AND (:search='' OR r.payload->>'title' ILIKE :pattern OR r.payload->>'case_identifier' ILIKE :pattern OR r.payload->>'pseudonym' ILIKE :pattern) ORDER BY k.patient_id LIMIT :limit"
        ),
        {
            "p": p,
            "actor": i.user_id,
            "admin": i.memberships[p] == "admin",
            "cursor": str(cursor) if cursor else None,
            "search": search,
            "pattern": "%" + search.replace("%", "\\%").replace("_", "\\_") + "%",
            "limit": limit + 1,
        },
    ).all()
    return ResearchCasePage(
        items=[research_profile(c, i, p, r.patient_id) for r in rows[:limit]],
        next_cursor=rows[limit - 1].patient_id if len(rows) > limit else None,
    )


def _append_profile(c, i, p, u, value, revision):
    c.execute(
        text(
            "INSERT INTO source.research_profile_revisions(id,project_id,patient_id,profile_revision,case_identifier,source_version_id,payload,recorded_by) VALUES(:id,:p,:u,:rev,:code,:source,CAST(:payload AS jsonb),:actor)"
        ),
        {
            "id": uuid4(),
            "p": p,
            "u": u,
            "rev": revision,
            "code": value.case_identifier,
            "source": value.source_version_id,
            "payload": value.model_dump_json(),
            "actor": i.user_id,
        },
    )
    audit(c, p, u, "RESEARCH_PROFILE_REVISION_SAVED")
    return research_profile(c, i, p, u)


def create_case(c, i, p, value: ResearchCaseInput, settings):
    _creation_gate(c, i, p, value.source_version_id)
    code = value.case_identifier.upper()
    c.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": f"case:{p}:{code}"}
    )
    if c.execute(
        text(
            "SELECT 1 FROM source.research_case_identifiers WHERE project_id=:p AND case_identifier=:code"
        ),
        {"p": p, "code": code},
    ).first():
        raise HTTPException(409)
    patient = resolve_mapping(
        c,
        i,
        p,
        LinkageInput(
            source_version_id=value.source_version_id,
            source_patient_key=SecretStr(value.pseudonym),
        ),
        settings,
    )
    if c.execute(
        text(
            "SELECT 1 FROM source.research_case_identifiers WHERE project_id=:p AND patient_id=:u"
        ),
        {"p": p, "u": patient.patient_id},
    ).first():
        raise HTTPException(409)
    c.execute(
        text(
            "INSERT INTO source.research_case_identifiers(project_id,case_identifier,patient_id) VALUES(:p,:code,:u)"
        ),
        {"p": p, "code": code, "u": patient.patient_id},
    )
    return _append_profile(
        c, i, p, patient.patient_id, value.model_copy(update={"case_identifier": code}), 1
    )


def update_profile(c, i, p, u, value: ResearchProfileUpdate):
    authorize_project(i, p, "admin")
    authorize_patient(c, i, p, u, edit=True)
    c.execute(
        text("SELECT id FROM source.research_patients WHERE project_id=:p AND id=:u FOR UPDATE"),
        {"p": p, "u": u},
    ).one()
    old = research_profile(c, i, p, u)
    _creation_gate(c, i, p, old.source_version_id)
    if (
        old.profile_revision != value.expected_profile_revision
        or old.case_identifier != value.case_identifier.upper()
        or old.pseudonym != value.pseudonym
    ):
        raise HTTPException(409)
    new = ResearchCaseInput(
        **value.model_dump(exclude={"expected_profile_revision"}),
        source_version_id=old.source_version_id,
    )
    return _append_profile(
        c,
        i,
        p,
        u,
        new.model_copy(update={"case_identifier": old.case_identifier}),
        old.profile_revision + 1,
    )


def _manual_model(model):
    return create_model(
        "Manual" + model.__name__,
        __base__=Contract,
        **{
            name: (field.annotation, field)
            for name, field in model.model_fields.items()
            if name not in {"client_record_key", "source_locator_id"}
        },
    )


class ManualNoteInput(Contract):
    kind: Literal["note"]
    time: ClinicalTime
    original_term: Annotated[str, Field(min_length=1, max_length=300)]
    certainty: Literal["documented", "reported", "uncertain", "unknown"]
    negation: Literal["affirmed", "negated", "unspecified"]
    text: SecretStr = Field(min_length=1, max_length=16000, json_schema_extra={"writeOnly": True})


ManualItem = Annotated[
    Union[
        tuple(
            _manual_model(m)
            for m in (VisitInput, NumericInput, DiagnosisInput, TreatmentInput, SymptomInput)
        )
        + (ManualNoteInput,)
    ],
    Field(discriminator="kind"),
]


class ManualObservationInput(Contract):
    expected_revision: int = Field(strict=True, ge=1)
    source_reference: Annotated[str, Field(min_length=1, max_length=1000)]
    observation: ManualItem
    corrects_record_id: UUID | None = None

    @field_validator("source_reference")
    @classmethod
    def meaningful_source_reference(cls, value):
        if value != value.strip() or not value.strip() or any(ord(c) < 32 for c in value):
            raise ValueError("Trimmed source reference required")
        return value


def _child_source(c, i, p, source, digest):
    return add_source(
        c,
        i,
        p,
        SourceVersionInput(
            **{
                **source.model_dump(exclude={"id", "project_id", "created_by", "recorded_at"}),
                "record_key": "manual-" + uuid4().hex,
                "version": 1,
                "manifest_sha256": digest,
                "title": "Private manually entered research source",
                "citation": "Patient-owned source reference is retained in the protected clinical locator",
            }
        ),
    )


def manual_observation(c, i, p, u, value: ManualObservationInput, key, storage):
    from canceros.note_runs import NoteRegistration, register_note

    authorize_project(i, p, "admin")
    authorize_patient(c, i, p, u, edit=True)
    c.execute(
        text("SELECT id FROM source.research_patients WHERE project_id=:p AND id=:u FOR UPDATE"),
        {"p": p, "u": u},
    ).one()
    profile = research_profile(c, i, p, u)
    source = _creation_gate(c, i, p, profile.source_version_id)
    require_source_action(c, i, p, source.id, SourceAction.DERIVATIVE)
    synthetic = source.origin == "synthetic_engineering_fixture"
    if synthetic and value.observation.time.reference.time_domain != "simulation":
        raise HTTPException(422)
    if not synthetic and value.observation.time.reference.time_domain == "simulation":
        raise HTTPException(422)
    current = c.execute(
        text(
            "SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u FOR UPDATE"
        ),
        {"p": p, "u": u},
    ).scalar_one()
    if value.expected_revision != current:
        raise HTTPException(409)
    mapping = c.execute(
        text(
            "SELECT id FROM source.patient_mappings WHERE project_id=:p AND patient_id=:u ORDER BY recorded_at LIMIT 1"
        ),
        {"p": p, "u": u},
    ).one()
    record = value.observation.model_dump(mode="json")
    logical_key = "manual-" + uuid4().hex
    if value.corrects_record_id:
        prior = read_record(c, i, p, u, value.corrects_record_id)
        logical_key = prior.item.client_record_key
        if prior.item.kind != record["kind"]:
            raise HTTPException(422)
    record["client_record_key"] = logical_key
    if record["kind"] == "note":
        raw = value.observation.text.get_secret_value().encode()
        if not raw.strip():
            raise HTTPException(422)
        digest = hashlib.sha256(raw).hexdigest()
        note_source = _child_source(c, i, p, source, digest)
        stored = storage.write_verified(p, raw)
        artifact_id = uuid4()
        c.execute(
            text(
                "INSERT INTO ops.artifacts(id,project_id,patient_id,object_key,object_version,byte_size,sha256,provenance,availability) VALUES(:id,:p,:u,:key,:version,:size,:hash,:origin,'verified')"
            ),
            {
                "id": artifact_id,
                "p": p,
                "u": u,
                "key": stored.key,
                "version": stored.version,
                "size": stored.byte_size,
                "hash": digest,
                "origin": "SYNTHETIC_GENERATED" if synthetic else "REAL_OBSERVED",
            },
        )
        register_root(c, i, p, u, artifact_id, "note_source_artifact", digest, note_source.id)
        note = register_note(
            c,
            i,
            p,
            u,
            NoteRegistration(artifact_id=artifact_id, anchor=value.observation.time),
            storage,
        )
        record.pop("text")
        record.update(
            concept="source_note",
            artifact_id=str(artifact_id),
            note_document_id=str(note.note_id),
            content_sha256=digest,
            language="en",
        )
    raw = json.dumps(
        {
            "schema_version": "clinical-source/1",
            "fixture_origin": "SYNTHETIC_ENGINEERING_FIXTURE"
            if synthetic
            else "AUTHORIZED_RESEARCH_SOURCE",
            "records": [record],
        },
        separators=(",", ":"),
    ).encode()
    digest = hashlib.sha256(raw).hexdigest()
    entered = _child_source(c, i, p, source, digest)
    staged = upload_source(
        c,
        i,
        p,
        u,
        ClinicalSourceUpload(
            source_version_id=entered.id,
            mapping_id=mapping.id,
            sha256=digest,
            content_base64=base64.b64encode(raw).decode(),
            source_reference=SecretStr(value.source_reference),
        ),
        storage,
    )
    return accept_batch(
        c,
        i,
        p,
        u,
        BatchCommand(
            source_artifact_id=staged.artifact_id,
            expected_revision=value.expected_revision,
            corrects_record_id=value.corrects_record_id,
        ),
        key,
        storage,
    )
