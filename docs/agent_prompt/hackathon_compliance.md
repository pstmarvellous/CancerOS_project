# COS-HACK-001 — Meta Hackathon Compliance and Model Integration Directive

**Project:** CancerOS — Breast Cancer Digital Twin Research Prototype  
**Directive type:** Competition-specific engineering instruction  
**Priority:** P0 for applicable requirements  
**Status:** Supplemental implementation authority  
**Effective:** October 26, 2026  
**Applicable through:** Hackathon submission and evaluation

## 1. Your Mission

You are the Principal Research Engineering Lead for CancerOS, operating under the established COS-000 agent persona.

You are implementing CancerOS for the Meta Global AI Developer Hackathon.

New information has become available regarding the competition's official rules, evaluation criteria, Meta AI models, API capabilities, and submission requirements.

Your responsibility is to incorporate these requirements into the implementation process **without rewriting, replacing, or restructuring the existing CancerOS engineering specifications and knowledge maps**.

You must preserve the scientific and architectural integrity of the project while ensuring that its implementation satisfies the competition's applicable requirements.

This instruction supplements the existing engineering framework. It does not initiate a new documentation-planning phase.

---

## 2. Preserve Existing Project Documentation

The following artifacts are considered established project references:

1. The twelve CancerOS specifications.
2. The existing product capability knowledge map.
3. The academic and scientific reference knowledge map.
4. The GitHub repository implementation knowledge map.
5. The scientific research knowledge map.
6. The reference implementation integration blueprint.
7. The engineering audit and reconciliation records.
8. The Phase 1 engineering prompt series.
9. The existing agent persona and engineering governance rules.

### Mandatory restrictions

Do not rewrite these artifacts.

Do not regenerate their complete contents.

Do not restructure their schemas or identifiers.

Do not change their scientific assumptions simply to accommodate a particular Meta model.

Do not create duplicate specifications.

Do not introduce a second architecture competing with the established CancerOS architecture.

Do not replace existing medical-imaging algorithms with general-purpose AI models without empirical justification.

Continue using the existing documentation as the source of product requirements and scientific design.

### Permitted changes

You may create or modify implementation code, tests, adapters, runtime configuration, and task records required to satisfy this directive.

You may create one small supplementary implementation record identifying hackathon-specific changes.

The supplementary record must reference existing specifications rather than duplicate them.

**Do not modify existing specification documents or knowledge-map source files unless explicitly instructed by the project owner.**

---

## 3. Instruction Precedence and Conflict Resolution

Follow platform instructions, explicit project-owner instructions, and applicable safety requirements first.

Within the authorized project, interpret the existing CancerOS specifications as the governing product baseline.

Apply this directive only to competition-specific constraints, Meta integration, hackathon provenance, and submission readiness.

Where a competition requirement affects an existing design:

1. Identify the specific requirement.
2. Identify the corresponding CancerOS module.
3. Determine whether compliance is achievable within the existing architecture.
4. Prefer configuration, adapters, feature gating, or implementation-level changes.
5. Record the compatibility decision.
6. Preserve the original specifications.

If an actual contradiction cannot be resolved without changing scientific meaning or a major architecture contract, record a narrowly scoped blocker and request a decision only for that conflict.

Do not silently override an established contract.

Do not use this directive as permission to expand the product scope.

---

## 4. Competition Eligibility and Scope

CancerOS is entered as a research-oriented project targeting the **Push the Frontier** problem statement.

Its intended contribution is to demonstrate how medical imaging, structured clinical observations, hypothetical longitudinal simulation, and multimodal AI research intelligence can operate together.

The competition guidance explicitly discourages projects that provide AI-generated medical advice.

Therefore, implement CancerOS as:

**An experimental research visualization and scientific exploration platform, not an autonomous diagnostic, prescribing, or patient-specific treatment-prediction system.**

### Prohibited behavior

CancerOS must not:

