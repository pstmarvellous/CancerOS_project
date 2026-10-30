# ADR-038: separate observation time and knowledge time

COS-051. A timeline query explicitly pins an immutable patient revision and either
observed source, synthetic source-fixture, or exact simulation branch/run/completion
scope. Complete simulated outputs must have been explicitly published. Read selected
state memberships and actual measurements; never read latent future profiles as
observations. Preserve source precision, original time domain and unknown times.

Knowledge-as-of uses source observation/retraction `recorded_at`, and the first
explicit complete-run publication for generated observations. Within the selected
revision, corrections are followed back to the record known at that cutoff;
retractions are applied by their own knowledge time. Current rights still govern
access to historical evidence. No calendar date, timezone or midnight is invented.

Time partitions retain basis/domain, relative anchor and documented shift basis.
Unknown/incomparable times remain visible unresolved records and cannot enter
ordered numeric features. Numeric and ordinal measures retain separate semantics.
Features provide actual intervals, counts, conflicts and last-measurement age,
without copying values into absent visits. Exact mask arithmetic is retained beside
rounded display quantities. Missing values retain dictionary-unit metadata where
known, which does not assert an original measurement or value.

The typed read-only `POST timeline-queries` freezes cursor membership in the
existing private cursor store. Every page rechecks all source permissions before
returning points or features. A cursor cannot change scope, revision or cutoff.
Publication and source chronology remain separate; a historical view is explicitly
marked when the patient has a newer revision. No clinical prediction is enabled.
