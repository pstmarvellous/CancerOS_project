# ADR-032: explicit SC-03 growth with honest geometry limits

COS-045. `sc03-explicit/1` requires positive strictly increasing numerical-region
volume knots above the baseline, with supplied ordered relative days and the common
bounded quantity contract (<1e15 mm3). There is no fitted growth rate, drug-effect
coefficient, new lesion, invasion or resistance mechanism. Clinical profile remains
independent. Generic hypothetical exposure events do not establish treatment failure;
specific unreviewed categories remain denied.

Reuse the same common immutable run and physical-space geometry adapter. Expanded
voxel cells outside the unchanged source grid fail explicitly before sampling.
No clipped mask or target-as-measurement fallback is produced. Missing tissue
segmentation means anatomical containment is not established, not silently passed.
The realized validator requires actual ordered growth and blocks missing, plateaued
or reversed quantities. Baseline and other branches remain immutable.

The authenticated common-run targets read supports permitted measurement-only
engineering workflows without geometry jobs. It resolves owned source measurement,
current rights, frozen code/environment and registered plugin; it is not a production
simulation authorization or a completed branch publication. Full orchestration and
scientific acceptance remain gated.
