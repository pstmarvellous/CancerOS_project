# API conformance closure

COS-071 proves the adopted contracts and security controls hold across the
whole API surface: ID-swapping isolation, role/mass-assignment denial,
strict validation with safe envelopes, escaped output with no prompt/code
execution, denied egress with closed external mode, and idempotent
interpretation-job replay.

Run the focused gate with disposable services running:

```powershell
uv run --python 3.12 python -X utf8 scripts/run_checks.py conformance
```

The target runs migrations, Ruff, mypy, the five conformance checks and
contract drift. Build fixture state before opening an HTTP session — the
session helper commits the fixture transaction, so post-session writes
are invisible to the app connection and read back as 404.

The checked flows use synthetic fixtures and mocked auth boundaries.
Live providers, genuine curation, qualified review and SPEC-011
evaluation remain open; passing checks are not penetration testing and
do not certify release readiness.
