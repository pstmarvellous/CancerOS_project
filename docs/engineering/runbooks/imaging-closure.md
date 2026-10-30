# Imaging and geometry closure

Discover studies at `GET studies` (owned associations grouped by study with
import/series counts), inspect an acquisition at `GET acquisitions/{import_id}`
(file count, status, frame shape, study/series identity) and enumerate
annotated segmentations with live QC at `GET segmentation-discoveries`.
Segmentation detail, QC reports, measurements, meshes and read grants keep
their existing routes; unavailable, blocked and failed-QC states explain
themselves with repair actions rather than empty geometry.

Request mesh/asset grants per artifact; each grant is short-lived (default
120 seconds), audited and non-logged. An issued URL may remain usable until
expiry even after withdrawal — renew the grant for continued review rather
than assuming immediate revocation. Never publish failed-QC geometry and
never drop orientation/spacing metadata in serialization.

```powershell
uv run python scripts/run_checks.py imaging-closure
```

The checked flow uses synthetic NIFTI, fixture annotations and mocked auth
boundaries. Real acquisition, qualified review and COS-071 coverage remain
open.
