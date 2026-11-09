# COS-REC-08 — Professional Product Design and Usability Refinement

**Role:** Senior Product Designer, UX Writer, Accessibility Engineer and Frontend Engineer

**Mission:** Create a coherent, professional application experience for non-medical users while preserving the existing scientific functionality.

Do not redesign backend services or introduce a new frontend framework.

## 1. Simplify application language

Review all major user-facing screens.

Use clear, task-oriented language.

Examples:

| Current technical language | Preferred user-facing language                                |
| -------------------------- | ------------------------------------------------------------- |
| Persisted state            | Saved timepoint                                               |
| Authorized case            | Research case                                                 |
| Configure research branch  | Explore a hypothetical scenario                               |
| Source-backed observation  | Recorded observation                                          |
| Geometry QC                | 3D model quality check                                        |
| Grounded interpretation    | Research explanation                                          |
| Fixture-tested             | Move to technical details; do not use as primary product copy |
| Snapshot hash              | Hide under Evidence / Technical Details                       |

Do not remove important meaning. A tooltip or expandable details section may preserve technical precision.

## 2. Establish button hierarchy

Use consistent patterns:

- Primary: Create Case, Explore Demo, Save, Generate.
- Secondary: Compare, Edit, View Details.
- Utility: Back, Fit View, Reset Camera, Refresh.
- Destructive: Delete or revoke, with confirmation where applicable.

Do not use bright primary styling for every action.

## 3. Improve page architecture

Each major screen should have:

1. A clear title.
2. A short explanation of the current task.
3. One unmistakable primary action.
4. Visible relevant data or functionality.
5. A clear next step.
6. Helpful loading, empty and error states.

Remove duplicated global and local navigation where possible.

Keep advanced engineering diagnostics out of primary workflows.

## 4. Improve presentation

Refine:

- Typography hierarchy.
- Spacing and alignment.
- Form grouping.
- Table readability.
- Chart labeling.
- 3D viewer framing.
- Loading and progress indicators.
- Icons.
- Toolbars.
- Responsive layouts.
- Keyboard accessibility.
- Contrast and focus visibility.

For mobile widths around 320–390px, ensure the interface does not require horizontal scrolling or display overlapping controls.

Do not shrink complex desktop tables to unreadable text; use appropriate responsive alternatives.

## 5. Demonstrate the improvements

Capture before-and-after screenshots of:

- Homepage.
- Research Cases.
- Case creation.
- Clinical Data.
- 3D Twin.
- Scenarios.
- AI Insights.
- Narrow-screen layouts.

Use the same viewport sizes for before-and-after comparisons.

## Acceptance gate

PASS requires:

- No inaccessible core actions.
- No manual UUID input in normal workflows.
- No overlapping or clipped primary controls.
- Clear loading and recovery messages.
- Working keyboard navigation for core controls.
- Correct technical details available when requested.
- Browser regression tests for functional workflows.

Do not accept visual polish if it breaks data selection, security, responsiveness or scientific labeling.

Record which usability problems were fixed and which remain.
