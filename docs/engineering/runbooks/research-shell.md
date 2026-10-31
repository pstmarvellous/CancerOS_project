# Research shell runbook

The layout renders one shared `AppShell` above every route: primary
navigation, optional case navigation when a patient is selected, the
research safety notice and the active selection line. Individual pages no
longer render their own `<main>` wrapper.

Current routes: `/` workspace, `/cases`, `/guided-demo`, `/evaluation`,
`/activity` (editors), `/admin`, plus existing `/mesh-preview`,
`/timeline`, `/simulation`. Later Phase 5 tasks fill each destination with
real API-connected behavior; until then each route states what it needs and
who may use it.

Selection reaching a page travels in the URL query string
(`project`, `patient`, `branch`, `run`, `state`, `lesion`, `panel`,
`compare`). Nothing clinical is stored in browser storage, analytics or
signed links.

```powershell
npm run lint
npm run typecheck
npm run test
npm run build
npm run contracts:check
```

The checked flow uses synthetic rendering tests only. Target-device
interaction, screen-reader walkthroughs and measured performance remain
open and are recorded per task, not assumed from this slice.
