# Simulation eligibility

Run `uv run python scripts/run_checks.py simulation-eligibility` against owned local
services. It uses disposable SQL/private fixtures and strict unit/context contracts.

An administrator can POST
`/api/v1/projects/{project}/patients/{patient}/eligibility-checks` with
`{"config_id":"<owned-config-version-id>","capability":"measurement"}`.
Use `anatomical_mesh` to ask for the more restrictive anatomical capability. GET the
returned Location to read the immutable audit result. Source evidence and current
rights are resolved server-side; client receptor/review assertions are rejected.
Viewer requests are denied. The result supplies ruleset version, baseline hash,
missing fields, evidence IDs, reason dispositions and next actions.

Current engineering baselines return insufficient_data for authentic approval;
anatomical requests can additionally be ineligible. Specific exposure categories
remain unreviewed. Never replace missing pathology with synthetic facts or treat
the descriptive software eligibility result as treatment advice. No particular
exposure assumption requires no invented receptors or optional labs.

Repeat a check after correction/withdrawal to see current restrictions. Prior report
and run metadata stay immutable. Every execution/publication must recheck, not trust
an earlier receipt. Test-only pending snapshots record missing eligibility and never
publish a scientific run. Production run authorization remains disabled.
