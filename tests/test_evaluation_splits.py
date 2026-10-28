from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_clinical_ingestion import clinical_db, row, stage
from test_patient_linkage import keys
from test_source_registry import example, hierarchy, registry_db, review

from canceros.evaluation_splits import (
    SplitInput,
    freeze_split,
    inherited_assignment,
    require_fit_access,
    require_independent_test_resource,
    split_audit,
)
from canceros.identity import Identity
from canceros.lineage import derive_resource, processing_spec, register_root
from canceros.patient_linkage import (
    LinkageInput,
    PersonLinkInput,
    append_person_link,
    resolve_mapping,
)
from canceros.source_registry import add_review, add_source

__all__ = ["clinical_db", "registry_db"]


def another_patient(data):
    connection, identity, project, _, _, _, _ = data
    _, _, component, source = hierarchy(connection, identity, project)
    add_review(connection, identity, project, component.id, review())
    return resolve_mapping(
        connection,
        identity,
        project,
        LinkageInput(source_version_id=source.id, source_patient_key="ARTIFICIAL-OTHER-PERSON"),
        keys(),
    )


def assignments(seed, *pairs):
    return SplitInput.model_validate(
        {
            "seed": seed,
            "assignments": [{"patient_id": patient, "role": role} for patient, role in pairs],
        }
    )


def link_value(left, right, **changes):
    return PersonLinkInput.model_validate(
        {
            "left_patient_id": left,
            "right_patient_id": right,
            "status": "confirmed",
            "confidence": "1",
            "evidence_reference": "Engineering fixture identity evidence only",
            "evidence_sha256": "b" * 64,
            **changes,
        }
    )


def test_frozen_group_split_reproducible_no_group_overlap_and_descendant_inherits(clinical_db):
    connection, identity, project, patient, origin, _, _ = clinical_db
    second = another_patient(clinical_db)
    source = stage(clinical_db, [row(origin)])
    specification = assignments(19, (patient.patient_id, "train"), (second.patient_id, "test"))
    first = freeze_split(connection, identity, project, specification)
    second_manifest = freeze_split(connection, identity, project, specification)
    assert (
        first.groups == second_manifest.groups
        and first.grouping_hash == second_manifest.grouping_hash
    )
    audit = split_audit(connection, identity, project, first.id, persist=True)
    assert audit.cross_role_group_overlap_count == 0 and not audit.grouping_changed
    assert (
        audit.status == "frozen_fixture_grouping_usable"
        and audit.real_data_clearance == "not_established"
    )
    derived = uuid4()
    derive_resource(
        connection,
        identity,
        project,
        patient.patient_id,
        derived,
        "synthetic_descendant",
        "c" * 64,
        [source.artifact_id],
        processing_spec(__file__, "fixture-derivative/1", "fixture/1", {}, seed=19),
    )
    assert (
        inherited_assignment(connection, identity, project, patient.patient_id, first.id).role
        == "train"
    )
    require_fit_access(connection, identity, project, patient.patient_id, first.id, [derived])
    with pytest.raises(HTTPException):
        require_fit_access(
            connection, identity, project, second.patient_id, first.id, [source.artifact_id]
        )
    with pytest.raises(DBAPIError), connection.begin_nested():
        connection.execute(
            text("DELETE FROM source.evaluation_splits WHERE id=:id"), {"id": first.id}
        )


def test_later_cross_role_identity_confirmation_marks_contamination_without_reassignment(
    clinical_db,
):
    connection, identity, project, patient, _, _, _ = clinical_db
    second = another_patient(clinical_db)
    manifest = freeze_split(
        connection,
        identity,
        project,
        assignments(7, (patient.patient_id, "train"), (second.patient_id, "test")),
    )
    append_person_link(
        connection, identity, project, link_value(patient.patient_id, second.patient_id)
    )
    audit = split_audit(connection, identity, project, manifest.id, persist=True)
    assert audit.grouping_changed and audit.cross_role_group_overlap_count == 1
    assert audit.status == "contaminated_or_review_required"
    assert (
        inherited_assignment(connection, identity, project, patient.patient_id, manifest.id).role
        == "train"
    )
    assert not inherited_assignment(
        connection, identity, project, patient.patient_id, manifest.id
    ).grouping_current
    with pytest.raises(HTTPException):
        freeze_split(
            connection,
            identity,
            project,
            assignments(7, (patient.patient_id, "train"), (second.patient_id, "test")),
        )


