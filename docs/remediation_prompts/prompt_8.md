# COS-REC-07 — Working AI Research Interpretation

**Role:** AI Infrastructure Engineer, Backend Integration Engineer, Application Security Engineer and UX Designer

**Mission:** Make CancerOS's research interpretation workflow usable and correctly connected to the selected case and data.

Inspect existing context assembly, provider transport, export policy, structured response, grounding and saved-result APIs.

Do not build a second AI gateway.

## Tasks

1. Remove manual state UUID entry from the normal research workflow.
2. Derive the selected state from the authorized case workspace.
3. Repair existing request/schema mismatches.
4. Verify evidence-context assembly and snapshot binding.
5. Establish a working deterministic local explanation path.
6. Identify whether the actual Meta provider path is operational or blocked.
7. Implement missing provider functionality within existing authorization controls.
8. Present readable results with supporting data references.
9. Clearly identify local, cached, live and unavailable results.
10. Make response errors understandable and recoverable.

## Example user interaction

The visitor selects a hypothetical scenario and Day 37.

They click:

**Explain This Scenario**

Expected local explanation:

"At Day 37, the modeled region measures 64 mm³, compared with 216 mm³ at the synthetic baseline. This is a hypothetical change generated for demonstration."

Beneath it, show:

**Data used:** Selected scenario, Day 37, region-volume measurement.

**Source:** Synthetic simulation.

**Method:** Local deterministic explanation.

This is a useful working result even before a live model is available.

## Live Meta integration

When live access and export authorization are verified, provide a separate action such as:

**Generate AI Research Summary**

Use the established provider model, permitted structured context and grounding validation.

Do not send genuine patient data to an external provider without appropriate permission.

Do not forge rights documents or bypass policy validation.

Never present a template response as a live Meta output.

## Acceptance gate

From a selected supported case/state:

- No UUID copying.
- Context resolves correctly.
- Local explanation uses exact selected values.
- State changes do not show stale results.
- Authorized results remain patient-scoped.
- Errors disclose no secrets.
- Genuine Meta output is marked verified only after an actual permitted request and validated response.

Require backend integration tests, two-patient negative access tests and real browser evidence.

Report local interpretation and live provider verification as separate results.
