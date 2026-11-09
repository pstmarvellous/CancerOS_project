# COS-REC-00 — Security and Recovery Baseline

**Role:** Senior Backend Engineer and Application Security Engineer

**Mission:** Stabilize the existing CancerOS implementation before any additional UX work.

Read the root AGENTS.md, applicable specifications, previous security findings, and relevant knowledge-map entries.

Do not redesign the product or modify the original specifications.

## Tasks

1. Inspect Git status, current branch, recent changes and existing tests. Preserve uncommitted work.
2. Create a dedicated recovery branch without discarding existing changes.
3. Reproduce the reported saved-interpretation patient-ownership defect using two artificial patients belonging to the same project.
4. Inspect all affected authorization and result-retrieval services.
5. Enforce the existing project, patient, role and grant checks before returning saved results.
6. Add negative tests ensuring that a valid project member cannot retrieve another patient's result without an appropriate grant.
7. Verify that no sensitive data or API credentials appear in public artifacts.
8. Establish reliable development startup and test commands.
9. Record the current behavior of the synthetic demo and case-management workflow for regression comparison.

## Required concrete evidence

Create artificial Patient A and Patient B within a disposable project.

A request authorized only for Patient A must not return Patient B's saved interpretation.

Test both the service layer and the actual HTTP route.

A forbidden request must produce the appropriate denial without exposing result content.

Existing authorized retrieval for Patient A must still work.

## Acceptance gate

PASS only when:

- The reported access-control issue is corrected or conclusively disproved with evidence.
- Positive and negative authorization tests pass.
- Existing critical regressions pass.
- The application starts successfully.
- No existing work has been discarded.
- The recovery baseline is recorded.

Do not claim that a function-level fix proves the HTTP endpoint secure without testing the endpoint.

## Report

Return: root cause, exact files modified, tests executed with counts, evidence paths, remaining risks, and PASS/FAIL/BLOCKED.

If a critical security defect remains, mark this stage FAILED. Do not authorize work with real patient data.
