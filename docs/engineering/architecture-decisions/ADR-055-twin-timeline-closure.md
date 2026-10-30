# ADR-055: twin/timeline closure with selected-state manifest

COS-069 implements SPEC-008 state/timeline/comparison contracts and SPEC-009/010
over the existing revision-pinned assembly, temporal window, comparison and
viewer services. No state reassembly policy, no timeline semantics and no
geometry handling are changed. One new read composes owned state: the
selected-state manifest resolving exactly the chosen snapshot's measurement,
mesh and observation artifacts with stable IDs, freshness, restrictions and
a selection identity binding patient, branch and snapshot.

State list/detail/build/review/publication keep exact revision, association
head, expected-hash and If-Match semantics; old states are never rebuilt
from mutable heads. Timeline pages pin signed cursor/filter/order/revision
with unknown times unplaced and DCE phases never treated as visits;
simulation timelines require the exact published completion. Comparisons use
the deterministic service with comparable/not_comparable/insufficient_data,
exact endpoint IDs, metric/unit integrity, null zero-baseline percentages
and hypothetical_vs_observed labeling instead of efficacy. Observed builds
take expected revision and OBSERVED context only; synthetic states come from
authorized runs; lab-only updates retain historical geometry with notice.
Fixture denominators cover manifest coherence, pair rejection, scope
isolation and HTTP boundaries — temporal correctness stays with Phase 3
suites and review remains open.
