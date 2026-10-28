# Authorized engineering mesh preview

Build/run the existing local web and API. Visit `/mesh-preview`, supply owned project,
patient and mesh-QC report UUIDs plus an authorized editor bearer token. These inputs
are engineering access tools, not a patient onboarding or identity-provider login UI.
Use Load private mesh. Successful reads show synthetic/private/pending-review labels,
source-time availability, annotation class, RAS/mm and authoritative mask quantities.

Select an annotation without changing shared camera scale. Rotate/pan/zoom through
buttons (Tab then Enter), or choose Interact with3D for pointer/touch gestures.
Escape/Done ends pointer interaction. Reset restores the original full-asset frame;
Fit preserves view direction. Values and geometry are not changed by these controls.
Context is omitted because no eligible patient breast-region anatomy is available.
No context/public-demo rights are implied by passing technical mesh QC.

Private connection inputs remain in page memory only. Use Clear private view when
finished. Changing inputs clears old geometry immediately. Wrong/expired tokens,
ownership or current rights failures give a recoverable status. Blocked mesh QC does
not invent geometry. WebGL failure retains the source-mask table and Retry3D.
The fixed public API origin uses NEXT_PUBLIC_API_BASE_URL at build time; backend
CORS must authorize the actual web origin. No arbitrary URL fetch destination exists.

## Repeat the real engineering browser smoke

Start owned data dependencies and migrate the explicitly disposable test DB. Ensure
port8000 is free; fixture launcher refuses to replace an existing API. Run:

```powershell
uv run python scripts/migrate_test.py
uv run python scripts/mesh_browser_fixture.py
uv run python scripts/run_checks.py frontend
uv run python -c "import sys; sys.path.insert(0,'scripts'); from local_services import start; start('web')"
uv run python scripts/run_checks.py mesh-preview
uv run python scripts/mesh_browser_fixture.py --stop
```

The fixture seeds artificial source/mask/QC/measurement/mesh/LOD through actual SQL
and private S3, then serves normal RS256-authenticated API reads on loopback. Its
temporary JWT bundle and owned-process record live only under ignored .local; never
attach/commit/print them. Stop removes the bundle after verifying process identity.
No user data/object cleanup is performed. Do not stop unrelated services to acquire
the port. If web was already running with an older build, restart its owned process
after building before verification. In a live service, use its authorized identity
flow instead of this isolated test launcher.

Evidence includes sanitized fixture screenshot, actual browser interaction and
initial render timing. It does not pass the 30warm/5cold target-device performance
protocol, genuine breast anatomy, independent scientific review or publication gates.