def test_uncertain_links_and_demo_exposure_exclude_independent_claims(clinical_db):
    connection, identity, project, patient, _, _, _ = clinical_db
    second = another_patient(clinical_db)
    append_person_link(
        connection,
        identity,
        project,
        link_value(patient.patient_id, second.patient_id, status="uncertain", confidence="0.5"),
    )
    manifest = freeze_split(
        connection,
        identity,
        project,
        assignments(1, (patient.patient_id, "test"), (second.patient_id, "demo")),
    )
    assert all(not group.held_out_group_eligible for group in manifest.groups)
    assert split_audit(connection, identity, project, manifest.id).unresolved_group_count == 2
    with pytest.raises(HTTPException):
        freeze_split(
            connection,
            Identity(identity.user_id, {project: "editor"}),
            project,
            assignments(1, (patient.patient_id, "train")),
        )
    with pytest.raises(HTTPException):
        inherited_assignment(connection, identity, uuid4(), patient.patient_id, manifest.id)


def test_confirmed_source_aliases_share_partition_and_new_sources_cannot_enter_old_fit(clinical_db):
    connection, identity, project, patient, origin, _, _ = clinical_db
    second = another_patient(clinical_db)
    append_person_link(
        connection, identity, project, link_value(patient.patient_id, second.patient_id)
    )
    first_source = stage(clinical_db, [row(origin)])
    manifest = freeze_split(
        connection, identity, project, assignments(3, (patient.patient_id, "train"))
    )
    assert set(manifest.groups[0].patient_ids) == {patient.patient_id, second.patient_id}
    require_fit_access(
        connection, identity, project, patient.patient_id, manifest.id, [first_source.artifact_id]
    )
    new_source = stage(
        clinical_db,
        [
            row(
                origin,
                original_value="13",
                result={"form": "exact", "quantity": {"value": "13", "unit": "g/dL"}},
            )
        ],
    )
    with pytest.raises(HTTPException):
        require_fit_access(
            connection, identity, project, patient.patient_id, manifest.id, [new_source.artifact_id]
        )
    test_manifest = freeze_split(
        connection, identity, project, assignments(3, (patient.patient_id, "test"))
    )
    with pytest.raises(HTTPException):
        require_independent_test_resource(
            connection,
            identity,
            project,
            patient.patient_id,
            test_manifest.id,
            first_source.artifact_id,
        )


def test_duplicate_imaging_bytes_flag_review_without_merging_identity(clinical_db):
    import hashlib

    connection, identity, project, patient, _, component, storage = clinical_db
    other = another_patient(clinical_db)
    other_component = connection.execute(
        text("SELECT parent_version_id FROM source.registry_versions WHERE id=:id"),
        {"id": other.source_version_id},
    ).scalar_one()
    raw = b"WHOLLY SYNTHETIC DUPLICATE BYTE FIXTURE - NOT A VALID MEDICAL IMAGE"
    digest = hashlib.sha256(raw).hexdigest()
    for person, parent_component in (
        (patient.patient_id, component),
        (other.patient_id, other_component),
    ):
        source = add_source(
            connection,
            identity,
            project,
            example(
                kind="artifact_source", parent_version_id=parent_component, manifest_sha256=digest
            ),
        )
        stored = storage.write_verified(project, raw)
        resource_id = uuid4()
        connection.execute(
            text(
                "INSERT INTO ops.artifacts(id,project_id,patient_id,object_key,object_version,byte_size,sha256,provenance,availability) VALUES(:id,:p,:u,:key,:v,:size,:hash,'SYNTHETIC_GENERATED','quarantined')"
            ),
            {
                "id": resource_id,
                "p": project,
                "u": person,
                "key": stored.key,
                "v": stored.version,
                "size": stored.byte_size,
                "hash": digest,
            },
        )
        register_root(
            connection,
            identity,
            project,
            person,
            resource_id,
            "imaging_source_artifact",
            digest,
            source.id,
        )
    manifest = freeze_split(
        connection,
        identity,
        project,
        assignments(1, (patient.patient_id, "train"), (other.patient_id, "test")),
    )
    assert len(manifest.groups) == 2
    assert all(
        "duplicate_imaging_bytes_require_identity_review" in group.exclusions
        for group in manifest.groups
    )
    assert split_audit(connection, identity, project, manifest.id).unresolved_group_count == 2
