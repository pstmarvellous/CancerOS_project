# ADR-059: real API-connected case library with honest availability

COS-073 replaces the COS-072 cases placeholder with a working case library
driven by the generated `PatientPage`/`PatientSummary` contract and a thin
same-origin `/api/cases` proxy to the canonical patient-list endpoint. The
component renders only authorized fields the server actually returns
(display code, data revision); examination, branch and modality
availability are deferred to the opened case and never invented in the list.
Search, source/modality filters and cursor pagination have no server
semantics in the adopted contract, so the task ships an honest bounded list
instead of client-side filtering that would misrepresent the cohort.

Distinct blocked states cover missing project, loading, empty, restricted
(401/403/404), stale preconditions (428/412) and retryable failure, each
with a role-appropriate next action and no nonfunctional upload control.
Switching projects reloads through an abortable fetch; stale responses are
ignored.

Fixture denominators: case-library tests for missing-project, populated,
empty and restricted paths; the full frontend suite; lint/typecheck/build
and contracts green. Live projects, genuine longitudinal badges, manual
screen-reader and target-device checks remain open.
