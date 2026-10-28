# Change control

Routine reversible implementation within approved scope: proceed with rationale.
Schema/contract/module-boundary change: versioned architecture decision plus affected
tests/generated clients. Clinical meaning, source rights and export changes: evidence
and appropriate user authorization; isolate unresolved capability, continue independent work.
No invented approval or blanket confirmation for ordinary coding. Design proposal,
adoption, implemented and verified are separate fields. Failed critical gates cannot
be waived. Evidence is task-local, never another agent's unsupported status assertion.

Ledger transitions: planned→in_progress; in_progress→verified/implemented_unverified/blocked;
blocked→in_progress; implemented_unverified→in_progress/verified/blocked;
verified→in_progress when new changes reopen it. Verified requires evidence. Validators
reject duplicate IDs, missing dependencies, cycles and invalid recorded transitions.
Trace TASK-* rows follow task state; domain rules remain separate and unverified.
