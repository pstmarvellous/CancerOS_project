# Configuration and identity contract

COS-014; C05 foundation selection. Settings in src/canceros/settings.py are shared
by API/workers. `.env.example` contains placeholders, not external credentials.
Local generation creates ignored `.env`/`.local/development.json` without displaying
secrets. Web `.env.example` exposes only the server-side API origin. Nothing requires
NEXT_PUBLIC database, identity, storage or provider values.

| Variables | Owner / secret / behavior |
| --- | --- |
| MODE | API/worker, public config; development/test/staging/production; deployed modes fail closed |
| DATABASE_URL / TEST_DATABASE_URL | Server/test secret; PostgreSQL only; integration tests require a disposable database name |
| QUEUE_URL | Server secret; redis/rediss only; no browser use |
| STORAGE_ENDPOINT / STORAGE_BUCKET | Server config; private local service; no embedded credentials |
| STORAGE_ACCESS_KEY / STORAGE_SECRET_KEY | Server secrets, required for storage |
| MONITOR_TOKEN | Server/monitor secret; readiness never anonymous |
| IDENTITY_ISSUER / IDENTITY_AUDIENCE | Trusted server config; exact token claim match |
| IDENTITY_PUBLIC_KEY / IDENTITY_PUBLIC_KEY_FILE | Trusted RSA verification material; actual issuer enrollment/key rotation is deployment work |
| CORS_ORIGINS | Explicit allowlist; wildcard/HTTP origins rejected in deployed modes |
| EXTERNAL_INFERENCE_ENABLED | Default false; true alone cannot authorize export |
| MODEL_PROVIDER / MODEL_IDENTIFIER | Candidate identifiers, not entitlement or suitability |
| MODEL_API_KEY / EXPORT_POLICY_PATH | Server secret/versioned permission-policy reference; absent by default |
| REQUEST_LIMIT_BYTES / ARTIFACT_LIMIT_BYTES | Provisional bounded engineering caps; defaults1MiB, not clinical thresholds |
| JOB_MAX_ATTEMPTS / DEPENDENCY_TIMEOUT_SECONDS | Defaults3/3s; bounded configuration, not measured clinical workload limits |
| API_BASE_URL | Web server-only HTTP origin; no credentials accepted |

## Identity/session choice

Bearer-only RS256 JWT; no cookie authentication, so no ambient-cookie CSRF path.
Require sub, iss, aud, exp, iat and nbf; pin algorithm and trusted issuer/audience/key.
PyJWT2.15.1 official usage sections RS256/issuer/audience/expiration were inspected.
Database access.users links issuer+subject; access.memberships supplies authoritative
project roles. Token role/project claims are ignored. Missing/invalid identity is401;
foreign project404; insufficient role403. No anonymous production bypass or automatic
user enrollment. Repository injection is allowed only in explicit test mode.

GET /api/v1/me and the scoped /foundation/status expose only identity/foundation
status. The latter is a documented foundation extension, not a clinical capability.
Protected responses are no-store. Full patient-specific grants and restricted production
SQL roles must be added before real patient routes/data are enabled. No local login
UI or real account enrollment is claimed by artificial token tests.

## Export and provider boundaries

External inference defaults denied. Enabling configuration requires private key,
versioned export/1 policy, provider/model match, hash-pinned permission evidence,
allowlisted fields and exact approved input hashes. This verifies policy integrity,
not the truth/legal sufficiency of the permission record: that still requires an
actual authorized review. No such policy is supplied. Phase1 has no registered
network provider adapter; even policy-valid calls fail with NO_VERIFIED_PROVIDER_ADAPTER.
No raw notes, mappings, images or secrets are default permitted fields. Injection
text cannot grant permissions. Tests assert denied requests make no outbound connection.

Official Meta models/quickstart pages were read and name muse-spark-1.3 and
https://api.meta.ai/v1. Authenticated catalog access, keys, account entitlement,
retention/training terms and approved patient-data processing remain unverified.
No paid/model request was made. D04 and provider-related hackathon checks stay open.

Sources: https://pyjwt.readthedocs.io/en/stable/usage.html ;
https://dev.meta.ai/docs/models ; https://dev.meta.ai/docs/quickstart .

## Hackathon Compliance Impact

Applies to configuration/privacy/provider gates. No original architecture or source
specification changed. Meta identifiers are configuration only; no medical data was
sent. Tests cover auth/role/project failures, safe settings and export denial. Actual
Meta connectivity/model response identity and grounded research-agent execution are
not verified in Phase1. Source rights D03, external access D04 and deployment D06 remain open.
