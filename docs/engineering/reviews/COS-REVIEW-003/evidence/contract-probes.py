"""Reproduce review contract failures using fabricated inputs; no service access.

Run from the repository root:
  .venv/Scripts/python.exe docs/engineering/reviews/COS-REVIEW-003/evidence/contract-probes.py

The saved-result probe is a function-level stub, not an HTTP exploit or a database
integration test. It demonstrates the authorization checks executed by read_saved
with a fabricated SQL response. It never connects to a database or external model.
"""

import copy
import json
from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "src"))

from pydantic import ValidationError  # noqa: E402

from canceros.context_contracts import ContextBuildInput  # noqa: E402
from canceros.grounding_contracts import GroundingCheckInput  # noqa: E402
from canceros.identity import Identity  # noqa: E402
from canceros.interpretation_contracts import InterpretationInput  # noqa: E402
from canceros.saved_runs import read_saved  # noqa: E402
from canceros.saved_runs_contracts import InterpretationPersistInput  # noqa: E402
from canceros.scenario_families import build_registry  # noqa: E402
from canceros.simulation_contracts import SimulationConfig  # noqa: E402
from canceros.simulation_execution import PublishRunInput  # noqa: E402


def uid(number):
    return UUID(f"00000000-0000-4000-8000-{number:012d}")


def validate(label, model, payload, source):
    try:
        model.model_validate(payload)
        return {"probe": label, "source": source, "model": model.__name__,
                "payload": payload, "schema_accepted": True,
                "qualification": "Schema acceptance does not establish runtime execution."}
    except ValidationError as error:
        return {"probe": label, "source": source, "model": model.__name__,
                "payload": payload, "schema_accepted": False,
                "errors": [{"location": list(item["loc"]), "type": item["type"],
                            "message": item["msg"]} for item in error.errors()]}


def builder_config(family="SC-01"):
    # Mirrors buildConfig in simulation-builder.tsx with its visible default days,
    # seed and volume; only branch ID/hash come from fabricated branch context.
    slots = [{"slot_id": f"slot-{i + 1}", "modality": "imaging", "relative_day": day}
             for i, day in enumerate(["10", "30", "60"])]
    return {
        "baseline_state_id": None, "baseline_hash": "a" * 64,
        "branch_id": str(uid(3)), "input_revision": 1,
        "scenario": {"family": family, "definition_version": family.lower() + "-explicit/1"},
        "treatment": {"exposure": "none"}, "schedule": {"slots": slots},
        "tumor_profile": {"metric": "numerical_region_volume", "unit": "mm3",
                          "points": [{"slot_id": slot["slot_id"], "target_mm3": "120.5"}
                                     for slot in slots]},
        "clinical_profile": {"configuration": "stable"}, "noise": {"mode": "none"},
        "missingness": {"mode": "none"}, "geometry_policy": "none", "seed": 7,
    }


def saved_metadata_probe():
    project, patient, saved, state, viewer = [uid(n) for n in range(101, 106)]
    row = {
        "id": saved, "project_id": project, "patient_id": patient,
        "context_snapshot_id": state, "context_hash": "a" * 64,
        "execution_mode": "rule_based_summary", "visibility": "visible_template",
        "model_identifier": "local-template/1", "model_revision": "unresolved",
        "prompt_version": "interpretation-template/1", "validator_version": "grounding-gate/1",
        "corpus_manifest": "fabricated-test-corpus", "finding_count": 1,
        "usage_tokens": None, "failure_stage": None, "status": "validated_ready",
        "superseded_by_id": None,
    }

    class Rows:
        def mappings(self):
            return self

        def one_or_none(self):
            return row

    class Connection:
        def __init__(self):
            self.queries = []

        def execute(self, statement, parameters):
            self.queries.append({"sql": str(statement), "parameters": parameters})
            return Rows()

    connection = Connection()
    identity = Identity(viewer, {project: "viewer"})
    returned = read_saved(connection, identity, project, saved)
    assert returned.patient_id == patient
    return {
        "probe": "saved_result_patient_authorization",
        "scope": "FUNCTION_LEVEL_STUB_ONLY_NOT_HTTP_EXPLOIT_OR_DATABASE_TEST",
        "source": ["src/canceros/saved_runs.py:138", "src/canceros/saved_runs.py:21",
                   "src/canceros/saved_api.py:88"],
        "setup": "Project viewer Identity; no patient grant is represented; all SQL rows fabricated.",
        "result": "Saved-result metadata returned without patient-grant lookup.",
        "executed_queries": connection.queries,
        "patient_grant_query_executed": any("patient_grants" in q["sql"] for q in connection.queries),
        "returned_metadata": returned.model_dump(mode="json"),
        "limitations": [
            "The connection stub fabricates the result of SQL; this does not test a live database.",
            "No JWT verification or HTTP request was performed.",
            "Returned metadata does not include raw clinical prose.",
            "A runtime HTTP reproduction would require a disposable authorized fixture and known saved-result ID.",
        ],
    }


def main():
    probes = []
    for label, model, payload, source in [
        ("insights_context", ContextBuildInput, {"branch_id": str(uid(3))},
         "apps/web/components/insights-explorer.tsx:103"),
        ("insights_summary", InterpretationInput, {"mode": "rule_based"},
         "apps/web/components/insights-explorer.tsx:128"),
        ("insights_grounding", GroundingCheckInput, {"interpretation": {}},
         "apps/web/components/insights-explorer.tsx:156"),
        ("insights_save", InterpretationPersistInput, {"interpretation": {}},
         "apps/web/components/insights-explorer.tsx:177"),
    ]:
        probes.append(validate(label, model, payload, source))
    for family in ["SC-01", "SC-02", "SC-03", "SC-04", "SC-05"]:
        probes.append(validate("builder_" + family, SimulationConfig, builder_config(family),
                               "apps/web/components/simulation-builder.tsx:161"))
    missing = copy.deepcopy(builder_config())
    for point in missing["tumor_profile"]["points"]:
        point.update(target_mm3=None, missing_reason="not measured")
    probes.append(validate("builder_missing_target", SimulationConfig, missing,
                           "apps/web/components/simulation-builder.tsx:181"))
    publication = {
        "completion_id": str(uid(4)), "expected_config_hash": "a" * 64,
        "expected_patient_revision": 1, "expected_association_head": 0,
        "expected_current_run_id": None, "engineering_attestation_sha256": "b" * 64,
    }
    probes.append(validate("publication_proxy_body", PublishRunInput, publication,
                           "apps/web/app/api/simulation/route.ts:80"))
    registry = []
    for family in ["SC-01", "SC-03"]:
        version = family.lower() + "-explicit/1"
        try:
            build_registry().resolve(family, version)
            registry.append({"family": family, "version": version, "registered": True})
        except ValueError as error:
            registry.append({"family": family, "version": version, "registered": False,
                             "message": str(error)})
    result = {
        "review": "COS-REVIEW-003", "fixture_origin": "FABRICATED_ENGINEERING_INPUTS_ONLY",
        "no_database_or_provider_connection": True,
        "scope": "Contract validation and function-level authorization inspection; not full HTTP journeys.",
        "interpretation_placeholder_note": "Ground/save use an empty report object because their outer key is forbidden regardless of report contents.",
        "reproduce": ".venv/Scripts/python.exe docs/engineering/reviews/COS-REVIEW-003/evidence/contract-probes.py",
        "contract_probes": probes, "registry_probes": registry,
        "saved_metadata_probe": saved_metadata_probe(),
    }
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
