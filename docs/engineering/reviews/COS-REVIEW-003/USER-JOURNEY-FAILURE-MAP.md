# User journey results and reproduction map

Expert inspection, 6 November 2026 WAT. These are task attempts by an AI reviewer, not participant-study results. Obstacle counts below count distinct observed failure types, not a statistical usability score. Source requirements and U-numbers link to the [deep review](UI-UX-DEEP-REVIEW.md).

## Test environments

The README native path was built and started on `127.0.0.1:3000` with API 8000. A separate repository-provided opt-in product preview ran on 3001 with the artificial product API on 8001. It used existing private local services and an explicitly disposable database. This fixture creates artificial source/access records; it grants no real source permissions. The first-use sequence started at `/` in a fresh browser context, then clicked visible links. Authenticated testing used its credential through the ordinary sign-in form, without preloading a cookie or editing a case URL.

**Full intended sequence:** Open application → create/select case → add clinical observation → import examination → inspect derived lesion → generate scenario → compare states/charts → inspect grounded insights. The current research journey reached saved clinical records, then stopped at absent import/lesion workflow. Additional attempts assessed the later entry points independently. A separate prepared-demo journey reached phantom viewing, family/state changes, clinical tables and local descriptive insights.

## J01 — first-time demonstration

Start: native homepage, fresh unauthenticated browser. Click Launch synthetic demo. Actual: “The synthetic demo is not ready”; Retry cannot enable its server flag or prepare a bundle. One obstacle: advertised capability not deployed. Outcome: failed in the documented default profile; P1, U01, SPEC-009 §15.1/UX-17. Screenshots [01](evidence/01-fresh-home.png), [02](evidence/02-default-demo-unavailable.png).

Authorized alternative: open the separately enabled preview from its homepage and click the same action. The phantom renders. This is a successful **opt-in synthetic viewing task**, not a successful real case workflow.

## J02 — create, save and reopen a case

Start: opt-in preview homepage. Open research case library → use artificial administrator credential → Create first case. Enter an artificial identifier/title/pseudonym, select the artificial eligible source and supply its artificial locator → Save research case. Actual: persistent profile opens; a fresh signed-in browser can reopen it from the library. Edit profile → add artificial history → save revision also works.

Outcome: successful artificial admin slice, with one usability obstacle: inside the workspace the primary label becomes a generated technical code rather than the saved title. U04, PRD FR-001–007. Screenshots [07](evidence/07-admin-case-library.png), [08](evidence/08-created-case.png). No authentic patient onboarding, source-rights review or all-role trial was established.

## J03 — enter and correct a laboratory observation

Start: case A Overview. Click Clinical Records. Select laboratory/hemoglobin; enter artificial source label/locator, date 2026-11-01, 12.3 g/dL → Save observation. Actual: record appears with synthetic origin. Click Correct → change to 12.4 → save. Actual: active history/chart shows 12.4; retained observation count becomes two. Click Charts: exact date/unit/origin table and plotted active value appear.

Outcome: partial success; three workflow obstacles: all form steps remain expanded, there is no final submission review, and correction has no explicit reason/original-replacement review. The path does not surface retraction or dependent-state job/publication. P1 U09/U10, SPEC-009 §4.6. Screenshots [09](evidence/09-clinical-entry.png), [10](evidence/10-case-charts.png). Only laboratory and profile history were saved; other category options were inspected only.

## J04 — resume clinical work after refresh

Start: working Clinical Records tab in A. Reload the current browser URL. Wait for the case/history to finish loading. Actual: “Loading observation permissions…” remains, with no input form. Recheck after another operation: still present. Click Overview and wait for Profile, then Clinical Records: form returns.

Outcome: failed normal resume, one repeated blocker with a developer-inferred workaround. P0 U07, SPEC-009 §11/UX-01/11. Screenshot [11](evidence/11-clinical-refresh-stuck.png). Cause is tab-dependent permission loading, established in source. Do not classify this as a deliberate scientific gate.

## J05 — attach imaging and create a baseline

Start: saved case A. Click Imaging & 3D. Actual: no associated studies or lesion identities; no upload/import action; the page explains that importing requires a separate reviewed workflow. The empty-state/error combination offers Retry and returning to the library, neither of which attaches imaging.

Diagnostic continuation: manually visit `/admin` while still signed in as administrator. Actual: static unavailable placeholder, without source/import/QC/publication controls. This manual route visit is not a successful discoverability test.

Outcome: blocked/incomplete; two implementation obstacles (no ingest surface, placeholder administration) plus absent authentic data/review. P0 U06, PRD UJ-02/FR-008–016, SPEC-009 §4.8. Screenshots [12](evidence/12-imaging-no-import.png), [22](evidence/22-admin-placeholder.png). No file was uploaded and no privacy control was bypassed. Prepared phantom viewing was the authorized alternative, explicitly separated from anatomy.

