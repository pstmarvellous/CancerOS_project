# ADR-037: complete engineering run manifests and atomic publication

COS-050. Reuse the existing durable CPU worker, private artifacts and exact-membership
twin states to compose one frozen simulation run. Record immutable completion
attempts with their failure stage. Pipeline success means ready engineering output;
it never publishes. Clinical events and actual mask-derived measurements remain
separate from private latent targets. Required geometry must be realized and pass
its family constraints. Tabular runs explicitly declare measurement-only scope.

An explicit administrator command checks a ready manifest, its V1–V8 software
validation, current rights, frozen revision/association head, runtime/config hashes
and expected current-run pointer. In one database transaction it records existing
state review/publication events, the complete manifest publication, and replaces
the branch pointer. Failures/retries/cancellation cannot move that pointer or
rewrite previously published history. Individual common-run state publication
remains blocked. Test-mode engineering publication cannot approve an authentic
baseline, clinical policy or public deployment.

Regression evidence distinguishes 50 tabular trajectories plus repeated five-family
replay from curated actual mask/mesh examples for each family. Synthetic baseline
rights/QC fixtures do not close D01/D03, longitudinal D02, scientific policy C06 or
real evaluation D05. Unsupported surgery remains disabled rather than simulated by
continuous shrinkage. No efficacy/clinical-response/causality claim is introduced.
