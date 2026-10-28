from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_clinical_ingestion import clinical_db, row, stage
from test_source_registry import registry_db, review

from canceros.clinical_ingestion import BatchCommand, accept_batch
from canceros.contracts import Provenance
from canceros.identity import Identity
from canceros.lineage import (
    WithdrawalInput,
    derive_resource,
    inherited_origin,
    lineage_detail,
    processing_spec,
    require_resource_action,
    withdraw_resource,
)
from canceros.source_registry import SourceAction, add_review

__all__ = ["clinical_db", "registry_db"]


def setup_lineage(clinical_db):
    connection, identity, project, patient, origin, _, storage = clinical_db
    source = stage(clinical_db, [row(origin)])
    accepted = accept_batch(
        connection,
        identity,
        project,
        patient.patient_id,
        BatchCommand(source_artifact_id=source.artifact_id, expected_revision=1),
        "lineage-original",
        storage,
    )
    return source, accepted.record_ids[0]


def test_immutable_lineage_pins_source_processing_and_synthetic_origin(clinical_db):
    connection, identity, project, patient, _, _, _ = clinical_db
    source, record = setup_lineage(clinical_db)
    lineage = lineage_detail(connection, identity, project, patient.patient_id, record)
    assert lineage.origin == Provenance.SYNTHETIC_GENERATED
    assert lineage.parents[0].id == source.artifact_id
    assert lineage.processing.algorithm == "source-clinical-mapping/1"
    assert lineage.processing.environment["owned_source_tree_sha256"]
    with pytest.raises(DBAPIError), connection.begin_nested():
        connection.execute(
            text("UPDATE ops.resource_registry SET origin='REAL_DERIVED' WHERE id=:id"),
            {"id": record},
        )
    with pytest.raises(HTTPException):
        derive_resource(
            connection,
            identity,
            project,
            patient.patient_id,
            uuid4(),
            "invalid-promotion",
            "a" * 64,
            [record],
            processing_spec(__file__, "fixture/1", "fixture/1", {}),
            expected_origin=Provenance.REAL_DERIVED,
        )


def test_cycle_dangling_and_foreign_patient_rejected(clinical_db):
    connection, identity, project, patient, _, _, _ = clinical_db
    source, record = setup_lineage(clinical_db)
    with pytest.raises(DBAPIError), connection.begin_nested():
        connection.execute(
            text(
                "INSERT INTO source.provenance_edges(project_id,patient_id,child_id,parent_id,relation) VALUES(:p,:u,:child,:parent,'derived_from')"
            ),
            {"p": project, "u": patient.patient_id, "child": source.artifact_id, "parent": record},
        )
    for requested_patient, parent in ((patient.patient_id, uuid4()), (uuid4(), record)):
        with pytest.raises(HTTPException):
            derive_resource(
                connection,
                identity,
                project,
                requested_patient,
                uuid4(),
                "fixture",
                "a" * 64,
                [parent],
                processing_spec(__file__, "fixture/1", "fixture/1", {}),
            )
    with pytest.raises(HTTPException):
        lineage_detail(
            connection,
            Identity(identity.user_id, {project: "viewer"}),
            project,
            patient.patient_id,
            record,
        )


def test_withdrawal_blocks_descendant_use_preserves_history_and_current_rights(clinical_db):
    connection, identity, project, patient, _, component, _ = clinical_db
    source, record = setup_lineage(clinical_db)
    require_resource_action(
        connection, identity, project, patient.patient_id, record, SourceAction.INTERNAL
    )
    withdrawn = withdraw_resource(
        connection,
        identity,
        project,
        patient.patient_id,
        source.artifact_id,
        WithdrawalInput(reason_code="rights_withdrawn"),
    )
    assert record in withdrawn.affected_descendant_ids
    with pytest.raises(HTTPException):
        require_resource_action(
            connection, identity, project, patient.patient_id, record, SourceAction.INTERNAL
        )
    detail = lineage_detail(connection, identity, project, patient.patient_id, record)
    assert (
        detail.origin == Provenance.SYNTHETIC_GENERATED
        and "ancestor_withdrawn" in detail.restrictions
    )
    add_review(connection, identity, project, component, review(decision="denied"))
    assert (
        "source_permission_denied"
        in lineage_detail(connection, identity, project, patient.patient_id, record).restrictions
    )


def test_origin_policy_retains_predicted_interpolated_and_synthetic_descendants():
    assert inherited_origin({Provenance.REAL_OBSERVED}) == Provenance.REAL_DERIVED
    assert (
        inherited_origin({Provenance.REAL_DERIVED, Provenance.INTERPOLATED})
        == Provenance.INTERPOLATED
    )
    assert (
        inherited_origin({Provenance.MODEL_PREDICTED, Provenance.INTERPOLATED})
        == Provenance.MODEL_PREDICTED
    )
    assert (
        inherited_origin({Provenance.SYNTHETIC_GENERATED, Provenance.REAL_OBSERVED})
        == Provenance.SYNTHETIC_GENERATED
    )
