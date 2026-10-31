# ADR-058: unified responsive research shell with URL-owned selection

COS-072 consolidates the existing Phase 1 shell and Phase 2–4 thin slices
into one readable responsive application without new frameworks, demo apps
or contract changes. One `AppShell` owns primary navigation (workspace,
cases, guided demo, evaluation), case sub-navigation (overview, twin,
scenarios, sources) and a single active-selection line read from the URL.

Selection ownership: URL carries authorized project/patient/branch/run/
state/lesion/panel/comparison IDs; server responses own scientific data;
local state owns camera and temporary drafts only. No payloads go into
browser storage. Route pages that complete in later tasks render honest
capability-specific blocked states instead of stubs or disabled buttons.

The documented SPEC-009 palette tokens already existed in `globals.css`;
COS-072 adds the two missing tokens referenced by the prompt (viewport
`#111827`, lesion `#E9A38A`) and responsive navigation/selection styles with
kept landmarks, skip link, visible focus and reduced-motion behavior. Color
values are reused as a starting point, not claimed compliant.

Fixture denominators: shell selection/navigation component tests plus the
existing 51-test suite; lint/typecheck/build/contracts green. Real-device
interaction, target-hardware performance and usability evidence remain open.
