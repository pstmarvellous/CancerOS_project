# Mask alignment and private overlay

Stage an approved artificial NIfTI label file through the imaging-file staging API.
Use an owned 3D canonical image or a COS-027 selected/preprocessed acquisition.

First an administrator POSTs `/mask-associations` with mask_file_id, target_image_id,
expected_study_id and evidence_sha256, then reviews/retains its returned ID. This is
an immutable fixture attestation, explicitly lacking real-source/qualified review.
Include that UUID as `association_id` in the alignment request below. The mask cannot
be silently rebound to another image/study. All displayed request fields must match
the stored association, and current source restrictions still apply.

```text
POST /api/v1/projects/{project_id}/patients/{patient_id}/mask-alignments
{"association_id":"<administrator-mask-association-uuid>","mask_file_id":"<staged-mask-uuid>","target_image_id":"<owned-image-artifact-uuid>","mask_study_id":"<recorded-study-uuid>","association_evidence_sha256":"<64-hex-source-evidence-hash>","config":{"expected_labels":[1,2],"mode":"exact_grid"}}
```

An authorized patient editor can submit/read runs. GET the returned Location; GET
`/mask-alignments/{id}/overlay` reads the private, rights-checked sampled overlay.
The overlay has target indices, intensity/label rows and sampling limits; use the
report's full target geometry to locate it physically. No signed/public URL exists.

For a justified resampling, explicitly choose nearest_neighbor and supply a proper
rigid `source_to_target_world` 4×4 matrix plus `transform_kind:"rigid"`. Direction is
source RAS-mm world to target RAS-mm world; the service computes its inverse pull
mapping. This declaration does not establish that a registration is anatomically
valid. A study mismatch, clipping, invalid label, unexpected component or excessive
physical-volume change blocks. Supply corrected source metadata/evidence rather
than resizing until the overlay looks plausible.

```powershell
uv run python scripts/run_checks.py mask-alignment
```

Checks exercise translated/rotated/reflected/anisotropic fixtures, exact labels,
source preservation, clipping, private SQL/S3 runs, study/patient/source rights and
actual JWT/SQL HTTP roles. A passing run stays aligned_pending_review and draft.
Annotation meaning, qualified review and authentic-case evaluation remain separate.
