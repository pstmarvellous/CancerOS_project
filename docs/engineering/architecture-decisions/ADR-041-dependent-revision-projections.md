# ADR-041: revision projections through the existing worker

COS-054 connects the existing transactional clinical domain outbox to an explicit,
authorized dependent-update command. Durable job creation, event receipt and
delivery acknowledgement commit together. Redis remains transport; existing worker
leases, frozen input/code hashes, cancellation and commit fencing remain in force.
Worker input continues to require synthetic engineering provenance. Authentic
observed-source execution is not enabled by this change.

Derived reports preserve exact revision/window, input dependencies and output
hashes. Feature extraction and comparisons reuse canonical temporal modules.
Fusion requires an explicit newly assembled canonical state with matching revision
and source membership; otherwise it remains unavailable with a next action. No
new laboratory observation enters an old snapshot. Existing physical measurements
and mesh artifacts are reused by exact identity; this command never generates them.
When a state is requested, the declared temporal event cutoff must equal its exact
time. Features, trends and fusion cannot describe different selected-time horizons.

Receipts are scoped by accepted event and calculation scope. Processing an event
for source calculations does not consume an explicitly requested branch calculation;
independent heads and composite foreign keys retain ownership and execution scope.
Global outbox acknowledgement records durable dispatch, not automatic branch fanout.

The latest-derived head is a preview of completed calculations, separate from
TwinState and current-run publication. A current-revision compare-and-set controls
head advancement. Older completed reports remain retained and stale, failed or
quarantined work cannot replace a valid view, and publication remains an explicit
existing command. Reads expose status and current rights without queueing work.

Source revision freshness is distinct from a changed physical baseline. Laboratory
corrections alone cannot assert that a baseline mesh changed. Branches retain their
pinned baseline and history; there is no automatic scientific rebasing or scenario
regeneration. Missing authentic data/review and scientific-policy gates stay open.