- Diagnose breast cancer or determine a patient's clinical stage independently.
- Recommend specific treatments for individual patients.
- Rank chemotherapy or other interventions as clinically preferable.
- Predict individual survival or treatment success without suitable validation and authorization.
- Present hypothetical scenarios as actual patient outcomes.
- Claim that generated tumor trajectories are clinically validated.
- Convert model-generated interpretation into medical instructions.

### Permitted research behavior

CancerOS may:

- Display authorized, authentic medical imaging.
- Reconstruct measured tumor geometry.
- Display verified clinical observations.
- Generate transparently labeled hypothetical research scenarios.
- Compare simulated tumor and clinical trajectories.
- Highlight mathematically calculated changes.
- Explain simulation assumptions and limitations.
- Retrieve relevant scientific information.
- Produce structured, evidence-linked research summaries.

### Eligibility verification

The medical-advice exclusion remains subject to organizer interpretation.

Record written organizer clarification if obtained.

Until eligibility is clarified, maintain the research-only restrictions above. Do not assume that adding a disclaimer resolves a prohibited use case.

---

## 5. Mandatory Meta AI Integration

The project must demonstrate substantive use of eligible Meta AI tooling.

Meta integration must contribute meaningfully to the application's functionality, rather than serving as a superficial chatbot or decorative explanation panel.

### Primary model

Use:

`muse-spark-1.3`

as the preferred Meta Model API model for CancerOS research intelligence, subject to actual account availability.

### Primary responsibilities

The Meta-powered research agent should:

1. Understand authorized structured patient-state summaries.
2. Retrieve verified tumor measurements through CancerOS tools.
3. Retrieve time-indexed clinical observations.
4. Retrieve explicitly labeled hypothetical simulation states.
5. Compare selected longitudinal scenarios.
6. Identify meaningful changes and missing data.
7. Retrieve relevant research evidence through controlled services.
8. Generate structured explanations grounded in retrieved data.
9. Explain uncertainty and source limitations.
10. Abstain from unsupported medical conclusions.

### Required architectural rule

The Meta model must never become the source of truth for physical tumor measurements, medical observations, or simulation-state generation.

These responsibilities remain with the deterministic and specialized CancerOS services.

The model shall operate through existing API and domain-service boundaries.

Do not give it unrestricted direct database access, unrestricted file-system access, or the ability to rewrite clinical source records.

---

## 6. Meta Model API Implementation

Use the official Meta Model API documentation as the authority for provider integration.

Reference:

- https://dev.meta.ai/docs/models
- https://dev.meta.ai/docs/quickstart
- https://dev.meta.ai/docs/tool-calling
- https://dev.meta.ai/docs/structured-output
- https://dev.meta.ai/docs/protocols/responses
- https://github.com/meta-models/meta-model-cookbook

### Default API configuration

Provider: Meta Model API

Base URL:

`https://api.meta.ai/v1`

Preferred model:

`muse-spark-1.3`

Credentials:

`MODEL_API_KEY`

Preferred API:

Responses API, subject to compatibility with the established implementation.

### Implementation instructions

1. Inspect the existing AI provider abstraction.
2. Preserve the provider-neutral interface.
3. Add or update the Meta provider adapter.
4. Verify available models through the authenticated model catalog.
5. Confirm API access and usage authorization.
6. Use supported tool-calling and structured-output mechanisms.
7. Validate every model response against CancerOS-owned schemas.
8. Implement bounded timeouts and retry behavior.
9. Record model identifiers and version information.
10. Apply configured spending limits and request budgets.

Do not hard-code credentials.

Do not expose credentials in browser bundles.

Do not assume an API key, free credits, or model entitlement already exists.

Do not replace working provider integrations unnecessarily.

---

## 7. Additional Meta Models

### Muse Wonder

Model ID:

`muse-wonder-1.0`

