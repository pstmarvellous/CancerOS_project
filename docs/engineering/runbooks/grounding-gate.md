# Grounding gate

Validate every interpretation before publication at
`POST patients/{patient_id}/states/{state_id}/interpretations/{interpretation_id}/grounding`
with interpretation_snapshot_id and optional expected_context_hash. The gate
rechecks context identity, reference membership, current rights, exact
numeric/unit fidelity, allowed-claim policy and abstention rules. `published`
is the only releasable verdict; `failed_grounding` (422) and
`withheld_insufficient_evidence` explain why with reason codes and a next
action. Never edit a rejected report into coherence; narrow the scope or
request curator review instead.

The frozen `grounding-language-suite/1` in
`src/canceros/grounding_suite.py` holds 20 grounded, 20 edge and 20
adversarial fixture cases. Gates: 100% numeric/unit/origin fidelity on
published outputs, zero published critical prohibited claims, correct
abstention on predefined critical insufficient cases. Fixture labels are not
reviewed scientific judgments; absent second review is disclosed.

```powershell
uv run python scripts/run_checks.py grounding-gate
```

The checked flow uses synthetic snapshots, fixture mutations and mocked auth
boundaries. Genuine curation, model access, qualified review and SPEC-011
evaluation remain open.
