"""Frozen original-patient groups, inherited assignments and training-only fit guard."""

import hashlib
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import Field
from sqlalchemy import text

from canceros.contracts import Contract, Hash, Provenance
from canceros.identity import authorize_project
from canceros.lineage import ancestors, get_resource, require_resource_action
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import science_hash
from canceros.source_registry import SourceAction

SplitRole = Literal["train", "validation", "test", "demo", "unassigned"]


class PatientAssignment(Contract):
    patient_id: UUID
    role: SplitRole
    demo_exposed: bool = False


class SplitInput(Contract):
    seed: Annotated[int, Field(strict=True, ge=0, le=4294967295)]
    assignments: Annotated[list[PatientAssignment], Field(min_length=1, max_length=1000)]


class GroupAssignment(Contract):
    group_id: UUID
    patient_ids: list[UUID]
    role: SplitRole
    demo_exposed: bool
    held_out_group_eligible: bool
    exclusions: list[str]


class SplitManifest(Contract):
    id: UUID
    version: Literal["patient-groups/1"] = "patient-groups/1"
    seed: int
    grouping_hash: Hash
    groups: list[GroupAssignment]
    identity_evidence_ids: list[UUID]
    source_version_ids: list[UUID]
    frozen_root_resource_ids: list[UUID]
    input_revisions: dict[str, int]
    fixture_verification_only: Literal[True] = True
    independent_real_evaluation_cleared: Literal[False] = False
    next_action: str = (
        "Audit frozen grouping before use; real cohort/reference independence remains D05 pending"
    )


class LeakageAudit(Contract):
    split_id: UUID
    grouping_changed: bool
    group_count: int
    patient_count: int
    cross_role_group_overlap_count: int
    unresolved_group_count: int
    status: Literal["frozen_fixture_grouping_usable", "contaminated_or_review_required"]
    reason_codes: list[str]
    real_data_clearance: Literal["not_established"] = "not_established"
    next_action: str


class InheritedAssignment(Contract):
    patient_id: UUID
    split_id: UUID
    group_id: UUID
    role: SplitRole
    demo_exposed: bool
    grouping_current: bool
    independent_evaluation_eligible: bool
    real_data_clearance: Literal["not_established"] = "not_established"


def identity_groups(connection, project, requested):
    patients = (
        connection.execute(
            text(
                "SELECT DISTINCT patient_id FROM source.patient_mappings WHERE project_id=:p ORDER BY patient_id"
            ),
            {"p": project},
        )
        .scalars()
        .all()
    )
    known = set(patients)
    if not set(requested) <= known:
        raise HTTPException(404)
    parent = {patient: patient for patient in patients}

    def find(patient):
        while parent[patient] != patient:
            parent[patient] = parent[parent[patient]]
            patient = parent[patient]
        return patient

    rows = (
        connection.execute(
            text(
                "SELECT DISTINCT ON (least(left_patient_id,right_patient_id),greatest(left_patient_id,right_patient_id)) id,left_patient_id,right_patient_id,status FROM source.person_link_events WHERE project_id=:p ORDER BY least(left_patient_id,right_patient_id),greatest(left_patient_id,right_patient_id),sequence DESC"
            ),
            {"p": project},
        )
        .mappings()
        .all()
    )
    for row in rows:
        left, right = row["left_patient_id"], row["right_patient_id"]
        if row["status"] == "confirmed" and left in known and right in known:
            a, b = find(left), find(right)
            parent[max(a, b, key=str)] = min(a, b, key=str)
    selected_groups = {find(patient) for patient in requested}
    closure = {patient for patient in patients if find(patient) in selected_groups}
    links = [
        row
        for row in rows
        if row["left_patient_id"] in closure or row["right_patient_id"] in closure
    ]
    uncertain = {
        patient
        for row in links
        if row["status"] == "uncertain"
        for patient in (row["left_patient_id"], row["right_patient_id"])
    }
    # Identical source imaging bytes flag review, never automatically merge people.
    imaging = (
        connection.execute(
            text(
                "SELECT id,patient_id,content_hash FROM ops.resource_registry WHERE project_id=:p AND kind IN ('imaging_source_artifact','imaging_volume','reference_mask_source','segmentation') ORDER BY id"
            ),
            {"p": project},
        )
        .mappings()
        .all()
    )
    by_hash: dict[str, set[UUID]] = {}
    for row in imaging:
        by_hash.setdefault(row["content_hash"], set()).add(row["patient_id"])
    duplicate_sets = [
        sorted(values, key=str)
        for values in by_hash.values()
        if len(values) > 1 and set(values) & closure
    ]
    duplicate_patients = {patient for values in duplicate_sets for patient in values}
    groups: dict[UUID, list[UUID]] = {}
    for patient in sorted(closure, key=str):
        groups.setdefault(find(patient), []).append(patient)
    basis = {
        "version": "patient-groups/1",
        "groups": {str(k): [str(v) for v in values] for k, values in groups.items()},
        "links": [{k: str(v) for k, v in row.items()} for row in links],
        "duplicate_imaging_patient_sets": [
            [str(v) for v in values] for values in sorted(duplicate_sets, key=str)
        ],
    }
    return groups, uncertain, duplicate_patients, links, science_hash(basis)