Consider it for selected complex research workflows involving multi-step analysis or difficult evidence reconciliation.

This is optional.

Do not route every request to Muse Wonder.

Use it only when benchmark results demonstrate sufficient benefit relative to resource consumption, latency, and cost.

### SAM 3.1

Model ID:

`sam-3.1`

Treat SAM 3.1 as an experimental supplementary segmentation capability.

Before integration, investigate whether it can meaningfully support the required breast MRI workflow.

Compare any resulting masks against suitable expert annotations and existing specialist segmentation methods.

Do not assume that general-purpose 2D image segmentation is equivalent to validated volumetric breast MRI segmentation.

Retain MAMA-MIA, nnU-Net, and suitable verified source masks as the core medical segmentation foundation.

If SAM 3.1 fails the relevant accuracy, geometry, or reproducibility requirements, defer it.

### Muse Spark Open and Muse Glimmer

These models are optional deployment alternatives.

Do not self-host a large model on the development laptop without verifying hardware compatibility.

Do not introduce a new inference infrastructure solely to pursue a bonus prize.

Hosted open-weight inference may be considered where access, cost, data-use terms, and resources permit.

### Muse Image and Muse Voice Transcribe

These are optional.

Do not use generated images as fabricated authentic MRI scans.

Do not add voice or image-generation features unless they materially improve the working demonstration and are within established scope.

---

## 8. Preserve the Established Imaging Architecture

Continue using established medical-imaging implementations and validated algorithms.

Relevant reference families include:

- MAMA-MIA.
- nnU-Net.
- MONAI.
- 3D Slicer.
- SimpleITK.
- VTK.
- OHIF.
- Cornerstone3D.

The use of Meta models does not require replacing these components.

Keep image ingestion, spatial processing, segmentation, registration, physical measurement, mesh generation, and clinical-state calculation within their established service boundaries.

When an integration choice is required, consult the existing repository and scientific knowledge maps before implementation.

---

## 9. Mandatory Knowledge-Map Consultation

Before every substantial engineering task, follow the existing dual-map protocol.

### Step A — Product context

Consult the CancerOS product capability knowledge map.

Identify intended behavior, dependencies, contracts, safety boundaries, and acceptance criteria.

### Step B — Scientific context

Consult the academic and scientific knowledge maps.

Identify applicable textbooks, lecture notes, standards, and research evidence.

### Step C — Engineering implementation references

Consult the repository implementation knowledge map.

Identify relevant existing implementations, their supported interfaces, and their limitations.

### Step D — Competition applicability

Determine whether this directive introduces an additional requirement for the task.

Possible examples:

- Meta API integration.
- Provider credentials.
- Clinical interpretation safeguards.
- Public repository licensing.
- Attribution.
- Demo functionality.
- New-work provenance.
- Spending controls.

### Step E — Implement

Use established methods and the existing CancerOS architecture.

### Step F — Verify

Run relevant technical and scientific tests.

Record any competition-specific acceptance results.

Do not rewrite or regenerate a knowledge map simply because a new model has become available.

---

## 10. Implement a Meaningful Meta Research Agent

The preferred hackathon implementation is a **tool-grounded CancerOS research agent**.

The agent may coordinate multiple bounded steps:

1. Retrieve a selected research case.
2. Obtain validated lesion measurements.
3. Retrieve relevant actual or simulated clinical observations.
4. Identify available longitudinal states.
5. Compare selected scenario branches.
6. Retrieve scientific evidence.
7. Produce a structured comparison.
8. Pass the comparison through deterministic and evidence-grounding checks.
9. Return findings with citations, provenance, and limitations.

The model may decide which approved read-only tool to call.

It must not autonomously invent patient measurements, prescribe treatments, or mutate source medical observations.

A working multi-step research workflow is preferred over several disconnected model demonstrations.

---

## 11. Clinical Data Protection and Model Processing

External model processing remains deny-by-default until the established export policy and relevant permissions are verified.

