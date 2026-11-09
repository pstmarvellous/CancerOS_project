"""REC-09 full-chain seed: case + image + mask binding + alignment + annotation + QC.

Artificial engineering records only, against the disposable product fixture API.
Writes .local/rec09-fullchain-seed.json for the browser spec.
"""

import base64
import hashlib
import json
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
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.status, json.loads(response.read().decode() or "{}")


def nifti_bytes(array, affine):
    image = nib.Nifti1Image(array, affine)
    image.header.set_xyzt_units("mm")
    image.header["descrip"] = b"ARTIFICIAL PRIVATE HEADER DO NOT EXPOSE"
    return image.to_bytes()


def create_artifact_source(api, admin, project, component, record_key, raw, key):
    digest = hashlib.sha256(raw).hexdigest()
    status, source = call(
        api, admin, "POST", "/api/v1/projects/%s/sources" % project,
        {
            "record_key": record_key,
            "version": 1,
            "kind": "artifact_source",
            "parent_version_id": component,
            "title": "REC-09 synthetic bytes " + record_key,
            "source_url": "https://example.org/" + record_key,
            "citation": "REC-09 synthetic bytes",
            "accession": record_key.upper(),
            "retrieved_on": "2026-11-09",
            "manifest_sha256": digest,
            "license_reference": "synthetic engineering fixture",
            "attribution": "CancerOS synthetic engineering fixture",
            "access_conditions": "fixture only",
            "retention_policy": "fixture only",
            "availability": "available",
            "origin": "synthetic_engineering_fixture",
        },
        key,
    )
    assert status == 201, (status, source)
    return source["id"], digest


