# Local development runbook

Primary path: native Windows API/web, isolated PostgreSQL, one SeaweedFS mini process,
one password-protected Redis Windows-port process. No Docker, GPU, model key or cloud
account is required. Original PostgreSQL service is left untouched. No clinical data
is loaded by these commands.

```powershell
uv sync --locked
npm.cmd ci
npm.cmd run contracts:generate
npm.cmd run build
uv run python scripts/bootstrap_tools.py
uv run python scripts/dev.py start foundation
uv run python scripts/dev.py status
uv run python scripts/worker_smoke.py
uv run python scripts/dev.py stop foundation
```

PostgreSQL binaries default to C:/Program Files/PostgreSQL/15/bin; set POSTGRES_BIN
to a compatible installed directory if needed. bootstrap_tools downloads pinned
Windows-only local service tools over official release HTTPS; hashes are recorded
under ignored .local/tools. Review ADR-003 for source/interface/licensing limits.

Profiles: `shell` starts API/web only, leaving dependency readiness unavailable when
data services are absent; `data` starts PostgreSQL/storage/queue; `foundation` starts
both. Stop/restart retains data. No destructive reset command exists. CPU workers run
only by explicit `uv run python -m workers.digest` (bounded engineering queue batch).
Digest success is a persisted ready result, not published scientific output.

Synthetic demo (token-free): `foundation` and `data` startup automatically ensures a
valid `.local/synthetic-demo.json` bundle (skips rebuild when valid with 24h+ left;
refreshes inside the window). To validate only, or rebuild explicitly:

```powershell
uv run python scripts/prepare_synthetic_demo.py --check
uv run python scripts/prepare_synthetic_demo.py --force
```

The bundle expires 7 days after preparation; the homepage enables Explore Interactive
Demo only when the bundle validates. Normal startup sets `CANCEROS_SYNTHETIC_DEMO=1`
for the web process, so no manual step is needed after `dev.py start foundation`.

| Component | Private loopback ports / location |
| --- | --- |
| Web / API | 3000 / 8000; .local/web.log / api.log |
| Isolated PostgreSQL | 55432; .local/postgres; 64MB shared buffers, max20 connections |
| Redis | 56379; .local/redis; max64MB, noeviction, AOF |
| Seaweed S3 | 58333, gRPC18334; .local/objects |
| Seaweed internal master / volume / filer | 19333/18080/18888 and derived gRPC ports; all bound loopback |
| Credentials/config/PIDs | .env and .local/development.json/processes.json; never commit or display |

Startup waits for actual private object roundtrip and dependency readiness, not just
open ports. On missing executable, run the pinned bootstrap. On occupied port, inspect
the listener and stop only a verified owned process; never kill every node/postgres
process. On dependency failure, inspect private logs without printing credentials or
signed URLs. Seaweed native cold allocation can need several seconds. Redis Windows
uses /cygdrive path semantics, handled by the launcher. Windows child windows are hidden.

Lower-resource workflow: use shell for UI work, data only for persistence tests,
and run the worker on demand. Next build uses two workers. Runtime memory is recorded
as measured evidence, not a promise the complete scientific pipeline fits8GB. Heavy
imaging remains a later approved remote-processing handoff with pinned environment,
input/output manifests and explicit data-export permission; these scripts upload nothing.

Optional container services are in compose.yaml and are untested when Docker is
absent. They are an alternative to native data services, never run concurrently on
the same ports. Use private .env values; do not print compose-expanded configuration.
Do not remove named volumes during ordinary stop. Production hosting, backups/restore,
restricted runtime SQL roles and real data authorization remain separate release gates.
