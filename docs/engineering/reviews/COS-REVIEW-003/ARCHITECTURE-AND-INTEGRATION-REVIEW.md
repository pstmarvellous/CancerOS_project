# Architecture, science, authorization and delivery

The established modular architecture can support recovery. The immediate problem is that browser routes, request bodies, published-state ownership and capability enablement do not form one working product. Replacing FastAPI, workers, Next.js, PostgreSQL or private storage would add work without addressing the demonstrated failures.

## Current system and integration seams

Current source includes identity and patient linkage, source registry/rights, clinical records, private imaging import, geometry/alignment/QC, measurements/mesh, twin snapshots/fusion, scenario definitions/configuration/runs, generated clinical observations, temporal updates, note extraction, corpus/retrieval, interpretation contexts/templates/grounding and saved results. These modules are more substantial than empty scaffolds, but availability is often restricted to synthetic engineering fixtures.

The browser adds server-side proxy routes and separate clients with handwritten JSON. Central OpenAPI/Pydantic/generated TypeScript exist, yet successful compilation does not validate those JSON bodies against the receiving models. The current failures are concrete:

| Seam | Current mismatch | Independent evidence |
| --- | --- | --- |
| Scenario route → builder | `simulation/page.tsx:5` passes empty project/patient; unused context wrapper exists | Browser J07 and source |
| Builder → registry | `sc-01-explicit/1` and `sc-03-explicit/1` differ from registered `sc01-explicit/1`, `sc03-explicit/1` | Executable registry probes |
| Family payloads | SC-02/04/05 omit required family parameter objects; missing targets use unsupported null/extra key | Pydantic probes |
| Revision binding | Builder hardcodes `input_revision=1` | `simulation-builder.tsx:165` source |
| Schedule preview | Proxy POSTs `/schedule-preview`; backend defines GET `/simulation-configs/{config_id}/schedule-preview` | `app/api/simulation/route.ts:73`; `state_api.py:233` |
| Publication | UI/proxy sends extra `completion_id` forbidden by `PublishRunInput` | Schema probe and route source |
| Insight context | `{branch_id}` instead of required patient/snapshot IDs | `insights-explorer.tsx:103`; schema probe |
| Insight generation | `rule_based`/`external_private` and missing context snapshot instead of owned modes/ID | `insights-explorer.tsx:128`; schema probe |
| Grounding and save | `{interpretation: report}` instead of interpretation snapshot ID and persistence idempotency key | `insights-explorer.tsx:156/177`; schema probes |

The [reproducible probe](evidence/contract-probes.py) rejects nine fabricated request variants; two basic scenario configurations pass schema validation but fail registry version resolution. These are request/registry checks, not completed HTTP scenarios. The publication mismatch remains relevant even if earlier configuration failures currently prevent reaching it.

Use generated request types at the actual fetch boundary and a small set of browser-to-real-test-API acceptance journeys. Do not create another endpoint catalog or hide failures in a permissive proxy translation layer. Contract changes must update owned models, OpenAPI, generated clients and affected negative tests together.

## Capability gates versus missing implementation

| Category | Current example | Required response |
| --- | --- | --- |
| Essential restriction | Source rights, pseudonymous linkage, patient grants, genuine mask semantics and external export permission | Preserve; close with real evidence and accountable review |
| Correct restriction, poor presentation | An unpublished baseline or missing source returns generic conflict/unavailable text | Return safe owned reasons and role-specific recovery, without disclosing private internals |
| Missing workflow integration | Saved observation/outbox has no finished job/new-snapshot handoff; timeline does not drive viewer/insights | Compose existing services inside one case selection |
| Unnecessary local complexity | Duplicate global/case/inner/legacy navigation; handwritten request contracts beside generated schemas | Consolidate ownership and typed boundaries, not services |
| Genuine capability gap | Authentic imaging and observed baseline cannot be enabled by evidence alone because code is fixture-only | Implement a narrowly controlled reviewed-source path before claiming authentic operation |

`imaging_ingestion.py:148` explicitly rejects nonfixture origin; artifact origin is synthetic. `annotation_import.py:42,104,243` fixes synthetic/fixture semantics. `twin_states.py:51,157–158,361–363` keeps observed verification false and synthetic-only branches/snapshots. Simulation/clinical-generation/geometry execution is also restricted outside test mode (`simulation_execution.py:173/338`, `simulation_runs.py:436`, `clinical_generation_runs.py:56`, `synthetic_geometry.py:98`).

These are defensible limits for an engineering stage. They are not a finished production path waiting only for a license checkbox. Recovery needs a real source-release/rights/identity/QC/review contract, an authentic measurement/baseline path and negative acceptance tests. Never substitute an artificial permission assertion or relabel synthetic artifacts as real.

The staging transport is also intentionally small: base64 input is capped at 900,000 characters, with additional file/decoded/voxel limits. ADR-013 documents that large-study streaming is not implemented. A reviewed multipart/private-object upload-session workflow with bounded manifests is the smallest credible route to representative studies; lifting every bound is not a solution.

## Scientific and medical research assessment

The inspected arithmetic has appropriate foundations for its declared engineering scope. Physical volume uses the selected-label voxel count and absolute determinant of the spatial affine (`physical_measurements.py:42`), including nonorthogonal grids. Mesh extraction pads labels, extracts a 0.5 isosurface, transforms coordinates once and corrects winding on reflection (`mesh_reconstruction.py:54–83`). Explicit DCE-phase handling does not manufacture follow-up examinations (`imaging_formats.py:132–161`).

