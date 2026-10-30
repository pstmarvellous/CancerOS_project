"""Irregular-time arithmetic, knowledge leakage and original-patient evaluation guards."""

from decimal import Decimal
from uuid import UUID

import pytest
from test_temporal_timeline import KNOWN, LATER, PATIENT, point, window

from canceros.contracts import Availability
from canceros.evaluation_splits import GroupAssignment, SplitManifest
from canceros.forecast_baselines import (
    ForecastEvaluationCase,
    ForecastProtocol,
    evaluate_forecasts,
    forecast_baseline,
)


def protocol(**changes):
    return ForecastProtocol.model_validate(
        {
            "metric_code": "hemoglobin",
            "unit": "g/dL",
            "method_version": "local-units/1",
            "supported_horizons": ["9", "17"],
            **changes,
        }
    )


def history():
    return [
        point(
            10, "0", numeric_result={"form": "exact", "quantity": {"value": "1", "unit": "g/dL"}}
        ),
        point(
            11, "3", numeric_result={"form": "exact", "quantity": {"value": "7", "unit": "g/dL"}}
        ),
        point(
            12, "11", numeric_result={"form": "exact", "quantity": {"value": "23", "unit": "g/dL"}}
        ),
        point(
            13, "20", numeric_result={"form": "exact", "quantity": {"value": "41", "unit": "g/dL"}}
        ),
    ]


def predict(points=None, method="locf", **kwargs):
    return forecast_baseline(
        history()[:3] if points is None else points,
        kwargs.pop("window", window("11")),
        kwargs.pop("protocol", protocol()),
        method,
        kwargs.pop("horizon", "9"),
    )


def split(**changes):
    group = GroupAssignment(
        group_id=UUID(int=99),
        patient_ids=[PATIENT],
        role="test",
        demo_exposed=False,
        held_out_group_eligible=True,
        exclusions=[],
    )
    return SplitManifest(
        id=UUID(int=200),
        seed=0,
        grouping_hash="a" * 64,
        groups=[group],
        identity_evidence_ids=[],
        source_version_ids=[],
        frozen_root_resource_ids=[],
        input_revisions={},
        **changes,
    )


def case(points=None, **changes):
    return ForecastEvaluationCase(
        id=UUID(int=300),
        patient_id=PATIENT,
        group_id=UUID(int=99),
        window=window("11"),
        horizon_days="9",
        label_knowledge_as_of=LATER,
        points=history() if points is None else points,
        **changes,
    )


def test_one_point_locf_only_under_explicit_protocol():
    assert predict(history()[:1]).estimate == "1"
    assert predict(history()[:1], "last_two_linear").reason_codes == [
        "INSUFFICIENT_DISTINCT_HISTORY_REQUIRES_2"
    ]
    assert predict(history()[:2], "ols_linear").reason_codes == [
        "INSUFFICIENT_DISTINCT_HISTORY_REQUIRES_3"
    ]


@pytest.mark.parametrize("method", ["last_two_linear", "ols_linear"])
def test_irregular_actual_days_linear_origin_plus_horizon(method):
    result = predict(method=method)
    assert result.status == "estimate" and Decimal(result.exact_estimate) == 41
    assert result.patient_facing_enabled is False
    # Last observation is at day3; forecast target is still origin11+horizon9, not 3+9.
    if method == "last_two_linear":
        assert predict(history()[:2], method).estimate == "41"


def test_no_future_event_or_later_known_correction_enters_fit():
    points = history()
    late = points[2].model_copy(update={"id": UUID(int=40), "recorded_at": LATER})
    result = predict([*points[:2], late, points[3]], method="last_two_linear")
    assert result.estimate == "41" and result.point_ids == [points[0].id, points[1].id]
    assert predict(points, window=window("3"), method="ols_linear").status == "abstained"


