"""Explicit engineering trajectory templates; no individualized treatment response model."""

from decimal import Decimal, localcontext
from typing import Literal

from canceros.contracts import Contract
from canceros.simulation_contracts import Family, SimulationConfig
from canceros.simulation_plugins import (
    ModelTurningPoint,
    PluginOutput,
    PluginRegistry,
    SC05ClinicalCondition,
    SimulationAdverseEvent,
    TumorTarget,
)

SC01_LABEL = "Strong simulated tumor reduction"
SC01_VERSION = "sc01-explicit/1"
SC02_VERSION = "sc02-explicit/1"
SC02_LABEL = "Modest simulated reduction or near-stable numerical region volume"
SC03_VERSION = "sc03-explicit/1"
SC03_LABEL = "Increasing simulated tumor burden"
SC04_VERSION = "sc04-explicit/1"
SC04_LABEL = "Simulated reduction followed by regrowth"
SC05_VERSION = "sc05-explicit/1"
SC05_LABEL = "Simulated clinical deterioration with independently selected tumor course"
MAX_VOLUME = Decimal("1000000000000000")


def _baseline(value: Decimal) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or not 0 < value < MAX_VOLUME:
        raise ValueError("Baseline must be finite positive numerical region volume below 1e15 mm3")


def _declining_targets(targets: list[TumorTarget], baseline: Decimal) -> None:
    _baseline(baseline)
    previous = baseline
    previous_day = Decimal(0)
    if not 3 <= len(targets) <= 16:
        raise ValueError("SC-01 requires three to sixteen explicit follow-up targets")
    seen = set()
    for target in targets:
        volume, day = Decimal(target.target_mm3), Decimal(target.relative_day)
        if target.slot_id in seen or not day.is_finite() or day <= previous_day:
            raise ValueError("SC-01 requires unique slots and strictly increasing relative days")
        if not volume.is_finite() or not 0 < volume < previous:
            raise ValueError(
                "SC-01 requires strictly declining positive volumes; zero is unsupported"
            )
        if target.metric != "numerical_region_volume" or target.unit != "mm3":
            raise ValueError("SC-01 supports numerical region volume in mm3 only")
        seen.add(target.slot_id)
        previous, previous_day = volume, day


class SC01Plugin:
    family: Family = "SC-01"
    definition_version = SC01_VERSION

    def validate(self, config: SimulationConfig) -> None:
        config = SimulationConfig.model_validate_json(config.model_dump_json())
        if (config.scenario.family, config.scenario.definition_version) != (
            self.family,
            self.definition_version,
        ):
            raise ValueError("SC-01 configuration does not match this versioned template")
        if config.treatment.category != "no_specific_assumption":
            raise ValueError("Specific treatment exposure rules remain unreviewed")
        previous = MAX_VOLUME
        for point in config.tumor_profile.points:
            value = Decimal(point.target_mm3)
            if not 0 < value < previous:
                raise ValueError(
                    "SC-01 requires strictly declining positive volumes; zero is unsupported"
                )
            previous = value

    def generate(self, config: SimulationConfig, baseline_quantity: Decimal) -> PluginOutput:
        self.validate(config)
        slots = {slot.slot_id: slot for slot in config.schedule.slots}
        targets = [
            TumorTarget(
                slot_id=point.slot_id,
                relative_day=slots[point.slot_id].relative_day,
                target_mm3=point.target_mm3,
            )
            for point in config.tumor_profile.points
        ]
        _declining_targets(targets, baseline_quantity)
        # Noise and missingness describe sampling, not a mutation of these latent knots.
        return PluginOutput(
            tumor_targets=targets,
            clinical_profile=config.clinical_profile.model_copy(deep=True),
            family="SC-01",
        )


def _sc02_values(config: SimulationConfig, values: list[Decimal], baseline: Decimal) -> None:
    """Requested mode takes precedence even when explicitly configured bands overlap."""
    _baseline(baseline)
    parameters = config.sc02_parameters
    if parameters is None:
        raise ValueError("SC-02 requires explicit mode parameters")
    if not values:
        raise ValueError("SC-02 requires explicit follow-up values")
    if any(not value.is_finite() or not 0 <= value < MAX_VOLUME for value in values):
        raise ValueError("SC-02 values must be finite nonnegative mm3 below 1e15")
    with localcontext() as context:
        context.prec = 50
        if parameters.mode == "near_stable":
            absolute_limit = Decimal(parameters.max_absolute_change_mm3)
            relative_limit = Decimal(parameters.max_relative_change) * baseline
            if any(abs(value - baseline) > min(absolute_limit, relative_limit) for value in values):
                raise ValueError("Near-stable value exceeds declared absolute or relative bound")
        else:
            previous = baseline
            for value in values:
                if not 0 < value < previous:
                    raise ValueError(
                        "Modest-reduction values must strictly decline and remain positive"
                    )
                previous = value
            decline = baseline - values[-1]
            if not (
                Decimal(parameters.min_relative_decline) * baseline
                <= decline
                <= Decimal(parameters.max_relative_decline) * baseline
            ):
                raise ValueError(
                    "Modest-reduction horizon decline is outside declared relative bounds"
                )


