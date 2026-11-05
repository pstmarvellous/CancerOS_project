# COS-E2E-001 Dataset Inventory

Inspected 2026-11-02 from the extracted `Data_folder/Demo_data/` tree.
Source files are immutable inputs; nothing was renamed, rewritten, or uploaded.

## Contents

| Item | Detail |
|---|---|
| Extracted subset | `Data_folder/Demo_data/BreastDCEDL_demo_data/` |
| DCE acquisitions (`.nii.gz`) | 21 files, 7 subjects: ACRIN-6698-102212, ACRIN-6698-103939 (spy2/vis1), ISPY1-1001..1003 (spy1/vis1), Breast_MRI_001/002 (duke) |
| Segmentation masks (`.nii.gz`) | 6 files: ACRIN-6698-102212, ACRIN-6698-103939, ACRIN-6698-104268, ISPY1-1001..1003 |
| Paired image+mask subjects | 5 of 7 (ACRIN-6698-104268 has a mask but no extracted DCE; Breast_MRI_001/002 and ACRIN-6698-107700+ have DCE/metadata rows but no masks in this subset) |
| Metadata | `BreastDCEDL_metadata_min_crop.csv`: 2070 rows, 29 columns (`pid`, `pCR`, `n_xy`, `n_z`, `n_times`, `pre`, `post_early`, `post_late`, `slice_thick`, `xy_spacing`, `mask_start`, `mask_end`, `sraw`/`eraw`, `scol`/`ecol`, `tum_vol`, `age`, `menopause`, `race_white/black`, `HR`, `HER2`, `HR_HER2_STATUS`, `TripleNeg`, `HER2pos`, `HRposHER2neg`, `dataset`, `test`) |
| Provenance docs | `BreastDCEDL_ A Deep Learning–Ready Breast DCE-MRI Dataset _ Zenodo.pdf`, `CancerOS_Resource_Download_Guide.md` (acquisition plan, CC BY-NC 4.0 noted; rights for hackathon/demo use still require confirmation) |

## Verified on one paired case

- `ACRIN-6698-102212_spy2_vis1_dce_aqc_0.nii.gz`: shape (42, 256, 256),
  zooms (1.0, 1.0, 1.0), units unknown. Mask: same shape, labels {0, 1}
  (single foreground annotation class; functional/anatomical separation is not
  asserted by this inventory).

## Supported workflows

- Authentic single-examination ingestion with verified mask geometry: YES for
  the 5 paired subjects (engineering path covered by
  `test_imaging_ingestion`, `test_mask_alignment`, `test_physical_measurements`
  — 29 passed 2026-11-02).
- Genuine longitudinal validation (two real examinations of one patient, D02):
  NOT supported by this subset — DCE phases (`_aqc_0/1/2…`) are contrast
  acquisitions within one visit, not follow-up visits. No second authentic
  examination was found. Longitudinal demonstration must use the synthetic
  five-scenario engine with explicit hypothetical labeling (D02 stays blocked).
- Clinical `pCR`, receptor status, and demographics exist only as CSV columns;
  source linkage, de-identification evidence, and case-level suitability were
  not verified here. No patient identifiers are reproduced in this report.

## Safety

- Files were read with nibabel/CSV only. No identifiers were logged.
- Nothing was transmitted externally (export gate enforced; provider tests use
  synthetic fixtures only).
- The `Unconfirmed 817807.crdownload` partial download was left untouched.