def test_missing_origin_population_horizon_metric_and_unit_abstain():
    assert predict(window=window(event_cutoff=None)).reason_codes == [
        "EXPLICIT_COMPARABLE_ORIGIN_REQUIRED"
    ]
    assert predict(horizon="1").reason_codes == ["UNSUPPORTED_HORIZON"]
    assert predict(protocol=protocol(population="real_breast_cancer")).reason_codes == [
        "REAL_EVALUATION_UNAVAILABLE"
    ]
    assert predict(protocol=protocol(metric_code="weight")).status == "abstained"
    assert predict(protocol=protocol(unit="kg")).status == "abstained"


def test_unit_conversion_and_zero_not_mape():
    p = point(numeric_result={"form": "exact", "quantity": {"value": "120", "unit": "g/L"}})
    assert predict([p]).estimate == "12"
    zero = p.model_copy(
        update={
            "numeric_result": point(
                numeric_result={"form": "exact", "quantity": {"value": "0", "unit": "g/dL"}}
            ).numeric_result
        }
    )
    assert predict([zero]).estimate == "0"


def test_negative_extrapolation_abstains_without_clipping():
    points = [
        point(10, "0"),
        point(
            11, "3", numeric_result={"form": "exact", "quantity": {"value": "1", "unit": "g/dL"}}
        ),
    ]
    result = predict(points, "last_two_linear")
    assert result.estimate is None and result.reason_codes == [
        "NEGATIVE_FORECAST_UNSUPPORTED_NO_CLIPPING"
    ]


def test_conflicts_censoring_missing_ordinal_and_latent_targets_are_not_history():
    censored = point(
        11,
        "3",
        numeric_result={
            "form": "censored",
            "comparator": "<",
            "threshold": {"value": "1", "unit": "g/dL"},
        },
    )
    missing = point(12, "11", availability=Availability.UNAVAILABLE)
    assert predict([history()[0], censored, missing], "last_two_linear").status == "abstained"
    duplicate = history()[0].model_copy(update={"id": UUID(int=66)})
    assert predict([history()[0], duplicate]).status == "abstained"
    assert (
        predict(
            [
                history()[0].model_copy(
                    update={"measurement_basis": "simulated_target_no_mask_realization"}
                )
            ]
        ).status
        == "abstained"
    )


def test_frozen_splits_exact_future_labels_and_common_eligible_metrics():
    report = evaluate_forecasts([case()], protocol(), split())
    assert len(report.cases) == 3
    values = {row.method: row.signed_error for row in report.cases}
    assert Decimal(values["locf"]) == -18 and Decimal(values["ols_linear"]) == 0
    assert report.real_evaluation == "unavailable"
    assert all(row.scored == 1 for row in report.metrics)
    assert all(row.mae == "18" for row in report.metrics if row.method == "locf")
    assert (
        report.model_dump_json()
        == evaluate_forecasts([case()], protocol(), split()).model_dump_json()
    )


def test_label_cutoff_prevents_unavailable_future_target_and_no_nearest_substitution():
    points = history()
    points[-1] = points[-1].model_copy(update={"recorded_at": LATER})
    early = case(points).model_copy(update={"label_knowledge_as_of": KNOWN})
    assert all(
        row.signed_error is None for row in evaluate_forecasts([early], protocol(), split()).cases
    )
    absent = case(history()[:-1])
    assert all(
        "EXACT_FUTURE_LABEL_UNAVAILABLE_OR_AMBIGUOUS" in row.reason_codes
        for row in evaluate_forecasts([absent], protocol(), split()).cases
    )


def test_censored_competing_target_cannot_be_ignored_to_choose_exact_label():
    points = history()
    competing = point(
        60,
        "20",
        numeric_result={
            "form": "censored",
            "comparator": "<",
            "threshold": {"value": "50", "unit": "g/dL"},
        },
    )
    report = evaluate_forecasts([case([*points, competing])], protocol(), split())
    assert all(result.signed_error is None for result in report.cases)


