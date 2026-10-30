# ADR-042: bounded baseline evaluation and public abstention

COS-055 authorizes a P0 engineering comparator framework, reconciling SPEC-006
baseline arithmetic with SPEC-011's disabled patient-forecasting gate. Per-origin
LOCF, last-two-point linear extrapolation and time-aware least squares are scoped
evaluation calculations. This records the limited baseline scope; it does not
authorize trained forecasting deployment, neural models or patient-specific claims.

Protocols pin metric definition, units, measurement method, lesion, population,
positive supported horizons and nonnegative output. Fits use actual elapsed times
and exact Decimal values, with explicit event and knowledge cutoffs. LOCF needs one
usable point, last-two linear two distinct times, and least squares three. No value
is carried into observed state fusion. Negative volume forecasts are withheld,
never clipped. Censored, conflicting and missing facts do not become exact values.

Backtests reuse the frozen original-patient split contract. Source/descendant groups
cannot cross partitions; demo or excluded groups are rejected. Future labels must
be unique, exact and at origin plus the declared horizon, known by a separate label
cutoff. Report all coverage/failures and original-unit MAE/RMSE, both per-method
eligible and common eligible cases, by patient and horizon. There are no default
percentage errors or calibrated intervals. Synthetic results remain engineering
evidence; authentic longitudinal evaluation and qualified review remain unavailable.

`POST /forecast-queries` loads an owned full timeline and optionally checks the
frozen split. It always returns an explicit abstention with null estimates. Client
protocol declarations cannot establish validation or enable patient forecasting.
Forecast DTOs remain separate from source, scenario and canonical state points.
No external inference, new model dependency, paid compute or publication is added.