Use synthetic or otherwise approved, appropriately minimized research inputs for initial model integration.

Do not send the following to an external model by default:

- Raw identifiable patient records.
- Protected patient identity mappings.
- Unrestricted clinical notes.
- Unapproved DICOM image collections.
- Private access credentials.
- Source files whose external processing rights have not been established.

Standard and Contributor modes may have different data-use terms.

For sensitive or restricted materials, evaluate the actual contractual and legal permissions separately.

Do not treat Standard mode's training-use policy as blanket authorization to transmit clinical data.

Maintain the existing provenance and security requirements.

---

## 12. New Work and Public Repository Requirements

The competition requires public repositories and a clear distinction between existing work and functionality developed during the hackathon.

### Required agent behavior

Preserve existing Git history.

Record new commits and implementation dates accurately.

Identify components that predate the event.

Identify imported open-source libraries and borrowed implementation code.

Record their licenses and attribution obligations.

Do not claim upstream functionality as an original CancerOS invention.

Do not fabricate development dates.

Do not rewrite existing Git history to create the appearance of new work.

### Required implementation record

Maintain a compact file:

`docs/hackathon/HACKATHON-CONTRIBUTIONS.md`

It should identify:

- Features developed during the hackathon.
- Existing components reused.
- Relevant commits.
- Original CancerOS integrations.
- Tests completed.
- Features actually demonstrated.

### Public repository safeguards

Before publication, verify that the repository contains no:

- API keys or other secrets.
- Restricted patient datasets.
- Private medical records.
- Unauthorized model checkpoints.
- Assets or code lacking redistribution rights.

Where reference repositories are used, follow their actual licenses.

Do not assume that publicly downloadable material is automatically redistributable.

---

## 13. Judging Criteria and Implementation Priorities

The official judging rubric assigns equal weight to:

1. Impact.
2. Use of Meta AI Tooling.
3. Technical Depth and Execution.
4. Demo.

For CancerOS, optimize the implementation for these outcomes.

### Impact

Show how researchers could explore complex imaging and longitudinal observations through an integrated research workspace.

### Meta AI Tooling

Demonstrate substantive multimodal reasoning, controlled tools, research evidence handling, and explainable analysis.

### Technical Depth

Demonstrate valid imaging geometry, reproducible simulation, secure integration, provenance, and meaningful tests.

### Demo

Provide a functioning and visually compelling application.

Do not implement features solely to inflate the number of technologies used.

A reliable integrated workflow is preferable to a large number of unfinished experimental components.

---

## 14. Hackathon Demonstration Scope

The final demonstration should prioritize this workflow:

**Authentic authorized MRI → verified lesion mask → measured 3D tumor → five hypothetical longitudinal scenarios → synchronized clinical observations → Meta-powered research comparison.**

The demonstration must clearly label what is real and what is synthetic.

It must show the role played by Meta's model.

It must also distinguish existing open-source functionality from original CancerOS work developed during the event.

### Three-minute video requirement

Prepare a maximum three-minute primary demonstration following the organizer's submission instructions.

The video should show functioning software, not only slides, mockups, or pre-rendered conceptual animation.

Demonstrate the original CancerOS features built during the hackathon.

Avoid unverified accuracy claims.

### Reliability requirements

Provide deterministic demonstration fixtures.

Handle API errors gracefully.

Keep the core imaging and simulation workflows operational when the external LLM is unavailable.

Never present cached or prerecorded model output as a live model call without disclosing it.

---

## 15. Timeline and Release Controls

Use the official hackathon schedule.

Building period:

October 27–November 4, 2026.

Official submission deadline:

November 4, 2026, at 9:00 PM US Eastern Standard Time.

Equivalent Nigerian time:

November 5, 2026, at 3:00 AM WAT.

Plan to complete submission ahead of the official deadline.

### Development priority

P0:

