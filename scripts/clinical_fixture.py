"""Run the private clinical HTTP pathway on disposable data, using ephemeral test identity."""

import base64
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from canceros.api import create_app
from canceros.persistence import load_revision
from canceros.settings import Settings

ROOT = Path(__file__).resolve().parents[1]


def run():
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(ROOT / ".env").get(
        "TEST_DATABASE_URL"
    )
    if not url or "disposable" not in (make_url(url).database or ""):
        raise RuntimeError("Explicit disposable test database required")
    project, user = uuid4(), uuid4()
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        private.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    config = Settings(
        mode="test",
        database_url=url,
        identity_public_key=public,
        linkage_active_key="fixture-ephemeral",
        linkage_keys={"fixture-ephemeral": base64.b64encode(os.urandom(32)).decode()},
    )
    engine = create_engine(url, hide_parameters=True)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO access.projects(id,name) VALUES(:id,'SYNTHETIC clinical HTTP fixture')"
            ),
            {"id": project},
        )
        connection.execute(
            text("INSERT INTO access.users(id,issuer,subject) VALUES(:id,:issuer,:subject)"),
            {"id": user, "issuer": config.identity_issuer, "subject": str(user)},
        )
        connection.execute(
            text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:u,'admin')"),
            {"p": project, "u": user},
        )
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user),
            "iss": config.identity_issuer,
            "aud": config.identity_audience,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=10),
        },
        private,
        algorithm="RS256",
    )
    headers = {"Authorization": "Bearer " + token}
    base = f"/api/v1/projects/{project}"
    steps = []

    with TestClient(create_app(config)) as client:

        def post(path, value, expected=200, key=None):
            response = client.post(
                path, json=value, headers={**headers, "Idempotency-Key": key or str(uuid4())}
            )
            if response.status_code != expected:
                raise RuntimeError(f"Synthetic workflow HTTP {response.status_code}")
            return response.json()

        def source(kind, parent=None, checksum="a" * 64):
            return post(
                base + "/sources",
                {
                    "record_key": "engineering-" + str(uuid4()),
                    "version": 1,
                    "kind": kind,
                    "parent_version_id": parent,
                    "title": "SYNTHETIC ENGINEERING FIXTURE",
                    "source_url": "https://example.org/canceros-clinical-fixture",
                    "citation": "CancerOS artificial fixture; no clinical cohort",
                    "accession": "ENGINEERING-ONLY",
                    "retrieved_on": now.date().isoformat(),
                    "manifest_sha256": checksum,
                    "license_reference": "EXAMPLE ONLY; not a real source license",
                    "attribution": "CancerOS synthetic engineering fixture",
                    "access_conditions": "Private disposable test only",
                    "retention_policy": "Discard artificial test data under local development policy",
                    "availability": "available",
                    "origin": "synthetic_engineering_fixture",
                },
                expected=201,
            )["id"]

        collection = source("collection")
        release = source("release", collection)
        component = source("component", release)
        post(
            base + f"/sources/{component}/rights-reviews",
            {
                "action": "internal_processing",
                "decision": "allowed",
                "basis": "engineering_fixture_example",
                "evidence_reference": "Artificial example only; no real reviewer or dataset approval",
                "evidence_sha256": "b" * 64,
                "valid_until": (now + timedelta(hours=1)).isoformat(),
            },
            expected=201,
        )
        post(
            base + f"/sources/{component}/rights-reviews",
            {
                "action": "derivative_creation",
                "decision": "allowed",
                "basis": "engineering_fixture_example",
                "evidence_reference": "Artificial example only; no real dataset rights",
                "evidence_sha256": "b" * 64,
                "valid_until": (now + timedelta(hours=1)).isoformat(),
            },
            expected=201,
        )
        mapping_source = source("artifact_source", component)
        patient = post(
            base + "/source-patient-resolutions",
            {
                "source_version_id": mapping_source,
                "source_patient_key": "ARTIFICIAL-PRIVATE-LINKAGE-" + str(uuid4()),
            },
        )
        patient_path = base + f"/patients/{patient['patient_id']}"
        origin = post(
            patient_path + "/timeline-origins",
            {
                "reference_meaning": "Artificial day zero; no calendar date",
                "time_domain": "simulation",
            },
            expected=201,
        )
        steps.append(
            "Authenticated fixture registry, rights scope, encrypted mapping and relative origin"
        )

        def stage(value):
            raw = json.dumps(
                {
                    "schema_version": "clinical-source/1",
                    "fixture_origin": "SYNTHETIC_ENGINEERING_FIXTURE",
                    "records": [
                        {
                            "kind": "laboratory",
                            "concept": "hemoglobin",
                            "client_record_key": "artificial-hgb-1",
                            "time": {
                                "reference": {
                                    "basis": "relative_day",
                                    "value": "0",
                                    "time_domain": "simulation",
                                    "timeline_origin_id": origin["id"],
                                },
                                "precision": "relative_day",
                            },
                            "original_term": "Artificial HGB row; no patient observation",
                            "certainty": "documented",
                            "negation": "affirmed",
                            "result": {
                                "form": "exact",
                                "quantity": {"value": value, "unit": "g/dL"},
                            },
                            "original_value": value,
                            "original_unit": "g/dL",
                        }
                    ],
                },
                separators=(",", ":"),
            ).encode()
            digest = hashlib.sha256(raw).hexdigest()
            source_id = source("artifact_source", component, digest)
            receipt = post(
                patient_path + "/clinical-source-artifacts",
                {
                    "source_version_id": source_id,
                    "mapping_id": patient["mapping_id"],
                    "sha256": digest,
                    "content_base64": base64.b64encode(raw).decode(),
                },
                expected=201,
            )
            return receipt["artifact_id"], digest

        first, first_hash = stage("12.5")
        command = {"source_artifact_id": first, "expected_revision": 1}
        assert post(patient_path + "/observation-batches/validations", command)["status"] == "valid"
        accepted = post(patient_path + "/observation-batches", command, key="fixture-original")
        assert accepted["status"] == "accepted" and accepted["result_revision"] == 2
        assert (
            post(patient_path + "/observation-batches", command, key="fixture-original") == accepted
        )
        steps.append(
            "Private versioned source bytes, validate-first batch, atomic accept and retry"
        )
        second, second_hash = stage("13.5")
        corrected = post(
            patient_path + "/observation-batches",
            {
                "source_artifact_id": second,
                "expected_revision": 2,
                "corrects_record_id": accepted["record_ids"][0],
            },
            key="fixture-correction",
        )
        assert corrected["result_revision"] == 3
        with engine.connect() as connection:
            assert (
                load_revision(connection, project, patient["patient_id"], 2)["members"]
                == accepted["record_ids"]
            )
            assert (
                load_revision(connection, project, patient["patient_id"], 3)["members"]
                == corrected["record_ids"]
            )
        old = client.get(
            patient_path + "/observations/" + accepted["record_ids"][0], headers=headers
        )
        assert old.status_code == 200 and old.json()["item"]["original_value"] == "12.5"
        assert (
            old.json()["origin"] == "SYNTHETIC_GENERATED" and old.json()["publication"] == "draft"
        )
        steps.append(
            "Correction appends revision N+1 while revision N and original value remain unchanged"
        )
        retracted = post(
            patient_path + "/observations/" + corrected["record_ids"][0] + "/retractions",
            {"expected_revision": 3, "reason_code": "entered_in_error"},
            key="fixture-retraction",
        )
        assert retracted["revision"] == 4
        with engine.connect() as connection:
            assert load_revision(connection, project, patient["patient_id"], 4)["members"] == []
        steps.append("Explicit retraction, immutable history and unpublished state")
        quality = post(patient_path + "/quality-reports", {"expected_revision": 4}, expected=201)
        assert quality["report"]["clinical_record_count"] == 0 and not quality["stale"]
        split = post(
            base + "/evaluation-splits",
            {"seed": 17, "assignments": [{"patient_id": patient["patient_id"], "role": "train"}]},
            expected=201,
        )
        leakage = client.get(base + f"/evaluation-splits/{split['id']}/leakage", headers=headers)
        assert leakage.status_code == 200 and leakage.json()["cross_role_group_overlap_count"] == 0
        assert not split["independent_real_evaluation_cleared"]
        steps.append(
            "Capability-specific quality snapshot and frozen fixture patient grouping with leakage report"
        )
        provenance = client.get(
            patient_path + f"/resources/{corrected['record_ids'][0]}/provenance", headers=headers
        )
        assert (
            provenance.status_code == 200 and provenance.json()["origin"] == "SYNTHETIC_GENERATED"
        )
        withdrawn = post(
            patient_path + f"/resources/{first}/withdrawals",
            {"reason_code": "rights_withdrawn"},
            key="fixture-withdrawal",
        )
        assert corrected["record_ids"][0] in withdrawn["affected_descendant_ids"]
        updated_quality = client.get(
            patient_path + f"/quality-reports/{quality['report']['id']}", headers=headers
        )
        assert updated_quality.status_code == 200 and updated_quality.json()["stale"]
        steps.append(
            "Authorized lineage view, inherited withdrawal block and stale quality evidence"
        )
    engine.dispose()
    report = {
        "result": "passed",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Synthetic engineering fixture through real SQL/private S3 and authenticated in-process HTTP; no real patient validation",
        "steps_passed": steps,
        "source_manifest": {
            "schema": "clinical-source/1",
            "first_sha256": first_hash,
            "corrected_sha256": second_hash,
            "origin": "SYNTHETIC_ENGINEERING_FIXTURE",
        },
        "versions": {
            p: version(p) for p in ("fastapi", "pydantic", "sqlalchemy", "cryptography", "boto3")
        },
        "remaining_gates": [
            "D01/D03 approved real source and privacy/linkage review",
            "C06 scientific configuration review",
            "Later imaging and state publication tasks",
        ],
    }
    path = ROOT / "docs/engineering/evidence/clinical-fixture.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS synthetic clinical HTTP workflow; evidence:", path.relative_to(ROOT))


if __name__ == "__main__":
    run()
