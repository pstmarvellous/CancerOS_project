"""Validate-first source-backed clinical import; no implicit patient/state publication."""

import base64
import hashlib
import json
from typing import Annotated, Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import HTTPException
from pydantic import Field, SecretStr, TypeAdapter, ValidationError
from sqlalchemy import text

from canceros.clinical_contracts import ClinicalInput, ClinicalRecord, ClinicalTime
from canceros.clinical_validation import component_validation, semantic_validation
from canceros.contracts import Availability, Context, Contract, Hash, Provenance, Quality
from canceros.identity import authorize_project
from canceros.lineage import (
    derive_resource,
    lock_lineage,
    processing_spec,
    register_root,
    require_resource_action,
)
from canceros.note_observation_adapter import persist_note_pointer, validate_note_pointer
from canceros.patient_linkage import audit, authorize_patient, release_for
from canceros.persistence import capture_revision, load_revision, science_hash
from canceros.source_registry import SourceAction, require_source_action
from canceros.storage import PrivateStorage, StoredObject


class ClinicalSourceUpload(Contract):
    source_version_id: UUID
    mapping_id: UUID
    sha256: Hash
    content_base64: SecretStr = Field(
        min_length=1, max_length=1400000, json_schema_extra={"writeOnly": True}
    )
    source_reference: SecretStr | None = Field(
        default=None, min_length=1, max_length=1000, json_schema_extra={"writeOnly": True}
    )


class ClinicalSourceReceipt(Contract):
    artifact_id: UUID
    patient_id: UUID
    sha256: Hash
    status: Literal["staged"] = "staged"
    next_action: str = "Validate this private source before accepting its records"


class BatchCommand(Contract):
    source_artifact_id: UUID
    expected_revision: Annotated[int, Field(strict=True, ge=1)]
    corrects_record_id: UUID | None = None


class RuleIssue(Contract):
    rule_id: str
    severity: Literal["error", "warning"]
    path: str
    reason: str
    next_action: str


class BatchReport(Contract):
    semantic_rule_version: Literal["clinical-structural/1"] = "clinical-structural/1"
    id: UUID
    status: Literal["valid", "quarantined", "accepted"]
    accepted_count: int
    rejected_count: int
    quarantined_count: int
    issues: list[RuleIssue]
    record_ids: list[UUID]
    input_revision: int
    result_revision: int | None = None
    publication: Literal["draft"] = "draft"
    verification_scope: Literal[
        "synthetic_engineering_fixture_only", "documented_source_structural_only"
    ] = "synthetic_engineering_fixture_only"
    next_action: str


class RetractionInput(Contract):
    expected_revision: Annotated[int, Field(strict=True, ge=1)]
    reason_code: Literal[
        "source_corrected", "entered_in_error", "identity_review", "withdrawn_source"
    ]


class RetractionReceipt(Contract):
    id: UUID
    record_id: UUID
    revision: int
    publication: Literal["draft"] = "draft"


