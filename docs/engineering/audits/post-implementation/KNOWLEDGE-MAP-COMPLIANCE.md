# COS-AUDIT-002 Knowledge-Map Compliance

**Run:** `cos-audit-002-arch-001` · **Candidate:** `bd7b2c2`
Rule: a map entry is a pointer. Functionally consistent code is **not** proof that a previous agent read the cited source. Classifications below reflect this audit's own queries, not inherited claims.

## Capability map (Knowlage_map_1)

| Node | Implementation | Classification |
|---|---|---|
| IMG.INGEST / IMG.PRE | `imaging_formats.py`, `imaging_ingestion.py`, `imaging_preprocessing.py` with study/series/sequence validation, slice sorting, checksum and orientation handling | Functionally consistent but consultation unverified |
| IMG.VOL | `physical_measurements.py` exact determinant accounting; `imaging_geometry.py` validators | Functionally consistent but consultation unverified |
| IMG.MESH | `mesh_reconstruction.py`, `mesh_quality.py` with mask-authoritative measurements | Functionally consistent but consultation unverified |
| DATA.PROV / D.GOV | Five provenance classes preserved end-to-end; synthetic never promoted | Followed and evidenced (contracts + tests) |
| D.SIM five families | `scenario_families.py` SC-01…SC-05 with frozen seeds and validation | Followed and evidenced (50/50 + determinism) |
| WF.REALVAL / EVAL.REAL | Longitudinal gate records zero eligible cases; D02 blocked | Followed and evidenced (honest block, no fabricated chronology) |

## Academic map (Knowlage_map_2)

| Behavior | Cited source | This audit's position |
|---|---|---|
| IMG.08 lesion volume/diameter | ITK Software Guide Vol. 2; IBSI reference manual; RECIST 1.1 (A05/A08/A18) | **Unable to assess** readership from code resemblance. Implementation computes voxel-count × \|det(A₃ₓ₃)\| with Decimal80 precision and keeps RECIST diameters distinct (`extent_definition: ..._not_RECIST_diameter`) — functionally consistent with the stated design, not proof of chapter reading. |
| IMG.13 synthetic shape generation | Insight into Images (A07); IBSI (A08); MIT graphics OCW (A17) | **Unable to assess** readership. Target-vs-realized tolerance `max(one voxel, 1% target)` implemented and tested — functionally consistent, not proof of source study. |
| SIM.01 five trajectory patterns | Longitudinal Data Analysis (A11); Stan PPC (A09); NCI PDQ (A12) | **Unable to assess** readership. Shape constraints on all five families verified by regression — functionally consistent. |
| DAT.04 patient-level splits | Referenced in Phase 6 evidence | Followed and evidenced for the fixture suites (`evaluation_splits` tests); no leakage found in the sampled paths. |

## Repository / scientific maps (dual reference-maps)

| Behavior | Candidate | Position |
|---|---|---|
| SIM.01 | Stan (R10): adopt diagnostics methodology, seed reproducibility | Functionally consistent: frozen seeds, repeated-set digest match. No Stan code vendored; license/copying question not triggered. |
| IMG behaviors | 3D Slicer (R03) reference geometry/segmentation/measurement | Study/reference only; no Slicer code adoption found. `not_verified` for execution — correctly not claimed. |
| Evidence behaviors | TCIA/ISPY2-style collections (P05) | No real cohort imported; blocked real-data gates consistent with this. |

## Deviations

No undocumented scope expansion found. Optional segmentation, temporal neural models, forecasting enablement, Contributor mode, and Kubernetes were all correctly left disabled with explicit gates. No deviation requiring new justification was identified in the sampled paths.
