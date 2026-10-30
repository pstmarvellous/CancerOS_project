"""Clinical/1 canonical contracts; local terminology without unverified external codes."""

from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from canceros.contracts import (
    Availability,
    Context,
    Contract,
    DecimalString,
    Hash,
    MissingReason,
    Provenance,
    Publication,
    Quality,
    Quantity,
    TimeReference,
)

DICTIONARY_VERSION = "canceros-local/1"
CLINICAL_UNITS = {
    "hemoglobin": ["g/dL", "g/L"],
    "wbc": ["10[9]/L"],
    "anc": ["10[9]/L"],
    "platelets": ["10[9]/L"],
    "creatinine": ["mg/dL"],
    "alt": ["U/L"],
    "ast": ["U/L"],
    "heart_rate": ["/min"],
    "temperature": ["Cel"],
    "weight": ["kg"],
    "systolic_bp": ["mmHg"],
    "diastolic_bp": ["mmHg"],
}
LAB_CONCEPTS = {"hemoglobin", "wbc", "anc", "platelets", "creatinine", "alt", "ast"}


class ClinicalTime(Contract):
    reference: TimeReference
    precision: Literal["second", "minute", "day", "relative_day", "unknown"]
    date_shift_basis: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    uncertainty_days: DecimalString | None = None

    @model_validator(mode="after")
    def consistent_time(self):
        time = self.reference
        valid = {
            "timestamp": {"second", "minute"},
            "date": {"day"},
            "relative_day": {"relative_day"},
            "unknown": {"unknown"},
        }
        if self.precision not in valid[time.basis]:
            raise ValueError("Precision does not match source time")
        if time.time_domain == "source_shifted" and not self.date_shift_basis:
            raise ValueError("Shifted source time requires its documented basis")
        if self.uncertainty_days is not None and Decimal(self.uncertainty_days) < 0:
            raise ValueError("Negative time uncertainty")
        if (
            time.basis == "timestamp"
            and self.precision == "minute"
            and (time.value.second or time.value.microsecond)
        ):
            raise ValueError("Minute precision cannot claim exact seconds")
        return self


class ExactResult(Contract):
    form: Literal["exact"]
    quantity: Quantity


class CensoredResult(Contract):
    form: Literal["censored"]
    comparator: Literal["<", "<=", ">", ">="]
    threshold: Quantity


class MissingResult(Contract):
    form: Literal["missing"]
    missing_reason: MissingReason


NumericResult = Annotated[ExactResult | CensoredResult | MissingResult, Field(discriminator="form")]
ReceptorStatus = Literal[
    "positive", "negative", "equivocal", "unknown", "not_tested", "not_recorded", "invalid"
]


class ClinicalItemInput(Contract):
    client_record_key: Annotated[str, Field(pattern=r"^[A-Za-z0-9._-]{1,80}$")]
    source_locator_id: UUID
    time: ClinicalTime
    dictionary_version: Literal["canceros-local/1"] = "canceros-local/1"
    original_term: Annotated[str, Field(min_length=1, max_length=300)]
    certainty: Literal["documented", "reported", "uncertain", "unknown"]
    negation: Literal["affirmed", "negated", "unspecified"]
    visit_id: UUID | None = None


class SourceReferenceInterval(Contract):
    low: DecimalString | None = None
    high: DecimalString | None = None
    unit: Annotated[str, Field(min_length=1, max_length=32)]
    source_description: Annotated[str, Field(min_length=1, max_length=300)]
    population_context: Annotated[str, Field(min_length=1, max_length=300)]
    version: Annotated[str, Field(min_length=1, max_length=80)]

    @model_validator(mode="after")
    def bounds(self):
        if self.low is None and self.high is None:
            raise ValueError("Source interval requires a bound")
        if (
            self.low is not None
            and self.high is not None
            and Decimal(self.low) > Decimal(self.high)
        ):
            raise ValueError("Reversed source interval")
        return self


class VisitInput(ClinicalItemInput):
    kind: Literal["visit"]
    concept: Literal["clinical_visit", "imaging_exam", "source_occasion", "unknown"]
    label: Annotated[str, Field(min_length=1, max_length=200)]


