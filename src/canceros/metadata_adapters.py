"""Small explicit metadata adapters; actual cohort adapters remain rights/dictionary gated."""

import base64
import csv
import hashlib
import io
import json
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import Field, SecretStr, TypeAdapter, ValidationError
from sqlalchemy import text

from canceros.clinical_contracts import ClinicalInput
from canceros.clinical_ingestion import ClinicalSourceUpload, RuleIssue, check_time, upload_source
from canceros.clinical_validation import semantic_validation
from canceros.contracts import Contract, Hash
from canceros.identity import authorize_project
from canceros.lineage import lock_lineage, processing_spec, register_root
from canceros.patient_linkage import audit, authorize_patient, release_for
from canceros.persistence import science_hash
from canceros.source_registry import (
    SourceAction,
    SourceVersionInput,
    add_source,
    require_source_action,
)

ADAPTER_VERSION = "engineering-clinical-csv/1"
COLUMNS = [
    "record_key",
    "kind",
    "concept",
    "relative_day",
    "value",
    "unit",
    "qualifier",
    "missing_reason",
    "original_term",
]
DICTIONARY = {
    "adapter_version": ADAPTER_VERSION,
    "columns": COLUMNS,
    "time_domain": "simulation",
    "supported_kinds": ["laboratory", "vital"],
    "source_parent": "Pinned artifact-source UUID and adapter-run raw input artifact",
    "empty_result": "Requires explicit missing_reason; never zero",
    "scope": "Wholly synthetic engineering fixture; not a real cohort dictionary",
}


class AdapterInput(Contract):
    adapter_version: Literal["engineering-clinical-csv/1"]
    source_version_id: UUID
    mapping_id: UUID
    timeline_origin_id: UUID
    sha256: Hash
    content_base64: SecretStr = Field(
        min_length=1, max_length=1400000, json_schema_extra={"writeOnly": True}
    )


class AdapterReport(Contract):
    id: UUID
    adapter_version: Literal["engineering-clinical-csv/1"] = "engineering-clinical-csv/1"
    dictionary_sha256: Hash
    status: Literal["staged", "quarantined"]
    source_version_id: UUID
    input_artifact_id: UUID
    output_artifact_id: UUID | None
    input_sha256: Hash
    output_sha256: Hash | None
    rows_seen: int
    rows_mapped: int
    issues: list[RuleIssue]
    verification_scope: Literal["synthetic_engineering_fixture_only"] = (
        "synthetic_engineering_fixture_only"
    )
    unsupported_capabilities: list[str] = [
        "Real cohort import",
        "Pathology inference",
        "Calendar dates",
        "DCE follow-up inference",
        "Imaging and longitudinal case validation",
    ]
    next_action: str


def parse_fixture_csv(raw, origin_id):
    """Pure deterministic transform; preserve original text/units and explicit absence."""
    issues: list[RuleIssue] = []
    output = []
    seen = set()
    rows_seen = 0
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
        if reader.fieldnames != COLUMNS:
            raise ValueError("Unsupported header")
        for index, row in enumerate(reader):
            rows_seen += 1
            if rows_seen > 100:
                raise ValueError("Row limit")
            path = f"/rows/{index}"
            try:
                if None in row or any(v is None or len(v) > 1000 for v in row.values()):
                    raise ValueError("Corrupt row")
                if row["record_key"] in seen:
                    raise ValueError("Duplicate identity")
                seen.add(row["record_key"])
                if row["relative_day"]:
                    time = {
                        "reference": {
                            "basis": "relative_day",
                            "value": row["relative_day"],
                            "time_domain": "simulation",
                            "timeline_origin_id": str(origin_id),
                        },
                        "precision": "relative_day",
                    }
                else:
                    time = {
                        "reference": {
                            "basis": "unknown",
                            "missing_reason": "not_recorded",
                            "time_domain": "simulation",
                        },
                        "precision": "unknown",
                    }
                if row["missing_reason"]:
                    if row["value"] or row["qualifier"] or row["unit"]:
                        raise ValueError("Missing with value")
                    result = {"form": "missing", "missing_reason": row["missing_reason"]}
                    original_value, original_unit = None, None
                else:
                    quantity = {"value": row["value"], "unit": row["unit"]}
                    result = (
                        {"form": "censored", "comparator": row["qualifier"], "threshold": quantity}
                        if row["qualifier"]
                        else {"form": "exact", "quantity": quantity}
                    )
                    original_value, original_unit = row["qualifier"] + row["value"], row["unit"]
                item = TypeAdapter(ClinicalInput).validate_python(
                    {
                        "kind": row["kind"],
                        "concept": row["concept"],
                        "client_record_key": row["record_key"],
                        "source_locator_id": uuid4(),
                        "time": time,
                        "original_term": row["original_term"],
                        "certainty": "documented",
                        "negation": "affirmed",
                        "result": result,
                        "original_value": original_value,
                        "original_unit": original_unit,
                    }
                )
                if item.kind not in ("laboratory", "vital"):
                    raise ValueError("Unsupported kind")
                _, findings = semantic_validation(item, path)
                if findings:
                    issues.extend(RuleIssue.model_validate(finding) for finding in findings)
                value = item.model_dump(mode="json")
                value.pop("source_locator_id")
                output.append(value)
            except (ValidationError, ValueError):
                issues.append(
                    RuleIssue(
                        rule_id="ADAPTER-ROW-1",
                        severity="error",
                        path=path,
                        reason="Unsupported/corrupt row, missingness or duplicate source record key",
                        next_action="Repair this row against the versioned fixture dictionary",
                    )
                )
    except (ValueError, UnicodeError, csv.Error):
        issues.append(
            RuleIssue(
                rule_id="ADAPTER-SCHEMA-1",
                severity="error",
                path="/header",
                reason="Encoding, header/schema or row-count mismatch",
                next_action="Use the exact approved adapter version and dictionary",
            )
        )
    document = {
        "schema_version": "clinical-source/1",
        "fixture_origin": "SYNTHETIC_ENGINEERING_FIXTURE",
        "records": output,
    }
    return (
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode(),
        rows_seen,
        output,
        issues,
    )


