# ADR-030: explicit SC-01 targets and realized ordering

COS-043. `sc01-explicit/1` accepts a positive mask-derived numerical-region baseline
in mm3 and at least three explicit decreasing positive knots at supplied relative
times. Piecewise linear interpolation uses Decimal precision40 within the declared
horizon, without extrapolation. Values are demonstration inputs, not estimated drug
effects. “Strong simulated tumor reduction” is a family label, with no RECIST or
clinical reduction threshold. Complete disappearance is unsupported for this plugin.

Clinical profile is retained independently. Noise/missingness are sampling inputs,
not unrecorded changes to latent knots. Specific exposure rules remain unreviewed
and unavailable. The registry has one explicit versioned family at this checkpoint.

The existing COS-040 operation now resolves common immutable isolated-test runs,
validates frozen environment/code and geometry policy, and uses the same mask,
physical measurement, mesh QC, private storage and state assembly. New common runs
pin association head; older snapshots lacking it cannot execute geometry. Database
constraints retain patient/branch/run ownership for both legacy fixture and common
run authorities. No fabricated legacy run row or follow-up source study is created.

Ready individual shapes do not establish a valid completed trajectory. The explicit
geometry-validation calculation accepts one result ID per frozen target slot,
checks ownership/current rights and compares actual measured ordering against the
baseline. A voxel-induced plateau/reversal blocks ordering; quantities are retained
and never changed to their targets. Its flag is `ordering_valid`, not publication
permission. Full-run clinical/structural validation, separate review/publication and
authentic observed-baseline gates remain open for COS-050.