class NumericInput(ClinicalItemInput):
    kind: Literal["laboratory", "vital"]
    concept: Literal[
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
    ]
    result: NumericResult
    original_value: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    original_unit: Annotated[str, Field(min_length=1, max_length=32)] | None = None
    component_group: UUID | None = None
    reference_interval: SourceReferenceInterval | None = None

    @model_validator(mode="after")
    def originals(self):
        if (self.kind == "laboratory") != (self.concept in LAB_CONCEPTS):
            raise ValueError("Concept does not match observation kind")
        if self.result.form != "missing" and (
            self.original_value is None or self.original_unit is None
        ):
            raise ValueError("Original value and unit are required for numeric results")
        quantity = (
            self.result.quantity
            if self.result.form == "exact"
            else self.result.threshold
            if self.result.form == "censored"
            else None
        )
        if quantity and (
            quantity.unit not in CLINICAL_UNITS[self.concept]
            or self.original_unit not in CLINICAL_UNITS[self.concept]
        ):
            raise ValueError("Unsupported unit; review the source mapping")
        return self


class DiagnosisInput(ClinicalItemInput):
    kind: Literal["diagnosis"]
    concept: Literal["source_pathology"]
    histology: str | None = Field(default=None, max_length=200)
    side: Literal["left", "right", "bilateral", "unknown"]
    er_status: ReceptorStatus
    pr_status: ReceptorStatus
    her2_status: ReceptorStatus
    clinical_stage: str | None = Field(default=None, max_length=100)
    pathologic_stage: str | None = Field(default=None, max_length=100)
    staging_system: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def stage_system(self):
        if (self.clinical_stage or self.pathologic_stage) and not self.staging_system:
            raise ValueError("Source stage requires its staging system")
        return self


class TreatmentInput(ClinicalItemInput):
    kind: Literal["treatment"]
    concept: Literal[
        "chemotherapy",
        "endocrine",
        "her2_targeted",
        "immunotherapy",
        "surgery",
        "radiotherapy",
        "other",
        "unknown",
    ]
    event_type: Literal[
        "ordered", "prescribed", "administered", "reported_exposure", "stopped", "unknown"
    ]
    exposure_status: Literal["documented_delivery", "ordered_only", "reported", "unknown"]
    regimen_text: str | None = Field(default=None, max_length=500)
    ended_time: ClinicalTime | None = None

    @model_validator(mode="after")
    def exposure(self):
        if (
            self.event_type in ("ordered", "prescribed")
            and self.exposure_status == "documented_delivery"
        ):
            raise ValueError("An order/prescription is not evidence of delivery")
        if self.ended_time is not None:
            start, end = self.time.reference, self.ended_time.reference
            if start.time_domain != end.time_domain:
                raise ValueError("Treatment interval has incompatible time domains")
            if start.basis == "relative_day" and end.basis == "relative_day":
                if (start.timeline_origin_id, start.anchor_state_id) != (
                    end.timeline_origin_id,
                    end.anchor_state_id,
                ):
                    raise ValueError("Treatment interval anchors differ")
                reversed_interval = Decimal(end.value) < Decimal(start.value)
                if reversed_interval:
                    raise ValueError("Treatment end precedes start")
            elif (start.basis == "timestamp" and end.basis == "timestamp") or (
                start.basis == "date" and end.basis == "date"
            ):
                if end.value < start.value:
                    raise ValueError("Treatment end precedes start")
        return self


class SymptomInput(ClinicalItemInput):
    kind: Literal["symptom"]
    concept: Literal["fatigue", "pain", "nausea", "swelling", "other"]
    presence: Literal["present", "absent", "unknown", "not_assessed"]
    reporter: Literal["patient", "clinician", "unknown"]
    severity: DecimalString | None = None
    instrument: str | None = Field(default=None, max_length=100)
    instrument_version: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def scale(self):
        if self.severity is not None:
            if (
                not self.instrument
                or not self.instrument_version
                or self.presence not in ("present", "absent")
            ):
                raise ValueError("Severity requires a known presence and versioned instrument")
            if self.presence == "absent" and Decimal(self.severity) != 0:
                raise ValueError("Absent symptoms cannot have positive severity")
        return self