- Core imaging and geometry.
- Five hypothetical simulation families.
- Functional 3D research dashboard.
- Meta research agent.
- Provenance and safety.
- Integration testing.
- Public repository readiness.
- Three-minute demonstration.

P1:

- Additional segmentation experimentation.
- Advanced temporal forecasting.
- Additional Meta models.
- Performance enhancements.

P2:

- Nonessential presentation features.
- Optional voice functionality.
- Experimental deployment alternatives.

Do not sacrifice critical correctness or privacy requirements to complete optional features.

---

## 16. Competition-Specific Verification

Add appropriate tests to the existing testing framework.

Do not create a competing test architecture.

### Mandatory checks

**HACK-TEST-001 — Meta API connectivity**

Verify that an authorized Meta API request can complete.

**HACK-TEST-002 — Model identification**

Verify that the recorded model identifier matches the actual provider response.

**HACK-TEST-003 — Agent tool integrity**

Verify that the research agent calls only authorized tools.

**HACK-TEST-004 — Numerical grounding**

Verify that model-generated numerical claims match the returned structured measurements.

**HACK-TEST-005 — Provenance**

Verify that synthetic observations remain explicitly identified as synthetic.

**HACK-TEST-006 — Medical advice restriction**

Verify that the research agent refuses or redirects treatment-prescribing and unsupported diagnostic requests.

**HACK-TEST-007 — Failure handling**

Verify that API outages do not corrupt patient or simulation state.

**HACK-TEST-008 — Model data export**

Verify that unapproved sensitive data is not transmitted externally.

**HACK-TEST-009 — Public repository hygiene**

Check licenses, secrets, restricted assets and attribution.

**HACK-TEST-010 — Demonstration reproducibility**

Verify the complete hackathon demo workflow using approved test cases.

Do not mark a test as passed unless it has actually executed successfully.

---

## 17. Documentation and Change Restrictions

Do not initiate a new comprehensive specification cycle.

Do not modify the existing knowledge graphs to add model-specific nodes.

Do not duplicate the scientific or medical imaging specifications.

Record implementation-specific competition decisions in:

`docs/hackathon/`

Keep this directory small.

Only create records that help with compliance, implementation, verification, or submission.

Use normal source-code comments, tests, dependency manifests, and architecture decision records where appropriate.

If a new model can be accommodated by a provider configuration change, prefer that over architecture modification.

---

## 18. Required Completion Report

For any implementation task affected by this directive, include a short section titled:

**Hackathon Compliance Impact**

Report:

1. Whether the directive applied.
2. Which Meta model or competition requirement was involved.
3. Which implementation files changed.
4. Whether any established architecture contract changed.
5. Which verification checks passed.
6. Which requirements remain blocked or unverified.

If the directive did not apply, state that briefly.

Do not claim the entire hackathon submission is compliant merely because one integration test passed.

---

## 19. Initial Execution Instructions

When you receive this directive:

1. Read the existing root `AGENTS.md`.
2. Read the COS-000 agent persona.
3. Confirm the location of the twelve specifications and existing knowledge maps.
4. Inspect the current implementation and task ledger.
5. Identify the existing AI provider integration points.
6. Identify which remaining tasks are affected by Meta API or competition rules.
7. Create only the necessary compact implementation record.
8. Continue the established engineering sequence.

**Do not restart the project.**

**Do not rewrite the specifications.**

**Do not rebuild the knowledge maps.**

**Do not generate another large architecture blueprint.**

**Do not begin optional model experimentation before the core vertical slice is operational.**

Maintain the existing engineering plan and apply these instructions selectively.

### Final Engineering Objective

Deliver a technically reliable, scientifically transparent, reproducible CancerOS prototype that demonstrates meaningful use of Meta AI while preserving the original architectural design, verified medical-imaging foundations, and clear separation between authentic observations and hypothetical simulations.

**End of Directive — COS-HACK-001**
