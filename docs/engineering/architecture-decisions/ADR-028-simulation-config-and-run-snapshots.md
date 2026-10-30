# ADR-028: common simulation configuration and frozen runs

COS-041. Reversible engineering decision under SPEC-004 sections3/5/7/15–17,
SPEC-008 section13.3 and audit A02/A03/A05. Scientific approval is not established.

Reuse existing patient-owned `imaging.twin_branches`, immutable source revisions,
resource lineage and state contracts. Append versioned editable draft revisions;
optimistic expected draft revision and patient lineage locks prevent lost edits.
Queueing freezes a complete typed config, baseline hash, exact revision manifest,
server-derived code/environment identity and independent seed-stream inputs.
An earlier run is always retrievable by ID; a rerun appends a new run identity.

The common model is `simulation-config/1`. Explicit schedules use stable slot IDs,
original relative days and distinct modalities; imaging has at least three followups
plus the shared baseline reference. Tumor and clinical profiles are independent.
No distribution, clinical range, efficacy coefficient, dose or receptor is invented.
Plugins validate/generate typed targets and clinical profiles under a family/version
registry. No fake family implementation is registered as clinical functionality.

Current Phase 2 branch records explicitly have unverified engineering baselines.
Draft storage is allowed; run snapshots for these branches require isolated test
mode. Their queued status means an immutable pending snapshot, with no dispatched
worker job or ready output until the later orchestration task is integrated.
No run is automatically published and no current-run pointer is changed here.
Production run authorization requires authentic published observed baseline and
reviewed policy through COS-042/050; fixtures cannot satisfy these gates.

The COS-040 isolated fixture run remains a legacy test adapter. COS-050 must consume
the common run snapshot and reuse its geometry operation, rather than promote
fixture authorization into production. Branches remain pinned; no baseline rebasing
or copying baseline evidence as synthetic observations is permitted.