def freeze_split(connection, identity, project, value: SplitInput):
    authorize_project(identity, project, "admin")
    requested = {assignment.patient_id: assignment for assignment in value.assignments}
    if len(requested) != len(value.assignments):
        raise HTTPException(422)
    groups, uncertain, duplicates, links, grouping_hash = identity_groups(
        connection, project, requested
    )
    assignments = []
    closure = set()
    for group_id, patients in groups.items():
        supplied = [requested[patient] for patient in patients if patient in requested]
        roles = {assignment.role for assignment in supplied}
        if len(roles) != 1:
            raise HTTPException(409)
        role = roles.pop()
        demo_exposed = any(
            assignment.demo_exposed or assignment.role == "demo" for assignment in supplied
        )
        reasons = []
        if set(patients) & uncertain:
            reasons.append("uncertain_identity")
        if set(patients) & duplicates:
            reasons.append("duplicate_imaging_bytes_require_identity_review")
        if demo_exposed:
            reasons.append("demo_exposure_excludes_independent_claims")
        assignments.append(
            GroupAssignment(
                group_id=group_id,
                patient_ids=patients,
                role=role,
                demo_exposed=demo_exposed,
                held_out_group_eligible=role == "test" and not reasons,
                exclusions=reasons,
            )
        )
        closure.update(patients)
    # Seed affects deterministic manifest order only. Operators explicitly select roles;
    # no universal ratio is forced onto a small cohort.
    assignments.sort(
        key=lambda group: hashlib.sha256(f"{value.seed}:{group.group_id}".encode()).hexdigest()
    )
    roots: list[UUID] = []
    sources: set[UUID] = set()
    revisions = {}
    for patient in sorted(closure, key=str):
        revisions[str(patient)] = connection.execute(
            text(
                "SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"
            ),
            {"p": project, "u": patient},
        ).scalar_one()
        rows = connection.execute(
            text(
                "SELECT id,source_version_id FROM ops.resource_registry WHERE project_id=:p AND patient_id=:u AND source_version_id IS NOT NULL ORDER BY id"
            ),
            {"p": project, "u": patient},
        ).all()
        roots.extend(row.id for row in rows)
        sources.update(row.source_version_id for row in rows)
        sources.update(
            connection.execute(
                text(
                    "SELECT source_version_id FROM source.patient_mappings WHERE project_id=:p AND patient_id=:u"
                ),
                {"p": project, "u": patient},
            )
            .scalars()
            .all()
        )
    manifest = SplitManifest(
        id=uuid4(),
        seed=value.seed,
        grouping_hash=grouping_hash,
        groups=assignments,
        identity_evidence_ids=[row["id"] for row in links],
        source_version_ids=sorted(sources, key=str),
        frozen_root_resource_ids=roots,
        input_revisions=revisions,
    )
    connection.execute(
        text(
            "INSERT INTO source.evaluation_splits(id,project_id,manifest,manifest_hash,created_by) VALUES(:id,:p,CAST(:manifest AS jsonb),:hash,:actor)"
        ),
        {
            "id": manifest.id,
            "p": project,
            "manifest": manifest.model_dump_json(),
            "hash": science_hash(manifest.model_dump(mode="json")),
            "actor": identity.user_id,
        },
    )
    audit(connection, project, manifest.id, "PATIENT_SPLIT_FROZEN")
    return manifest


def load_split(connection, project, split_id):
    row = connection.execute(
        text(
            "SELECT manifest,manifest_hash FROM source.evaluation_splits WHERE project_id=:p AND id=:id"
        ),
        {"p": project, "id": split_id},
    ).one_or_none()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.manifest) != row.manifest_hash:
        raise HTTPException(409)
    return SplitManifest.model_validate(row.manifest)