## J06 — continue into the 3D viewer using primary navigation

Start: an opened case with project/patient in its URL. Click primary Digital Twin. Wait for `/twin` to settle. Actual: URL contains no case selection; page asks to open a case, although one was just opened. Secondary 3D Digital Twin carries selection but is competing navigation.

Outcome: failed handoff; one selection-loss blocker. P0 U03, SPEC-009 §3/UX-01. Screenshot [14](evidence/14-primary-nav-loses-case.png). Reproduction does not require an imaging dataset; losing the selection itself is the defect.

## J07 — run an ordinary hypothetical scenario

Start: an opened case. Use the secondary case Hypothetical Scenarios link, which preserves project/patient. Actual: route still says “Open a case ... first”. Click Retry loading branches. Actual: error changes to “Select an authorized branch”, but no branch list appears.

Outcome: failed before baseline eligibility can be assessed; two connected obstacles (route ignores context, recovery itself needs a branch). P0 U14, SPEC-009 §4.5/UX-12. Screenshot [13](evidence/13-case-scenario-context-failure.png). Contract probes separately show further builder/proxy failures; they were not forced through UI using injected IDs.

## J08 — inspect temporal changes and two selected research states

Start: case A Timeline tab. Actual: artificial case has saved observations but no published state/branch; legacy timeline link explicitly says it does not inherit the tab automatically. A populated persisted A/B pair was therefore not browser-verified. Code shows textual pinning without an A→B comparison request or viewer synchronization.

Outcome: research comparison blocked/not verified, P1 U15. Requirement: SPEC-009 §§7.3/8–9. Do not report the absence of a branch on a newly created case as a broken comparison algorithm; the missing process from saved observations/baseline to published state is the relevant workflow gap.

Prepared alternative: in the demo use Previous/Next and discrete state buttons. SC-01 changes 216→64 mm³ and its chart highlights the selected state. All five prepared families load four positions after waiting for their selected-family data. This establishes sample discrete playback, not new simulation or genuine longitudinal comparison. Screenshots [03](evidence/03-demo-twin.png), [04](evidence/04-demo-followup.png), [21](evidence/21-sc05-clinical.png).

## J09 — inspect AI findings for the selected case

Start: reopened case A. Click secondary AI Research Insights. Actual: a State text field and instruction to paste a Timeline state ID; no available-state selector or automatically bound snapshot. One immediate blocker: internal identifier handoff. Outcome: incomplete, P0 U17, PRD UJ-07/FR-056; screenshot [15](evidence/15-insights-state-uuid.png).

No live inference was attempted. Independently validating emitted request shapes shows that context, generation, grounding and saving would fail the actual schemas. The prepared demo instead displays a correctly labeled local template with no live Meta result, screenshot [06](evidence/06-demo-insights.png). That truthful fallback does not establish the research insight workflow.

## J10 — use the guided tour, activity and evaluation

From Evaluation click Follow guided demo. Choose step two. Its link is bare `/twin`, not a pinned case/state. Preflight is explanatory prose and a confirmation checkbox, not readiness verification. Outcome: guide not accepted, P1 U19; [17](evidence/17-guided-tour.png). Direct diagnostic visit to Activity in the signed-in admin session returns a placeholder ([23](evidence/23-activity-placeholder.png)).

Evaluation is reachable and states missing scientific evidence. It also hardcodes fixture success claims and maps UX IDs to meanings different from original §18. Outcome: accessible information page, not a verified report-delivery workflow; P1 U18, screenshot [16](evidence/16-evaluation.png).

## J11 — mobile and non-canvas interaction

At 320 CSS pixels load the homepage from `/`: two narrow entry columns make ordinary onboarding difficult; document width is 329. At the same width, the authenticated case library measured 320 with no page overflow. At 390, the demo measured 390 and its canvas 324×464. Outcome: specific homepage reflow failure, not a global mobile rejection. P1 U20, SPEC-009 §§4.3/13/UX-15. Screenshots [18](evidence/18-mobile-home-320.png), [24](evidence/24-mobile-case-library.png), [25](evidence/25-mobile-demo.png).

Camera buttons and keyboard actions executed; fullscreen entered; maximize enlarged the view. Actual touchscreen behavior, screen-reader announcements, browser zoom and contrast were not verified. The initial `touchAction:none` policy is a confirmed implementation concern requiring physical-device testing. No full accessibility pass is claimed.

## J12 — switch between two cases

Create artificial B through the same visible form. It has zero observations. Return to library, select A by its title and open Clinical Records: its corrected 12.4 g/dL value remains. Outcome: simple library switching succeeded without observed record mixing. This does not test delayed responses, query-only same-component changes or every authorization endpoint. Source inspection still identifies stale-selection risks requiring a focused race test. Saved-result patient authorization is a separate confirmed code/function-probe finding, not inferred from these ordinary browser actions.
