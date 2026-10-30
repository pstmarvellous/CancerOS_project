# ADR-040: computed context over exact state membership

COS-053 adds `FusionReport` as a read projection of an existing `StateView`, keyed
by the canonical state ID/hash, revision and assembly policy. No competing snapshot
table or automatic membership selection is introduced. Original typed members and
their source times, origins, definitions and current/historical roles remain visible.

`POST /fusion-queries` accepts a state identity and optional owned timeline context,
never replacement clinical values, note assertions or externally generated prose.
The optional timeline must match that state's branch/revision and published
completion. The server bounds event time at the selected state and retains the
declared knowledge cutoff; only comparisons ending at that exact state are included.
Current source rights are rechecked, including for retained historical snapshots.

Available, Historical, Missing and Conflicting blocks have explicit next actions.
Source-specific uncertainty is retained. Structured-source priority affects display
only and never deletes a conflicting assertion. No averaging, overall health score,
learned fusion, synthetic supplementation of observed data or clinical inference is
added. Absent extraction/retrieval remains unavailable. Current state contracts are
synthetic engineering fixtures; authentic observed-state enablement remains gated.