class SC02Plugin:
    family: Family = "SC-02"
    definition_version = SC02_VERSION

    def validate(self, config: SimulationConfig) -> None:
        config = SimulationConfig.model_validate_json(config.model_dump_json())
        if (config.scenario.family, config.scenario.definition_version) != (
            self.family,
            self.definition_version,
        ):
            raise ValueError("SC-02 configuration does not match this versioned template")
        if config.treatment.category != "no_specific_assumption":
            raise ValueError("Specific treatment exposure rules remain unreviewed")
        if config.sc02_parameters is None:
            raise ValueError("SC-02 requires explicit mode parameters")

    def generate(self, config: SimulationConfig, baseline_quantity: Decimal) -> PluginOutput:
        self.validate(config)
        slots = {slot.slot_id: slot for slot in config.schedule.slots}
        targets = [
            TumorTarget(
                slot_id=point.slot_id,
                relative_day=slots[point.slot_id].relative_day,
                target_mm3=point.target_mm3,
            )
            for point in config.tumor_profile.points
        ]
        _sc02_values(config, [Decimal(target.target_mm3) for target in targets], baseline_quantity)
        assert config.sc02_parameters is not None
        return PluginOutput(
            tumor_targets=targets,
            clinical_profile=config.clinical_profile.model_copy(deep=True),
            family="SC-02",
            mode=config.sc02_parameters.mode,
        )


def _increasing_targets(targets: list[TumorTarget], baseline: Decimal) -> None:
    _baseline(baseline)
    if not 3 <= len(targets) <= 16:
        raise ValueError("SC-03 requires three to sixteen explicit follow-up targets")
    previous, previous_day = baseline, Decimal(0)
    seen = set()
    for target in targets:
        value, day = Decimal(target.target_mm3), Decimal(target.relative_day)
        if target.slot_id in seen or not day.is_finite() or day <= previous_day:
            raise ValueError("SC-03 requires unique slots and strictly increasing relative days")
        if not value.is_finite() or not previous < value < MAX_VOLUME:
            raise ValueError("SC-03 requires strictly increasing positive volumes below 1e15 mm3")
        if target.metric != "numerical_region_volume" or target.unit != "mm3":
            raise ValueError("SC-03 supports numerical region volume in mm3 only")
        seen.add(target.slot_id)
        previous, previous_day = value, day


class SC03Plugin:
    family: Family = "SC-03"
    definition_version = SC03_VERSION

    def validate(self, config: SimulationConfig) -> None:
        config = SimulationConfig.model_validate_json(config.model_dump_json())
        if (config.scenario.family, config.scenario.definition_version) != (
            self.family,
            self.definition_version,
        ):
            raise ValueError("SC-03 configuration does not match this versioned template")
        if config.treatment.category != "no_specific_assumption":
            raise ValueError("Specific treatment exposure rules remain unreviewed")
        previous = Decimal(0)
        for point in config.tumor_profile.points:
            value = Decimal(point.target_mm3)
            if not previous < value < MAX_VOLUME:
                raise ValueError(
                    "SC-03 requires strictly increasing positive volumes below 1e15 mm3"
                )
            previous = value

    def generate(self, config: SimulationConfig, baseline_quantity: Decimal) -> PluginOutput:
        self.validate(config)
        slots = {slot.slot_id: slot for slot in config.schedule.slots}
        targets = [
            TumorTarget(
                slot_id=point.slot_id,
                relative_day=slots[point.slot_id].relative_day,
                target_mm3=point.target_mm3,
            )
            for point in config.tumor_profile.points
        ]
        _increasing_targets(targets, baseline_quantity)
        return PluginOutput(
            tumor_targets=targets,
            clinical_profile=config.clinical_profile.model_copy(deep=True),
            family="SC-03",
        )


