# ADR-016: explicit, conservative mask-grid alignment

COS-028, 2026-10-28. SPEC-005 P-04/P-08, SPEC-008 section 7 and SPEC-011
section 5 govern alignment/1. The original maps and specifications are unchanged.

An owned staged NIfTI mask requires a matching patient/release mapping, explicitly
asserted study ID/evidence hash and an owned canonical or preprocessed target image.
The study must equal the target's recorded import association. This records evidence,
not a qualified annotation review. Unknown/corrupt labels and missing 3D targets
quarantine. DCE targets must first select one explicit acquisition with COS-027.

Exact-grid default requires the same physical grid, not merely array shape. Optional
nearest-neighbor resampling uses a declared proper rigid source-world to target-world
transform, explicit target grid and zero background. Pull mapping is
inv(source_affine) × inv(source_to_target_world) × target_affine. Use SciPy 1.17.1
affine_transform order=0, prefilter=False, grid-constant mode; no intensity interpolation
then rounding, no inferred resize, no world scaling/deformable registration.
Reflected index grids are supported through their complete affines.

Check per-label sets/counts, six-connected components, physical cell bounds and
before/after determinant volumes. Partial clipping, lost labels, component changes
or excess volume error quarantine and yield no output/preview. The numerical volume
allowance is max(one source voxel, one target voxel, at most one percent of source
label volume), versioned engineering policy rather than clinical tolerance.
Full original masks/images remain immutable. Passing aligned masks and bounded
private overlay JSON receive lineage from both sources. Current source rights and
withdrawal gates apply even on replay and preview reads. Foreign keys preserve patient
ownership. Reports and configuration are immutable and hash-checked.

The sampled overlay has a disclosed limit: a thumbnail may omit small regions.
It is a technical preview, with reviewer acceptance pending; no clinical annotation,
measurement-ready segmentation, scientific approval or publication is created.
COS-029 classifies annotations and COS-031 owns segmentation QC. No authentic pair
or qualified reviewer was available. Evidence: mask-alignment.json.

Review amendment during COS-029: require a separately recorded administrator
mask-association UUID before alignment. It binds one staged mask to one owned
study/image and evidence hash; editors cannot rebind it by changing request fields.
The basis is explicitly administrator_fixture_attestation_real_review_not_established,
not an independently verified source-manifest/qualified review. Real paths remain
disabled. Migration 0019 and mask-associations POST/GET own this additional contract;
AlignmentInput adds required association_id and cross-checks all displayed fields.
Current output withdrawal blocks successful replay. Annotation reads recompute current
rights-based capability flags while immutable source metadata/history remain retained.
Affected tests/clients: alignment, annotation, preprocessing and generated OpenAPI/TS.