class NoteInput(ClinicalItemInput):
    kind: Literal["note"]
    concept: Literal["source_note"]
    artifact_id: UUID
    note_document_id: UUID | None = None
    content_sha256: Hash
    language: Annotated[str, Field(min_length=2, max_length=20)]


ClinicalInput = Annotated[
    VisitInput | NumericInput | DiagnosisInput | TreatmentInput | SymptomInput | NoteInput,
    Field(discriminator="kind"),
]


class ClinicalRecord(Contract):
    schema_version: Literal["clinical/1"] = "clinical/1"
    id: UUID
    project_id: UUID
    patient_id: UUID
    item: ClinicalInput
    origin: Provenance
    context: Context
    quality: Quality
    availability: Availability
    publication: Publication = Publication.DRAFT
    scientific_review: Literal["pending", "approved", "rejected", "not_applicable"] = "pending"
    numeric_normalization: "NumericNormalization | None" = None

    @model_validator(mode="after")
    def context_origin(self):
        if self.context == Context.OBSERVED and (
            self.origin == Provenance.SYNTHETIC_GENERATED
            or self.item.time.reference.time_domain == "simulation"
        ):
            raise ValueError("Synthetic content cannot be observed")
        if self.context == Context.SYNTHETIC and self.origin in (
            Provenance.REAL_OBSERVED,
            Provenance.REAL_DERIVED,
        ):
            raise ValueError("Generated clinical records cannot claim real origin")
        relative = self.item.time.reference
        if relative.basis == "relative_day" and relative.anchor_state_id == self.id:
            raise ValueError("Self anchor rejected")
        return self


class NumericNormalization(Contract):
    conversion_rule_version: Literal["local-units/1"] = "local-units/1"
    original_value: str | None
    original_unit: str | None
    canonical_result: NumericResult


class ClinicalDictionary(Contract):
    version: Literal["canceros-local/1"] = "canceros-local/1"
    namespace: Literal["local_research"] = "local_research"
    external_terminology: Literal["none_adopted"] = "none_adopted"
    interpretation_status: Literal["engineering_only_review_pending"] = (
        "engineering_only_review_pending"
    )
    concepts: dict[str, list[str]]
    receptor_statuses: list[str]
    missing_reasons: list[str]
    units: dict[str, list[str]]
    symptom_instruments: dict[str, dict[str, str]]


def clinical_dictionary():
    from typing import get_args

    return ClinicalDictionary(
        concepts={
            "laboratory": sorted(LAB_CONCEPTS),
            "vital": sorted(set(CLINICAL_UNITS) - LAB_CONCEPTS),
            "treatment": list(get_args(TreatmentInput.model_fields["concept"].annotation)),
            "symptom": list(get_args(SymptomInput.model_fields["concept"].annotation)),
            "diagnosis": ["source_pathology"],
            "note": ["source_note"],
            "visit": ["clinical_visit", "imaging_exam", "source_occasion", "unknown"],
        },
        receptor_statuses=list(get_args(ReceptorStatus)),
        missing_reasons=list(get_args(MissingReason)),
        units=CLINICAL_UNITS,
        symptom_instruments={
            "engineering_ordinal": {
                "version": "1",
                "minimum": "0",
                "maximum": "10",
                "scope": "synthetic engineering fixtures only; no clinical grade",
            }
        },
    )


def validate_anchor_graph(references: dict[UUID, ClinicalTime]):
    """Validate a bounded caller-owned graph; callers enforce project/patient scope."""
    done = set()

    def visit(record_id, trail):
        if record_id in trail:
            raise ValueError("Cyclic time anchor")
        if record_id in done:
            return
        current = references[record_id].reference
        if current.basis == "relative_day" and current.anchor_state_id:
            target_id = current.anchor_state_id
            if target_id not in references:
                raise ValueError("Unresolved time anchor")
            target = references[target_id].reference
            if target.basis == "unknown" or target.time_domain != current.time_domain:
                raise ValueError("Incomparable time anchor")
            visit(target_id, trail | {record_id})
        done.add(record_id)

    for identity in references:
        visit(identity, set())
