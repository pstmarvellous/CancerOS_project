# Observation timeline and temporal features

Run `uv run python scripts/run_checks.py observation-timeline` for source revision,
knowledge-cutoff, exact generated-membership, pagination and private API checks.
Run the frontend target for `/timeline` component checks and production build.

Open `/timeline` with an authorized administrator token held only in memory. Choose
observed source, synthetic source fixture, or an exact published simulation
branch/run/completion and patient revision. Provide an aware UTC knowledge cutoff;
an optional event cutoff additionally bounds comparable observation times. Source
dates, shifted dates and relative anchors stay distinct. Unknown/incomparable
events remain visible unresolved entries and do not enter numeric windows.

The table preserves exact point/state IDs, units, precision, origin, missingness,
recording time and correction lineage. Selecting a point with an actual generated
mesh loads only that point's private geometry. Selecting a lab or unavailable point
clears the previous mesh. Temporal features report actual intervals, counts,
conflicts and last-measurement age; they do not fill another visit's values.

Pagination retains its original scope, revision, cutoffs and membership even if a
new source revision arrives. All snapshot permissions are checked on every page;
withdrawal requires a fresh permitted query. Source corrections/retractions after
the knowledge cutoff cannot silently supply future information. Full source notes,
latent generator profiles and missing values are not converted into numeric input.

Software fixtures do not establish authentic longitudinal evidence, a qualified
observed baseline, clinical significance or a forecast. Browser/WebGL interaction
for the new timeline remains a separate final integration check.
