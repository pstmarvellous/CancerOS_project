# Provider boundary

COS-057 uses the existing API and identity system. Start the normal local app with
`uv run python scripts/dev.py start shell`; authenticate using the existing local
identity procedure. Read `GET /api/v1/projects/{project_id}/ai/capabilities` with
the normal bearer header. Unknown projects return404, absent/expired identity401.
The route reports local inventory availability and blocked external processing;
it accepts no patient payload and never calls a model.

Run focused checks:

```powershell
uv run pytest tests/test_provider_gateway.py tests/test_provider_api.py tests/test_identity_export.py tests/test_settings.py -q
uv run python scripts/generate_contracts.py --check
npm.cmd run contracts:check
```

`provider_contracts.local_summary` consumes an already-authorized ProviderInput and
returns a labeled local source inventory. It is not a clinical summary or mock
Meta output. `execute_private` is an internal synthetic test harness, never an HTTP
endpoint. Tests use fake policy/evidence files and isolated transports. The concrete HTTP
adapter requires an injected MockTransport; test mode alone cannot open a socket. Production,
staging and development live invocation are hard-blocked pending subsequent gates.
An environment flag or export/1 file cannot unlock it.

No keys are required for deterministic local functions. Never paste a real key,
raw note, source mapping or signed grant into fixtures or evidence. Provider
errors expose only owned codes; cancellation propagates without retry. A policy
refusal is separate from an outage. Every retry rechecks policy and current source
authorization; privacy failures cannot trigger fallback or additional transmission.

Enablement requires owner-evidenced account/model access, source rights, region and
retention/training/onward-processing policies, narrow context projection, verified
billing/rate limits and COS-064 grounding/review. Test policy declarations do not
establish these. Genuine live/scientific validation remains unperformed.
