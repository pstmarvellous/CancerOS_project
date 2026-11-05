# COS-E2E-001 Test Environment

Recorded: 2026-11-02 (UTC). Scope: real loopback development stack on the
developer laptop; no deployment, no external transmission.

## Services

| Service | Endpoint | Result |
|---|---|---|
| PostgreSQL (loopback disposable dev cluster) | 127.0.0.1:55432 | Ready via `scripts/dev.py start foundation` |
| Private object store | 127.0.0.1:58333 | Ready (startup byte-probe round-trip) |
| Queue | 127.0.0.1:56379 | Started, tracked in `.local/processes.json` |
| Backend API | http://127.0.0.1:8000/health/live | 200 `{"status":"ok"}` |
| Research shell | http://127.0.0.1:3000 | 200, all 11 routes serve |
| Web API proxy | http://127.0.0.1:3000/api/health | 200 `{"status":"ok"}` |

Started with `EXTERNAL_INFERENCE_ENABLED=false` in the process environment only
(the committed `.env` carries `EXTERNAL_INFERENCE_ENABLED=true` with a live
`MODEL_API_KEY`, and `Settings` refuses to boot without a verified versioned
export policy). No file was modified; the credential was never printed, logged,
or committed. Live-provider verification stays BLOCKED pending export-policy
evidence (Scenario F).

## Browser

- Playwright 1.64.1, Chromium headless (existing `tests/browser/` harness).
- New probes: `tests/browser/e2e-journey-probe.spec.ts`,
  `tests/browser/e2e-negative-probe.spec.ts`.
- Screenshots: `route-*.png` in this directory (sanitized: no identifiers,
  no credentials; gated routes show honest empty states).

## Hardware and limits

- Windows 11 laptop (platform string in evidence JSONs), Ryzen 5 / 8 GB class.
- Development build only. No performance, device-matrix, or production-load
  claim. Memory-heavy suites (timeline DB fixtures) were not run against the
  live dev stack to avoid database contention; unit/contract suites ran green.
