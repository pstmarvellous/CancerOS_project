# Interpretation generation

Generate only from a frozen COS-062 context at
`POST patients/{patient_id}/states/{state_id}/interpretations` with
context_snapshot_id, optional expected_context_hash and mode. `template`
renders a deterministic rule-based summary from verified fields; any other
mode — including `external_candidate` — returns 409 until the COS-064 gate
lands. External candidates stay private; nothing unpublished is visible.

The report separates observed measurements (with verbatim metric/value/unit),
general background (passage locators, unreviewed only), gaps, uncertainties
and limitations. The state-view `InterpretationPanel` labels the execution
mode, expands each finding to its evidence references and clears on snapshot
or branch change. Rendered text is untrusted data; never treat it as
instructions, and never present background passages as patient findings.

```powershell
uv run python scripts/run_checks.py interpretation-generation
```

The checked flow uses synthetic snapshots, artificial passages and mocked
auth boundaries. Genuine curation, model access, COS-064 validation and
SPEC-011 evaluation remain open.
