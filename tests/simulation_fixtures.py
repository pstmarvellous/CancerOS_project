"""Actual private imaging pipeline on a purely artificial large-grid engineering cube."""

from uuid import uuid4

import nibabel as nib
import numpy as np
from sqlalchemy import text
from test_annotation_import import command_for
from test_imaging_ingestion import preview_command, stage
from test_lesion_tracking import event, lesion

from canceros.alignment_runs import AlignmentInput, run_alignment
from canceros.annotation_contracts import LabelDefinition
from canceros.annotation_import import import_annotations
from canceros.imaging_ingestion import confirm_import, preview_imaging
from canceros.imaging_volumes import GeometryValidationInput, validate_volume
from canceros.mask_alignment import AlignmentConfig
from canceros.mask_associations import MaskAssociationInput, bind_mask
from canceros.measurement_runs import MeasurementInput, create_measurement
from canceros.segmentation_reviews import SegmentationQCInput, run_segmentation_qc


def setup_simulation_baseline(data):
    """Return (216 mm³ measurement, simulation origin, baseline association).

    The same returned measurement can seed all five isolated branches. No authentic
    examination, reviewed contour or real patient baseline is asserted by this fixture.
    """
    c, i, p, patient, _, storage, config = data
    u = patient.patient_id
    image = nib.Nifti1Image(np.arange(24**3, dtype=np.int16).reshape((24, 24, 24)), np.eye(4))
    image.header.set_xyzt_units("mm")
    image.header["descrip"] = b"ARTIFICIAL ENGINEERING FIXTURE"
    receipt, _ = stage(data, image.to_bytes())
    imported = preview_imaging(c, i, p, u, preview_command(patient, receipt), storage, config)
    confirm_import(c, i, p, u, imported.id)
    volume = validate_volume(c, i, p, u, GeometryValidationInput(import_id=imported.id), storage)
    assert volume.status == "valid" and volume.volume_artifact_id
    mask_data = np.zeros((24, 24, 24), dtype=np.uint16)
    mask_data[9:15, 9:15, 9:15] = 1
    mask = nib.Nifti1Image(mask_data, np.eye(4))
    mask.header.set_xyzt_units("mm")
    mask_receipt, _ = stage(data, mask.to_bytes())
    binding = bind_mask(
        c,
        i,
        p,
        u,
        MaskAssociationInput(
            mask_file_id=mask_receipt.artifact_id,
            target_image_id=volume.volume_artifact_id,
            expected_study_id=imported.study_id,
            evidence_sha256="a" * 64,
        ),
        storage,
    )
    alignment = run_alignment(
        c,
        i,
        p,
        u,
        AlignmentInput(
            association_id=binding.id,
            mask_file_id=mask_receipt.artifact_id,
            target_image_id=volume.volume_artifact_id,
            mask_study_id=imported.study_id,
            association_evidence_sha256="a" * 64,
            config=AlignmentConfig(expected_labels=(1,), mode="exact_grid"),
        ),
        storage,
    )
    assert alignment.status == "aligned_pending_review"
    batch = import_annotations(
        c,
        i,
        p,
        u,
        command_for(alignment).model_copy(
            update={
                "labels": (LabelDefinition(label=1, meaning="tumor_region"),),
                "method_reference": "engineering_fixture_mask",
            }
        ),
        storage,
    )
    segmentation = batch.segmentation_ids[0]
    run_segmentation_qc(
        c,
        i,
        p,
        u,
        SegmentationQCInput(segmentation_id=segmentation),
        storage,
        "simulation-baseline-qc",
    )
    measurement = create_measurement(
        c,
        i,
        p,
        u,
        MeasurementInput(segmentation_ids=[segmentation], expected_revision=1),
        storage,
        "simulation-baseline-measurement",
    )
    assert measurement.values.exact_volume_mm3 == "216"
    assert measurement.origin == "SYNTHETIC_GENERATED"
    origin = uuid4()
    c.execute(
        text(
            "INSERT INTO source.timeline_origins(id,project_id,patient_id,reference_meaning,time_domain) "
            "VALUES(:id,:p,:u,'Artificial simulation cube baseline day zero','simulation')"
        ),
        {"id": origin, "p": p, "u": u},
    )
    identity = lesion(data, segmentation, "simulation-baseline-lesion")
    association = event(
        data, identity, segmentation, measurement, origin, 0, "simulation-baseline-association"
    )
    return measurement, origin, association
