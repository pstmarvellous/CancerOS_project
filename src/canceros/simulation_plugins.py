"""Deterministic plugin boundary, with no production scenario registered implicitly."""

import hashlib
import json
from decimal import Decimal
from typing import Annotated, Literal, Protocol

from pydantic import Field

from canceros.contracts import Contract, DecimalString, Provenance
from canceros.simulation_contracts import (
    ClinicalConcept,
    ClinicalProfile,
    Family,
    SC05Parameters,
    SimulationConfig,
    StableId,
    TreatmentAssumptions,
)


class TumorTarget(Contract):
    slot_id: StableId
    relative_day: DecimalString
    target_mm3: DecimalString
    metric: Literal["numerical_region_volume"] = "numerical_region_volume"
    unit: Literal["mm3"] = "mm3"


class ModelTurningPoint(Contract):
    configured_day: DecimalString
    configured_nadir_mm3: DecimalString
    latent_sampled_minimum_slot_id: StableId
    latent_sampled_minimum_day: DecimalString
    latent_sampled_minimum_mm3: DecimalString
    kind: Literal["model_control_not_detected_biology"] = "model_control_not_detected_biology"


class SimulationAdverseEvent(Contract):
    event_type: Literal["configured_clinical_condition_change"] = (
        "configured_clinical_condition_change"
    )
    affected_concept: ClinicalConcept
    onset_day: DecimalString
    resolution_day: DecimalString | None
    grading: Literal["ungraded"] = "ungraded"
    attribution: Literal["hypothetical_association_not_causal"] = (
        "hypothetical_association_not_causal"
    )
    parameter_reference: Annotated[str, Field(strict=True, min_length=1, max_length=160)]
    evidence_slot_ids: Annotated[list[StableId], Field(min_length=2, max_length=64)]


class SC05ClinicalCondition(Contract):
    version: Literal["clinical-condition/1"] = "clinical-condition/1"
    parameters: SC05Parameters
    exposure_context: TreatmentAssumptions
    events: Annotated[list[SimulationAdverseEvent], Field(min_length=1, max_length=16)]
    severity_meaning: Literal["internal_simulation_setting_not_ctcae"] = (
        "internal_simulation_setting_not_ctcae"
    )
    origin: Literal[Provenance.SYNTHETIC_GENERATED] = Provenance.SYNTHETIC_GENERATED


class PluginOutput(Contract):
    family: Family | None = None
    mode: Literal["modest_reduction", "near_stable"] | None = None
    measurement_uncertainty: Literal["not_established"] = "not_established"
    turning_point: ModelTurningPoint | None = None
    clinical_condition: SC05ClinicalCondition | None = None
    tumor_targets: Annotated[list[TumorTarget], Field(min_length=3, max_length=16)]
    clinical_profile: ClinicalProfile
    origin: Literal[Provenance.SYNTHETIC_GENERATED] = Provenance.SYNTHETIC_GENERATED
    assumptions: Literal["unreviewed_demonstration_not_patient_prediction"] = (
        "unreviewed_demonstration_not_patient_prediction"
    )


class SimulationPlugin(Protocol):
    family: Family
    definition_version: str

    def validate(self, config: SimulationConfig) -> None: ...

    def generate(self, config: SimulationConfig, baseline_quantity: Decimal) -> PluginOutput: ...


