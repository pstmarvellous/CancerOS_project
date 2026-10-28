# CPU preprocessing

With a confirmed import and valid geometry report, an authorized patient editor calls:

```text
POST /api/v1/projects/{project_id}/patients/{patient_id}/preprocessing-runs
{"volume_artifact_id":"<canonical-volume-uuid>","config":{"expected_sequence":"t1","method":"identity"}}
```

GET the returned Location for immutable details. `processed` remains draft/scientific
review pending. `blocked` has no output; check source sequence, finite intensities
and explicit phase evidence. Source files/canonical volumes remain unchanged.
`per_volume_zscore` is optional numerical preprocessing, not a clinical quantity.

For a 4D DCE source, use expected_sequence `dce` and selected_phase with `index`,
`role` (`precontrast`, `postcontrast`, `unknown`), `acquisition_offsets_seconds`
(one decimal string per phase in strictly increasing source order) and source
`evidence_sha256`. Do not invent offsets or treat this declaration as motion QC.
Only the chosen acquisition is processed; no phase fusion/clinical visit is created.

```powershell
uv run python scripts/run_checks.py imaging-preprocessing
```

Checks cover deterministic output, unchanged source/affine, source/hash/rights and
patient ownership, constants/nonfinite values, missing sequences, phase order and
held-out fit denial through COS-024. Uses wholly artificial fixtures with private
SQL/S3 and in-process HTTP. No real MRI evaluation or complete frontend is claimed.