def upload_source(
    connection,
    identity,
    project,
    patient,
    value: ClinicalSourceUpload,
    storage: PrivateStorage,
    lineage_parents=None,
    processing=None,
):
    authorize_project(identity, project, "admin")
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    require_source_action(
        connection, identity, project, value.source_version_id, SourceAction.INTERNAL
    )
    source, release = release_for(connection, identity, project, value.source_version_id)
    if source.origin == "real_source":
        require_source_action(
            connection, identity, project, source.id, SourceAction.PATIENT, real_data=True
        )
    mapping = connection.execute(
        text(
            "SELECT patient_id,release_version_id FROM source.patient_mappings WHERE project_id=:p AND id=:id"
        ),
        {"p": project, "id": value.mapping_id},
    ).one_or_none()
    if mapping is None or mapping.patient_id != patient or mapping.release_version_id != release:
        raise HTTPException(404)
    try:
        raw = base64.b64decode(value.content_base64.get_secret_value(), validate=True)
    except ValueError:
        raise HTTPException(422) from None
    if len(raw) > storage.cap:
        raise HTTPException(413)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != value.sha256 or digest != source.manifest_sha256:
        raise HTTPException(422)
    # Bound JSON structure before storage; malformed rows still survive in quarantined private input.
    document = source_document(raw)
    if (document["fixture_origin"] == "SYNTHETIC_ENGINEERING_FIXTURE") != (
        source.origin == "synthetic_engineering_fixture"
    ):
        raise HTTPException(422)
    provenance = (
        Provenance.SYNTHETIC_GENERATED
        if source.origin == "synthetic_engineering_fixture"
        else Provenance.REAL_OBSERVED
    )
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:s,0))"),
        {"s": f"source-upload:{project}:{patient}:{source.id}"},
    )
    existing = connection.execute(
        text(
            "SELECT a.id FROM source.ingestion_artifacts i JOIN ops.artifacts a ON (a.project_id,a.id)=(i.project_id,i.id) WHERE i.project_id=:p AND i.patient_id=:u AND i.source_version_id=:source AND a.sha256=:hash"
        ),
        {"p": project, "u": patient, "source": source.id, "hash": digest},
    ).first()
    if existing:
        return ClinicalSourceReceipt(artifact_id=existing.id, patient_id=patient, sha256=digest)
    stored = storage.write_verified(project, raw)
    artifact_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO ops.artifacts(id,project_id,patient_id,object_key,object_version,byte_size,sha256,provenance,availability) VALUES(:id,:p,:u,:key,:version,:size,:hash,:origin,'verified')"
        ),
        {
            "id": artifact_id,
            "p": project,
            "u": patient,
            "key": stored.key,
            "version": stored.version,
            "size": stored.byte_size,
            "hash": digest,
            "origin": provenance.value,
        },
    )
    connection.execute(
        text(
            "INSERT INTO source.ingestion_artifacts(id,project_id,patient_id,source_version_id,mapping_id,recorded_by) VALUES(:id,:p,:u,:source,:mapping,:actor)"
        ),
        {
            "id": artifact_id,
            "p": project,
            "u": patient,
            "source": source.id,
            "mapping": value.mapping_id,
            "actor": identity.user_id,
        },
    )
    for index, row in enumerate(document["records"]):
        locator = uuid5(NAMESPACE_URL, f"canceros:{artifact_id}:records:{index}")
        connection.execute(
            text(
                "INSERT INTO source.source_locators(id,project_id,patient_id,artifact_id,row_index,record_hash,source_reference) VALUES(:id,:p,:u,:a,:row,:hash,:reference)"
            ),
            {
                "id": locator,
                "p": project,
                "u": patient,
                "a": artifact_id,
                "row": index,
                "hash": science_hash(row),
                "reference": value.source_reference.get_secret_value()
                if value.source_reference
                else None,
            },
        )
    audit(connection, project, artifact_id, "CLINICAL_SOURCE_STAGED")
    if lineage_parents:
        derive_resource(
            connection,
            identity,
            project,
            patient,
            artifact_id,
            "clinical_source_artifact",
            digest,
            lineage_parents,
            processing,
        )
    else:
        register_root(
            connection,
            identity,
            project,
            patient,
            artifact_id,
            "clinical_source_artifact",
            digest,
            source.id,
        )
    return ClinicalSourceReceipt(artifact_id=artifact_id, patient_id=patient, sha256=digest)