def seed_stream(
    seed: int, family: str, definition_version: str, slot_id: str, modality: str, channel: str
) -> int:
    """Stable independent stream identity; JSON array framing prevents concatenation collisions."""
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**32:
        raise ValueError("Seed must be uint32")
    parts = (family, definition_version, slot_id, modality, channel)
    if any(not isinstance(part, str) or not part or len(part) > 80 for part in parts):
        raise ValueError("Stream identity fields must be bounded nonempty strings")
    framed = json.dumps(["slre-stream/1", seed, *parts], ensure_ascii=True, separators=(",", ":"))
    return int.from_bytes(hashlib.sha256(framed.encode("ascii")).digest(), "big")


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[tuple[str, str], SimulationPlugin] = {}

    def register(self, plugin: SimulationPlugin) -> None:
        key = (plugin.family, plugin.definition_version)
        if key in self._plugins:
            raise ValueError("Duplicate scenario definition")
        self._plugins[key] = plugin

    def resolve(self, family: str, definition_version: str) -> SimulationPlugin:
        try:
            return self._plugins[(family, definition_version)]
        except KeyError as exc:
            raise ValueError("Scenario definition not registered") from exc

    def generate(self, config: SimulationConfig, baseline_quantity: Decimal) -> PluginOutput:
        if not baseline_quantity.is_finite() or baseline_quantity <= 0:
            raise ValueError("Baseline quantity must be finite positive mm3")
        # Frozen Pydantic models still contain mutable lists. Never expose the caller's
        # graph to plugin callbacks, and compare against a pre-callback serialized pin.
        pinned = SimulationConfig.model_validate_json(config.model_dump_json())
        pinned_json = pinned.model_dump_json()
        clinical_json = pinned.clinical_profile.model_dump_json()
        isolated = SimulationConfig.model_validate_json(pinned_json)
        plugin = self.resolve(pinned.scenario.family, pinned.scenario.definition_version)
        plugin.validate(isolated)
        self._unchanged(isolated, pinned_json)
        generated = plugin.generate(isolated, baseline_quantity)
        self._unchanged(isolated, pinned_json)
        # Revalidate plugin output, including models constructed with unchecked model_copy/construct.
        output = PluginOutput.model_validate(generated.model_dump(mode="json"))
        if output.family is not None and output.family != pinned.scenario.family:
            raise ValueError("Plugin changed requested scenario family")
        parameters = getattr(pinned, "sc02_parameters", None)
        if pinned.scenario.family == "SC-02" and (
            parameters is None or output.mode != parameters.mode or output.family != "SC-02"
        ):
            raise ValueError("Plugin changed or omitted requested SC-02 mode")
        if pinned.scenario.family == "SC-04":
            control = pinned.sc04_parameters
            turning = output.turning_point
            minimum = min(output.tumor_targets, key=lambda target: Decimal(target.target_mm3))
            if (
                control is None
                or turning is None
                or output.family != "SC-04"
                or output.mode is not None
                or Decimal(turning.configured_day) != Decimal(control.change_point_day)
                or Decimal(turning.configured_nadir_mm3) != Decimal(control.nadir_mm3)
                or turning.latent_sampled_minimum_slot_id != minimum.slot_id
                or Decimal(turning.latent_sampled_minimum_day) != Decimal(minimum.relative_day)
                or Decimal(turning.latent_sampled_minimum_mm3) != Decimal(minimum.target_mm3)
            ):
                raise ValueError(
                    "Plugin changed or omitted configured and sampled SC-04 turning points"
                )
        elif output.turning_point is not None:
            raise ValueError("Turning-point metadata is only supported for SC-04")
        if pinned.scenario.family == "SC-05":
            condition = output.clinical_condition
            if (
                condition is None
                or output.family != "SC-05"
                or condition.parameters != pinned.sc05_parameters
                or condition.exposure_context != pinned.treatment
            ):
                raise ValueError(
                    "Plugin changed or omitted the independent SC-05 clinical condition"
                )
            configured_slots = {slot.slot_id for slot in pinned.schedule.slots}
            if any(
                not set(event.evidence_slot_ids) <= configured_slots for event in condition.events
            ):
                raise ValueError("Clinical event references an unconfigured evidence slot")
            assert pinned.sc05_parameters is not None
            if {event.affected_concept for event in condition.events} != {
                affected.concept for affected in pinned.sc05_parameters.affected_concepts
            } or len(condition.events) != len(pinned.sc05_parameters.affected_concepts):
                raise ValueError("Clinical events must exactly match configured affected concepts")
            for event in condition.events:
                expected_ids = [
                    point.slot_id
                    for point in pinned.clinical_profile.points
                    if point.code == event.affected_concept
                ]
                expected_ids.extend(
                    point.slot_id
                    for point in pinned.sc05_parameters.symptom_course
                    if point.concept == event.affected_concept
                )
                if (
                    event.evidence_slot_ids != expected_ids
                    or event.onset_day != pinned.sc05_parameters.onset_day
                    or event.resolution_day != pinned.sc05_parameters.recovery_day
                ):
                    raise ValueError(
                        "Clinical event differs from explicit course evidence and timing"
                    )
        elif output.clinical_condition is not None:
            raise ValueError("Clinical-condition metadata is only supported for SC-05")
        if output.clinical_profile.model_dump_json() != clinical_json:
            raise ValueError("Plugin cannot implicitly alter independent clinical configuration")
        slots = [slot for slot in pinned.schedule.slots if slot.modality == "imaging"]
        if len(output.tumor_targets) != len(slots):
            raise ValueError("Plugin omitted imaging targets")
        for target, slot in zip(output.tumor_targets, slots, strict=True):
            if (
                target.slot_id != slot.slot_id
                or Decimal(target.relative_day) != Decimal(slot.relative_day)
                or not Decimal(target.target_mm3).is_finite()
                or not 0 <= Decimal(target.target_mm3) < Decimal("1000000000000000")
            ):
                raise ValueError("Plugin target has invalid slot, time or volume")
        return output

    @staticmethod
    def _unchanged(config: SimulationConfig, pinned_json: str) -> None:
        validated = SimulationConfig.model_validate_json(config.model_dump_json())
        if validated.model_dump_json() != pinned_json:
            raise ValueError("Plugin mutated pinned simulation configuration")
