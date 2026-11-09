# Independent evidence and checks

Date: 6 November 2026 WAT. Review baseline `4ce26c0cfecb3eea915640d82f7af0e33e5cf08e`. Earlier reports and screenshots were excluded. Existing deletions were observed before work; the requested fresh report files were recreated, and the deleted old milestone report was not restored. No application implementation changed.

## Actually executed

| Command or action | Result | What it establishes |
| --- | --- | --- |
| `git status --short`, `git rev-parse HEAD`, short `git log` | Working-tree deletions and current commit inspected | Preservation/baseline and change sequence, not prior acceptance |
| `uv run --python 3.12 python -X utf8 scripts/reference_context.py COS-REVIEW-003-INDEPENDENT usability clinical scenario geometry provenance --sections ...` | 41 capability nodes, 13 academic behaviors, 191 adjacent edges recorded | Original-map consultation; `usability` has explicit no-match results |
| Original PDF extraction/hash inspection | All 12 identities/pages/hashes match source manifest; complete extracted texts read in specialist pass | Original-source baseline; see source inventory for precise reading and visual limits |
| `npm.cmd run build` | Exit 0, Next 16.4.3 compile, TypeScript and route generation completed | Current source builds; not usable journeys or science |
| `uv run python scripts/dev.py start data` | Existing isolated PostgreSQL/private object store/queue ready | Local dependencies; no reset |
| `uv run python scripts/dev.py start shell` | Native API/web available on 8000/3000 | Documented default startup; demo flag absent |
| `node scripts/serve_product_workspace.mjs` | Separate opt-in web preview on 3001 | Synthetic-demo-enabled test preview; not deployment |
| `uv run python scripts/product_browser_fixture.py` | Artificial API on 8001; disposable SQL and artificial rights/access setup | Controlled artificial continuation; no real patient/source authorization |
| Five-file focused pytest command | 119 passed; recorded rerun 3.03s, exit 0 | Synthetic geometry/scenario/unit/MockTransport scope only; [full command/output](tests-summary.json) |
| `.venv/Scripts/python.exe docs/engineering/reviews/COS-REVIEW-003/evidence/contract-probes.py` | Nine payloads rejected; two schema-valid configurations have unregistered versions; fabricated saved metadata returned without patient check | Reproducible contract/registry and function-level authorization evidence, not HTTP exploit |
| Fresh browser task inspection | Partial clinical success and reproduced failures | [Sanitized checks](browser-checks.json), [journeys](../USER-JOURNEY-FAILURE-MAP.md) and screenshots below |
| `.venv/Scripts/python.exe scripts/check_governance.py` | Failed: historical `planned→implemented` transition at COS-074 | Same failure reproduced against committed HEAD; new review entry validates separately. [Details](governance-check.json). No historical records rewritten. |
| Review artifact integrity inspection | Seven required reports, 25 valid PNGs, all local links resolve, 12 original source hashes unchanged, over 40% UI/journey word allocation | [Scoped result](report-integrity.json); documentation integrity is not product acceptance |

Chromium version: 156.0.8078.4; Windows headless browser. Desktop continuation used 1440×1000 CSS pixels; narrow checks used 320×800 and 390×844. Screenshots from the other browser tool can use its device pixel ratio; canvas sizes quoted in the report are DOM CSS measurements, not PNG dimensions. Fullscreen required waiting for its asynchronous transition. Strict/exact locator mistakes, an unsupported module-loading attempt and two automation timeouts were corrected; they are not counted as application defects.

The reviewer created two clearly artificial cases in the disposable fixture, one artificial lab plus correction and one artificial profile-history revision. No rights gate was bypassed, authentic data imported or external model called. The fixture credential remained in ignored local storage and was used only to fill the normal form; it is excluded from evidence.

The attempted transient PyMuPDF setup was stopped while dependencies downloaded; it is not a successful page render. Cached pypdf/Pillow then extracted the two original embedded SPEC-009 p4 figures for successful read-only visual inspection. Full visual inspection of every PDF page/figure is not claimed. Source documents remained unchanged.

