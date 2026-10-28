# CancerOS Reference Knowledge Maps — v3.0

Two **complementary** source-navigation indexes with shared stable behavior IDs:

- `repository-map/`: 17 GitHub repositories and a map of **40** engineering behaviors to implementation candidates, with *inspect/adopt/avoid/test* instructions.
- `scientific-map/`: 18 academic/lecture/reference entries, 5 paper/standards records and **40** behavior evidence routes.
- `shared/combined-knowledge-graph.json`: 80 nodes and 209 typed links.

Existing CancerOS design and source maps remain separately available and are not replaced. This package reuses their stable behavior identifiers and academic locators.

## Installation
Copy this directory to `CancerOS/docs/reference-maps/` and merge `AGENTS-map-appendix.md` into the root `AGENTS.md`.

## Search
```sh
python docs/reference-maps/shared/query_references.py IMG.10
python docs/reference-maps/shared/query_references.py tumor
python docs/reference-maps/shared/query_references.py SIM. --json
```

## Verification status
References are candidate engineering resources. Mapping does not certify code checkout, license, weights access, execution, model quality or clinical validation. Read `shared/AGENT-DUAL-MAP-PROTOCOL.md` before implementation.
