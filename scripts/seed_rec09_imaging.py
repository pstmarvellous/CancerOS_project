"""REC-09 Journey C seed: research case plus staged/confirmed synthetic NIfTI study.

Artificial engineering records only, against the disposable product fixture API.
Prints project/patient/study/import IDs as JSON for the browser spec.
"""

import base64
import hashlib
import json
import sys
import urllib.request
import uuid

import nibabel as nib
import numpy as np


def call(api, token, method, path, body=None, key=None):
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    request = urllib.request.Request(
        api + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.status, json.loads(response.read().decode() or "{}")


def main() -> int:
    bundle = json.load(open(".local/product-browser-fixture.json", encoding="utf-8"))
    assert bundle["synthetic_only"] is True
    api = bundle["api_url"]
    project = bundle["project_id"]
    admin = bundle["admin_token"]
    pseudonym = "REC09-IMAGING-%s" % uuid.uuid4().hex[:8].upper()

    image = nib.Nifti1Image(
        np.arange(24, dtype=np.int16).reshape(3, 4, 2), np.diag([2.0, 3.0, 4.0, 1.0])
    )
    image.header.set_xyzt_units("mm")
    image.header["descrip"] = b"ARTIFICIAL PRIVATE HEADER DO NOT EXPOSE"
    raw = image.to_bytes()
    digest = hashlib.sha256(raw).hexdigest()

    status, case = call(
        api, admin, "POST", "/api/v1/projects/%s/research-cases" % project,
        {
            "source_version_id": bundle["source_version_id"],
            "case_identifier": pseudonym,
            "title": "REC-09 Imaging Acceptance Case",
            "pseudonym": pseudonym,
            "status": "draft",
            "sex": "not_recorded",
            "age_at_observation": None,
            "age_observed_on": None,
            "profile_source_reference": "Artificial register entry 093",
            "medical_history": None,
        },
        "rec09-case-" + pseudonym,
    )
    assert status == 201, (status, case)
    patient = case["patient_id"]

    status, fixture_source = call(
        api, admin, "GET", "/api/v1/projects/%s/sources/%s" % (project, bundle["source_version_id"])
    )
    assert status == 200, (status, fixture_source)
    status, component = call(
        api, admin, "GET", "/api/v1/projects/%s/sources/%s" % (project, fixture_source["parent_version_id"])
    )
    assert status == 200 and component["kind"] == "component", (status, component)

    status, source = call(
        api, admin, "POST", "/api/v1/projects/%s/sources" % project,
        {
            "record_key": "rec09-nifti-%s" % uuid.uuid4().hex[:8],
            "version": 1,
            "kind": "artifact_source",
            "parent_version_id": component["id"],
            "title": "REC-09 synthetic NIfTI bytes",
            "source_url": "https://example.org/rec09-nifti",
            "citation": "REC-09 synthetic imaging bytes",
            "accession": "REC09-NIFTI-1",
            "retrieved_on": "2026-11-09",
            "manifest_sha256": digest,
            "license_reference": "synthetic engineering fixture",
            "attribution": "CancerOS synthetic engineering fixture",
            "access_conditions": "fixture only",
            "retention_policy": "fixture only",
            "availability": "available",
            "origin": "synthetic_engineering_fixture",
        },
        "rec09-source-" + pseudonym,
    )
    assert status == 201, (status, source)
    # Rights reviews attach at the component level; the fixture component
    # already carries current internal/derivative reviews covering this source.

    status, mapping = call(
        api, admin, "POST", "/api/v1/projects/%s/source-patient-resolutions" % project,
        {"source_version_id": source["id"], "source_patient_key": pseudonym},
        "rec09-map-" + pseudonym,
    )
    assert status == 200, (status, mapping)
    assert mapping["patient_id"] == patient, "case mapping mismatch"
    assert mapping["mapping_id"], "missing mapping"

    status, staged = call(
        api, admin, "POST",
        "/api/v1/projects/%s/patients/%s/imaging-files" % (project, patient),
        {
            "source_version_id": source["id"],
            "mapping_id": mapping["mapping_id"],
            "format": "nifti",
            "sha256": digest,
            "content_base64": base64.b64encode(raw).decode(),
        },
    )
    assert status == 201, (status, staged)

    study_id = str(uuid.uuid4())
    series_id = str(uuid.uuid4())
    status, preview = call(
        api, admin, "POST",
        "/api/v1/projects/%s/patients/%s/imaging-import-previews" % (project, patient),
        {
            "file_ids": [staged["artifact_id"]],
            "association": {
                "mapping_id": mapping["mapping_id"],
                "study_id": study_id,
                "series_id": series_id,
                "source_study_key": "REC09-STUDY",
                "source_series_key": "REC09-SERIES",
                "sequence": "t1",
                "acquisition_time_status": "not_recorded",
                "association_basis": "administrator_manifest_attestation",
                "evidence_sha256": "e" * 64,
            },
        },
    )
    assert status == 201, (status, preview)
    assert preview["status"] == "awaiting_confirmation", preview

    status, confirmed = call(
        api, admin, "POST",
        "/api/v1/projects/%s/patients/%s/imaging-imports/%s/confirmations"
        % (project, patient, preview["id"]),
    )
    assert status == 200, (status, confirmed)
    assert confirmed["status"] == "staged_pending_geometry", confirmed

    print(json.dumps({
        "project_id": project,
        "patient_id": patient,
        "study_id": study_id,
        "import_id": preview["id"],
    }))
    with open(".local/rec09-imaging-seed.json", "w", encoding="utf-8") as stream:
        json.dump({
            "project_id": project,
            "patient_id": patient,
            "study_id": study_id,
            "import_id": preview["id"],
        }, stream)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
