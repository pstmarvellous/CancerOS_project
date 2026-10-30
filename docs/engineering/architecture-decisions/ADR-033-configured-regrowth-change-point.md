# ADR-033: SC-04 configured change point and sampled pattern

COS-046. `sc04-explicit/1` uses explicit change-point day and nadir volume with
continuous piecewise linear paths from baseline to that point and then the final
declared knot. Parameters are demonstration assumptions; no acquired-resistance
mechanism or drug efficacy is inferred. Regrowth may remain below the baseline.

The change point can lie on or between supplied imaging slots. A latent unsampled
nadir is a model control, never an invented clinical visit or measured quantity.
At least baseline plus three actual supplied followups must show initial reduction
and subsequent increase. Insufficient schedules, contradictory knots and erased
turning patterns fail instead of adding hidden points or relabeling the scenario.

Plugin metadata separates configured point from the minimum of its latent sampled
targets. Geometry validation separately reports minima of actual mask measurements,
including multiple equal minima. Quantization or missingness cannot be used to
publish an unobservable pattern. Clinical profile and hypothetical exposure timeline
remain independently configured. Complete-run publication and scientific review
are separate gates, never granted by this pattern check.