def source_document(raw):
    def unique_object(pairs):
        output = {}
        for key, value in pairs:
            if key in output:
                raise ValueError("Duplicate JSON field")
            output[key] = value
        return output

    try:
        document = json.loads(
            raw,
            object_pairs_hook=unique_object,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
        if (
            set(document) != {"schema_version", "fixture_origin", "records"}
            or document["schema_version"] != "clinical-source/1"
            or document["fixture_origin"]
            not in ("SYNTHETIC_ENGINEERING_FIXTURE", "AUTHORIZED_RESEARCH_SOURCE")
        ):
            raise ValueError()
        if not isinstance(document["records"], list) or not 1 <= len(document["records"]) <= 100:
            raise ValueError()
        if not all(isinstance(row, dict) for row in document["records"]):
            raise ValueError()
    except (ValueError, TypeError, RecursionError):
        raise HTTPException(422) from None
    return document


def load_source(connection, identity, project, patient, artifact_id, storage):
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    row = connection.execute(
        text(
            "SELECT i.source_version_id,a.object_key,a.object_version,a.sha256,a.byte_size FROM source.ingestion_artifacts i JOIN ops.artifacts a ON (a.project_id,a.id)=(i.project_id,i.id) WHERE i.project_id=:p AND i.patient_id=:u AND i.id=:id"
        ),
        {"p": project, "u": patient, "id": artifact_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    require_source_action(
        connection, identity, project, row.source_version_id, SourceAction.INTERNAL
    )
    source, _ = release_for(connection, identity, project, row.source_version_id)
    if source.origin == "real_source":
        require_source_action(
            connection, identity, project, source.id, SourceAction.PATIENT, real_data=True
        )
    require_resource_action(
        connection, identity, project, patient, artifact_id, SourceAction.INTERNAL
    )
    stored = StoredObject(project, row.object_key, row.object_version, row.sha256, row.byte_size)
    return source_document(storage.read(stored, project))


def check_time(connection, project, patient, time: ClinicalTime):
    reference = time.reference
    if reference.basis == "relative_day":
        if reference.anchor_state_id:
            # State anchors require the later authoritative state service, never a guessed ID.
            raise HTTPException(409)
        row = connection.execute(
            text(
                "SELECT id FROM source.timeline_origins WHERE project_id=:p AND patient_id=:u AND id=:id AND time_domain=:domain"
            ),
            {
                "p": project,
                "u": patient,
                "id": reference.timeline_origin_id,
                "domain": reference.time_domain,
            },
        ).first()
        if row is None:
            raise HTTPException(422)


def validate_batch(connection, identity, project, patient, command: BatchCommand, storage):
    document = load_source(
        connection, identity, project, patient, command.source_artifact_id, storage
    )
    revision = connection.execute(
        text("SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"),
        {"p": project, "u": patient},
    ).scalar_one()
    if command.expected_revision != revision:
        raise HTTPException(409)
    items, indexed_items = [], []
    issues: list[RuleIssue] = []
    keys = set()
    for index, raw_item in enumerate(document["records"]):
        path = f"/records/{index}"
        locator = connection.execute(
            text(
                "SELECT id,record_hash FROM source.source_locators WHERE project_id=:p AND patient_id=:u AND artifact_id=:a AND row_index=:row"
            ),
            {"p": project, "u": patient, "a": command.source_artifact_id, "row": index},
        ).one()
        if science_hash(raw_item) != locator.record_hash:
            raise HTTPException(409)
        try:
            if "source_locator_id" in raw_item:
                raise ValueError("Source locators are server-owned")
            item = TypeAdapter(ClinicalInput).validate_python(
                {**raw_item, "source_locator_id": locator.id}
            )
            if item.client_record_key in keys:
                raise ValueError("Duplicate source key")
            keys.add(item.client_record_key)
            check_time(connection, project, patient, item.time)
            if (
                document["fixture_origin"] == "AUTHORIZED_RESEARCH_SOURCE"
                and item.time.reference.time_domain == "simulation"
            ):
                raise ValueError("Observed source time cannot use simulation domain")
            if item.kind == "treatment" and item.ended_time:
                check_time(connection, project, patient, item.ended_time)
            if item.visit_id:
                visit = connection.execute(
                    text(
                        "SELECT kind FROM clinical.observations WHERE project_id=:p AND patient_id=:u AND id=:id"
                    ),
                    {"p": project, "u": patient, "id": item.visit_id},
                ).scalar_one_or_none()
                if visit != "visit":
                    raise ValueError("Unresolved visit")
            if item.kind == "note":
                validate_note_pointer(connection, identity, project, patient, item)
            _, findings = semantic_validation(item, path)
            issues.extend(RuleIssue.model_validate(finding) for finding in findings)
            items.append(item)
            indexed_items.append((index, item))
        except ValidationError as error:
            for detail in error.errors():
                issues.append(
                    RuleIssue(
                        rule_id="SCHEMA-1",
                        severity="error",
                        path=path + "/" + "/".join(str(v) for v in detail["loc"]),
                        reason="Unsupported or invalid source field",
                        next_action="Correct the source mapping; retain the original artifact",
                    )
                )
        except (ValueError, HTTPException):
            issues.append(
                RuleIssue(
                    rule_id="SOURCE-TIME-OWNERSHIP-1",
                    severity="error",
                    path=path,
                    reason="Source identity, time, visit or adapter requires review",
                    next_action="Resolve the owned source reference before accepting this batch",
                )
            )
    if command.corrects_record_id and len(document["records"]) != 1:
        issues.append(
            RuleIssue(
                rule_id="CORRECTION-SINGLE-1",
                severity="error",
                path="/records",
                reason="A correction requires exactly one record",
                next_action="Stage one corrected source record",
            )
        )
    issues.extend(
        RuleIssue.model_validate(finding) for finding in component_validation(indexed_items)
    )
    errors = [issue for issue in issues if issue.severity == "error"]
    invalid_rows = len(
        {issue.path.split("/")[2] for issue in errors if issue.path.startswith("/records/")}
    )
    report = BatchReport(
        id=uuid5(
            NAMESPACE_URL,
            f"validate:{command.source_artifact_id}:{science_hash(command.model_dump(mode='json'))}",
        ),
        status="quarantined" if errors else "valid",
        accepted_count=0,
        rejected_count=invalid_rows,
        quarantined_count=len(document["records"]) if errors else 0,
        issues=issues,
        record_ids=[],
        input_revision=revision,
        verification_scope="synthetic_engineering_fixture_only"
        if document["fixture_origin"] == "SYNTHETIC_ENGINEERING_FIXTURE"
        else "documented_source_structural_only",
        next_action="Repair the reported source rows and stage a corrected artifact"
        if errors
        else "Explicitly accept this validated batch; states remain unpublished",
    )
    return report, items


def accept_batch(connection, identity, project, patient, command, key, storage):
    authorize_patient(connection, identity, project, patient, edit=True)
    # Patient lock serializes correction, fingerprint replay and revision journal/outbox writes.
    current = connection.execute(
        text(
            "SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u FOR UPDATE"
        ),
        {"p": project, "u": patient},
    ).scalar_one()
    fingerprint = science_hash(command.model_dump(mode="json"))
    previous = connection.execute(
        text(
            "SELECT request_hash,report FROM source.ingestion_results WHERE project_id=:p AND patient_id=:u AND actor_id=:actor AND command_key=:key"
        ),
        {"p": project, "u": patient, "actor": identity.user_id, "key": key},
    ).one_or_none()
    # Recheck source rights before replay, even if the caller already owns the patient.
    load_source(connection, identity, project, patient, command.source_artifact_id, storage)
    if previous:
        if previous.request_hash != fingerprint:
            raise HTTPException(409)
        prior_report = BatchReport.model_validate(previous.report)
        for identifier in prior_report.record_ids:
            for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE):
                require_resource_action(connection, identity, project, patient, identifier, action)
        return prior_report
    report, items = validate_batch(connection, identity, project, patient, command, storage)
    synthetic = report.verification_scope == "synthetic_engineering_fixture_only"
    origin = Provenance.SYNTHETIC_GENERATED if synthetic else Provenance.REAL_DERIVED
    if report.status == "quarantined":
        report = report.model_copy(update={"id": uuid4()})
        return persist_report(
            connection, identity, project, patient, command, key, fingerprint, report
        )
    manifest = load_revision(connection, project, patient, current)
    members = list(manifest.get("members", []))
    ids = []
    for index, item in enumerate(items):
        head = connection.execute(
            text(
                "SELECT record_id FROM clinical.observation_heads WHERE project_id=:p AND patient_id=:u AND logical_key=:key"
            ),
            {"p": project, "u": patient, "key": item.client_record_key},
        ).scalar_one_or_none()
        if head != command.corrects_record_id:
            raise HTTPException(409)
        record_id = uuid4()
        normalized, findings = semantic_validation(item, "/record")
        has_warnings = any(finding["severity"] == "warning" for finding in findings) or any(
            issue.severity == "warning" and issue.path.startswith(f"/records/{index}/")
            for issue in report.issues
        )
        record = ClinicalRecord(
            id=record_id,
            project_id=project,
            patient_id=patient,
            item=item,
            origin=origin,
            context=Context.SYNTHETIC if synthetic else Context.OBSERVED,
            quality=Quality.WARNING if has_warnings else Quality.PENDING,
            availability=Availability.AVAILABLE,
            numeric_normalization=normalized,
            source_reference=connection.execute(
                text(
                    "SELECT source_reference FROM source.source_locators WHERE project_id=:p AND patient_id=:u AND id=:id"
                ),
                {"p": project, "u": patient, "id": item.source_locator_id},
            ).scalar_one(),
        )
        payload = record.model_dump(mode="json")
        connection.execute(
            text(
                "INSERT INTO clinical.observations(id,project_id,patient_id,source_locator_id,logical_key,kind,supersedes_id,payload,payload_hash,time_reference_id) VALUES(:id,:p,:u,:loc,:key,:kind,:prior,CAST(:payload AS jsonb),:hash,:time)"
            ),
            {
                "id": record_id,
                "p": project,
                "u": patient,
                "loc": item.source_locator_id,
                "key": item.client_record_key,
                "kind": item.kind,
                "prior": head,
                "payload": json.dumps(payload),
                "hash": science_hash(payload),
                "time": persist_time(connection, project, patient, item.time),
            },
        )
        connection.execute(
            text(
                "INSERT INTO clinical.observation_heads(project_id,patient_id,logical_key,record_id) VALUES(:p,:u,:key,:id) ON CONFLICT(project_id,patient_id,logical_key) DO UPDATE SET record_id=excluded.record_id,retracted=false"
            ),
            {"p": project, "u": patient, "key": item.client_record_key, "id": record_id},
        )
        persist_subtype(connection, project, patient, record_id, item, normalized)
        parents = [command.source_artifact_id] + ([head] if head else [])
        if item.kind == "note":
            assert item.note_document_id is not None
            parents.append(item.note_document_id)
        derive_resource(
            connection,
            identity,
            project,
            patient,
            record_id,
            "clinical_observation",
            science_hash(payload),
            parents,
            processing_spec(
                __file__,
                "source-clinical-mapping/1",
                "clinical-structural/1",
                {"dictionary_version": item.dictionary_version},
            ),
            expected_origin=origin,
        )
        if head and str(head) in members:
            members.remove(str(head))
        members.append(str(record_id))
        ids.append(record_id)
    next_revision = current + 1
    capture_revision(
        connection, project, patient, next_revision, {**manifest, "members": sorted(members)}
    )
    connection.execute(
        text("UPDATE source.research_patients SET data_revision=:r WHERE project_id=:p AND id=:u"),
        {"r": next_revision, "p": project, "u": patient},
    )
    connection.execute(
        text(
            "INSERT INTO ops.domain_outbox(id,project_id,patient_id,revision,event_code) VALUES(:id,:p,:u,:r,'CLINICAL_REVISION_ACCEPTED')"
        ),
        {"id": uuid4(), "p": project, "u": patient, "r": next_revision},
    )
    audit(connection, project, patient, "CLINICAL_REVISION_ACCEPTED")
    report = report.model_copy(
        update={
            "id": uuid4(),
            "status": "accepted",
            "accepted_count": len(ids),
            "record_ids": ids,
            "result_revision": next_revision,
            "next_action": "Review accepted records; build and publish a state explicitly when eligible",
        }
    )
    return persist_report(connection, identity, project, patient, command, key, fingerprint, report)


def persist_report(connection, identity, project, patient, command, key, fingerprint, report):
    connection.execute(
        text(
            "INSERT INTO source.ingestion_results(id,project_id,patient_id,artifact_id,actor_id,command_key,request_hash,report) VALUES(:id,:p,:u,:a,:actor,:key,:hash,CAST(:report AS jsonb))"
        ),
        {
            "id": report.id,
            "p": project,
            "u": patient,
            "a": command.source_artifact_id,
            "actor": identity.user_id,
            "key": key,
            "hash": fingerprint,
            "report": report.model_dump_json(),
        },
    )
    return report


def persist_time(connection, project, patient, time):
    reference = time.reference
    time_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO clinical.time_references(id,project_id,patient_id,basis,time_domain,timestamp_value,date_value,relative_day,timeline_origin_id,missing_reason) VALUES(:id,:p,:u,:basis,:domain,:timestamp,:date,:day,:origin,:missing)"
        ),
        {
            "id": time_id,
            "p": project,
            "u": patient,
            "basis": reference.basis,
            "domain": reference.time_domain,
            "timestamp": reference.value if reference.basis == "timestamp" else None,
            "date": reference.value if reference.basis == "date" else None,
            "day": reference.value if reference.basis == "relative_day" else None,
            "origin": reference.timeline_origin_id if reference.basis == "relative_day" else None,
            "missing": reference.missing_reason if reference.basis == "unknown" else None,
        },
    )
    return time_id


