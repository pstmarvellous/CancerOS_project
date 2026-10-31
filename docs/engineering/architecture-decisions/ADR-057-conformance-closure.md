# ADR-057: final API authentication/authorization/validation conformance

COS-071 closes Phase 4 Workstream 09 with cross-cutting conformance over the
adopted Phase 1 identity/session integration and the COS-057–070 services.
No second auth system, no new endpoint catalog and no domain-logic change
are introduced. The five checks exercise cross-project/patient/branch ID
isolation, role-escalation/mass-assignment denial, strict request validation
with the canonical error envelope, output escaping with prompt-injection
nonexecution and denied egress, plus one end-to-end state → manifest →
interpretation-job → grounding journey.

One staged-test defect was fixed without touching implementation: the e2e
test built its twin state after opening the HTTP session, so the fixture
transaction commit hid the new snapshot from the app's connection and the
manifest/state reads returned 404. Building the state before opening the
session matches every neighboring closure test and keeps the suite green.
An unused `pytest` import was also removed to keep Ruff clean.

Fixture denominators cover isolation, validation, escaping and the e2e
journey — penetration testing, certification, live-provider behavior,
real-data evaluation and qualified review remain explicitly open. Passing
conformance checks do not establish clinical suitability or release
readiness.
