# COS-REVIEW-003 — independent review

Review date: 6 November 2026 (WAT). Repository baseline: `4ce26c0cfecb3eea915640d82f7af0e33e5cf08e` plus the working tree inspected during this review.

**Verdict: do not accept the current build as the specified integrated CancerOS research prototype.** A usable artificial case/clinical-record slice and a coherent read-only phantom demonstration exist. Authentic imaging onboarding, ordinary scenario generation, grounded insight requests and cross-screen state continuity remain incomplete.

Read the [executive assessment](EXECUTIVE-PRODUCT-REVIEW.md), then the primary [UI/UX review](UI-UX-DEEP-REVIEW.md) and [recovery plan](PRIORITIZED-PRODUCT-RECOVERY-PLAN.md).

| Deliverable | Purpose |
| --- | --- |
| [Executive product review](EXECUTIVE-PRODUCT-REVIEW.md) | Intended product, actual delivery and separate acceptance verdicts |
| [UI/UX deep review](UI-UX-DEEP-REVIEW.md) | Largest assessment: first use, screens, interactions, visual hierarchy and accessibility |
| [Specification compliance matrix](SPECIFICATION-COMPLIANCE-MATRIX.md) | Original requirements mapped to implementation, entry points and evidence |
| [Seven-phase gap review](SEVEN-PHASE-PRODUCT-GAP-REVIEW.md) | What each phase contributed and whether it reached the user |
| [Architecture and integration review](ARCHITECTURE-AND-INTEGRATION-REVIEW.md) | Contracts, science, authorization, root causes and smallest corrections |
| [User journey failure map](USER-JOURNEY-FAILURE-MAP.md) | Reproduction steps, successful partial journeys and blocked continuations |
| [Prioritized recovery plan](PRIORITIZED-PRODUCT-RECOVERY-PLAN.md) | Dependency-aware work and observable exit conditions |

## Independence and evidence boundaries

The owner explicitly requested a fresh assessment ignoring previous reviews. Earlier product reviews, audit conclusions, browser reports and old screenshots were excluded as evidence. A checkpoint/startup document encountered during discovery contained historical claims; none were accepted as findings. Original requirements, design decisions, current code, prompt responsibilities and ledger status metadata were inspected. The consolidated predevelopment audit was not used to reach the verdict; adoption uncertainty is recorded rather than silently resolved from it.

The principal agent conducted browser inspection and integrated three bounded AI-agent inspections: original specifications, frontend implementation, and backend/scientific/security implementation. These are AI specialist perspectives, not independent human clinicians, statisticians or participant research. No such consultation or clinical approval occurred.

The application was freshly built. First-use browser sessions started at `/` without preloaded credentials, state IDs or internal routes. The authenticated continuation used the existing **artificial product fixture**, through the visible sign-in form, against an explicitly disposable local database. Manual diagnostic visits to `/admin` and `/activity` are labeled as such; they do not count as discoverable user journeys. No authentic records, source PDFs, map sources or application code were changed. No model request, publication, push, deployment or external patient-data transfer occurred.

UI/UX is the primary deliverable. Its detailed screen assessment and reproduction map together account for more than 40% of the substantive assessment narrative; this is a report allocation, not a numerical product score.

## Evidence index

- [Browser checks and explicit limitations](evidence/browser-checks.json).
- [Prepared family values observed after loading](evidence/demo-family-observations.json).
- [Fresh original PDF identities, hashes and reading coverage](evidence/source-inventory.json).
- [Executable contract/security probes](evidence/contract-probes.py) and [sanitized results](evidence/contract-probes.json).
- [Evidence and check register](evidence/CHECKS.md), including screenshot index and actual commands.
- [Task-local original-map context](../../reference-reviews/COS-REVIEW-003-INDEPENDENT.md). Retrieved pointers are not proof of textbook reading or clinical validation.

Line references describe this checkout; they can move during later work. Requirement citations use original document IDs, PDF page numbers and sections. Exact source paths are in the inventory. Screenshots contain artificial review data only. All findings distinguish browser observation, code inspection, contract probe and untested risk.