@pytest.mark.parametrize(
    "field,value",
    [("role", "train"), ("demo_exposed", True), ("exclusions", ["uncertain_identity"])],
)
def test_demo_cross_role_and_unresolved_original_groups_rejected(field, value):
    frozen = split()
    frozen.groups[0] = frozen.groups[0].model_copy(update={field: value})
    with pytest.raises(ValueError):
        evaluate_forecasts([case()], protocol(), frozen)


def test_descendants_cannot_change_original_patient_assignment():
    frozen = split()
    frozen.groups.append(
        frozen.groups[0].model_copy(update={"group_id": UUID(int=888), "role": "train"})
    )
    with pytest.raises(ValueError, match="overlapping"):
        evaluate_forecasts([case()], protocol(), frozen)
    with pytest.raises(ValueError, match="inherit"):
        evaluate_forecasts(
            [case().model_copy(update={"group_id": UUID(int=1)})], protocol(), split()
        )


def test_common_intersection_does_not_choose_successful_different_cases():
    early = case().model_copy(
        update={"id": UUID(int=301), "window": window("3"), "horizon_days": "17"}
    )
    report = evaluate_forecasts([early], protocol(), split())
    assert sum(row.scored for row in report.metrics if row.sample == "common_eligible") == 0
    assert any(row.scored == 1 for row in report.metrics if row.sample == "method_eligible")


def test_unknown_origin_abstains_in_evaluation_instead_of_crashing_label_lookup():
    unknown = {"basis": "unknown", "time_domain": "simulation", "missing_reason": "not_recorded"}
    selected = case().model_copy(update={"window": window(event_cutoff=unknown)})
    report = evaluate_forecasts([selected], protocol(), split())
    assert all(result.forecast.status == "abstained" for result in report.cases)
    assert all(result.target_value is None for result in report.cases)


def test_nonpositive_evaluation_horizon_never_selects_a_historical_label():
    report = evaluate_forecasts(
        [case().model_copy(update={"horizon_days": "-8"})], protocol(), split()
    )
    assert all(
        row.forecast.status == "abstained" and row.target_point_id is None for row in report.cases
    )


def test_tiny_physical_measurement_errors_use_unrounded_exact_values():
    points = []
    for index, (day, exact) in enumerate(
        ((0, "0.00000000001"), (3, "0.00000000002"), (11, "0.00000000003"), (20, "0.00000000004"))
    ):
        points.append(
            point(
                70 + index,
                str(day),
                modality="imaging",
                concept="numerical_region_volume",
                metric_definition="anatomical_contour/1",
                method_version="full-affine-volume/1",
                numeric_result={"form": "exact", "quantity": {"value": "0", "unit": "mm3"}},
                exact_value=exact,
                measurement_basis="mask_realized",
            )
        )
    policy = protocol(
        metric_code="numerical_region_volume",
        unit="mm3",
        method_version="full-affine-volume/1",
        metric_definition="anatomical_contour/1",
    )
    report = evaluate_forecasts([case(points)], policy, split())
    locf = next(result for result in report.cases if result.method == "locf")
    assert locf.forecast.estimate == "0"  # Wire display rounding is explicit.
    assert Decimal(locf.forecast.exact_estimate) == Decimal("0.00000000003")
    assert Decimal(locf.signed_error) == Decimal("-0.00000000001")


def test_cli_fixture_report_is_repeatable_and_retains_all_origins_and_groups():
    from pathlib import Path
    from runpy import run_path

    fixture_report = run_path(
        str(Path(__file__).resolve().parents[1] / "scripts/evaluate_forecast_baselines.py")
    )["fixture_report"]

    report = fixture_report()
    assert len(report.cases) == 27 and len(report.split_manifest.groups) == 3
    assert report.model_dump_json() == fixture_report().model_dump_json()
    assert all(
        metric.attempted == metric.scored + metric.abstained + metric.excluded
        for metric in report.metrics
    )
