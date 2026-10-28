# CancerOS Agent Context Refresh and Knowledge Retrieval Rules

Use `canceros-knowledge-graph.json` as an indexed engineering knowledge model and `COS-KMAP-001.md` for human-readable navigation.

## At the start of each task
1. Search graph nodes by ID/title/tag/description corresponding to the assigned capability.
2. Expand 1-2 hops of incoming and outgoing relations. ALWAYS include `CONSTRAINS`, `GUARDS`, `EXCLUDES`, `VERIFIES` and `WORKFLOW_PRECEDES`.
3. Read original source specifications, not just graph summaries. If the source file is unavailable, say so and treat the map as provisional.
4. Inspect upstream repository at a pinned commit if the task calls for reuse. Check separate code/model/data licensing and reproduce a test first.
5. Declare exact input/output data contract, provenance states, error cases and accepted quality thresholds.
6. Before coding, establish the unit and end-to-end tests implied by connected evaluation nodes.
7. Do not claim implemented/tested unless executing tests yields evidence. Update status and audit log only after review.

## Required task note
- Target node IDs and linked specification sections
- Parent and downstream dependencies
- Non-negotiable invariant IDs
- Implementation choice and upstream provenance
- Data fixtures and constraints
- Tests executed and measured results
- Known unknowns, follow-up work, and any changes to this graph

## Forbidden shortcuts
- Do not relabel a functional enhancement mask as a complete anatomical lesion without validation.
- Do not convert DCE acquisition phases into separate visits.
- Do not count five simulated branches as five independent real patients.
- Do not treat synthetic response curves as observed treatment effects or calibrated patient forecasts.
- Do not let an LLM supply numerical measurements absent from deterministic sources.
- Do not silently fill missing biomarker, pathology or laboratory fields.
- Do not conflate physical voxel coordinates with rendering vertices.
- Do not copy code, weights or datasets before checking each relevant license.
- Do not make upstream projects the product requirements; extend them through CancerOS contracts.
