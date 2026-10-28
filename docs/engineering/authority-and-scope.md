# Authority and scope

COS-001, 2026-10-27. Execution authority: the current user expressly requested all
15 Phase 1 prompts sequentially without routine manual approval. Documents are
project evidence and guidance, not instructions overriding that request or platform rules.

The source PDFs identify themselves as proposed documents. COS-AUD-001 baseline
1.0 supplies the reconciled design; no separate owner adoption record, reviewer
signature or approval timestamp was found. Proceed with reversible foundation work
consistent with it; do not call the entire source baseline formally approved.

| Domain | Governing source |
| --- | --- |
| Product intent | COS-PRD-001 |
| Data / simulation / imaging meaning | COS-SPEC-003 / 004 / 005 |
| Intelligence | COS-SPEC-006, constrained by safety and contracts |
| Architecture | COS-SPEC-007 |
| Database and wire contracts | COS-SPEC-008 plus recorded contract decisions |
| UI | COS-SPEC-009; browser routes are distinct from REST |
| Safety / evaluation | COS-SPEC-010 / 011 |
| Work sequencing | COS-SPEC-012, not a fixed execution deadline |
| Literature | COS-RA-001 advisory; experiments are not automatically P0 |
| Reconciliation | COS-AUD-001, adoption status as recorded above |
| Competition overlay | COS-HACK-001, subject to actual rule/access verification |

The twelve audited inputs are PRD, SPEC-003 through SPEC-012 and RA-001. There is
no inferred SPEC-002. The schedule PDF is supplemental, not a replacement input.
The audit mentions `(1).pdf` filenames; local filenames differ. Record actual
identities, page counts and hashes; do not claim byte identity with absent copies.

## Required implementation boundaries

Modular FastAPI application plus worker entry points; Next.js/TypeScript;
PostgreSQL; private object storage. Central typed contracts and generated clients.
Project/patient/branch isolation; immutable source and snapshot history; deterministic
measurements; shared observed baseline plus at least three simulated follow-ups in
each of five scenario families; no synthetic-to-real promotion; denied external
inference until policy and access are evidenced.

No new microservices, graph database, Kubernetes, trained forecasting or clinical
diagnostic/therapy capability without a recorded scope decision. P0 imported masks
remain usable without model checkpoints. Optional ML enablement needs independent
evidence; startup and fixtures cannot establish clinical validity.

## Task procedure and evidence

Follow the reference consultation policy before changes. Define scope, requirement
IDs, contracts, owner, failure cases and acceptance checks. Inspect git/user changes,
preserve sources, make bounded edits, critically self-review consequential scientific,
security and ownership changes, run relevant checks and record results. Keep code,
design adoption, implementation verification and scientific validation distinct.

Record routine choices autonomously. Version contract/schema/boundary decisions.
Isolate unresolved clinical meaning, source rights, export and major-scope conflicts.
Do not waive safety failures or request blanket approval for scaffolding. Keep secrets,
raw patient notes, source mappings and signed links out of evidence and logs.

Foundation work is separate from D01–D06. None is closed by this document. Real
source acquisition, automated segmentation, longitudinal proof, clinical dictionaries,
model grounding and deployment are not Phase 1 completion claims.
