# ADR-036: versioned independent observation sampling

COS-049. Optional `sampling/1` settings declare bounded timing jitter, additive
uniform variability and Bernoulli missingness with explicit reasons. No clinical
distribution, normal interval or treatment effect is a default. Existing explicit
offset/missing profiles remain deterministic inputs; ambiguous duplicate policies
are rejected. Independent SHA256 counter streams derive from the configuration seed,
family/generator version, modality, slot, channel and purpose. Job IDs, wall time,
iteration order and unrelated analytes cannot affect scientific samples.

Keep latent tumor/clinical profiles separate from sampled observation values.
Generation never reconstructs SC-04 control parameters from noisy observations.
Post-sampling temporal/component/family constraints block invalid requests rather
than silently clamping, sorting collisions away or filling gaps. Optional clinical
missingness does not remove a visit; required missing imaging blocks anatomical
completion. Full anatomical family acceptance still requires actual mask-derived
measurements. Variability is an engineering assumption, never a confidence interval.

Retain per-modality relative times with numeric(12,4) precision and a branch origin;
no calendar date is fabricated. Explicit treatment/adverse controls retain configured
times; unsupported jitter on these controls is rejected. Future timeline/forecast
features consume visible records, never hidden future/latent targets.
