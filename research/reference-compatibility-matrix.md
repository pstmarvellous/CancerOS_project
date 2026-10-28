# Adopted reference compatibility (scoped entries)

This records only current mesh additions; it is not an audit of all proposed
repositories, models or source data in COS-REF-001.

| Reference | Pin | Owned boundary | Decision | Evidence/remaining gap |
| --- | --- | --- | --- | --- |
| scikit-image | 0.26.0 | Binary mask→RAS/mm surface | Adopt dependency; owned adapter | mesh-reconstruction.json; authentic anatomy/general topology pending |
| SciPy ConvexHull | 1.17.1 | Candidate convex LOD, independently exact-checked | Reuse existing dependency | mesh-quality.json; concave/compound intersections unsupported |
| Three | 0.186.1 | Private typed mesh→interactive preview | Adopt dependency; no anatomy assets | frontend.json/mesh-preview.json when executed; final device/demo pending |

Dependencies and code licenses are separate from annotation/data/model rights.
No entry establishes external inference, source acquisition or publication approval.
