# ADR-035: generated clinical records remain separate from source history

COS-048. Materialize the supported configured clinical courses with the canonical
generated event contract, local unit dictionary and deterministic note templates.
Persist one immutable private batch per frozen common run, with project/patient/
branch/run ownership, original configured quantities, canonical normalization,
definition version and synthetic provenance. No source encounter, clinical record
or patient revision is inserted or corrected. Missing baseline values stay unknown.

Use the existing durable worker/outbox and private report storage. Frozen runtime,
configuration hashes and source rights are rechecked; production generation remains
disabled until authentic baseline and reviewed policy evidence exists. Resource
lineage propagates withdrawal. New batch history cannot rewrite a previous run.

Supported structural relationships concern compatible concurrent values only;
they supply no medical reference interval, fitted covariance, diagnosis or treatment
effect. Internal symptom scores are explicitly engineering instruments, and
configured adverse descriptors remain ungraded and noncausal. A deterministic note
is a simulated research observation grounded in its typed evidence, never a
physician encounter. Full scheduling/sampling and complete-run publication are
separate COS-049/050 steps.