def split_audit(connection, identity, project, split_id, persist=False):
    authorize_project(identity, project, "admin")
    manifest = load_split(connection, project, split_id)
    selected = [patient for group in manifest.groups for patient in group.patient_ids]
    current_groups, _, _, _, current_hash = identity_groups(connection, project, selected)
    frozen_roles = {
        patient: group.role for group in manifest.groups for patient in group.patient_ids
    }
    overlap = sum(
        len({frozen_roles[patient] for patient in members if patient in frozen_roles}) > 1
        for members in current_groups.values()
    )
    changed = current_hash != manifest.grouping_hash
    unresolved = sum(bool(group.exclusions) for group in manifest.groups)
    reasons = (["identity_or_duplicate_evidence_changed"] if changed else []) + (
        ["group_exclusions_require_review"] if unresolved else []
    )
    report = LeakageAudit(
        split_id=split_id,
        grouping_changed=changed,
        group_count=len(manifest.groups),
        patient_count=len(selected),
        cross_role_group_overlap_count=overlap,
        unresolved_group_count=unresolved,
        status="contaminated_or_review_required" if reasons else "frozen_fixture_grouping_usable",
        reason_codes=reasons,
        next_action="Preserve this manifest and create a new reviewed split/evaluation version"
        if reasons
        else "Use only the frozen eligible patient groups and source roots; real evaluation remains unverified",
    )
    if persist:
        connection.execute(
            text(
                "INSERT INTO source.split_audits(id,project_id,split_id,report,report_hash) VALUES(:id,:p,:split,CAST(:report AS jsonb),:hash)"
            ),
            {
                "id": uuid4(),
                "p": project,
                "split": split_id,
                "report": report.model_dump_json(),
                "hash": science_hash(report.model_dump(mode="json")),
            },
        )
        audit(connection, project, split_id, "SPLIT_LEAKAGE_AUDITED")
    return report


def inherited_assignment(connection, identity, project, patient, split_id):
    authorize_patient(connection, identity, project, patient)
    manifest = load_split(connection, project, split_id)
    group = next((group for group in manifest.groups if patient in group.patient_ids), None)
    if group is None:
        raise HTTPException(404)
    selected = [p for item in manifest.groups for p in item.patient_ids]
    _, _, _, _, current_hash = identity_groups(connection, project, selected)
    return InheritedAssignment(
        patient_id=patient,
        split_id=split_id,
        group_id=group.group_id,
        role=group.role,
        demo_exposed=group.demo_exposed,
        grouping_current=current_hash == manifest.grouping_hash,
        independent_evaluation_eligible=group.held_out_group_eligible
        and current_hash == manifest.grouping_hash,
    )


def require_fit_access(connection, identity, project, patient, split_id, resource_ids):
    authorize_patient(connection, identity, project, patient, edit=True)
    assignment = inherited_assignment(connection, identity, project, patient, split_id)
    if assignment.role != "train" or not assignment.grouping_current:
        raise HTTPException(409)
    manifest = load_split(connection, project, split_id)
    allowed = set(manifest.frozen_root_resource_ids)
    if not resource_ids or len(resource_ids) > 256:
        raise HTTPException(422)
    for resource_id in resource_ids:
        get_resource(connection, identity, project, patient, resource_id)
        require_resource_action(
            connection, identity, project, patient, resource_id, SourceAction.INTERNAL
        )
        require_resource_action(
            connection, identity, project, patient, resource_id, SourceAction.DERIVATIVE
        )
        roots = [
            row
            for row in ancestors(connection, project, patient, resource_id)
            if row["source_version_id"]
        ]
        if not roots or any(row["id"] not in allowed for row in roots):
            raise HTTPException(409)


def require_independent_test_resource(
    connection, identity, project, patient, split_id, resource_id
):
    assignment = inherited_assignment(connection, identity, project, patient, split_id)
    resource = get_resource(connection, identity, project, patient, resource_id)
    if not assignment.independent_evaluation_eligible or resource["origin"] not in (
        Provenance.REAL_OBSERVED,
        Provenance.REAL_DERIVED,
    ):
        raise HTTPException(409)
    manifest = load_split(connection, project, split_id)
    if not manifest.independent_real_evaluation_cleared:
        raise HTTPException(409)
    roots = [
        row
        for row in ancestors(connection, project, patient, resource_id)
        if row["source_version_id"]
    ]
    if not roots or any(row["id"] not in manifest.frozen_root_resource_ids for row in roots):
        raise HTTPException(409)