def main() -> int:
    bundle = json.load(open(".local/product-browser-fixture.json", encoding="utf-8"))
    assert bundle["synthetic_only"] is True
    api = bundle["api_url"]
    project = bundle["project_id"]
    admin = bundle["admin_token"]
    tag = uuid.uuid4().hex[:8].upper()
    pseudonym = "REC09-FULL-" + tag
    key = lambda name: "rec09-full-%s-%s" % (name, tag)

    status, case = call(
        api, admin, "POST", "/api/v1/projects/%s/research-cases" % project,
        {
            "source_version_id": bundle["source_version_id"],
            "case_identifier": pseudonym,
            "title": "REC-09 Full Chain Case",
            "pseudonym": pseudonym,
            "status": "draft",
            "sex": "not_recorded",
            "age_at_observation": None,
            "age_observed_on": None,
            "profile_source_reference": "Artificial register entry 094",
            "medical_history": None,
        },
        key("case"),
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
    component_id = component["id"]

    image_raw = nifti_bytes(
        np.arange(24, dtype=np.int16).reshape(3, 4, 2), np.diag([2.0, 3.0, 4.0, 1.0])
    )
    image_source, image_digest = create_artifact_source(
        api, admin, project, component_id, "rec09-full-img-" + tag.lower(), image_raw, key("imgsrc")
    )
    status, mapping = call(
        api, admin, "POST", "/api/v1/projects/%s/source-patient-resolutions" % project,
        {"source_version_id": image_source, "source_patient_key": pseudonym},
        key("map"),
    )
    assert status == 200, (status, mapping)
    assert mapping["patient_id"] == patient
    mapping_id = mapping["mapping_id"]

    status, staged = call(
        api, admin, "POST",
        "/api/v1/projects/%s/patients/%s/imaging-files" % (project, patient),
        {
            "source_version_id": image_source,
            "mapping_id": mapping_id,
            "format": "nifti",
            "sha256": image_digest,
            "content_base64": base64.b64encode(image_raw).decode(),
        },
    )
    assert status == 201, (status, staged)

    study_id, series_id = str(uuid.uuid4()), str(uuid.uuid4())
    status, preview = call(
        api, admin, "POST",
        "/api/v1/projects/%s/patients/%s/imaging-import-previews" % (project, patient),
        {
            "file_ids": [staged["artifact_id"]],
            "association": {
                "mapping_id": mapping_id,
                "study_id": study_id,
                "series_id": series_id,
                "source_study_key": "REC09-FULL-STUDY",
                "source_series_key": "REC09-FULL-SERIES",
                "sequence": "t1",
                "acquisition_time_status": "not_recorded",
                "association_basis": "administrator_manifest_attestation",
                "evidence_sha256": "e" * 64,
            },
        },
    )
    assert status == 201 and preview["status"] == "awaiting_confirmation", (status, preview)
    status, confirmed = call(
        api, admin, "POST",
        "/api/v1/projects/%s/patients/%s/imaging-imports/%s/confirmations"
        % (project, patient, preview["id"]),
    )
    assert status == 200, (status, confirmed)

    status, geometry = call(
        api, admin, "POST",
        "/api/v1/projects/%s/patients/%s/geometry-validations" % (project, patient),
        {"import_id": preview["id"]},
    )
    assert status == 201 and geometry["status"] == "valid", (status, geometry)
    volume_id = geometry["volume_artifact_id"]

    mask_array = np.zeros((3, 4, 2), dtype=np.uint16)
    mask_array[1, 1, 0] = 1
    mask_array[1, 2, 1] = 2
    mask_raw = nifti_bytes(mask_array, np.diag([2.0, 3.0, 4.0, 1.0]))
    mask_source, mask_digest = create_artifact_source(
        api, admin, project, component_id, "rec09-full-mask-" + tag.lower(), mask_raw, key("masksrc")
    )
    status, mask_staged = call(
        api, admin, "POST",
        "/api/v1/projects/%s/patients/%s/imaging-files" % (project, patient),
        {
            "source_version_id": mask_source,
            "mapping_id": mapping_id,
            "format": "nifti",
            "sha256": mask_digest,
            "content_base64": base64.b64encode(mask_raw).decode(),
        },
    )
    assert status == 201, (status, mask_staged)

    status, binding = call(
        api, admin, "POST",
        "/api/v1/projects/%s/patients/%s/mask-associations" % (project, patient),
        {
            "mask_file_id": mask_staged["artifact_id"],
            "target_image_id": volume_id,
            "expected_study_id": study_id,
            "evidence_sha256": "a" * 64,
        },
    )
    assert status == 201, (status, binding)

    status, aligned = call(
        api, admin, "POST",
        "/api/v1/projects/%s/patients/%s/mask-alignments" % (project, patient),
        {
            "association_id": binding["id"],
            "mask_file_id": mask_staged["artifact_id"],
            "target_image_id": volume_id,
            "mask_study_id": study_id,
            "association_evidence_sha256": "a" * 64,
            "config": {"expected_labels": [1, 2]},
        },
    )
    assert status == 201, (status, aligned)

    status, batch = call(
        api, admin, "POST",
        "/api/v1/projects/%s/patients/%s/annotation-batches" % (project, patient),
        {
            "alignment_run_id": aligned["id"],
            "annotation_class": "anatomical_tumor_contour",
            "authorship": "unknown",
            "labels": [
                {"label": 1, "meaning": "tumor_region"},
                {"label": 2, "meaning": "tumor_region"},
            ],
            "source_annotation_evidence_sha256": "c" * 64,
        },
    )
    assert status == 201, (status, batch)
    segmentations = batch["segmentation_ids"]

    qc_ids = []
    for index, segmentation in enumerate(segmentations):
        status, qc = call(
            api, admin, "POST",
            "/api/v1/projects/%s/patients/%s/segmentation-qc-reports" % (project, patient),
            {"segmentation_id": segmentation},
            key("qc-%d" % index),
        )
        assert status == 201, (status, qc)
        assert qc["technical"]["technical_status"] == "pass", qc
        qc_ids.append(qc["id"])

    status, measurement = call(
        api, admin, "POST",
        "/api/v1/projects/%s/patients/%s/physical-measurements" % (project, patient),
        {"segmentation_ids": segmentations, "expected_revision": 1},
        key("measure"),
    )
    assert status == 201, (status, measurement)
    assert measurement["values"]["availability"] == "available", measurement

    out = {
        "project_id": project,
        "patient_id": patient,
        "study_id": study_id,
        "import_id": preview["id"],
        "segmentation_ids": segmentations,
        "measurement_id": measurement["id"],
        "measurement_volume_mm3": measurement["values"].get("volume_mm3"),
    }

    import time

    def enqueue(command, key):
        status, job = call(
            api, admin, "POST",
            "/api/v1/projects/%s/patients/%s/imaging-jobs" % (project, patient),
            {"expected_revision": 1, "command": command},
            key,
        )
        assert status in (201, 202), (status, job)
        return job["id"]

    def poll(job_id):
        for _ in range(60):
            time.sleep(3)
            status, job = call(
                api, admin, "GET",
                "/api/v1/projects/%s/patients/%s/imaging-jobs/%s"
                % (project, patient, job_id),
            )
            assert status == 200, (status, job)
            if job["status"] in ("succeeded", "failed", "cancelled"):
                return job
        raise RuntimeError("job timed out: " + job_id)

    mesh_job = enqueue(
        {"operation": "mesh", "input": {"measurement_id": measurement["id"]}}, key("meshjob")
    )
    mesh_result = poll(mesh_job)
    assert mesh_result["status"] == "succeeded", mesh_result
    mesh_report_id = mesh_result["result_report_id"]

    qc_job = enqueue(
        {"operation": "mesh_qc", "input": {"mesh_run_id": mesh_report_id}}, key("meshqcjob")
    )
    qc_result = poll(qc_job)
    assert qc_result["status"] == "succeeded", qc_result
    mesh_qc_id = qc_result["result_report_id"]

    status, lesion = call(
        api, admin, "POST",
        "/api/v1/projects/%s/patients/%s/lesions" % (project, patient),
        {
            "baseline_segmentation_id": segmentations[0],
            "evidence_sha256": "a" * 64,
            "expected_revision": 1,
        },
        key("lesion"),
    )
    assert status == 201, (status, lesion)
    out["lesion_id"] = lesion["id"]
    out["mesh_qc_report_id"] = mesh_qc_id

    print(json.dumps(out))
    with open(".local/rec09-fullchain-seed.json", "w", encoding="utf-8") as stream:
        json.dump(out, stream)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
