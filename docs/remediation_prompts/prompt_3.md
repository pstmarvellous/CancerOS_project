# COS-REC-02 — First-Time Experience and Reliable Demo Launch

**Role:** Senior UX Designer, Frontend Engineer and Product Engineer

**Mission:** Make CancerOS understandable and operational for a first-time visitor with no medical training.

The intended audience includes prospective software-development clients.

Preserve scientific truthfulness and existing security boundaries.

## Tasks

1. Review the current homepage, demo launch logic, demo data preparation and related error states.
2. Resolve the reported "Synthetic demo is not ready" failure. Determine whether it results from missing bundles, expired prepared data, startup ordering or another defect.
3. Provide an idempotent, documented local demo preparation command that validates required artifacts and reports actionable failures.
4. Ensure the demo entry point does not advertise availability when required assets are missing.
5. Replace engineering-heavy homepage explanations with concise, plain-language product descriptions.
6. Provide one primary call to action and one secondary option.
7. Preserve a separate authorized research-case entry point.

## Required homepage experience

Suggested headline:

**Explore How a Tumor Could Change Over Time**

Suggested introduction:

"CancerOS demonstrates how medical images, 3D visualization, hypothetical simulations and AI can work together in one research application."

Primary button:

**Explore Interactive Demo**

Secondary action:

**Create or Open a Research Case**

Show three short capabilities:

- Explore a 3D model.
- Compare hypothetical scenarios.
- Understand the associated data.

The synthetic-data disclosure must remain visible but should not dominate the page.

## Demo launch requirements

Clicking Explore Interactive Demo must:

1. Open a valid demonstration session.
2. Load the existing synthetic data.
3. Present an interactive 3D model.
4. Display a short instruction explaining what to do.
5. Offer a clear next action.

The visitor must not need an API token, project UUID, terminal command or explanation from the developer.

If the demo is genuinely unavailable, identify the specific operational cause in developer diagnostics while giving the visitor a clear recovery message.

## Acceptance gate

From a fresh Chrome session with no stored data:

- Open the homepage.
- Click Explore Interactive Demo.
- Verify the real 3D canvas loads.
- Rotate the model.
- Select a scenario.
- Inspect a follow-up state.
- Refresh and repeat.

Run the journey after an actual restart of the application's supported demo environment.

The stage fails if the demo requires undocumented manual preparation after normal startup, or if a clickable launch button leads to an unexplained error.

Capture homepage and working-demo screenshots.