def run_adapter(connection, identity, project, patient, value: AdapterInput, storage):
    authorize_project(identity, project, "admin")
    authorize_patient(connection, identity, project, patient, edit=True)
    lock_lineage(connection, project, patient)
    require_source_action(
        connection, identity, project, value.source_version_id, SourceAction.INTERNAL
    )
    require_source_action(
        connection, identity, project, value.source_version_id, SourceAction.DERIVATIVE
    )
    source, release = release_for(connection, identity, project, value.source_version_id)
    if source.origin != "synthetic_engineering_fixture":
        raise HTTPException(409)
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
    # A source/patient/config fingerprint makes repeated delivery one adapter run.
    fingerprint = science_hash(
        {
            "source": str(source.id),
            "mapping": str(value.mapping_id),
            "origin": str(value.timeline_origin_id),
            "sha256": digest,
            "dictionary": science_hash(DICTIONARY),
        }
    )
    connection.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:s,0))"),
        {"s": f"adapter:{project}:{patient}:{fingerprint}"},
    )
    previous = connection.execute(
        text(
            "SELECT report FROM source.adapter_runs WHERE project_id=:p AND patient_id=:u AND input_hash=:hash"
        ),
        {"p": project, "u": patient, "hash": fingerprint},
    ).scalar_one_or_none()
    if previous:
        return AdapterReport.model_validate(previous)
    output_bytes, rows_seen, rows, issues = parse_fixture_csv(raw, value.timeline_origin_id)
    for index, row in enumerate(rows):
        item = TypeAdapter(ClinicalInput).validate_python({**row, "source_locator_id": uuid4()})
        try:
            check_time(connection, project, patient, item.time)
        except HTTPException:
            issues.append(
                RuleIssue(
                    rule_id="ADAPTER-TIME-1",
                    severity="error",
                    path=f"/rows/{index}/relative_day",
                    reason="Timeline origin is not owned by this patient/domain",
                    next_action="Choose the patient's explicit simulation origin",
                )
            )
    if rows_seen == 0:
        issues.append(
            RuleIssue(
                rule_id="ADAPTER-EMPTY-1",
                severity="error",
                path="/rows",
                reason="No supported source records",
                next_action="Provide a nonempty approved source subset",
            )
        )
    stored = storage.write_verified(project, raw)
    raw_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO ops.artifacts(id,project_id,patient_id,object_key,object_version,byte_size,sha256,provenance,availability) VALUES(:id,:p,:u,:key,:v,:size,:hash,'SYNTHETIC_GENERATED','verified')"
        ),
        {
            "id": raw_id,
            "p": project,
            "u": patient,
            "key": stored.key,
            "v": stored.version,
            "size": stored.byte_size,
            "hash": stored.sha256,
        },
    )
    output_id, output_hash = None, None
    register_root(
        connection,
        identity,
        project,
        patient,
        raw_id,
        "metadata_source_artifact",
        digest,
        source.id,
    )
    if not any(issue.severity == "error" for issue in issues):
        output_hash = hashlib.sha256(output_bytes).hexdigest()
        parent = get_component_source(source)
        derived_source = add_source(
            connection,
            identity,
            project,
            SourceVersionInput.model_validate(
                {
                    **parent,
                    "record_key": "adapter-derived-" + str(uuid4()),
                    "version": 1,
                    "manifest_sha256": output_hash,
                }
            ),
        )
        receipt = upload_source(
            connection,
            identity,
            project,
            patient,
            ClinicalSourceUpload(
                source_version_id=derived_source.id,
                mapping_id=value.mapping_id,
                sha256=output_hash,
                content_base64=SecretStr(base64.b64encode(output_bytes).decode()),
            ),
            storage,
            lineage_parents=[raw_id],
            processing=processing_spec(
                __file__,
                ADAPTER_VERSION,
                ADAPTER_VERSION,
                {"dictionary_sha256": science_hash(DICTIONARY)},
            ),
        )
        output_id = receipt.artifact_id
    report = AdapterReport(
        id=uuid4(),
        dictionary_sha256=science_hash(DICTIONARY),
        status="quarantined" if output_id is None else "staged",
        source_version_id=source.id,
        input_artifact_id=raw_id,
        output_artifact_id=output_id,
        input_sha256=digest,
        output_sha256=output_hash,
        rows_seen=rows_seen,
        rows_mapped=len(rows),
        issues=issues,
        next_action="Repair the mapped row/schema issues and submit new source bytes"
        if output_id is None
        else "Validate the derived clinical-source artifact before accepting records",
    )
    connection.execute(
        text(
            "INSERT INTO source.adapter_runs(id,project_id,patient_id,source_version_id,input_artifact_id,output_artifact_id,input_hash,report) VALUES(:id,:p,:u,:s,:raw,:out,:hash,CAST(:report AS jsonb))"
        ),
        {
            "id": report.id,
            "p": project,
            "u": patient,
            "s": source.id,
            "raw": raw_id,
            "out": output_id,
            "hash": fingerprint,
            "report": report.model_dump_json(),
        },
    )
    audit(connection, project, report.id, "METADATA_ADAPTER_RUN")
    return report


def get_component_source(source):
    # Retain source URL/citation/attribution/release hierarchy; run record pins exact CSV parent.
    return SourceVersionInput.model_validate(
        {key: getattr(source, key) for key in SourceVersionInput.model_fields}
    ).model_dump(mode="json")
