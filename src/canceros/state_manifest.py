"""Selected-state manifest with stable artifact IDs and freshness."""

from uuid import UUID

from fastapi import HTTPException

from canceros.contracts import Contract
from canceros.patient_linkage import authorize_patient
from canceros.twin_states import read_state


class StateArtifact(Contract):
    kind: str
    artifact_id: UUID | None
    status: str
    next_action: str


class StateManifest(Contract):
    snapshot_id: UUID
    snapshot_hash: str
    stale: bool
    current_use_allowed: bool
    restrictions: list[str]
    artifacts: list[StateArtifact]
    selection_identity: str
    next_action: str = "resolve_grants_for_selected_state_only"


def state_manifest(c, i, p: UUID, u: UUID, snapshot_id: UUID) -> StateManifest:
    authorize_patient(c, i, p, u)
    view = read_state(c, i, p, u, snapshot_id)
    snapshot = view.snapshot
    artifacts: list[StateArtifact] = []
    for member in snapshot.imaging_members:
        artifacts.append(
            StateArtifact(
                kind="measurement",
                artifact_id=member.measurement.id,
                status="ready" if member.measurement.values.availability == "available" else "unavailable",
                next_action="open_physical_measurement_then_mesh_grant",
            )
        )
        if member.mesh_qc is not None and member.mesh_qc.display_artifact_id is not None:
            artifacts.append(
                StateArtifact(
                    kind="mesh",
                    artifact_id=member.mesh_qc.display_artifact_id,
                    status="ready",
                    next_action="request_short_lived_read_grant",
                )
            )
    for member in snapshot.clinical_members:
        artifacts.append(
            StateArtifact(
                kind="observation",
                artifact_id=None,
                status="ready",
                next_action="open_exact_observation_record",
            )
        )
    if not artifacts:
        raise HTTPException(404)
    return StateManifest(
        snapshot_id=snapshot.id,
        snapshot_hash=view.snapshot_hash,
        stale=view.stale,
        current_use_allowed=view.current_use_allowed,
        restrictions=list(view.restrictions),
        artifacts=artifacts,
        selection_identity=f"{snapshot.patient_id}:{snapshot.branch_id}:{snapshot.id}",
        next_action="resolve_grants_for_selected_state_only",
    )
