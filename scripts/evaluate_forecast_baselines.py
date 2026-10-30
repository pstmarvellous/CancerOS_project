"""Deterministic synthetic arithmetic backtest; no patient data, training or public estimates."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from canceros.evaluation_splits import GroupAssignment, SplitManifest
from canceros.forecast_baselines import ForecastEvaluationCase, ForecastProtocol, evaluate_forecasts
from canceros.temporal_timeline import TimelinePoint, TimelineWindow


def fixture_report():
    known = datetime(2026, 10, 1, tzinfo=timezone.utc)
    protocol = ForecastProtocol(
        metric_code="hemoglobin",
        unit="g/dL",
        method_version="local-units/1",
        supported_horizons=["3", "8", "9"],
    )
    groups = []
    cases = []
    for patient_number in range(1, 4):
        patient, origin, branch, run = (
            UUID(int=patient_number * 100 + offset) for offset in (1, 2, 3, 4)
        )
        group = UUID(int=patient_number)
        groups.append(
            GroupAssignment(
                group_id=group,
                patient_ids=[patient],
                role="test",
                demo_exposed=False,
                held_out_group_eligible=True,
                exclusions=[],
            )
        )

        def reference(day):
            return {
                "basis": "relative_day",
                "value": str(day),
                "time_domain": "simulation",
                "timeline_origin_id": origin,
            }

        points = []
        for index, day in enumerate((0, 3, 11, 20)):
            # Explicit engineering numbers; no biological distribution or treatment claim.
            value = str(10 + patient_number + index)
            points.append(
                TimelinePoint.model_validate(
                    dict(
                        id=UUID(int=1000 * patient_number + index),
                        patient_id=patient,
                        time={"reference": reference(day), "precision": "relative_day"},
                        recorded_at=known,
                        revision=1,
                        origin="SYNTHETIC_GENERATED",
                        context="SYNTHETIC",
                        modality="laboratory",
                        concept="hemoglobin",
                        numeric_result={
                            "form": "exact",
                            "quantity": {"value": value, "unit": "g/dL"},
                        },
                        availability="available",
                        source_ids=[UUID(int=9000 + patient_number)],
                        source_hash="a" * 64,
                        method_version="local-units/1",
                        branch_id=branch,
                        run_id=run,
                    )
                )
            )
        for index, (day, horizon) in enumerate(((0, 3), (3, 8), (11, 9))):
            window = TimelineWindow.model_validate(
                dict(
                    scope={
                        "mode": "simulation",
                        "branch_id": branch,
                        "run_id": run,
                        "data_revision": 1,
                    },
                    event_cutoff=reference(day),
                    knowledge_as_of=known,
                )
            )
            cases.append(
                ForecastEvaluationCase(
                    id=UUID(int=2000 * patient_number + index),
                    patient_id=patient,
                    group_id=group,
                    window=window,
                    horizon_days=str(horizon),
                    label_knowledge_as_of=known,
                    points=points,
                )
            )
    split = SplitManifest(
        id=UUID(int=50000),
        seed=0,
        grouping_hash="b" * 64,
        groups=groups,
        identity_evidence_ids=[],
        source_version_ids=[],
        frozen_root_resource_ids=[],
        input_revisions={},
    )
    return evaluate_forecasts(cases, protocol, split)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = fixture_report()
    rendered = json.dumps(report.model_dump(mode="json"), sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