def persist_subtype(connection, project, patient, record_id, item, normalized=None):
    if item.kind in ("laboratory", "vital"):
        result = normalized.canonical_result if normalized else item.result
        quantity = (
            result.quantity
            if result.form == "exact"
            else result.threshold
            if result.form == "censored"
            else None
        )
        connection.execute(
            text(
                "INSERT INTO clinical.numeric_results(observation_id,value,comparator,threshold,unit,missing_reason,original_value,original_unit,conversion_version) VALUES(:id,:value,:comparator,:threshold,:unit,:missing,:original_value,:original_unit,'local-units/1')"
            ),
            {
                "id": record_id,
                "value": quantity.value if result.form == "exact" and quantity else None,
                "comparator": result.comparator if result.form == "censored" else None,
                "threshold": quantity.value if result.form == "censored" and quantity else None,
                "unit": quantity.unit if quantity else None,
                "missing": result.missing_reason if result.form == "missing" else None,
                "original_value": item.original_value,
                "original_unit": item.original_unit,
            },
        )
        if item.reference_interval:
            interval = item.reference_interval
            connection.execute(
                text(
                    "INSERT INTO clinical.reference_intervals(id,observation_id,low,high,unit,source_description,population_context,version) VALUES(:id,:record,:low,:high,:unit,:source,:context,:version)"
                ),
                {
                    "id": uuid4(),
                    "record": record_id,
                    "low": interval.low,
                    "high": interval.high,
                    "unit": interval.unit,
                    "source": interval.source_description,
                    "context": interval.population_context,
                    "version": interval.version,
                },
            )
    elif item.kind == "visit":
        connection.execute(
            text(
                "INSERT INTO clinical.visits(observation_id,label,occasion_type) VALUES(:id,:label,:concept)"
            ),
            {"id": record_id, "label": item.label, "concept": item.concept},
        )
    elif item.kind == "diagnosis":
        connection.execute(
            text(
                "INSERT INTO clinical.diagnosis_results(observation_id,histology,side,er_status,pr_status,her2_status,clinical_stage,pathologic_stage,staging_system) VALUES(:id,:histology,:side,:er,:pr,:her2,:clinical,:pathologic,:system)"
            ),
            {
                "id": record_id,
                "histology": item.histology,
                "side": item.side,
                "er": item.er_status,
                "pr": item.pr_status,
                "her2": item.her2_status,
                "clinical": item.clinical_stage,
                "pathologic": item.pathologic_stage,
                "system": item.staging_system,
            },
        )
    elif item.kind == "treatment":
        ended = (
            persist_time(connection, project, patient, item.ended_time) if item.ended_time else None
        )
        connection.execute(
            text(
                "INSERT INTO clinical.treatment_events(observation_id,category,event_type,exposure_status,regimen_text,ended_time_id) VALUES(:id,:category,:event,:status,:regimen,:end)"
            ),
            {
                "id": record_id,
                "category": item.concept,
                "event": item.event_type,
                "status": item.exposure_status,
                "regimen": item.regimen_text,
                "end": ended,
            },
        )
    elif item.kind == "symptom":
        connection.execute(
            text(
                "INSERT INTO clinical.symptom_results(observation_id,presence,reporter,severity_value,severity_scale_id,severity_scale_version) VALUES(:id,:presence,:reporter,:severity,:scale,:version)"
            ),
            {
                "id": record_id,
                "presence": item.presence,
                "reporter": item.reporter,
                "severity": item.severity,
                "scale": item.instrument,
                "version": item.instrument_version,
            },
        )
    elif item.kind == "note":
        persist_note_pointer(connection, project, patient, record_id, item)
    else:
        raise HTTPException(409)


