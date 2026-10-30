"""Deterministic runtime OpenAPI plus separate foundation JSON Schema; --check fails drift."""

import argparse
import json
from pathlib import Path

from pydantic import TypeAdapter

from canceros.api import create_app
from canceros.clinical_contracts import ClinicalRecord
from canceros.contracts import FoundationEnvelope, TimelineOrigin
from canceros.settings import Settings

ROOT = Path(__file__).resolve().parents[1]


def generate(check=False):
    directory = ROOT / "packages/contracts/generated"
    directory.mkdir(parents=True, exist_ok=True)
    app = create_app(Settings(mode="test", _env_file=None))
    output = {
        "openapi.json": app.openapi(),
        "foundation.schema.json": TypeAdapter(FoundationEnvelope).json_schema(),
        "timeline-origin.schema.json": TimelineOrigin.model_json_schema(),
        "clinical.schema.json": ClinicalRecord.model_json_schema(),
    }
    for name, data in output.items():
        content = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        target = directory / name
        if check:
            assert target.exists() and target.read_text(encoding="utf-8") == content, (
                f"Contract drift: {name}"
            )
        else:
            target.write_text(content, encoding="utf-8")
    assert all(
        p
        in (
            "/health/live",
            "/health/ready",
            "/api/v1/me",
            "/api/v1/projects/{project_id}/foundation/status",
            "/api/v1/projects/{project_id}/ai/capabilities",
            "/api/v1/projects/{project_id}/evidence-document-metadata",
            "/api/v1/projects/{project_id}/evidence-retrieval-queries",
            "/api/v1/projects/{project_id}/evidence-citation-checks",
            "/api/v1/projects/{project_id}/evidence-document-excerpts",
            "/api/v1/projects/{project_id}/evidence-documents/{document_id}",
            "/api/v1/projects/{project_id}/evidence-documents/{document_id}/restrictions",
            "/api/v1/projects/{project_id}/evidence-corpora",
            "/api/v1/projects/{project_id}/evidence-corpora/{corpus_id}",
            "/api/v1/projects/{project_id}/evidence-corpus-current",
            "/api/v1/projects/{project_id}/evidence-corpus-activations",
            "/api/v1/projects/{project_id}/evidence-corpora/{corpus_id}/passages/{passage_id}",
            "/api/v1/projects/{project_id}/clinical-concepts",
            "/api/v1/projects/{project_id}/clinical-concepts/{concept_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/relationships",
            "/api/v1/projects/{project_id}/patients/{patient_id}/relationships/{relationship_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/relationship-queries",
            "/api/v1/projects/{project_id}/concept-relationships",
            "/api/v1/projects/{project_id}/concept-relationships/{relationship_id}",
            "/api/v1/projects/{project_id}/concept-relationship-queries",
            "/api/v1/projects/{project_id}/patients/{patient_id}/note-documents",
            "/api/v1/projects/{project_id}/patients/{patient_id}/note-documents/{note_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/note-extractions",
            "/api/v1/projects/{project_id}/patients/{patient_id}/note-extractions/{extraction_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/note-extractions/{extraction_id}/facts/{fact_index}/source-span",
            "/api/v1/projects/{project_id}/sources",
            "/api/v1/projects/{project_id}/sources/{source_id}",
            "/api/v1/projects/{project_id}/sources/{source_id}/rights-reviews",
            "/api/v1/projects/{project_id}/sources/{source_id}/capabilities/{action}",
            "/api/v1/projects/{project_id}/patient-linkage/status",
            "/api/v1/projects/{project_id}/source-patient-resolutions",
            "/api/v1/projects/{project_id}/patient-mappings/{mapping_id}",
            "/api/v1/projects/{project_id}/patient-mappings/{mapping_id}/key-rotations",
            "/api/v1/projects/{project_id}/person-link-events",
            "/api/v1/projects/{project_id}/person-link-events/{event_id}",
            "/api/v1/projects/{project_id}/dictionaries/clinical",
            "/api/v1/projects/{project_id}/patients/{patient_id}/timeline-origins",
            "/api/v1/projects/{project_id}/patients/{patient_id}/timeline-origins/{origin_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/clinical-source-artifacts",
            "/api/v1/projects/{project_id}/patients/{patient_id}/clinical-source-artifacts/{artifact_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/observation-batches/validations",
            "/api/v1/projects/{project_id}/patients/{patient_id}/observation-batches",
            "/api/v1/projects/{project_id}/patients/{patient_id}/observations/{record_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/observations/{record_id}/retractions",
            "/api/v1/projects/{project_id}/patients/{patient_id}/metadata-adapter-runs",
            "/api/v1/projects/{project_id}/patients/{patient_id}/metadata-adapter-runs/{run_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/resources/{resource_id}/provenance",
            "/api/v1/projects/{project_id}/patients/{patient_id}/resources/{resource_id}/withdrawals",
            "/api/v1/projects/{project_id}/patients/{patient_id}/quality-reports",
            "/api/v1/projects/{project_id}/patients/{patient_id}/quality-reports/{report_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/quality-revalidations",
            "/api/v1/projects/{project_id}/evaluation-splits",
            "/api/v1/projects/{project_id}/evaluation-splits/{split_id}",
            "/api/v1/projects/{project_id}/evaluation-splits/{split_id}/leakage",
            "/api/v1/projects/{project_id}/evaluation-splits/{split_id}/leakage-audits",
            "/api/v1/projects/{project_id}/patients/{patient_id}/evaluation-splits/{split_id}/assignment",
            "/api/v1/projects/{project_id}/patients/{patient_id}/imaging-files",
            "/api/v1/projects/{project_id}/patients/{patient_id}/imaging-import-previews",
            "/api/v1/projects/{project_id}/patients/{patient_id}/imaging-imports/{import_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/imaging-imports/{import_id}/confirmations",
            "/api/v1/projects/{project_id}/patients/{patient_id}/geometry-validations",
            "/api/v1/projects/{project_id}/patients/{patient_id}/geometry-validations/{report_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/preprocessing-runs",
            "/api/v1/projects/{project_id}/patients/{patient_id}/preprocessing-runs/{run_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/mask-alignments",
            "/api/v1/projects/{project_id}/patients/{patient_id}/mask-alignments/{run_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/mask-alignments/{run_id}/overlay",
            "/api/v1/projects/{project_id}/patients/{patient_id}/annotation-batches",
            "/api/v1/projects/{project_id}/patients/{patient_id}/annotation-batches/{batch_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/segmentations/{segmentation_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/mask-associations",
            "/api/v1/projects/{project_id}/patients/{patient_id}/mask-associations/{association_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/segmentation-qc-reports",
            "/api/v1/projects/{project_id}/patients/{patient_id}/segmentation-qc-reports/{report_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/imaging-jobs",
            "/api/v1/projects/{project_id}/patients/{patient_id}/imaging-jobs/{job_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/imaging-jobs/{job_id}/cancellations",
            "/api/v1/projects/{project_id}/patients/{patient_id}/artifacts/{artifact_id}/read-grants",
            "/api/v1/projects/{project_id}/patients/{patient_id}/imaging-cleanup-plans",
            "/api/v1/projects/{project_id}/patients/{patient_id}/imaging-cleanup-plans/{plan_id}/applications",
            "/api/v1/projects/{project_id}/patients/{patient_id}/physical-measurements",
            "/api/v1/projects/{project_id}/patients/{patient_id}/physical-measurements/{report_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/mesh-runs/{run_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/mesh-runs/{run_id}/asset",
            "/api/v1/projects/{project_id}/patients/{patient_id}/mesh-qc-reports/{report_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/mesh-qc-reports/{report_id}/asset",
            "/api/v1/projects/{project_id}/patients/{patient_id}/registrations/{report_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/lesions",
            "/api/v1/projects/{project_id}/patients/{patient_id}/lesions/{lesion_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/lesion-associations",
            "/api/v1/projects/{project_id}/patients/{patient_id}/lesion-associations/{event_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/measurement-series",
            "/api/v1/projects/{project_id}/patients/{patient_id}/measurement-series/{series_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/branches",
            "/api/v1/projects/{project_id}/patients/{patient_id}/branches/{branch_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/states",
            "/api/v1/projects/{project_id}/patients/{patient_id}/states/{state_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/states/{state_id}/reviews",
            "/api/v1/projects/{project_id}/patients/{patient_id}/states/{state_id}/publications",
            "/api/v1/projects/{project_id}/patients/{patient_id}/simulation-fixture-runs",
            "/api/v1/projects/{project_id}/patients/{patient_id}/branches/{branch_id}/simulation-configs",
            "/api/v1/projects/{project_id}/patients/{patient_id}/branches/{branch_id}/simulation-runs",
            "/api/v1/projects/{project_id}/patients/{patient_id}/simulation-configs/{config_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/eligibility-checks",
            "/api/v1/projects/{project_id}/patients/{patient_id}/eligibility-checks/{check_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/simulation-runs/{run_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/simulation-runs/{run_id}/geometry-validation",
            "/api/v1/projects/{project_id}/patients/{patient_id}/simulation-runs/{run_id}/targets",
            "/api/v1/projects/{project_id}/patients/{patient_id}/generated-clinical-batches/{batch_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/simulation-configs/{config_id}/schedule-preview",
            "/api/v1/projects/{project_id}/patients/{patient_id}/simulation-runs/{run_id}/sampling",
            "/api/v1/projects/{project_id}/patients/{patient_id}/simulation-completions/{completion_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/simulation-completions/{completion_id}/publications",
            "/api/v1/projects/{project_id}/patients/{patient_id}/branches/{branch_id}/current-simulation",
            "/api/v1/projects/{project_id}/patients/{patient_id}/timeline-queries",
            "/api/v1/projects/{project_id}/patients/{patient_id}/trend-queries",
            "/api/v1/projects/{project_id}/patients/{patient_id}/fusion-queries",
            "/api/v1/projects/{project_id}/patients/{patient_id}/forecast-queries",
            "/api/v1/projects/{project_id}/patients/{patient_id}/dependent-updates",
            "/api/v1/projects/{project_id}/patients/{patient_id}/dependent-updates/latest",
            "/api/v1/projects/{project_id}/patients/{patient_id}/simulation-fixture-runs/{run_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/synthetic-geometry-results/{result_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/synthetic-geometry-results/{result_id}/mesh",
            "/api/v1/projects/{project_id}/patients/{patient_id}/interpretation-contexts",
            "/api/v1/projects/{project_id}/patients/{patient_id}/interpretation-contexts/export-view",
            "/api/v1/projects/{project_id}/patients/{patient_id}/states/{state_id}/interpretations",
            "/api/v1/projects/{project_id}/patients/{patient_id}/states/{state_id}/interpretations/{interpretation_id}/grounding",
            "/api/v1/projects/{project_id}/patients/{patient_id}/states/{state_id}/interpretations/{interpretation_id}/saved-results",
            "/api/v1/projects/{project_id}/patients/{patient_id}/saved-interpretations/{saved_id}",
            "/api/v1/projects/{project_id}/patients/{patient_id}/states/{state_id}/saved-result-queries",
        )
        for p in output["openapi.json"]["paths"]
    ), "Unreviewed runtime endpoint"
    print(
        "PASS canonical generation"
        + (" check" if check else "")
        + "; only implemented runtime routes exposed"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generate(args.check)
