"""Owned computed state context; neither source heads nor snapshots are rewritten."""

from uuid import UUID

from fastapi import HTTPException

from canceros.contracts import Contract
from canceros.simulation_execution import read_completion
from canceros.simulation_runs import _usable
from canceros.state_fusion import FusionReport, fuse_state
from canceros.temporal_trends import PointComparison, analyze_trends
from canceros.timeline_runs import TimelineQuery, read_window_points
from canceros.twin_states import read_state


class FusionQuery(Contract):
    state_id: UUID
    timeline: TimelineQuery | None = None


def query_fusion(c, i, p, u, value: FusionQuery) -> FusionReport:
    view = read_state(c, i, p, u, value.state_id)
    _usable(c, i, p, u, value.state_id)
    snapshot = view.snapshot
    comparisons: list[PointComparison] | None = None
    if value.timeline is not None:
        query = value.timeline
        scope = query.window.scope
        if (
            query.cursor is not None
            or scope.mode != "simulation"
            or scope.branch_id != snapshot.branch_id
            or scope.data_revision != snapshot.input_revision
            or query.completion_id is None
        ):
            raise HTTPException(422, detail="fusion_requires_exact_state_revision_and_branch")
        completion = read_completion(c, i, p, u, query.completion_id)
        if snapshot.id not in completion.state_ids or scope.run_id != completion.run_id:
            raise HTTPException(409, detail="fusion_state_not_in_selected_completion")
        # A full timeline may contain later visits. Fusion never uses these to
        # describe the selected state, irrespective of a client's display cutoff.
        window = query.window.model_copy(update={"event_cutoff": snapshot.time})
        bounded = query.model_copy(update={"window": window})
        points, _ = read_window_points(c, i, p, u, bounded)
        if not any(snapshot.id in point.state_ids for point in points):
            raise HTTPException(409, detail="fusion_state_unavailable_at_knowledge_cutoff")
        trends = analyze_trends(points, window)
        selected = {}
        for series in trends.series:
            for comparison in [*series.segments, series.endpoint]:
                if comparison is not None and snapshot.id in comparison.to_state_ids:
                    selected[(comparison.left_point_id, comparison.right_point_id)] = comparison
        comparisons = list(selected.values())
    try:
        return fuse_state(view, comparisons=comparisons)
    except ValueError:
        raise HTTPException(409, detail="fusion_membership_or_context_invalid") from None
