# COS-E2E-002 Demonstration Case Record

Selected subject: **ISPY1_1001** (`ISPY1_1001_spy1_vis1`, single visit).

## Files (read-only inspection; bytes verified from the extracted subset)

| File | Size (bytes) | SHA-256 (truncated) |
|---|---|---|
| `dce/ISPY1_1001_spy1_vis1_dce_aqc_0.nii.gz` | 2,247,717 | `ed8d2357…` |
| `mask/ISPY1_1001_spy1_vis1_mask.nii.gz` | 90,064 | `90be17ef…` |
| `BreastDCEDL_demo_data.tar.gz` (distribution) | 54,838,099 | MD5 `5b7d8701…` matches published `5b7d8701309c2c3807f8d126f7ddcede` |

Machine record: `docs/engineering/testing/browser-e2e/E2E-002-case-ISPY1_1001.json`
(produced by `scripts/demo_case_verify.py`, no DB writes, no identifiers logged).

## Technical verification (offline, nibabel)

- Shapes match: image and mask both `(30, 256, 256)`; affines identical.
- Mask labels: `{0, 1}`, foreground voxels: 17,331 (single foreground class).
- Headers: NIfTI-1 single-file, no extensions, vox_offset 352, float64.
- Chosen over ACRIN subjects for smallest size and the spy1/ISPY1 framing;
  ACRIN-6698-102212/103939/ISPY1-1002/1003 pair identically (affine-match True)
  and remain available alternatives.

## Permissions and blockers (explicit)

- Distribution license: **CC BY-NC 4.0** as shipped in the Zenodo record.
  No separate LICENSE file or per-case rights statement was found in the repo.
- **De-identification: no evidence found.** No de-identification report,
  consent record, or IRB statement is present in the workspace for these files.
- **Public/hackathon demo permission: NOT established.** The acquisition guide
  itself says to "confirm intended hackathon/public-demo rights."
- Consequence: real bytes were **not** provisioned into any database and were
  **not** transmitted anywhere. The rendered browser demonstration runs on the
  explicitly synthetic, correctly labeled fixture channel (§3–§4), never
  presented as this subject's anatomy.
- Additional engineering bound: the `bounded-imaging/1` parser requires
  millimeter spatial units and the staging contract caps payloads well below
  whole-breast file sizes; the demo files report `unknown` units, so they are
  also **technically ineligible** for the current ingestion contract without a
  separately reviewed adapter. No contract was changed to force them in.

## What "the demonstration case" means for the E2E-002 demo

- Case identity/provenance reference: ISPY1_1001 as documented above.
- Interactive browser demonstration: disposable synthetic fixture contexts
  (mesh + phase3), each labeled synthetic, with server-authoritative
  measurements — the only channel the implementation authorizes for display.
