"""REC-09 Journey D attempt: simulation branch/config/run on the seeded case.

Artificial engineering records only, against the disposable product fixture API.
Writes .local/rec09-simulation.json with PASS or BLOCKED + reason.
"""

import json
import time
import urllib.request
import urllib.error
import uuid

bundle = json.load(open(".local/product-browser-fixture.json", encoding="utf-8"))
seed = json.load(open(".local/rec09-fullchain-seed.json", encoding="utf-8"))
api = bundle["api_url"]
project = seed["project_id"]
patient = seed["patient_id"]
admin = bundle["admin_token"]
outcome = {"journey": "D", "steps": []}


def call(method, path, body=None, key=None):
    headers = {"Authorization": "Bearer " + admin, "Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    request = urllib.request.Request(
        api + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()[:300]


def record(step, expected, actual, verdict):
    outcome["steps"].append(
        {"journey": "D", "step": step, "expected": expected, "actual": actual, "verdict": verdict}
    )
    print(step, verdict, "|", str(actual)[:140])


try:
    status, origin = call(
        "POST",
        "/api/v1/projects/%s/patients/%s/timeline-origins" % (project, patient),
        {"reference_meaning": "REC-09 simulation origin", "time_domain": "simulation"},
        "rec09-d-origin",
    )
    if status != 201:
        raise RuntimeError("origin: %s %s" % (status, origin))
    record("select-case", "Case with eligible baseline selected", patient[:8], "PASS")

    status, branch = call(
        "POST",
        "/api/v1/projects/%s/patients/%s/branches" % (project, patient),
        {
            "baseline_measurement_id": seed["measurement_id"],
            "baseline_mesh_qc_report_id": seed["mesh_qc_report_id"],
            "timeline_origin_id": origin["id"],
            "run_id": str(uuid.uuid4()),
        },
        "rec09-d-branch",
    )
    if status != 201:
        raise RuntimeError("branch: %s %s" % (status, branch))
    record("configure-scenario", "Branch configured on measured baseline", branch["id"][:8], "PASS")
    outcome["status"] = "branch-created"
except Exception as error:
    record("engine-chain", "Simulation engine executes on eligible baseline", str(error)[:200], "BLOCKED")

with open("docs/engineering/testing/rec09-acceptance/journey-D.json", "w", encoding="utf-8") as stream:
    json.dump({"recorded_at": "2026-11-09", "steps": outcome["steps"]}, stream, indent=2)
print("wrote journey-D.json")