def retract_record(connection, identity, project, patient, record_id, value):
    authorize_patient(connection, identity, project, patient, edit=True)
    revision = connection.execute(
        text(
            "SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u FOR UPDATE"
        ),
        {"p": project, "u": patient},
    ).scalar_one()
    if revision != value.expected_revision:
        raise HTTPException(409)
    head = connection.execute(
        text(
            "SELECT logical_key FROM clinical.observation_heads WHERE project_id=:p AND patient_id=:u AND record_id=:id AND NOT retracted"
        ),
        {"p": project, "u": patient, "id": record_id},
    ).one_or_none()
    if head is None:
        raise HTTPException(409)
    retraction = uuid4()
    connection.execute(
        text(
            "INSERT INTO clinical.retractions(id,project_id,patient_id,record_id,reason_code,actor_id) VALUES(:id,:p,:u,:record,:reason,:actor)"
        ),
        {
            "id": retraction,
            "p": project,
            "u": patient,
            "record": record_id,
            "reason": value.reason_code,
            "actor": identity.user_id,
        },
    )
    connection.execute(
        text(
            "UPDATE clinical.observation_heads SET retracted=true WHERE project_id=:p AND patient_id=:u AND record_id=:id"
        ),
        {"p": project, "u": patient, "id": record_id},
    )
    manifest = load_revision(connection, project, patient, revision)
    capture_revision(
        connection,
        project,
        patient,
        revision + 1,
        {
            **manifest,
            "members": [m for m in manifest["members"] if m != str(record_id)],
            "retractions": manifest.get("retractions", []) + [str(retraction)],
        },
    )
    connection.execute(
        text("UPDATE source.research_patients SET data_revision=:r WHERE project_id=:p AND id=:u"),
        {"r": revision + 1, "p": project, "u": patient},
    )
    connection.execute(
        text(
            "INSERT INTO ops.domain_outbox(id,project_id,patient_id,revision,event_code) VALUES(:id,:p,:u,:r,'CLINICAL_RECORD_RETRACTED')"
        ),
        {"id": uuid4(), "p": project, "u": patient, "r": revision + 1},
    )
    audit(connection, project, record_id, "CLINICAL_RECORD_RETRACTED")
    return RetractionReceipt(id=retraction, record_id=record_id, revision=revision + 1)


def read_record(connection, identity, project, patient, record_id):
    authorize_project(identity, project, "editor")
    authorize_patient(connection, identity, project, patient)
    row = connection.execute(
        text(
            "SELECT payload,payload_hash FROM clinical.observations WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": project, "u": patient, "id": record_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.payload) != row.payload_hash:
        raise HTTPException(409)
    return ClinicalRecord.model_validate(row.payload)
