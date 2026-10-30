# ADR-050: fail-closed grounding gate with frozen fixture suite

COS-064 implements SPEC-010 SAFE-01–25, SPEC-011 section 9 and SPEC-008
FAILED_GROUNDING over frozen contexts and template reports. No semantic
entailment, second-LLM judge or embedding similarity is admitted as proof;
only exact field equality, reference membership, rights checks and the
bounded prohibited-pattern policy decide. The gate runs identically for
template reports and private external candidates; no candidate publishes
before this gate passes.

Numeric statements compare metric code, value and unit case-insensitively
against the exact fused context members; signs, units, denominators and
volume-versus-diameter wording must match or the report fails. Citation
resolution (locator, hash, active rights) is necessary but never sufficient
for claim support: general background without permitted markers and current
passage refs fails as unsupported novel prose. Prohibited clinical patterns
(staging, survival, resistance, response grades, treatment advice, causal
adverse events, diagnosis, invented confidence) fail with a critical count;
rejected reports are withheld whole — no clause is silently deleted.

Empty findings or unmatched numerics abstain with structured
withheld_insufficient_evidence rather than a reassuring generic message. The
frozen grounding-language-suite/1 holds 20 grounded, 20 edge and 20
adversarial fixture cases with disjoint development/final naming; reported
gates are 100% numeric/unit/origin fidelity on published fixtures, zero
published critical prohibited claims and correct abstention on predefined
critical insufficient cases. Finite fixture success is not safety proof, and
absent second-review adjudication is disclosed rather than claimed.
