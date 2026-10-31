# Case library runbook

The `/cases` page renders `CaseLibrary` against the same-origin proxy
`/api/cases?project=<uuid>`, which forwards the caller's authorization
header to `GET /api/v1/projects/{project_id}/patients` and returns the
server page unchanged with `private, no-store` caching.

```powershell
npm run lint
npm run typecheck
npm run test
npm run build
npm run contracts:check
```

Expected: 58 component tests green (3 case-library tests), production
build with the `/api/cases` dynamic route, contract drift passing with no
backend changes. To exercise against real data, start the API and open
`/cases?project=<project-id>` with an authorized session; without one the
page shows the restricted state truthfully. No search/filter/pagination
controls ship in this slice because the adopted patient-list contract
exposes no such semantics.
