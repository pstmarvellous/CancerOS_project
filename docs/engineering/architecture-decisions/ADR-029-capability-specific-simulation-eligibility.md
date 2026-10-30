# ADR-029: capability-specific simulation eligibility

COS-042. Reuse stored branch/config/measurement/state and current-rights evidence.
The public request contains only an owned config ID and requested capability; it
cannot assert receptor values, source approval, rule review or eligibility flags.
An immutable audit report explains eligibility at check time. Execution/publication
must reevaluate; an old eligibility receipt is never a grant.

`simulation-eligibility/1` separates eligible/ineligible/insufficient_data with
baseline hash, exact rules, missing fields, source IDs, reasons and next actions.
Numerical measurement and patient-derived anatomical mesh are distinct capabilities.
Optional labs do not block a descriptive scenario without an exposure assumption.
Unknown/equivocal/unrecorded receptors are not negative and cannot be made positive
by a synthetic value. Conflicting current assertions remain conflicts.

The matrix records only specification-required context guards. All specific exposure
options lack qualified rule review and remain disabled. Endocrine/HER2 guards do
not establish treatment appropriateness; immunotherapy has no invented subtype
allowlist. Surgery requires a discrete residual/removal transition and stays disabled.
No dose, biological response parameter or contraindication threshold is introduced.

Current baseline/state implementations are unverified engineering fixtures. Their
administrator publication cannot satisfy authentic observed-baseline approval.
Test-only pending run snapshots may record an insufficient eligibility result; they
never enable constrained production runs. Production authorization remains denied.
The later COS-050 publication path must recheck current source rights and frozen
scientific inputs. Source revisions mark old baseline/config snapshots superseded
without mutating their content.

Negative-rights reports are audit metadata, not newly usable scientific derivatives.
They are stored outside resource grants so a denied source can still be explained;
they contain structured reasons/references and no copied source patient payload.
