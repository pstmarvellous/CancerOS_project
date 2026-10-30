"""Counter-hash sampling of explicitly declared engineering distributions; no clinical fit."""

import hashlib
import json
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
from typing import Annotated, Literal

from pydantic import Field, model_validator

from canceros.clinical_validation import decimal_text
from canceros.contracts import Contract, DecimalString, MissingReason
from canceros.simulation_contracts import Modality, SimulationConfig, StableId
from canceros.simulation_plugins import PluginOutput, seed_stream


class SamplingError(ValueError):
    pass


class SampledSlot(Contract):
    slot_id: StableId
    modality: Modality
    configured_day: DecimalString
    relative_day: DecimalString


class SampledTumorTarget(Contract):
    slot_id: StableId
    relative_day: DecimalString
    target_mm3: DecimalString | None
    missing_reason: MissingReason | None
    metric: Literal["numerical_region_volume"] = "numerical_region_volume"
    unit: Literal["mm3"] = "mm3"

    @model_validator(mode="after")
    def explicit_missingness(self):
        if (self.target_mm3 is None) != (self.missing_reason is not None):
            raise ValueError("Missing sampled target requires a reason and no numeric value")
        return self


class SampledValue(Contract):
    slot_id: StableId
    channel: StableId
    modality: Modality
    relative_day: DecimalString
    value: DecimalString | None
    missing_reason: MissingReason | None
    unit: str

    @model_validator(mode="after")
    def explicit_missingness(self):
        if (self.value is None) != (self.missing_reason is not None):
            raise ValueError(
                "Missing sampled clinical value requires a reason and no numeric value"
            )
        return self


class SampledObservations(Contract):
    version: Literal["sampling/1"] = "sampling/1"
    prng_version: Literal["sha256-counter/1"] = "sha256-counter/1"
    seed: Annotated[int, Field(strict=True, ge=0, le=2**32 - 1)]
    seed_derivation: Literal["framed_sha256_named_streams/1"] = "framed_sha256_named_streams/1"
    policy: Literal["explicit_demo_distributions_not_real_care"] = (
        "explicit_demo_distributions_not_real_care"
    )
    slots: Annotated[list[SampledSlot], Field(max_length=64)]
    tumor_targets: Annotated[list[SampledTumorTarget], Field(min_length=3, max_length=16)]
    clinical_values: Annotated[list[SampledValue], Field(max_length=128)]


def _draw(config: SimulationConfig, slot_id: str, modality: str, channel: str, purpose: str) -> int:
    stream = seed_stream(
        config.seed,
        config.scenario.family,
        config.scenario.definition_version,
        slot_id,
        modality,
        channel,
    )
    frame = json.dumps(["sha256-counter/1", str(stream), purpose, 0], separators=(",", ":"))
    return int.from_bytes(hashlib.sha256(frame.encode("ascii")).digest(), "big")


def _uniform(config, slot, modality, channel, purpose, lower, upper, places):
    # Draw on the closed decimal lattice, guaranteeing quantization never leaves the bounds.
    with localcontext() as context:
        context.prec = 100
        scale = Decimal(10) ** places
        low = int((lower * scale).to_integral_value(rounding=ROUND_CEILING))
        high = int((upper * scale).to_integral_value(rounding=ROUND_FLOOR))
        if high < low:
            raise SamplingError(
                "Declared sampling interval contains no representable decimal lattice point"
            )
        digest = _draw(config, slot, modality, channel, purpose)
        index = (digest * (high - low + 1)) // 2**256
        return Decimal(low + index) / scale


def sample_observations(config: SimulationConfig, output: PluginOutput) -> SampledObservations:
    with localcontext() as context:
        context.prec = 100
        return _sample_observations(config, output)


