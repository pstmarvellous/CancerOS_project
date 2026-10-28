# Python foundation

COS-010. One installed distribution from src/canceros, managed by root pyproject.toml
and uv.lock. Python3.12.14 selected and installed via uv after the bare `python`
Windows Store alias proved unusable. Use `uv run`, not that alias. No GPU/imaging or
training framework is required for API startup.

```powershell
uv sync --locked
uv run uvicorn services.api.main:app --host 127.0.0.1 --port 8000
uv run pytest tests/test_api.py tests/test_contracts.py tests/test_settings.py
uv run ruff check src tests scripts
uv run mypy
uv run python scripts/generate_contracts.py
uv run python scripts/generate_contracts.py --check
```

Health/live is process-only. Health/ready requires a private monitor token and real
dependency checks, otherwise returns 503. Patient/scenario/AI endpoints do not exist
yet. Correlation IDs and JSON log messages exclude input bodies, URL query strings,
notes, credentials and arbitrary exception text. Errors use RFC9457 Problem Details.

Pydantic owns decimal-string quantities, explicit time unions, timeline-origin
identifiers, separate origin/context/availability/QC/publication. These are engineering
validation types, not clinical dictionaries or proof of claim grounding. Original
units and detailed clinical observation variants remain future domain work.

C01 domain discovery and C04 assembly runtime are future work. C02/C03 persistence
verification belongs to COS-012; C05 identity/configuration to COS-014. External model
access is neither required nor verified. Contract generation keeps current runtime
OpenAPI distinct from design-only schema and future routes.
