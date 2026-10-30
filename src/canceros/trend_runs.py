"""Deterministic comparison requests consume full owned observation windows, never client values."""

from uuid import UUID

from fastapi import HTTPException
from pydantic import model_validator

from canceros.contracts import Contract, DecimalString
from canceros.temporal_trends import TrendReport, analyze_trends
from canceros.timeline_runs import TimelineQuery, read_window_points


class TrendQuery(Contract):
    timeline: TimelineQuery
    tolerance: DecimalString = "0"
    left_point_id: UUID | None = None
    right_point_id: UUID | None = None

    @model_validator(mode="after")
    def exact_pair(self):
        if (self.left_point_id is None) != (self.right_point_id is None):
            raise ValueError("Comparison requires both point identities")
        return self


def query_trends(c, i, p, u, value: TrendQuery) -> TrendReport:
    points, _ = read_window_points(c, i, p, u, value.timeline)
    try:
        return analyze_trends(
            points,
            value.timeline.window,
            value.tolerance,
            value.left_point_id,
            value.right_point_id,
        )
    except ValueError:
        raise HTTPException(422, detail="trend_window_or_numeric_tolerance_invalid") from None
