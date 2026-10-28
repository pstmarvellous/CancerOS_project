# Reference annotation import

After a valid private mask alignment, an authorized patient editor can submit:

```text
POST /api/v1/projects/{project_id}/patients/{patient_id}/annotation-batches
{"alignment_run_id":"<owned-passing-alignment-uuid>","annotation_class":"anatomical_tumor_contour","authorship":"unknown","method_reference":null,"labels":[{"label":1,"meaning":"tumor_region"},{"label":2,"meaning":"tumor_region"}],"source_annotation_evidence_sha256":null}
```

This example records an unreviewed declaration with missing evidence; it grants no
anatomical claim. Supply actual known source metadata, never invented authorship,
review or model versions. Dictionary labels must equal all positive aligned labels.
Other classes use functional_region, bounding_region, region or unknown meanings
as required by the generated AnnotationInput schema.

GET the returned Location for the immutable batch and each
`/segmentations/{segmentation_id}` for class, label, source, geometry and permitted
uses. Two labels create two distinct annotation IDs; no cross-examination lesion
correspondence is implied. Unknown fields such as scientific_review are rejected.
Every result remains draft, pending technical QC and scientific review. A functional
or bounding annotation never grants anatomical volume/mesh permission.

```powershell
uv run python scripts/run_checks.py annotation-import
```

Actual tests use artificial labels/private SQL/S3 and JWT/SQL HTTP. They cover
distinct labels, missing authorship, label mismatch, failed/wrong-patient alignment,
source rights, immutable history and prohibited review assertions. No authentic
annotation, checkpoint, segmentation inference or qualified review is established.
Next: COS-031 technical QC. Optional COS-030 model inference stays disabled.
