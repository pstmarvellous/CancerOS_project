# Coding standards

COS-004. Contract authority: SPEC-008 sections 3–4/11/18; audit A01/A02/C03.
Python 3.12 is the selected local runtime; uv manages one pyproject/uv.lock and an
installable src-layout distribution. TypeScript strict mode and npm workspaces use
one root package-lock. Resolve and lock actual compatible versions at COS-010/011.
Use Ruff formatting/lint, mypy, pytest; ESLint, tsc and component tests. Configuration
and successful execution are later tasks, not implied by this selection.

Python module/functions snake_case, types PascalCase; TypeScript components/types
PascalCase, values camelCase; wire fields snake_case. Server creates UUIDs. Quantities
cross JSON as finite decimal strings, with explicit dictionary units. Preserve original
source values/units separately from conversions. Dates, offset timestamps, relative
days and unknown are discriminated time variants, not coerced datetimes.

Canonical contracts own provenance, context, availability, QC and publication types.
Controlled codes use versioned dictionaries. Clinical visit, imaging acquisition,
snapshot, branch and job are separate entities. No untyped metadata blob substitutes
for core scientific fields. No duplicated browser clinical arithmetic or origin enums.

Input rejects unknown fields; output supports safe unknown future values in the UI.
Use Problem Details errors with safe field pointers and correlation IDs. Structured
logs omit request bodies, raw notes, source keys, credentials and signed URLs. Do
not expose exception text/validation input values. Parameterize SQL, use transactions,
number migrations, pin dependencies, preserve small reviewable diffs. Comments explain
domain meaning, assumptions and limits. User wording describes available behavior.

Every substantive module task records mapped behavior, governing spec section,
physical/temporal units, decision alternatives and local negative/acceptance tests.
References go in reference-reviews/TASK.md; versioned design decisions go in
architecture-decisions/. Map IDs are stable navigation, not clinical dictionary codes.
