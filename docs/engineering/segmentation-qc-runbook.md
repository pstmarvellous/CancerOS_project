# Technical segmentation QC

Use an owned label-specific segmentation UUID from the reference import:

```text
POST /api/v1/projects/{project_id}/patients/{patient_id}/segmentation-qc-reports
Idempotency-Key: case-qc-attempt-1
{"segmentation_id":"<annotation-uuid>","reference_segmentation_id":null,"rule_version":"segmentation-qc/1"}
```

GET the returned Location. The report separates technical pass/fail, independent
accuracy eligibility/exclusions, scientific review, attempt count and next action.
Retry with the same key/input for the same result; use a new key for another attempt.
Changing input under an existing key returns 409. Old attempts remain intact.

A passing technical report is not segmentation accuracy or anatomical approval.
Self/shared-mask comparison produces no accuracy score. All currently onboarded
objects are artificial with qualified review pending, so independent accuracy is
not_evaluated even if a reference UUID is supplied. No caller field can override
this evidence gate. Undefined metric quantities remain null.

```powershell
uv run python scripts/run_checks.py segmentation-qc
```

Uses known artificial overlap/distance/anisotropic/sheared/empty fixtures and actual
private SQL/S3/authenticated HTTP checks. Clinical thresholds, authentic reference
metrics, human review and a complete evaluation UI remain unestablished.
