"""Versioned SLRE input contracts; explicit demonstration assumptions, never efficacy rules."""

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from canceros.clinical_contracts import CLINICAL_UNITS, LAB_CONCEPTS
from canceros.contracts import Contract, DecimalString, Hash, MissingReason, Provenance

StableId = Annotated[str, Field(strict=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")]
Family = Literal["SC-01", "SC-02", "SC-03", "SC-04", "SC-05"]
Modality = Literal[
    "imaging", "laboratory", "vital", "symptom", "treatment", "adverse_event", "narrative"
]


class ScenarioDefinition(Contract):
    family: Family
    definition_version: Annotated[
        str, Field(strict=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,79}$")
    ]


class ScheduleSlot(Contract):
    slot_id: StableId
    modality: Modality
    relative_day: DecimalString

    @model_validator(mode="after")
    def positive_day(self):
        day = Decimal(self.relative_day)
        if not 0 <= day < Decimal("100000000") or (
            day == 0 and self.modality not in ("treatment", "adverse_event")
        ):
            raise ValueError(
                "Follow-up day must be positive; only explicit treatment/adverse controls may start at zero"
            )
        return self


class ObservationSchedule(Contract):
    slots: Annotated[list[ScheduleSlot], Field(min_length=3, max_length=64)]

    @model_validator(mode="after")
    def ordered_slots(self):
        ids = [slot.slot_id for slot in self.slots]
        if len(ids) != len(set(ids)):
            raise ValueError("Schedule slot IDs must be unique")
        last: dict[str, Decimal] = {}
        imaging = 0
        for slot in self.slots:
            day = Decimal(slot.relative_day)
            if slot.modality in last and day <= last[slot.modality]:
                raise ValueError("Each modality schedule must be strictly increasing")
            last[slot.modality] = day
            imaging += slot.modality == "imaging"
        if not 3 <= imaging <= 16:
            raise ValueError("Require three to sixteen imaging follow-ups in addition to baseline")
        return self


class TreatmentEvent(Contract):
    event_id: StableId
    relative_day: DecimalString
    category: Literal["hypothetical_exposure_start", "hypothetical_exposure_stop"]

    @model_validator(mode="after")
    def nonnegative_day(self):
        if not 0 <= Decimal(self.relative_day) < Decimal("100000000"):
            raise ValueError("Exposure day must be nonnegative and bounded")
        return self


class TreatmentAssumptions(Contract):
    exposure: Literal["none", "hypothetical"]
    category: Literal[
        "no_specific_assumption",
        "chemotherapy",
        "endocrine",
        "her2_targeted",
        "immunotherapy",
        "surgery",
        "radiotherapy",
    ] = "no_specific_assumption"
    setting: Literal[
        "not_recorded", "neoadjuvant", "adjuvant", "metastatic", "other_documented"
    ] = "not_recorded"
    intent: Literal["not_recorded", "curative", "palliative", "research_hypothetical"] = (
        "not_recorded"
    )
    events: Annotated[list[TreatmentEvent], Field(max_length=32)] = []

    @model_validator(mode="after")
    def coherent(self):
        if self.exposure == "none" and self.category != "no_specific_assumption":
            raise ValueError("Specific exposure category requires hypothetical exposure events")
        if (self.exposure == "none") != (not self.events):
            raise ValueError("Hypothetical exposure requires explicit events; none forbids events")
        if len({event.event_id for event in self.events}) != len(self.events):
            raise ValueError("Exposure event IDs must be unique")
        if any(
            Decimal(a.relative_day) > Decimal(b.relative_day)
            for a, b in zip(self.events, self.events[1:])
        ):
            raise ValueError("Exposure events must be time ordered")
        return self


class TumorProfilePoint(Contract):
    slot_id: StableId
    target_mm3: DecimalString

    @model_validator(mode="after")
    def nonnegative(self):
        if not 0 <= Decimal(self.target_mm3) < Decimal("1000000000000000"):
            raise ValueError("Numerical region volume must be nonnegative and below 1e15 mm3")
        return self


class TumorProfile(Contract):
    metric: Literal["numerical_region_volume"] = "numerical_region_volume"
    unit: Literal["mm3"] = "mm3"
    points: Annotated[list[TumorProfilePoint], Field(min_length=3, max_length=16)]


class ClinicalProfilePoint(Contract):
    slot_id: StableId
    code: StableId
    unit: Annotated[str, Field(strict=True, min_length=1, max_length=32)]
    value: DecimalString

    @model_validator(mode="after")
    def supported_quantity(self):
        if self.code not in CLINICAL_UNITS or self.unit not in CLINICAL_UNITS[self.code]:
            raise ValueError("Unsupported clinical concept/unit pair")
        if self.code != "temperature" and Decimal(self.value) < 0:
            raise ValueError("Clinical quantity cannot be negative for this concept")
        return self


class ClinicalProfile(Contract):
    configuration: Literal[
        "stable", "mild_deterioration", "moderate_deterioration", "severe_deterioration", "recovery"
    ]
    points: Annotated[list[ClinicalProfilePoint], Field(max_length=64)] = []


class NoisePoint(Contract):
    slot_id: StableId
    channel: StableId
    additive_offset: DecimalString


class ExplicitNoise(Contract):
    mode: Literal["none", "explicit"]
    points: Annotated[list[NoisePoint], Field(max_length=64)] = []

    @model_validator(mode="after")
    def no_implicit_distribution(self):
        if (self.mode == "none") != (not self.points):
            raise ValueError("Explicit noise requires offsets; none forbids offsets")
        return self


class MissingPoint(Contract):
    slot_id: StableId
    channel: StableId
    reason: MissingReason


class ExplicitMissingness(Contract):
    mode: Literal["none", "explicit"]
    points: Annotated[list[MissingPoint], Field(max_length=64)] = []

    @model_validator(mode="after")
    def no_implicit_probability(self):
        if (self.mode == "none") != (not self.points):
            raise ValueError("Explicit missingness requires points; none forbids points")
        return self


class ModestReductionParameters(Contract):
    mode: Literal["modest_reduction"]
    min_relative_decline: DecimalString
    max_relative_decline: DecimalString

    @model_validator(mode="after")
    def declared_bounds(self):
        if not 0 < Decimal(self.min_relative_decline) <= Decimal(self.max_relative_decline) <= 1:
            raise ValueError("Declared relative decline bounds must satisfy 0 < min <= max <= 1")
        return self


class NearStableParameters(Contract):
    mode: Literal["near_stable"]
    max_absolute_change_mm3: DecimalString
    max_relative_change: DecimalString

    @model_validator(mode="after")
    def declared_bounds(self):
        if (
            Decimal(self.max_absolute_change_mm3) < 0
            or not 0 <= Decimal(self.max_relative_change) <= 1
        ):
            raise ValueError("Declared absolute/relative stability bounds must be nonnegative")
        return self


SC02Parameters = Annotated[
    ModestReductionParameters | NearStableParameters, Field(discriminator="mode")
]


class SC04Parameters(Contract):
    change_point_day: DecimalString
    nadir_mm3: DecimalString

    @model_validator(mode="after")
    def positive_control(self):
        if not 0 < Decimal(self.change_point_day) < Decimal("100000000"):
            raise ValueError("Configured change point must be positive and bounded")
        if not 0 < Decimal(self.nadir_mm3) < Decimal("1000000000000000"):
            raise ValueError("Configured nadir must be positive and below 1e15 mm3")
        return self


SymptomConcept = Literal["fatigue", "pain", "nausea", "swelling"]
ClinicalConcept = Literal[
    "hemoglobin",
    "wbc",
    "anc",
    "platelets",
    "creatinine",
    "alt",
    "ast",
    "heart_rate",
    "temperature",
    "weight",
    "systolic_bp",
    "diastolic_bp",
    "fatigue",
    "pain",
    "nausea",
    "swelling",
]


class AffectedConcept(Contract):
    concept: ClinicalConcept
    numeric_direction: Literal["increasing", "decreasing"] | None = None

    @model_validator(mode="after")
    def explicit_numeric_direction(self):
        if (self.concept in CLINICAL_UNITS) != (self.numeric_direction is not None):
            raise ValueError(
                "Numeric clinical concepts require explicit direction; symptoms use internal ratings"
            )
        return self


class SymptomCoursePoint(Contract):
    slot_id: StableId
    concept: SymptomConcept
    rating: Annotated[int, Field(strict=True, ge=0, le=10)]
    scale: Literal["simulation_0_10"] = "simulation_0_10"
    presence: Literal["absent", "present"]

    @model_validator(mode="after")
    def coherent_presence(self):
        if (self.presence == "absent") != (self.rating == 0):
            raise ValueError(
                "Absent internal symptom requires zero; present requires a positive rating"
            )
        return self


class SC05Parameters(Contract):
    profile_version: Literal["clinical-condition/1"]
    tumor_family: Literal["SC-01", "SC-02", "SC-03"]
    affected_concepts: Annotated[list[AffectedConcept], Field(min_length=1, max_length=16)]
    onset_day: DecimalString
    recovery_day: DecimalString | None = None
    internal_severity: Literal["mild", "moderate", "severe"]
    symptom_course: Annotated[list[SymptomCoursePoint], Field(max_length=64)] = []

    @model_validator(mode="after")
    def explicit_course(self):
        onset = Decimal(self.onset_day)
        if not 0 <= onset < Decimal("100000000"):
            raise ValueError("Internal onset day must be nonnegative and bounded")
        if self.recovery_day is not None and not onset < Decimal(self.recovery_day) < Decimal(
            "100000000"
        ):
            raise ValueError("Internal recovery must follow onset and remain bounded")
        concepts = [item.concept for item in self.affected_concepts]
        if len(concepts) != len(set(concepts)):
            raise ValueError("Affected concepts must be unique")
        if any(point.concept not in concepts for point in self.symptom_course):
            raise ValueError("Symptom course must belong to an explicitly affected concept")
        return self


class SlotJitter(Contract):
    slot_id: StableId
    min_offset_days: DecimalString
    max_offset_days: DecimalString

    @model_validator(mode="after")
    def bounds(self):
        if Decimal(self.min_offset_days) > Decimal(self.max_offset_days):
            raise ValueError("Jitter bounds are reversed")
        return self


class UniformNoise(Contract):
    slot_id: StableId
    channel: StableId
    min_offset: DecimalString
    max_offset: DecimalString
    distribution: Literal["uniform"] = "uniform"

    @model_validator(mode="after")
    def bounds(self):
        if Decimal(self.min_offset) > Decimal(self.max_offset):
            raise ValueError("Noise bounds are reversed")
        return self


class BernoulliMissing(Contract):
    slot_id: StableId
    channel: StableId
    probability: DecimalString
    reason: MissingReason
    distribution: Literal["bernoulli"] = "bernoulli"

    @model_validator(mode="after")
    def bounds(self):
        if not 0 <= Decimal(self.probability) <= 1:
            raise ValueError("Missingness probability must be within zero and one")
        return self


class SamplingConfig(Contract):
    version: Literal["sampling/1"] = "sampling/1"
    prng_version: Literal["sha256-counter/1"] = "sha256-counter/1"
    jitter_rules: Annotated[list[SlotJitter], Field(max_length=64)] = []
    noise_rules: Annotated[list[UniformNoise], Field(max_length=64)] = []
    missingness_rules: Annotated[list[BernoulliMissing], Field(max_length=64)] = []


class SimulationConfig(Contract):
    schema_version: Literal["simulation-config/1"] = "simulation-config/1"
    config_version: Literal["simulation-config/1"] = "simulation-config/1"
    simulator_version: Literal["slre/1"] = "slre/1"
    scientific_policy: Literal["unreviewed_demo"] = "unreviewed_demo"
    baseline_state_id: UUID | None
    baseline_hash: Hash
    branch_id: UUID
    input_revision: Annotated[int, Field(strict=True, ge=1)]
    scenario: ScenarioDefinition
    treatment: TreatmentAssumptions
    schedule: ObservationSchedule
    tumor_profile: TumorProfile
    clinical_profile: ClinicalProfile
    noise: ExplicitNoise
    missingness: ExplicitMissingness
    geometry_policy: Literal["none", "isotropic-fixed-grid/1"]
    seed: Annotated[int, Field(strict=True, ge=0, le=2**32 - 1)]
    sc02_parameters: SC02Parameters | None = None
    sc04_parameters: SC04Parameters | None = None
    sc05_parameters: SC05Parameters | None = None
    sampling: SamplingConfig | None = None

    @model_validator(mode="after")
    def cross_references(self):
        tumor_sc02 = (
            self.scenario.family == "SC-05"
            and self.sc05_parameters is not None
            and self.sc05_parameters.tumor_family == "SC-02"
        )
        if (self.scenario.family == "SC-02" or tumor_sc02) != (self.sc02_parameters is not None):
            raise ValueError("SC-02 requires explicit mode parameters; other families forbid them")
        if (self.scenario.family == "SC-04") != (self.sc04_parameters is not None):
            raise ValueError(
                "SC-04 requires explicit change-point parameters; other families forbid them"
            )
        if (self.scenario.family == "SC-05") != (self.sc05_parameters is not None):
            raise ValueError(
                "SC-05 requires explicit clinical-condition parameters; other families forbid them"
            )
        slots = {slot.slot_id: slot for slot in self.schedule.slots}
        imaging = [slot.slot_id for slot in self.schedule.slots if slot.modality == "imaging"]
        if [point.slot_id for point in self.tumor_profile.points] != imaging:
            raise ValueError("Tumor points must match every imaging slot in order")
        seen = set()
        for point in self.clinical_profile.points:
            expected = "laboratory" if point.code in LAB_CONCEPTS else "vital"
            if point.slot_id not in slots or slots[point.slot_id].modality != expected:
                raise ValueError("Clinical point must reference a matching modality slot")
            key = (point.slot_id, point.code)
            if key in seen:
                raise ValueError("Duplicate clinical point")
            seen.add(key)
        channels = {
            (point.slot_id, "numerical_region_volume") for point in self.tumor_profile.points
        }
        channels.update((point.slot_id, point.code) for point in self.clinical_profile.points)
        if self.sc05_parameters is not None:
            seen_symptoms = set()
            for symptom_point in self.sc05_parameters.symptom_course:
                if (
                    symptom_point.slot_id not in slots
                    or slots[symptom_point.slot_id].modality != "symptom"
                ):
                    raise ValueError("Symptom course requires an actual configured symptom slot")
                key = (symptom_point.slot_id, symptom_point.concept)
                if key in seen_symptoms:
                    raise ValueError("Duplicate symptom course point")
                seen_symptoms.add(key)
            channels.update(seen_symptoms)
        for profile in (self.noise, self.missingness):
            keys = [(point.slot_id, point.channel) for point in profile.points]
            if len(keys) != len(set(keys)) or not set(keys) <= channels:
                raise ValueError(
                    "Noise/missingness channels must uniquely reference configured points"
                )
        if self.sampling is not None:
            jitter_ids = [rule.slot_id for rule in self.sampling.jitter_rules]
            if len(jitter_ids) != len(set(jitter_ids)) or not set(jitter_ids) <= slots.keys():
                raise ValueError("Jitter rules must uniquely reference configured slots")
            for rules, explicit in (
                (self.sampling.noise_rules, self.noise.points),
                (self.sampling.missingness_rules, self.missingness.points),
            ):
                keys = [(rule.slot_id, rule.channel) for rule in rules]
                if len(keys) != len(set(keys)) or not set(keys) <= channels:
                    raise ValueError(
                        "Sampling rules must uniquely reference configured value channels"
                    )
                if set(keys) & {(point.slot_id, point.channel) for point in explicit}:
                    raise ValueError(
                        "A channel cannot combine fixed and random profiles for the same purpose"
                    )
        return self


class GeneratedQuantity(Contract):
    kind: Literal["quantity"]
    code: StableId
    value: DecimalString
    unit: Annotated[str, Field(strict=True, min_length=1, max_length=32)]
    canonical_value: DecimalString | None = None
    canonical_unit: Annotated[str, Field(strict=True, min_length=1, max_length=32)] | None = None
    definition_version: Literal["canceros-local/1"] | None = None
    generator_version: Literal["clinical-generation/1"] | None = None

    @model_validator(mode="after")
    def compatible_unit(self):
        units = {**CLINICAL_UNITS, "numerical_region_volume": ["mm3"]}
        if self.code not in units or self.unit not in units[self.code]:
            raise ValueError("Unsupported generated quantity/unit")
        if self.code != "temperature" and Decimal(self.value) < 0:
            raise ValueError("Generated quantity must be nonnegative for this concept")
        if (self.canonical_value is None) != (self.canonical_unit is None):
            raise ValueError("Canonical value and unit must be provided together")
        if self.canonical_value is not None:
            if self.code == "numerical_region_volume":
                expected_unit, factor = "mm3", Decimal(1)
            else:
                from canceros.clinical_validation import UNITS

                if self.code not in UNITS or self.unit not in UNITS[self.code]:
                    raise ValueError("Canonical normalization rule is unavailable")
                expected_unit, factor = UNITS[self.code][self.unit]
            if (
                self.canonical_unit != expected_unit
                or Decimal(self.canonical_value) != Decimal(self.value) * factor
            ):
                raise ValueError(
                    "Canonical quantity must exactly normalize the configured value/unit"
                )
        return self


class GeneratedText(Contract):
    kind: Literal["text"]
    text: Annotated[str, Field(strict=True, min_length=1, max_length=2000)]


class GeneratedMissing(Contract):
    kind: Literal["missing"]
    reason: MissingReason
    channel: StableId | None = None


class GeneratedSymptom(Contract):
    kind: Literal["symptom"]
    concept: SymptomConcept
    rating: Annotated[int, Field(strict=True, ge=0, le=10)]
    scale: Literal["engineering_ordinal/1"] = "engineering_ordinal/1"
    configured_scale: Literal["simulation_0_10"] = "simulation_0_10"
    presence: Literal["absent", "present"]
    negation: Literal["affirmed", "negated"]
    resolution_status: Literal["present", "absent_no_previous_report", "configured_resolution"]
    report_type: Literal["hypothetical_self_report"] = "hypothetical_self_report"

    @model_validator(mode="after")
    def coherent(self):
        if (self.presence == "absent") != (self.rating == 0):
            raise ValueError("Absent symptom requires zero internal rating")
        if (self.presence == "absent") != (self.negation == "negated"):
            raise ValueError("Symptom negation must preserve configured presence")
        if (self.presence == "present") != (self.resolution_status == "present"):
            raise ValueError("Symptom resolution status conflicts with presence")
        return self


class GeneratedTreatment(Contract):
    kind: Literal["treatment"]
    event_reference: StableId
    action: Literal["hypothetical_exposure_start", "hypothetical_exposure_stop"]
    category: Literal["no_specific_assumption"] = "no_specific_assumption"
    assumption: Literal["hypothetical_not_prescription"] = "hypothetical_not_prescription"


class GeneratedAdverseEvent(Contract):
    kind: Literal["adverse_event"]
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


class GeneratedEvent(Contract):
    event_id: UUID
    branch_id: UUID
    run_id: UUID
    slot_id: StableId
    relative_day: DecimalString
    modality: Modality
    value: Annotated[
        GeneratedQuantity
        | GeneratedText
        | GeneratedMissing
        | GeneratedSymptom
        | GeneratedTreatment
        | GeneratedAdverseEvent,
        Field(discriminator="kind"),
    ]
    origin: Literal[Provenance.SYNTHETIC_GENERATED] = Provenance.SYNTHETIC_GENERATED

    @model_validator(mode="after")
    def matching_modality(self):
        day = Decimal(self.relative_day)
        if not 0 <= day < Decimal("100000000") or (
            day == 0 and self.modality not in ("treatment", "adverse_event")
        ):
            raise ValueError("Only explicitly scheduled treatment/adverse events may start at zero")
        if self.value.kind == "quantity":
            code = self.value.code
            expected = (
                "imaging"
                if code == "numerical_region_volume"
                else "laboratory"
                if code in LAB_CONCEPTS
                else "vital"
            )
            if self.modality != expected:
                raise ValueError("Generated quantity does not match modality")
        elif self.value.kind == "text" and self.modality in ("imaging", "laboratory", "vital"):
            raise ValueError("Numeric modalities require quantity or explicit missingness")
        elif (
            self.value.kind in ("symptom", "treatment", "adverse_event")
            and self.modality != self.value.kind
        ):
            raise ValueError("Typed generated clinical value does not match modality")
        return self
