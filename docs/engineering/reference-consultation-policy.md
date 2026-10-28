# Reference consultation policy

COS-001. Use original paths in [the guide](../../IMPLEMENTATION_GUIDE.md#4-locate-the-maps-and-specifications).
Read both retrieval protocols and the repository/scientific dual-reference protocol.
Do not copy/restructure maps or alter identifiers to repair stale example paths.

Before meaningful edits run, using the selected Python runtime:

```powershell
uv run --python 3.12 python -X utf8 scripts/reference_context.py COS-001 provenance architecture --sections "Actual source sections inspected"
```

Replace task/terms/sections truthfully. The script executes all three original query
tools and records exact outputs, IDs and adjacent edges under
`docs/engineering/reference-reviews/`. Read relevant nodes and constraints, then open
the governing specification. Extend 1–2 hops when needed. No-match results and
stale local paths are explicit dependencies, not invented coverage.

## Source Learning Record template

Task/scope; capability IDs; academic behavior IDs; reference ID; author/title;
edition/version and exact subsection actually read; URL/access result; principle;
assumptions; failure modes; verified source claim versus local inference; relevance;
unavailable reason. Summarize in original language; never store copyrighted chapters.

## Three-Source Decision Note template

Academic principle → pinned candidate implementation/API → empirical cohort,
modality and measured endpoint → scoped integration decision → negative/acceptance
tests. Record alternatives, code/model/data license separately, commands/results,
resource constraints and gaps. Missing categories stay explicitly unverified.

Routine build, governance and cosmetic tasks may mark medical readings not
applicable with a scope reason. Scientific/clinical/geometry/AI decisions require
actual relevant reading and evidence before capability enablement. Map entries
do not prove reading, reproduction, license permission or validation.

Implementation status lives in task/evidence records, never silently rewritten into
original knowledge-map sources. Use `docs/engineering/architecture-decisions/` for
versioned decisions and `reference-reviews/<TASK-ID>.md` for task-local context.
