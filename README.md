# CancerOS

Breast cancer research prototype under implementation. Research prototype. Not
validated for diagnosis or treatment decisions.

Start with [agent instructions](AGENTS.md), [implementation guide](IMPLEMENTATION_GUIDE.md),
[task ledger](docs/engineering/task-ledger.json), [contracts](docs/engineering/integration-contracts.md)
and [module boundaries](docs/engineering/module-boundaries.md). Original specifications
are inventoried in [the source manifest](docs/specifications/source-manifest.json).

Phase 1 establishes governance and a lightweight development foundation. It does not
establish real MRI processing, a completed digital twin, five implemented scenarios,
model entitlement, authentic longitudinal evidence or clinical validation.

Python: one installable src/canceros distribution, uv/uv.lock, Python3.12. Node: npm
workspaces, one root package-lock, apps/web. Logical packages record ownership;
generated contracts are separate from their source. Native API/web and only needed
private local services form the intended low-resource workflow. See infrastructure
runbook when created; do not infer that planned services already run.

No clinical data, source mappings, provider credentials or checkpoints belong in Git.
Data_folder and local service data are ignored. Public fixtures are explicitly
engineering-only. Original source rights, public repository licensing and hackathon
eligibility remain separately reviewed release gates. The owner authorized publication
of this implementation to https://github.com/pstmarvellous/CancerOS_project.

Current verification and limitations: [Phase 1 report](docs/engineering/phase-1-verification-report.md).
Phase 2 implementation coverage and open evidence gates:
[Phase 2 report](docs/engineering/phase-2-verification.md).
Phase 3 implementation and fixture verification:
[execution record](docs/engineering/phase-3-execution.md). The private `/simulation`
and `/timeline` screens expose hypothetical runs, exact observation history,
deterministic trends and state context. See the [simulation](docs/engineering/runbooks/simulation-complete.md),
[revision update](docs/engineering/runbooks/dependent-updates.md) and
[forecast baseline](docs/engineering/runbooks/forecast-baselines.md) runbooks.
Authentic observed baselines and qualified scientific review remain gated; public
forecast requests abstain. Synthetic fixtures do not establish clinical validation.
Native startup and service profiles: [development runbook](infrastructure/README.md).
After locked installation and a frontend build, use `uv run python scripts/dev.py start foundation`.
The local shell is at http://127.0.0.1:3000. Run `uv run python scripts/dev.py stop foundation`
to stop only tracked project services while retaining local data.
