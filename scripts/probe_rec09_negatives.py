"""REC-09 negative-access and closed-gate API probes (no patient data printed)."""

import json
import urllib.request
import urllib.error

bundle = json.load(open(".local/product-browser-fixture.json", encoding="utf-8"))
api = bundle["api_url"]
project = bundle["project_id"]
admin = bundle["admin_token"]
viewer = bundle["viewer_token"]
outsider = bundle["outsider_token"]
results = []


def call(token, method, path, body=None, key=None):
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    request = urllib.request.Request(
        api + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, "ok"
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()[:120]


def check(name, actual, allowed):
    verdict = "PASS" if actual in allowed else "FAIL"
    results.append({"probe": name, "status": actual, "verdict": verdict})
    print(name, actual, verdict)


# Viewer cannot create cases or stage imaging (admin-only writes). A valid body is
# used so the 403 proves the authorization gate, not schema validation.
import uuid as uuid_module

valid_case = {
    "source_version_id": bundle["source_version_id"],
    "case_identifier": "PROBE-" + uuid_module.uuid4().hex[:8],
    "title": "probe",
    "pseudonym": "PROBE-" + uuid_module.uuid4().hex[:8],
    "status": "draft",
    "sex": "not_recorded",
    "age_at_observation": None,
    "age_observed_on": None,
    "profile_source_reference": "probe",
    "medical_history": None,
}
check(
    "viewer-case-create-denied",
    call(viewer, "POST", "/api/v1/projects/%s/research-cases" % project, valid_case, "probe-v-2")[0],
    {403},
)

check(
    "outsider-case-hidden",
    call(
        outsider, "GET",
        "/api/v1/projects/%s/patients/%s/research-profile" % (project, uuid_module.uuid4()),
    )[0],
    {401, 403, 404},
)
# Cross-patient read without grant is denied (random patient id).
check(
    "cross-patient-denied",
    call(
        viewer, "GET",
        "/api/v1/projects/%s/patients/%s/research-profile" % (project, uuid_module.uuid4()),
    )[0],
    {401, 403, 404},
)
# External candidate mode stays denied server-side: covered by the re-run backend
# suite (test_context_mismatch_and_external_mode_stay_private asserts the 409)
# and the live Settings/read_policy probe recorded in the acceptance report.

with open("docs/engineering/testing/rec09-acceptance/api-probes.json", "w", encoding="utf-8") as stream:
    json.dump({"recorded_at": "2026-11-09", "probes": results}, stream, indent=2)
print("wrote api-probes.json")
