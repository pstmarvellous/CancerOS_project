# CancerOS — Mandatory Stage Execution Rules

Execute only the assigned COS-REC stage. Do not begin another stage automatically.

1. Read the relevant existing specifications, AGENTS.md and knowledge-map entries. Do not rewrite them.
2. Inspect existing code before creating or replacing modules.
3. Preserve unrelated work and established scientific/security controls.
4. Implement the stage requirements using the smallest appropriate changes.
5. Test real backend/frontend integration, not only mocked components.
6. Complete the stated browser acceptance journey.
7. Capture genuine execution evidence and report actual failures.
8. Use `PASS`, `FAIL`, `BLOCKED` or `PARTIAL` accurately. Never convert unverified work into PASS.
9. If a task is blocked, identify the exact blocker, its owner, what evidence is missing and the next action. Do not silently bypass it.
10. After implementation, stop and provide a handoff report. Do not refactor unrelated components or begin the next stage.

For every stage, provide:

- Requirement and expected user outcome.
- Files changed.
- Existing components reused.
- Actual functionality delivered.
- Tests executed and their results.
- Screenshots or traces.
- Remaining blockers.
- Final stage verdict.

**A stage is complete only if every mandatory acceptance condition has evidence. A successful build or unit test alone does not qualify.**
