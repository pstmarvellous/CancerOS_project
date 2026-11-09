"""Prepare synthetic registered sources for browser upload; never stage source bytes.

Uses only the disposable fixture component's inherited engineering permissions.
All bytes, manifests and IDs are written under ignored .local/. No credentials print.
"""

import hashlib
import json
import uuid
from pathlib import Path

import nibabel as nib
import numpy as np
from seed_rec09_fullchain import call, create_artifact_source, nifti_bytes


def main():
    root = Path(__file__).resolve().parents[1]
    local = root / ".local"
    bundle = json.loads((local / "product-browser-fixture.json").read_text(encoding="utf-8"))
    assert bundle["synthetic_only"] is True
    api, token, project = bundle["api_url"], bundle["admin_token"], bundle["project_id"]
    tag = uuid.uuid4().hex[:8]
    pseudonym = "UPLOAD-ARTIFICIAL-" + tag.upper()
    prefix = f"/api/v1/projects/{project}"
    status, source = call(api, token, "GET", prefix + "/sources/" + bundle["source_version_id"])
    assert status == 200 and source["origin"] == "synthetic_engineering_fixture"
    status, component = call(api, token, "GET", prefix + "/sources/" + source["parent_version_id"])
    assert status == 200 and component["kind"] == "component"
    assert component["origin"] == "synthetic_engineering_fixture"
    status, case = call(
        api,
        token,
        "POST",
        prefix + "/research-cases",
        {
            "source_version_id": source["id"],
            "case_identifier": pseudonym,
            "title": "Browser Upload Synthetic Engineering Case",
            "pseudonym": pseudonym,
            "status": "draft",
            "sex": "not_recorded",
            "age_at_observation": None,
            "age_observed_on": None,
            "profile_source_reference": "Artificial upload audit entry",
            "medical_history": None,
        },
        "upload-case-" + tag,
    )
    assert status == 201
    patient = case["patient_id"]
    affine = np.diag([2.0, 3.0, 4.0, 1.0])
    image = nifti_bytes(np.arange(24, dtype=np.int16).reshape(3, 4, 2), affine)
    labels = np.zeros((3, 4, 2), dtype=np.uint16)
    labels[1:3, 1:3, :] = 1
    mask = nifti_bytes(labels, affine)
    # Confirm that the browser fixture bytes actually encode the claimed metadata.
    parsed = nib.Nifti1Image.from_bytes(image)
    assert parsed.header.get_xyzt_units()[0] == "mm"
    image_source, digest = create_artifact_source(
        api,
        token,
        project,
        component["id"],
        "upload-image-" + tag,
        image,
        "upload-image-source-" + tag,
    )
    mask_source, mask_digest = create_artifact_source(
        api,
        token,
        project,
        component["id"],
        "upload-mask-" + tag,
        mask,
        "upload-mask-source-" + tag,
    )
    status, mapping = call(
        api,
        token,
        "POST",
        prefix + "/source-patient-resolutions",
        {"source_version_id": image_source, "source_patient_key": pseudonym},
        "upload-map-" + tag,
    )
    assert status == 200 and mapping["patient_id"] == patient
    study, series = str(uuid.uuid4()), str(uuid.uuid4())
    image_manifest = {
        "source_version_id": image_source,
        "mapping_id": mapping["mapping_id"],
        "association": {
            "mapping_id": mapping["mapping_id"],
            "study_id": study,
            "series_id": series,
            "source_study_key": "ARTIFICIAL-UPLOAD-STUDY-" + tag,
            "source_series_key": "ARTIFICIAL-UPLOAD-SERIES-" + tag,
            "sequence": "t1",
            "acquisition_time_status": "not_recorded",
            "association_basis": "administrator_manifest_attestation",
            "evidence_sha256": hashlib.sha256(b"synthetic association " + tag.encode()).hexdigest(),
        },
    }
    mask_manifest = {
        "source_version_id": mask_source,
        "mapping_id": mapping["mapping_id"],
        "evidence_sha256": hashlib.sha256(
            b"synthetic mask association " + tag.encode()
        ).hexdigest(),
        "annotation_class": "functional_enhancement_region",
        "authorship": "unknown",
        "method_reference": "engineering_fixture_mask",
        "labels": [{"label": 1, "meaning": "functional_region"}],
    }
    image_path, mask_path = local / "recovery-upload-image.nii", local / "recovery-upload-mask.nii"
    image_path.write_bytes(image)
    mask_path.write_bytes(mask)
    (local / "recovery-upload-study-manifest.json").write_text(
        json.dumps(image_manifest), encoding="utf-8"
    )
    (local / "recovery-upload-mask-manifest.json").write_text(
        json.dumps(mask_manifest), encoding="utf-8"
    )
    status, imports = call(api, token, "GET", prefix + f"/patients/{patient}/imaging-imports")
    assert status == 200 and imports["items"] == [], "Browser must perform the actual upload"
    (local / "recovery-upload.json").write_text(
        json.dumps(
            {
                "synthetic_only": True,
                "project_id": project,
                "patient_id": patient,
                "study_id": study,
                "image_path": str(image_path),
                "mask_path": str(mask_path),
                "image_manifest": image_manifest,
                "mask_manifest": mask_manifest,
                "image_sha256": digest,
                "mask_sha256": mask_digest,
                "expected_region_volume_mm3": "192",
                "pre_browser_import_count": 0,
            }
        ),
        encoding="utf-8",
    )
    print("Prepared synthetic browser-upload fixture; no imaging bytes staged by setup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