The bounded test command passed 119 checks. These establish synthetic arithmetic, geometry, scenario behavior and mock provider behavior. They do not establish authentic segmentation quality, independently inspected MRI/mask alignment, clinical realism, calibrated uncertainty, treatment benefit, real cohort performance or a genuine longitudinal endpoint.

Actual source reading supports the distinction between array indices and spatial images: [SimpleITK Fundamental Concepts, Images](https://simpleitk.readthedocs.io/en/master/fundamentalConcepts.html) describes origin, spacing, direction and physical extent. Its relevance here is geometric representation, not proof that a particular CancerOS import is clinically correct. [Stan 2.40 predictive checks](https://mc-stan.org/docs/stan-users-guide/posterior-predictive-checks.html) distinguishes replicated-data checks from comparison with observed data; scenario reproducibility alone is not external validation.

SPEC-011 §§6/11 still requires independent release-case overlay/measurement validation and genuine repeated imaging. No qualified oncology/radiology/biostatistical consultation occurred. Synthetic clinical ratings remain unvalidated demonstration values. The reviewer did not inspect private source patient data or claim authentic benchmark results.

Clinical save/correction retains source/time/unit/provenance in the exercised artificial slice. `clinical_ingestion.py:545–567` increments revision and emits an outbox event; `dependent_updates.py:94/111` still needs explicit administrative exact-revision publication. The product must expose this as saved → processing/review → published state, retaining the earlier snapshot. A saved row is not a synchronized twin update.

## AI and evidence

The application does not currently supply a live Meta research agent. `provider_gateway.py:157` restricts the transport to test/MockTransport; `execute_private:306` rejects other modes and has no app route caller. `interpretation_runs.py:114` rejects external candidates. A separate authorized live-test script is a harness, not evidence of application integration or a live call in this review.

Deterministic context/template/grounding modules exist, with immutable snapshot and evidence references. The demo correctly labels its local descriptive template. However, ordinary Insights cannot complete even local context/generation because of the schema drift above. Restore that usable fallback independently of external provider access. Then implement a bounded read-only agent only after actual provider documentation/access, export permissions, costs and model identity can be evidenced. Numerical measurements remain deterministic.

The original source tension is material: SPEC-006 §21 calls Meta interpretation P0, SPEC-012 permits provider-conditional fallback, and COS-HACK separately requires substantive Meta use. Report fallback usability, original AI fulfillment and hackathon eligibility separately. No current organizer-rule or entitlement verification was performed for submission.

## Authorization and persistence

**High-priority patient-boundary exception:** the saved interpretation detail handler ignores `patient_id` (`saved_api.py:88–92`). `saved_runs.read_saved:138–142` checks project viewer membership and `_row:21–32` selects by project/saved ID, without a patient-grant/path match. The reproducible fabricated connection probe returns another fabricated patient's result metadata using one project-only query. Returned scope is patient/context UUIDs, hashes, mode, counts and status; this review did not demonstrate raw clinical prose disclosure or a full HTTP exploit.

Fix by resolving the row under the requested project/patient, enforcing the current patient's grant before returning any result, and applying the same relevant withdrawal/lineage restrictions as other reads. Add negative HTTP tests with two patients, a project viewer with only one grant, wrong patient path and withdrawn resources. Knowing an opaque result ID must never replace ownership authorization. Treat closure as a release prerequisite.

Normal browser switching between two artificial cases did not mix the observed records. That does not disprove the saved-result exception or selection-race risks. `useEffect([])` initial binding in some viewer/state components and retained workspace permissions/filter on case changes warrant targeted delayed-response tests. Those races are identified risks, not proven cross-patient leaks.

## Root-cause analysis

The most supported cause is a missing acceptance layer across the seams. `simulation-builder.test.tsx:29–33` fabricates successful fetch responses instead of validating emitted payloads against the real API. Similar insights tests preload state context. Shell tests check labels/visibility rather than following context-preserving destinations. The resulting code can compile and render while the ordinary route and receiving contracts disagree.

Git history shows incremental implementation/verification commits for timeline, chart synchronization, insights readability and evaluation summary. That establishes the sequence of local changes, not the quality of a prior audit or blame for a particular agent/model. Current ledger statuses retain substantial unverified scope. It is therefore unsupported to claim that seven phases were all accepted and then regressed solely through visual styling.

A second supported cause is incomplete source-enablement ownership: synthetic fixture branches were expanded before a controlled authentic baseline path became usable. A third is navigation/state ownership split across component-local state, URL parameters, local last-case selection and independent screens. Safety gates themselves are not the demonstrated root cause of the empty scenario props or invalid Insights payloads.

The repository governance check also fails on historical ledger transitions, beginning with COS-074's `planned → implemented`. The same ledger validator fails on committed HEAD; the newly appended review entry validates independently. This is a pre-existing record/tool incompatibility, preserved in [governance-check.json](evidence/governance-check.json). It reinforces the need to reconcile evidence machinery with actual statuses; it is not a passing overall governance result.

## Operations and smallest recovery

The fresh build and local data/shell/fixture launch succeeded. No deployment, backup/restore, restricted production-role audit, sustained performance or browser/device matrix was verified. Native local startup and artificial fixture helpers must not become an administrator provisioning experience.

Keep the current architecture. Repair patient authorization and real request contracts; make one case/state/capability owner; integrate observation/import/job publication; add controlled authentic source enablement; then execute the original scientific/operational acceptance bundle. No new microservice, graph database, Kubernetes deployment or trained forecaster is justified by this review.
