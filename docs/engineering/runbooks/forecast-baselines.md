# Baseline evaluation and forecast abstention

COS-055 provides private engineering arithmetic and rolling-origin evaluation.
Use `uv run python scripts/evaluate_forecast_baselines.py` for the deterministic
synthetic demonstration. Its JSON reports method coverage, individual cases and
original-unit MAE/RMSE, with common eligible cases separated from each method's
coverage. These artificial patient groups do not establish real clinical accuracy.

LOCF requires one exact usable observation. Last-two linear requires two distinct
times; centered time-aware least squares requires three. Protocols declare metric,
unit, measurement method, lesion, population and supported positive horizons.
Forecast origins require both an event cutoff and a timezone-aware knowledge cutoff.
No future observation can enter fitting. Labels are exact unique observations at
origin plus horizon, known by the declared label cutoff; nearby visits are not
silently substituted. Missing, censored, conflicting, negative extrapolated and
incomparable inputs yield explicit reasons. No prediction intervals are estimated.

`POST /api/v1/projects/{project_id}/patients/{patient_id}/forecast-queries` accepts
an exact `TimelineQuery`, a declared `ForecastProtocol`, method, horizon and optional
owned split ID. It always returns `status: abstained`, null estimates and the missing
review/evaluation requirements. It never calls external inference or inserts a
forecast into source/scenario history. Use descriptive trends while these gates remain.

Run the `forecast-baselines` check target for actual results. Authentic longitudinal
data, source rights and a qualified endpoint/population/horizon review are required
before patient forecasts could be considered. Optional COS-056 neural experiments
remain deferred behind their separate data/evaluation/compute gates.
