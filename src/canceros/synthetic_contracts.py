"""Hypothetical geometry membership, separate from examinations and source annotations."""

from typing import Literal
from uuid import UUID

from canceros.contracts import Contract, Hash, RelativeTime
from canceros.imaging_geometry import CanonicalGeometry
from canceros.mesh_quality import SurfaceQuality
from canceros.mesh_reconstruction import Surface
from canceros.synthetic_shape import ShapeReport


class GeometrySummary(Contract):
    id: UUID
    branch_id: UUID
    run_id: UUID
    baseline_hash: Hash
    baseline_measurement_id: UUID
    baseline_segmentation_id: UUID
    baseline_mask_sha256: Hash
    grid_geometry: CanonicalGeometry
    input_revision: int
    association_head: int
    time: RelativeTime
    target_metric: Literal["numerical_region_volume"] = "numerical_region_volume"
    shape: ShapeReport
    mask_artifact_id: UUID | None
    mesh_artifact_id: UUID | None
    mesh_qc: SurfaceQuality | None
    status: Literal["ready", "zero", "blocked"]
    actual_followup_imaging_acquired: Literal[False] = False
    anatomical_containment: Literal["not_established"] = "not_established"
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    display_label: Literal["Simulated"] = "Simulated"
    scientific_review: Literal["pending"] = "pending"
    publication: Literal["draft"] = "draft"
    next_action: str


class GeneratedMesh(Contract):
    geometry_id: UUID
    baseline_segmentation_id: UUID
    meaning: Literal["hypothetical_region_not_followup_scan"] = (
        "hypothetical_region_not_followup_scan"
    )
    origin: Literal["SYNTHETIC_GENERATED"] = "SYNTHETIC_GENERATED"
    display_label: Literal["Simulated"] = "Simulated"
    surface: Surface