def _sc04_controls(
    config: SimulationConfig, baseline: Decimal
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    _baseline(baseline)
    control = config.sc04_parameters
    if control is None or config.scenario.family != "SC-04":
        raise ValueError("SC-04 requires explicit change-point parameters")
    horizon = max(
        Decimal(slot.relative_day) for slot in config.schedule.slots if slot.modality == "imaging"
    )
    day, nadir = Decimal(control.change_point_day), Decimal(control.nadir_mm3)
    final = Decimal(config.tumor_profile.points[-1].target_mm3)
    if not 0 < day < horizon or not 0 < nadir < baseline or not nadir < final < MAX_VOLUME:
        raise ValueError(
            "SC-04 requires interior change point, positive nadir below baseline and later regrowth"
        )
    return day, nadir, horizon, final


def sc04_volume_at(config: SimulationConfig, baseline: Decimal, day: Decimal) -> Decimal:
    """Continuous control path; the configured nadir is not an extra observation."""
    control_day, nadir, horizon, final = _sc04_controls(config, baseline)
    if not isinstance(day, Decimal) or not day.is_finite() or not 0 <= day <= horizon:
        raise ValueError("Requested relative day is outside the configured trajectory")
    if day == control_day:
        return nadir
    with localcontext() as context:
        context.prec = 40
        if day < control_day:
            return baseline + (nadir - baseline) * day / control_day
        return nadir + (final - nadir) * (day - control_day) / (horizon - control_day)


def _regrowth_minimum(values: list[Decimal], baseline: Decimal) -> int:
    _baseline(baseline)
    if not 3 <= len(values) <= 16 or any(
        not value.is_finite() or not 0 < value < MAX_VOLUME for value in values
    ):
        raise ValueError("SC-04 requires at least three positive finite follow-ups")
    all_values = [baseline, *values]
    minimum = min(all_values)
    if all_values.count(minimum) != 1:
        raise ValueError("SC-04 sampled nadir must be unique")
    index = all_values.index(minimum)
    if not 0 < index < len(all_values) - 1:
        raise ValueError("SC-04 schedule must show sampled decline followed by regrowth")
    if any(a <= b for a, b in zip(all_values[:index], all_values[1 : index + 1])):
        raise ValueError("SC-04 sampled decline must be strict")
    if any(a >= b for a, b in zip(all_values[index:-1], all_values[index + 1 :])):
        raise ValueError("SC-04 sampled regrowth must be strict")
    return index - 1


class SC04Plugin:
    family: Family = "SC-04"
    definition_version = SC04_VERSION

    def validate(self, config: SimulationConfig) -> None:
        config = SimulationConfig.model_validate_json(config.model_dump_json())
        if (config.scenario.family, config.scenario.definition_version) != (
            self.family,
            self.definition_version,
        ):
            raise ValueError("SC-04 configuration does not match this versioned template")
        if config.treatment.category != "no_specific_assumption":
            raise ValueError("Specific treatment exposure rules remain unreviewed")
        assert config.sc04_parameters is not None
        horizon = max(
            Decimal(slot.relative_day)
            for slot in config.schedule.slots
            if slot.modality == "imaging"
        )
        if not Decimal(config.sc04_parameters.change_point_day) < horizon:
            raise ValueError("SC-04 configured change point must lie strictly inside the horizon")

    def generate(self, config: SimulationConfig, baseline_quantity: Decimal) -> PluginOutput:
        self.validate(config)
        _sc04_controls(config, baseline_quantity)
        slots = {slot.slot_id: slot for slot in config.schedule.slots}
        targets = [
            TumorTarget(
                slot_id=point.slot_id,
                relative_day=slots[point.slot_id].relative_day,
                target_mm3=point.target_mm3,
            )
            for point in config.tumor_profile.points
        ]
        for target in targets:
            if Decimal(target.target_mm3) != sc04_volume_at(
                config, baseline_quantity, Decimal(target.relative_day)
            ):
                raise ValueError(
                    "Supplied SC-04 target conflicts with the explicitly configured control path"
                )
        index = _regrowth_minimum(
            [Decimal(target.target_mm3) for target in targets], baseline_quantity
        )
        minimum = targets[index]
        assert config.sc04_parameters is not None
        return PluginOutput(
            family="SC-04",
            tumor_targets=targets,
            clinical_profile=config.clinical_profile.model_copy(deep=True),
            turning_point=ModelTurningPoint(
                configured_day=config.sc04_parameters.change_point_day,
                configured_nadir_mm3=config.sc04_parameters.nadir_mm3,
                latent_sampled_minimum_slot_id=minimum.slot_id,
                latent_sampled_minimum_day=minimum.relative_day,
                latent_sampled_minimum_mm3=minimum.target_mm3,
            ),
        )


def sc05_base_config(config: SimulationConfig) -> SimulationConfig:
    """Copy the selected tumor configuration; no synthetic symptom becomes an observed baseline."""
    parameters = config.sc05_parameters
    if parameters is None or config.scenario.family != "SC-05":
        raise ValueError("SC-05 requires explicit clinical-condition parameters")
    value = config.model_dump(mode="json")
    family = parameters.tumor_family
    versions = {"SC-01": SC01_VERSION, "SC-02": SC02_VERSION, "SC-03": SC03_VERSION}
    value["scenario"] = {"family": family, "definition_version": versions[family]}
    value["sc05_parameters"] = None
    if family != "SC-02":
        value["sc02_parameters"] = None
    # Symptom sampling is retained on the original SC-05 configuration and descriptor.
    # The tumor plugin has no symptom course and must not interpret those channels.
    symptom_keys = {(point.slot_id, point.concept) for point in parameters.symptom_course}
    for name in ("noise", "missingness"):
        points = [
            point
            for point in value[name]["points"]
            if (point["slot_id"], point["channel"]) not in symptom_keys
        ]
        value[name] = {"mode": "explicit" if points else "none", "points": points}
    if value.get("sampling") is not None:
        for name in ("noise_rules", "missingness_rules"):
            value["sampling"][name] = [
                rule
                for rule in value["sampling"][name]
                if (rule["slot_id"], rule["channel"]) not in symptom_keys
            ]
    return SimulationConfig.model_validate(value)


def _clinical_condition(config: SimulationConfig) -> SC05ClinicalCondition:
    parameters = config.sc05_parameters
    if parameters is None:
        raise ValueError("SC-05 requires explicit clinical-condition parameters")
    expected = parameters.internal_severity + "_deterioration"
    if config.clinical_profile.configuration != expected and not (
        config.clinical_profile.configuration == "recovery" and parameters.recovery_day is not None
    ):
        raise ValueError(
            "Clinical profile label conflicts with the explicit internal severity/recovery setting"
        )
    slots = {slot.slot_id: slot for slot in config.schedule.slots}
    onset = Decimal(parameters.onset_day)
    recovery = Decimal(parameters.recovery_day) if parameters.recovery_day is not None else None
    events = []
    for affected in parameters.affected_concepts:
        if affected.numeric_direction is not None:
            numeric = [
                point for point in config.clinical_profile.points if point.code == affected.concept
            ]
            if len({point.unit for point in numeric}) > 1:
                raise ValueError(
                    "Affected numeric course requires a consistent declared unit: "
                    + affected.concept
                )
            samples = [
                (point.slot_id, Decimal(slots[point.slot_id].relative_day), Decimal(point.value))
                for point in numeric
            ]
            direction = Decimal(1) if affected.numeric_direction == "increasing" else Decimal(-1)
        else:
            symptoms = [
                point for point in parameters.symptom_course if point.concept == affected.concept
            ]
            samples = [
                (point.slot_id, Decimal(slots[point.slot_id].relative_day), Decimal(point.rating))
                for point in symptoms
            ]
            direction = Decimal(1)  # Defined internal simulation rating, not a clinical grade.
        if len(samples) < 2:
            raise ValueError(
                "Affected concept requires at least two explicit course points: " + affected.concept
            )
        if any(a[1] >= b[1] for a, b in zip(samples, samples[1:])):
            raise ValueError(
                "Affected course points must have strictly increasing actual slot times: "
                + affected.concept
            )
        worsening = any(
            (b[2] - a[2]) * direction > 0
            and b[1] >= onset
            and (recovery is None or b[1] < recovery)
            for a, b in zip(samples, samples[1:])
        )
        if not worsening:
            raise ValueError(
                "Affected concept lacks explicit deterioration in the configured interval: "
                + affected.concept
            )
        deterioration_samples = [
            sample for sample in samples if recovery is None or sample[1] < recovery
        ]
        if (deterioration_samples[-1][2] - deterioration_samples[0][2]) * direction <= 0:
            raise ValueError(
                "Affected course does not retain its configured deterioration direction: "
                + affected.concept
            )
        if recovery is not None and not any(
            (b[2] - a[2]) * direction < 0 and b[1] >= recovery for a, b in zip(samples, samples[1:])
        ):
            raise ValueError(
                "Configured recovery lacks a supporting explicit recovery course point: "
                + affected.concept
            )
        if (
            recovery is not None
            and (samples[-1][2] - deterioration_samples[-1][2]) * direction >= 0
        ):
            raise ValueError(
                "Configured recovery course does not retain its declared recovery direction: "
                + affected.concept
            )
        events.append(
            SimulationAdverseEvent(
                affected_concept=affected.concept,
                onset_day=parameters.onset_day,
                resolution_day=parameters.recovery_day,
                parameter_reference="clinical-condition/1:" + affected.concept,
                evidence_slot_ids=[sample[0] for sample in samples],
            )
        )
    return SC05ClinicalCondition(
        parameters=parameters.model_copy(deep=True),
        exposure_context=config.treatment.model_copy(deep=True),
        events=events,
    )


class SC05Plugin:
    family: Family = "SC-05"
    definition_version = SC05_VERSION

    def validate(self, config: SimulationConfig) -> None:
        config = SimulationConfig.model_validate_json(config.model_dump_json())
        if (config.scenario.family, config.scenario.definition_version) != (
            self.family,
            self.definition_version,
        ):
            raise ValueError("SC-05 configuration does not match this versioned template")
        if config.treatment.category != "no_specific_assumption":
            raise ValueError("Specific treatment exposure rules remain unreviewed")
        _clinical_condition(config)
        underlying = sc05_base_config(config)
        build_registry().resolve(
            underlying.scenario.family, underlying.scenario.definition_version
        ).validate(underlying)

    def generate(self, config: SimulationConfig, baseline_quantity: Decimal) -> PluginOutput:
        self.validate(config)
        underlying = build_registry().generate(sc05_base_config(config), baseline_quantity)
        return PluginOutput(
            family="SC-05",
            mode=underlying.mode,
            tumor_targets=underlying.tumor_targets,
            clinical_profile=config.clinical_profile.model_copy(deep=True),
            clinical_condition=_clinical_condition(config),
        )


def build_registry() -> PluginRegistry:
    registry = PluginRegistry()
    registry.register(SC01Plugin())
    registry.register(SC02Plugin())
    registry.register(SC03Plugin())
    registry.register(SC04Plugin())
    registry.register(SC05Plugin())
    return registry


def volume_at(output: PluginOutput, baseline_quantity: Decimal, relative_day: Decimal) -> Decimal:
    """Piecewise-linear volume between explicit knots, with no extrapolation or biology claim."""
    _declining_targets(output.tumor_targets, baseline_quantity)
    if (
        not isinstance(relative_day, Decimal)
        or not relative_day.is_finite()
        or not 0 <= relative_day <= Decimal(output.tumor_targets[-1].relative_day)
    ):
        raise ValueError("Requested relative day is outside the configured trajectory")
    start_day, start_volume = Decimal(0), baseline_quantity
    with localcontext() as context:
        context.prec = 40
        for target in output.tumor_targets:
            end_day, end_volume = Decimal(target.relative_day), Decimal(target.target_mm3)
            if relative_day <= end_day:
                fraction = (relative_day - start_day) / (end_day - start_day)
                return start_volume + (end_volume - start_volume) * fraction
            start_day, start_volume = end_day, end_volume
    raise ValueError("Requested relative day is outside the configured trajectory")


class TrajectoryValidation(Contract):
    status: Literal["ready", "blocked"]
    ordering_valid: bool
    reasons: list[str]
    publication_gate: Literal["separate_review_and_complete_run_required"] = (
        "separate_review_and_complete_run_required"
    )


def check_realized_order(
    targets: list[TumorTarget], realized: list[Decimal | None], baseline_quantity: Decimal
) -> TrajectoryValidation:
    """Check measured ordering only; target tolerance and all other run gates stay separate."""
    try:
        _declining_targets(targets, baseline_quantity)
    except ValueError:
        return TrajectoryValidation(
            status="blocked",
            ordering_valid=False,
            reasons=["invalid_baseline_or_configured_decline"],
        )
    if len(realized) != len(targets):
        return TrajectoryValidation(
            status="blocked", ordering_valid=False, reasons=["realized_measurement_count_mismatch"]
        )
    reasons = []
    previous = baseline_quantity
    for index, value in enumerate(realized):
        slot = targets[index].slot_id
        if value is None:
            reasons.append("missing_realized_measurement:" + slot)
        elif not isinstance(value, Decimal) or not value.is_finite() or not 0 < value < MAX_VOLUME:
            reasons.append("invalid_realized_measurement:" + slot)
        else:
            if value == previous:
                reasons.append("realized_decline_plateau:" + slot)
            elif value > previous:
                reasons.append("realized_decline_reversed:" + slot)
            previous = value
    return TrajectoryValidation(
        status="blocked" if reasons else "ready", ordering_valid=not reasons, reasons=reasons
    )


def check_family_realized(
    config: SimulationConfig,
    targets: list[TumorTarget],
    realized: list[Decimal | None],
    baseline_quantity: Decimal,
) -> TrajectoryValidation:
    """Validate actual measurements against the explicitly requested family and mode only."""
    try:
        expected = build_registry().generate(config, baseline_quantity)
        if targets != expected.tumor_targets:
            raise ValueError("Supplied targets differ from configured family targets")
    except ValueError:
        return TrajectoryValidation(
            status="blocked",
            ordering_valid=False,
            reasons=["invalid_family_configuration_or_targets"],
        )
    if config.scenario.family == "SC-01":
        return check_realized_order(targets, realized, baseline_quantity)
    if config.scenario.family == "SC-05":
        return check_family_realized(sc05_base_config(config), targets, realized, baseline_quantity)
    if config.scenario.family == "SC-03":
        return check_realized_growth(targets, realized, baseline_quantity)
    if config.scenario.family == "SC-04":
        if len(realized) != len(targets) or any(value is None for value in realized):
            return TrajectoryValidation(
                status="blocked",
                ordering_valid=False,
                reasons=["missing_or_incomplete_realized_regrowth_measurements"],
            )
        try:
            values = [value for value in realized if value is not None]
            if any(not isinstance(value, Decimal) for value in values):
                raise ValueError("Actual measurements must be Decimal quantities")
            actual_index = _regrowth_minimum(values, baseline_quantity)
            expected_index = _regrowth_minimum(
                [Decimal(target.target_mm3) for target in targets], baseline_quantity
            )
            if actual_index != expected_index:
                raise ValueError("Geometry realization shifted the sampled nadir")
        except ValueError:
            return TrajectoryValidation(
                status="blocked",
                ordering_valid=False,
                reasons=["realized_regrowth_erased_or_sampled_nadir_shifted"],
            )
        return TrajectoryValidation(status="ready", ordering_valid=True, reasons=[])
    if len(realized) != len(targets):
        return TrajectoryValidation(
            status="blocked", ordering_valid=False, reasons=["realized_measurement_count_mismatch"]
        )
    if any(value is None for value in realized):
        return TrajectoryValidation(
            status="blocked", ordering_valid=False, reasons=["missing_realized_measurement"]
        )
    try:
        values = [value for value in realized if value is not None]
        if any(not isinstance(value, Decimal) for value in values):
            raise ValueError("Realized measurements must be Decimal quantities")
        _sc02_values(config, values, baseline_quantity)
    except ValueError:
        return TrajectoryValidation(
            status="blocked",
            ordering_valid=False,
            reasons=["realized_values_outside_declared_mode_constraints"],
        )
    return TrajectoryValidation(status="ready", ordering_valid=True, reasons=[])


def check_realized_growth(
    targets: list[TumorTarget], realized: list[Decimal | None], baseline_quantity: Decimal
) -> TrajectoryValidation:
    """Require actual numerical growth; does not establish containment, mechanism or causation."""
    try:
        _increasing_targets(targets, baseline_quantity)
    except ValueError:
        return TrajectoryValidation(
            status="blocked",
            ordering_valid=False,
            reasons=["invalid_baseline_or_configured_growth"],
        )
    if len(realized) != len(targets):
        return TrajectoryValidation(
            status="blocked", ordering_valid=False, reasons=["realized_measurement_count_mismatch"]
        )
    reasons = []
    previous = baseline_quantity
    for target, value in zip(targets, realized, strict=True):
        if value is None:
            reasons.append("missing_realized_measurement:" + target.slot_id)
        elif not isinstance(value, Decimal) or not value.is_finite() or not 0 < value < MAX_VOLUME:
            reasons.append("invalid_realized_measurement:" + target.slot_id)
        else:
            if value == previous:
                reasons.append("realized_growth_plateau:" + target.slot_id)
            elif value < previous:
                reasons.append("realized_growth_reversed:" + target.slot_id)
            previous = value
    return TrajectoryValidation(
        status="blocked" if reasons else "ready", ordering_valid=not reasons, reasons=reasons
    )
