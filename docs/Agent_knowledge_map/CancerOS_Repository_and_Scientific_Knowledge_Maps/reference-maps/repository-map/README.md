# CancerOS repository implementation knowledge map

This map indexes **existing software references** by CancerOS behavior ID. It does not represent cloned, installed, licensed, tested or integrated software.

Use `repository-register.json` to inspect candidate repos, `behavior-to-repository.json` for implementation choices, and shared `query_references.py` for lookup. Pin commits and assess repository, model and data licenses before adoption.

## Evidence classes
- `documentation_referenced_not_executed`: upstream design/public documentation reviewed; no reproduction evidence.
- `candidate_not_executed`: relevant project to inspect; source tree/API and compatibility still require validation.
- `verified_locally`: only set after recording command, commit, test artifact and output.

Do not claim reuse or upstream accuracy until the specific build passes CancerOS fixtures.
