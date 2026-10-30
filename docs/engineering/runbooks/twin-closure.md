# Twin state and timeline closure

Read one selected state coherently: `GET states` (branch/published filters,
stable cursors), `GET states/{state_id}` for the exact view, and
`GET states/{state_id}/manifest` for the artifact manifest with stable IDs,
freshness and selection identity. Resolve viewer grants from the manifest
only; cancel or discard any response whose snapshot hash no longer matches
the current selection, so old geometry can never appear as a new scan.

Query timelines at `POST timeline-queries` with pinned windows; unknown
times stay unplaced and DCE phases are never extra visits. Compare at
`POST trend-queries` with exact endpoint pairs; incompatible metrics,
zero-baseline percentages and mixed hypothetical/observed contexts report
explicitly instead of numbers. Lab-only states keep historical geometry
with its actual time and notice, never as a new acquisition.

```powershell
uv run python scripts/run_checks.py twin-closure
```

The checked flow uses synthetic states, fixture windows and mocked auth
boundaries. Temporal correctness, genuine review and COS-071 coverage
remain open.
