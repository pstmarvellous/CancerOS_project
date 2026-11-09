# COS-REC-07 critical implementation review

Reviewed 2026-11-09 against `docs/remediation_prompts/prompt_8.md`. This is an
engineering review of artificial fixtures, not clinical validation or proof of
live Meta execution. Prior uncommitted work was preserved.

## Original completion claim

The earlier `verified` claim was too broad. The test named “clears stale results
on state change” never changed state. The existing HTTP context test replaced
the context builder and tested an invalid token rather than crossing two actual
patient/state identities. The earlier browser explanation evidence exercised the
static demo rather than the authorized case context/interpretation chain.

## Defects found and repaired

| Finding | Consequence | Repair and regression |
| --- | --- | --- |
| State picker only updated its selected ID | Old prose and context remained beneath a new selection; generation could send the new state with the old context | `insights-explorer.tsx` clears all derived result state, aborts and invalidates pending requests, and resets case state through a keyed component. Tests actually change states, check the changed numeric value and resolve an abort-ignoring old request. |
| Deep-link state loading shared the branch-inventory abort controller | Loading the linked state could cancel the branch list | Branch inventory owns its controller separately. |
| Note assertions rendered as background research passages | Evidence meaning and source references were wrong; real passages were absent | Separate unverified note assertions (including negation and certainty) and `context.passages`, with document/corpus/locator references. |
| Context projected only a time basis | “relative_day” replaced the actual selected day | Preserve actual relative day/date/timestamp and time domain, while retaining unknown times as unknown. |
| Default rebuild discarded comparison/note/retrieval context inputs | A legitimately assembled non-default context failed its expected hash at interpretation | Optional pinned `InterpretationInput.context_input`; route validates patient/state against the authorized URL and rebuilds the same inputs. Browser sends the complete pinned input. |
| Comparison ID was accepted without projecting its measurements | No useful comparison findings, and future/different revision contexts were insufficiently constrained | Independently cited comparison values; require same branch, revision, relative-time anchor/domain and strictly earlier time. No new arithmetic, lesion correspondence or treatment-effect claim. |
| Context did not require current source action rights on its snapshot | Retained history could supply content after source withdrawal | Reuse `_usable` for selected and comparison snapshots. Actual lineage withdrawal test blocks subsequent context use. |
| Caller could select a same-patient extraction absent from the snapshot | Snapshot context could acquire unrelated or later note content | Require the extraction's exact note document among canonical snapshot note members; recheck branch. Actual unrelated-note HTTP request returns 409 without text. |
| API adapters passed no private storage | Canonical retained note context failed while loading private text | Inject configured `PrivateStorage` in context/export-view and interpretation adapters. Actual private S3/SQL/HTTP canonical-note roundtrip verifies success. |
| Template findings lacked readable synthetic wording | Selected numerical values lacked a clear hypothetical description | Each synthetic numeric finding states its exact source time/value/unit and hypothetical simulation status. Comparison values remain separately cited. |
| Private external candidates were labeled “Saved result” and rendered | A future caller could misrepresent or expose unpublished prose | Explicit private/unpublished label and withheld prose. Regression verifies candidate summary/numeric findings do not appear. |

## Checks actually executed

- `uv run pytest tests/test_context_runs.py tests/test_interpretation_runs.py tests/test_grounding_runs.py tests/test_grounding_validator.py -q`: **26 passed**. Includes genuine disposable PostgreSQL/private object-storage state generation, exact zero-volume output, comparison grounding, two actual patients, crossed-state HTTP access, source withdrawal, canonical note extraction and unrelated-note rejection. No live provider request.
- `npm.cmd test -- apps/web/components/insights-workspace.test.tsx apps/web/components/insights-explorer.test.tsx`: **9 passed** after final changes.
- `npm.cmd test -- apps/web/components/interpretation-panel.test.tsx`: **3 passed** after the mode-label/prose repair.
- Targeted Ruff checks and final format check passed for all eight changed Python files.
- Mypy passed for the seven changed runtime Python modules.
- ESLint passed for explorer/panel and their three test files.

Intermediate failures exposed a missing test-fixture `passages` array, outdated
request-body expectation, an incorrect extraction fixture attribute and the
extractor's punctuation-free span. These fixture assertions were corrected; no
runtime safety gate was weakened to make them pass.

## Result modes and remaining gates

**Local:** implemented and verified on the actual owned backend path with
artificial data. Exact source values remain deterministic; zero remains zero.
Imported clinical rows that retain pending quality are not promoted into primary
interpretation facts to satisfy a test.

**Cached/saved:** existing persistence contracts remain distinct. Insights does
not currently retrieve a cached report, and this review does not claim a cached
browser workflow passed. A saved record is never sufficient evidence of live use.

**Live:** unavailable in this reviewed flow; `external_candidate` remains denied.
No permitted live Meta request or validated live result was performed by this
review. Source rights, external processing authorization, provider access and
scientific/publication gates remain separate.

**Browser:** root integration review owns fresh canonical case/state browser
evidence. This sub-review does not substitute component tests or static demo
screenshots for that acceptance gate. See the enclosing remediation audit for
the final browser result and generated-contract/build verification.

## References and compliance impact

Consulted `IMPLEMENTATION_GUIDE.md`, its four governing Markdown sources,
authority/scope and reference consultation policy; original local specification
extracts for SPEC-006 §2.3–2.4, §4.1, §6.6–6.7, §7.4 and SPEC-009 §1–4.
Capability query `interpretation` returned `D.AI`, `AI.LLM`, `WF.AI`, `EVAL.E2E`
and their provenance/grounding/safety dependencies. Academic query `grounding`
returned no direct match, retained as a gap. Repository/scientific query
`interpretation` returned `AI.06` and A12/A14/P03 pointers; no claim of full
paper/book review or empirical clinical validation follows from those pointers.
The parent task also records the combined audit map context.

No new gateway, inference provider, medical policy, patient export or dependency
was introduced. Existing modular services and private storage were reused.
Contract additions are optional; generated clients and final drift checks are
coordinated by the root reviewer. Source specifications/maps remain unchanged.
