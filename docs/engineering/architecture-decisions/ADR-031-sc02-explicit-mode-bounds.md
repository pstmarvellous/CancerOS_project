# ADR-031: explicit SC-02 mode and engineering bounds

COS-044. Reuse the common registry, explicit schedules, baseline pins, clinical
descriptor and geometry worker. The configuration explicitly selects modest_reduction
or near_stable; the plugin returns both the original family and requested mode.
It never silently recategorizes an overlapping trajectory.

All bounds are required user-supplied demonstration parameters, not RECIST or
clinical significance limits. Near-stable mode checks both absolute mm3 and relative
variation around baseline. Modest reduction checks explicit relative decline bounds
and ordered reduction. Mode-specific schemas forbid irrelevant contradictory keys.
Wrong units, invalid baseline or out-of-band targets fail instead of being clipped.

Latent targets, optional sampling offsets/missingness, actual realized geometry and
unavailable measurement uncertainty remain distinct. Clinical profile stays
independent, including deterioration with stable size. Geometry checks use actual
mask measurements against the same explicit mode bounds. A failure blocks that
check; full-run publication and scientific review remain separate open gates.

Optional config fields do not rewrite old JSON/hash history. A new queue request
against a legacy expanded DTO must save a new config version; earlier receipts and
run snapshots remain retrievable. No source/clinical evidence or reviewed threshold
is fabricated to enable constrained production use.
