"""Pure relation semantics checks; no patient truth or source rights established."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from canceros.knowledge_contracts import (
    EntityRef,
    RelationshipInput,
    ResolvedEntity,
    TraversalQuery,
    relationship_validation_status,
    validate_relationship,
)


@pytest.fixture
def scope():
    return uuid4(), uuid4(), uuid4()


def entity(scope, kind, *, generic=False, branch=False, origin="REAL_DERIVED"):
    project, patient, branch_id = scope
    return ResolvedEntity(
        ref=EntityRef(kind=kind, id=patient if kind == "patient" else uuid4()),
        project_id=project,
        patient_id=None if generic else patient,
        branch_id=branch_id if branch else None,
        provenance=None if kind in ("patient", "clinical_concept") else origin,
    )


def relation(source, target, kind, *, assertion="recorded_association", **changes):
    return RelationshipInput(
        relation=kind,
        source=source.ref,
        target=target.ref,
        assertion_kind=assertion,
        supporting_resource_ids=[source.ref.id],
        **changes,
    )


def validate(scope, value, source, target, **kwargs):
    project, patient, _ = scope
    validate_relationship(
        value, source, target, project_id=project, patient_id=patient, branch_id=None, **kwargs
    )


@pytest.mark.parametrize(
    "kind,source_kind,target_kind",
    [
        ("HAS_OBSERVATION", "patient", "clinical_observation"),
        ("HAS_LESION", "patient", "lesion_identity"),
        ("HAS_MEASUREMENT", "lesion_identity", "physical_measurement"),
        ("ASSOCIATED_WITH", "clinical_observation", "physical_measurement"),
    ],
)
def test_explicit_allowed_relationships_retain_unreviewed_source_status(
    scope, kind, source_kind, target_kind
):
    source, target = entity(scope, source_kind), entity(scope, target_kind)
    value = relation(source, target, kind)
    validate(scope, value, source, target)
    assert relationship_validation_status(value.assertion_kind) == "source_linked_unreviewed"


def test_extracted_assertions_require_exact_fact_support_and_never_become_observations(scope):
    source = entity(scope, "note_extraction")
    target = entity(scope, "clinical_concept", generic=True)
    value = relation(
        source,
        target,
        "ABOUT_CONCEPT",
        assertion="extracted_assertion",
        extraction_id=source.ref.id,
        fact_id=uuid4(),
    )
    validate(scope, value, source, target)
    assert relationship_validation_status(value.assertion_kind) == "unverified_extracted_assertion"
    for changes in (
        {"fact_id": None},
        {"extraction_id": uuid4()},
        {"supporting_resource_ids": []},
        {"source": target.ref},
    ):
        with pytest.raises(ValidationError):
            RelationshipInput.model_validate({**value.model_dump(), **changes})
    for assertion in ("recorded_association", "hypothetical_simulation"):
        with pytest.raises(ValueError):
            validate(
                scope,
                relation(source, target, "ABOUT_CONCEPT", assertion=assertion),
                source,
                target,
            )


@pytest.mark.parametrize(
    "assertion,status",
    [
        ("recorded_association", "source_linked_unreviewed"),
        ("extracted_assertion", "unverified_extracted_assertion"),
        ("general_research", "source_linked_unreviewed"),
        ("hypothetical_simulation", "hypothetical"),
        ("model_proposal", "unverified_proposal"),
    ],
)
def test_assertion_status_cannot_claim_qualified_approval(assertion, status):
    assert relationship_validation_status(assertion) == status


def test_generic_concept_cycles_are_allowed_without_provenance_cycle_confusion(scope):
    source = entity(scope, "clinical_concept", generic=True)
    target = entity(scope, "clinical_concept", generic=True)
    for left, right in ((source, target), (target, source), (source, source)):
        value = relation(left, right, "RELATED_TO", assertion="general_research")
        validate_relationship(
            value, left, right, project_id=scope[0], patient_id=None, branch_id=None
        )
        with pytest.raises(ValueError, match="project-only"):
            validate(scope, value, left, right)


def test_literature_cannot_establish_patient_finding_or_outcome(scope):
    source = entity(scope, "clinical_observation")
    target = entity(scope, "physical_measurement")
    value = relation(source, target, "ASSOCIATED_WITH", assertion="general_research")
    with pytest.raises(ValueError, match="patient fact"):
        validate(scope, value, source, target)
    publication = entity(scope, "publication", generic=True)
    outcome = entity(scope, "outcome")
    with pytest.raises(ValueError, match="not enabled"):
        validate(scope, relation(publication, outcome, "ASSOCIATED_WITH"), publication, outcome)


@pytest.mark.parametrize("kind", ["SUPPORTED_BY_PUBLICATION", "EXPOSED_TO_TREATMENT"])
def test_reserved_relations_do_not_pretend_to_have_canonical_backing(scope, kind):
    source = entity(scope, "clinical_observation")
    target = entity(scope, "physical_measurement")
    with pytest.raises(ValueError, match="not enabled"):
        validate(scope, relation(source, target, kind), source, target)


@pytest.mark.parametrize(
    "prohibited", ["CAUSES", "RESISTANT_TO", "TREATS", "IMPROVES_SURVIVAL", "SELECT_THERAPY"]
)
def test_prohibited_clinical_meaning_is_not_a_relation_enum(scope, prohibited):
    source, target = entity(scope, "clinical_observation"), entity(scope, "physical_measurement")
    with pytest.raises(ValidationError):
        relation(source, target, prohibited)


@pytest.mark.parametrize("change", ["project", "patient", "branch", "endpoint_id", "endpoint_kind"])
def test_independently_resolved_endpoint_identity_and_scope_are_required(scope, change):
    source, target = entity(scope, "patient"), entity(scope, "clinical_observation")
    value = relation(source, target, "HAS_OBSERVATION")
    if change in ("project", "patient", "branch"):
        target = target.model_copy(update={f"{change}_id": uuid4()})
    else:
        ref = target.ref.model_copy(
            update={"id": uuid4()} if change == "endpoint_id" else {"kind": "physical_measurement"}
        )
        target = target.model_copy(update={"ref": ref})
    with pytest.raises(ValueError):
        validate(scope, value, source, target)


def test_synthetic_unbranched_fixtures_remain_hypothetical(scope):
    source = entity(scope, "patient")
    target = entity(scope, "clinical_observation", origin="SYNTHETIC_GENERATED")
    with pytest.raises(ValueError, match="Synthetic"):
        validate(scope, relation(source, target, "HAS_OBSERVATION"), source, target)
    validate(
        scope,
        relation(source, target, "HAS_OBSERVATION", assertion="hypothetical_simulation"),
        source,
        target,
    )


def test_only_verified_baseline_link_can_cross_observed_to_synthetic_branch(scope):
    source = entity(scope, "physical_measurement", branch=True, origin="SYNTHETIC_GENERATED")
    target = entity(scope, "physical_measurement")
    value = relation(source, target, "GENERATED_FROM_BASELINE", assertion="hypothetical_simulation")
    validate_relationship(
        value,
        source,
        target,
        project_id=scope[0],
        patient_id=scope[1],
        branch_id=scope[2],
        baseline_link_verified=True,
    )
    for proof, branch in ((False, scope[2]), (True, None), (True, uuid4())):
        with pytest.raises(ValueError, match="baseline"):
            validate_relationship(
                value,
                source,
                target,
                project_id=scope[0],
                patient_id=scope[1],
                branch_id=branch,
                baseline_link_verified=proof,
            )
    ordinary = relation(source, target, "ASSOCIATED_WITH", assertion="hypothetical_simulation")
    with pytest.raises(ValueError, match="Cross-branch"):
        validate_relationship(
            ordinary,
            source,
            target,
            project_id=scope[0],
            patient_id=scope[1],
            branch_id=scope[2],
            baseline_link_verified=True,
        )


def test_proposal_can_be_unsupported_but_cannot_be_labeled_accepted(scope):
    source, target = entity(scope, "clinical_observation"), entity(scope, "physical_measurement")
    proposal = RelationshipInput(
        relation="ASSOCIATED_WITH",
        source=source.ref,
        target=target.ref,
        assertion_kind="model_proposal",
    )
    validate(scope, proposal, source, target)
    assert relationship_validation_status(proposal.assertion_kind) == "unverified_proposal"
    with pytest.raises(ValidationError):
        RelationshipInput.model_validate(
            {**proposal.model_dump(), "assertion_kind": "recorded_association"}
        )


def test_existing_branch_to_canonical_baseline_requires_independent_membership_proof(scope):
    source = entity(scope, "twin_branch", branch=True, origin="SYNTHETIC_GENERATED")
    target = entity(scope, "physical_measurement")
    value = relation(source, target, "GENERATED_FROM_BASELINE", assertion="hypothetical_simulation")
    validate_relationship(
        value,
        source,
        target,
        project_id=scope[0],
        patient_id=scope[1],
        branch_id=scope[2],
        baseline_link_verified=True,
    )
    with pytest.raises(ValueError, match="baseline"):
        validate_relationship(
            value, source, target, project_id=scope[0], patient_id=scope[1], branch_id=scope[2]
        )


def test_unverified_lexical_concept_cycle_needs_no_invented_literature(scope):
    first = entity(scope, "clinical_concept", generic=True)
    second = entity(scope, "clinical_concept", generic=True)
    for source, target in ((first, second), (second, first)):
        value = RelationshipInput(
            relation="RELATED_TO",
            source=source.ref,
            target=target.ref,
            assertion_kind="model_proposal",
        )
        validate_relationship(
            value, source, target, project_id=scope[0], patient_id=None, branch_id=None
        )
        assert relationship_validation_status(value.assertion_kind) == "unverified_proposal"


@pytest.mark.parametrize(
    "fields",
    [
        {"depth": 0},
        {"depth": 4},
        {"depth": True},
        {"depth": 1.5},
        {"limit": 0},
        {"limit": 101},
        {"limit": "25"},
        {"offset": -1},
        {"offset": 10001},
        {"relation_kinds": ["CAUSES"]},
        {"relation_kinds": ["RELATED_TO", "RELATED_TO"]},
    ],
)
def test_traversal_budgets_and_relation_filters_are_strict(scope, fields):
    with pytest.raises(ValidationError):
        TraversalQuery(start=entity(scope, "patient").ref, **fields)


def test_request_rejects_duplicate_support_and_untrusted_extra_instructions(scope):
    source, target = entity(scope, "patient"), entity(scope, "clinical_observation")
    value = relation(source, target, "HAS_OBSERVATION")
    for changes in (
        {"supporting_resource_ids": [source.ref.id, source.ref.id]},
        {"sql": "DROP TABLE clinical.observations"},
        {"patient_id": uuid4()},
        {"validation_status": "approved"},
        {"fact_id": uuid4()},
    ):
        with pytest.raises(ValidationError):
            RelationshipInput.model_validate({**value.model_dump(), **changes})