After inspection, the owned artificial API/preview and native foundation services started for this review were stopped with their repository ownership-aware commands. The ignored fixture credential bundle was removed by its stop command; local data was retained. The original PostgreSQL service on 5432 was not stopped or reset. No artificial review rows were promoted or published as authentic data.

## Screenshot register

| File | What it records |
| --- | --- |
| [01-fresh-home.png](01-fresh-home.png) | First-use homepage before an internal route or sign-in |
| [02-default-demo-unavailable.png](02-default-demo-unavailable.png) | Native-start demo action fails readiness |
| [03-demo-twin.png](03-demo-twin.png) | Enabled synthetic phantom, measurement, controls, timeline |
| [04-demo-followup.png](04-demo-followup.png) | Discrete synthetic follow-up selected |
| [05-demo-clinical.png](05-demo-clinical.png) | Demo clinical content and its own collection times |
| [06-demo-insights.png](06-demo-insights.png) | Truthful local-template/no-live-model disclosure |
| [07-admin-case-library.png](07-admin-case-library.png) | Signed-in artificial project/library |
| [08-created-case.png](08-created-case.png) | Saved artificial profile and technical case heading |
| [09-clinical-entry.png](09-clinical-entry.png) | Saved lab plus expanded form interaction |
| [10-case-charts.png](10-case-charts.png) | Active corrected 12.4 g/dL observation/chart/table |
| [11-clinical-refresh-stuck.png](11-clinical-refresh-stuck.png) | Tab-dependent permissions remain unresolved after reload |
| [12-imaging-no-import.png](12-imaging-no-import.png) | No study/lesion, no import action, confusing empty/error mixture |
| [13-case-scenario-context-failure.png](13-case-scenario-context-failure.png) | Valid case link still rejected by scenario page |
| [14-primary-nav-loses-case.png](14-primary-nav-loses-case.png) | Primary Twin route asks user to reopen a case |
| [15-insights-state-uuid.png](15-insights-state-uuid.png) | Insights requires manual state identifier |
| [16-evaluation.png](16-evaluation.png) | Static evidence claims and mismatched original UX meanings |
| [17-guided-tour.png](17-guided-tour.png) | Descriptive guide with contextless route link |
| [18-mobile-home-320.png](18-mobile-home-320.png) | Entry cards remain compressed into two columns |
| [19-maximized-viewer.png](19-maximized-viewer.png) | Working expanded phantom viewport |
| [20-keyboard-followup.png](20-keyboard-followup.png) | Follow-up after camera keyboard actions |
| [21-sc05-clinical.png](21-sc05-clinical.png) | Stable phantom volume and separately generated fatigue observations |
| [22-admin-placeholder.png](22-admin-placeholder.png) | Diagnostic admin visit while signed in; static page |
| [23-activity-placeholder.png](23-activity-placeholder.png) | Diagnostic Activity visit; static page |
| [24-mobile-case-library.png](24-mobile-case-library.png) | Narrow authenticated library, no observed page overflow |
| [25-mobile-demo.png](25-mobile-demo.png) | Narrow demo layout, no observed page overflow |

Screenshots support observations but are not the sole basis: code, schemas, source requirements and interactions were inspected. Browser state races, qualified imaging review, all clinical subtypes, editor-role behavior, current source withdrawal, live provider execution, physical touch, assistive technology, browser zoom, contrast and performance remain unverified except where explicitly narrower code/probe evidence is described.

## Source learning and adoption limits

Original map edges include provenance guards over timelines, imaging mesh before 3D, branching before timeline, AI safety before insight and observation import before history update. Source pointers are retained in the task-local JSON. Retrieved academic/upstream IDs were not all read or reproduced. Actual external methodological sections inspected: SimpleITK Fundamental Concepts → Images; Stan 2.40 → Posterior and Prior Predictive Checks; W3C WCAG 2.2 Understanding Reflow → criterion/intent. No new dependency or upstream implementation was adopted, and no new empirical clinical claim was made.

The review recommends preserving physical coordinates, distinguishing replicated versus observed evidence and testing non-3D reflow. These principles inform acceptance; they do not authorize enabling a clinical capability. Original CancerOS requirements remain the product authority.