def _sample_observations(config: SimulationConfig, output: PluginOutput) -> SampledObservations:
    config = SimulationConfig.model_validate_json(config.model_dump_json())
    output = PluginOutput.model_validate_json(output.model_dump_json())
    if output.clinical_profile != config.clinical_profile:
        raise SamplingError("Sampling output differs from frozen independent clinical profile")
    if [target.slot_id for target in output.tumor_targets] != [
        point.slot_id for point in config.tumor_profile.points
    ]:
        raise SamplingError("Sampling targets differ from configured stable slots")
    configured_slots = {slot.slot_id: slot for slot in config.schedule.slots}
    if output.family not in (None, config.scenario.family) or any(
        Decimal(target.target_mm3) != Decimal(point.target_mm3)
        or Decimal(target.relative_day) != Decimal(configured_slots[target.slot_id].relative_day)
        for target, point in zip(output.tumor_targets, config.tumor_profile.points, strict=True)
    ):
        raise SamplingError("Sampling requires the frozen family targets and original slot times")
    policy = config.sampling
    jitter = {rule.slot_id: rule for rule in policy.jitter_rules} if policy else {}
    slots = []
    previous: dict[str, Decimal] = {}
    for slot in config.schedule.slots:
        day = Decimal(slot.relative_day)
        rule = jitter.get(slot.slot_id)
        if rule is not None:
            if slot.modality in ("treatment", "adverse_event"):
                raise SamplingError(
                    "Treatment/adverse event control jitter is unsupported; preserve explicit control windows"
                )
            day += _uniform(
                config,
                slot.slot_id,
                slot.modality,
                "schedule",
                "timing_jitter",
                Decimal(rule.min_offset_days),
                Decimal(rule.max_offset_days),
                4,
            )
        if day != day.quantize(Decimal("0.0001")):
            raise SamplingError(
                "Sampled relative time exceeds numeric(12,4) precision; no silent rounding"
            )
        if not 0 <= day < Decimal("100000000") or (
            day == 0 and slot.modality not in ("treatment", "adverse_event")
        ):
            raise SamplingError("Jitter produced a nonpositive or out-of-range follow-up time")
        if slot.modality in previous and day <= previous[slot.modality]:
            raise SamplingError("Jitter caused within-modality schedule collision or reordering")
        previous[slot.modality] = day
        slots.append(
            SampledSlot(
                slot_id=slot.slot_id,
                modality=slot.modality,
                configured_day=slot.relative_day,
                relative_day=decimal_text(day),
            )
        )
    slot_map = {slot.slot_id: slot for slot in slots}
    offsets = {(point.slot_id, point.channel): point for point in config.noise.points}
    missing = {(point.slot_id, point.channel): point for point in config.missingness.points}
    noise = {(rule.slot_id, rule.channel): rule for rule in policy.noise_rules} if policy else {}
    omissions = (
        {(rule.slot_id, rule.channel): rule for rule in policy.missingness_rules} if policy else {}
    )

    def sampled(slot_id, channel, value, symptom=False):
        slot = slot_map[slot_id]
        key = slot_id, channel
        if key in missing:
            return None, missing[key].reason
        omission = omissions.get(key)
        if omission is not None:
            with localcontext() as context:
                context.prec = 100
                threshold = Decimal(omission.probability) * Decimal(2**256)
            if _draw(config, slot_id, slot.modality, channel, "missingness") < threshold:
                return None, omission.reason
        amount = Decimal(value)
        if key in offsets:
            amount += Decimal(offsets[key].additive_offset)
        variation = noise.get(key)
        if variation is not None:
            amount += _uniform(
                config,
                slot_id,
                slot.modality,
                channel,
                "measurement_noise",
                Decimal(variation.min_offset),
                Decimal(variation.max_offset),
                9,
            )
        if not amount.is_finite() or abs(amount) >= Decimal("1000000000000000"):
            raise SamplingError("Sampled quantity is nonfinite or exceeds the numeric range")
        if channel != "temperature" and amount < 0:
            raise SamplingError("Sampled count, mass, volume or rating became negative")
        if channel == "weight" and amount <= 0:
            raise SamplingError("Sampled weight must remain positive")
        if symptom and (amount != amount.to_integral_value() or not 0 <= amount <= 10):
            raise SamplingError(
                "Sampled symptom must preserve integer engineering ordinal range zero to ten"
            )
        return decimal_text(amount), None

    targets = []
    for target in output.tumor_targets:
        value, reason = sampled(target.slot_id, "numerical_region_volume", target.target_mm3)
        targets.append(
            SampledTumorTarget(
                slot_id=target.slot_id,
                relative_day=slot_map[target.slot_id].relative_day,
                target_mm3=value,
                missing_reason=reason,
            )
        )
    clinical = []
    for point in config.clinical_profile.points:
        value, reason = sampled(point.slot_id, point.code, point.value)
        sampled_slot = slot_map[point.slot_id]
        clinical.append(
            SampledValue(
                slot_id=point.slot_id,
                channel=point.code,
                modality=sampled_slot.modality,
                relative_day=sampled_slot.relative_day,
                value=value,
                missing_reason=reason,
                unit=point.unit,
            )
        )
    if config.sc05_parameters is not None:
        for symptom in config.sc05_parameters.symptom_course:
            value, reason = sampled(
                symptom.slot_id, symptom.concept, str(symptom.rating), symptom=True
            )
            sampled_slot = slot_map[symptom.slot_id]
            clinical.append(
                SampledValue(
                    slot_id=symptom.slot_id,
                    channel=symptom.concept,
                    modality="symptom",
                    relative_day=sampled_slot.relative_day,
                    value=value,
                    missing_reason=reason,
                    unit="engineering_ordinal/1",
                )
            )
    return SampledObservations(
        seed=config.seed, slots=slots, tumor_targets=targets, clinical_values=clinical
    )
