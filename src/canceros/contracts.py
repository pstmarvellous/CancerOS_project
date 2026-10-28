"""Canonical foundation/1 wire contracts, governed by SPEC-008 and ADR-001."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


def finite_quantity(value: str) -> str:
    number = Decimal(value)
    if not number.is_finite() or abs(number) >= Decimal("1000000000000000"):
        raise ValueError("Quantity outside numeric(24,9) range")
    return value


DecimalString = Annotated[
    str,
    Field(strict=True, pattern=r"^-?(0|[1-9]\d*)(\.\d{1,9})?$"),
    AfterValidator(finite_quantity),
]
Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Provenance(StrEnum):
    REAL_OBSERVED = "REAL_OBSERVED"
    REAL_DERIVED = "REAL_DERIVED"
    SYNTHETIC_GENERATED = "SYNTHETIC_GENERATED"
    INTERPOLATED = "INTERPOLATED"
    MODEL_PREDICTED = "MODEL_PREDICTED"


def derived_origin(origin: Provenance) -> Provenance:
    """Processing cannot promote simulated/interpolated/predicted material to real."""
    if origin in (Provenance.REAL_OBSERVED, Provenance.REAL_DERIVED):
        return Provenance.REAL_DERIVED
    return origin


class Context(StrEnum):
    OBSERVED = "OBSERVED"
    SYNTHETIC = "SYNTHETIC"


class Quality(StrEnum):
    PENDING = "pending"
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


class Availability(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    PENDING = "pending"
    INVALID = "invalid"
    REJECTED = "rejected"


class Publication(StrEnum):
    DRAFT = "draft"
    VALIDATING = "validating"
    READY = "ready"
    PUBLISHED = "published"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


TimeDomain = Literal["source_calendar", "source_shifted", "source_relative", "simulation"]
MissingReason = Literal[
    "unknown", "not_recorded", "not_collected", "not_applicable", "below_detection", "withheld"
]


class TimestampTime(Contract):
    basis: Literal["timestamp"]
    value: AwareDatetime
    time_domain: Literal["source_calendar", "source_shifted", "simulation"]

    @field_validator("value", mode="before")
    @classmethod
    def reject_numeric_timestamp(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError("Offset timestamp required")
        return value


class DateTimeReference(Contract):
    basis: Literal["date"]
    value: date
    time_domain: Literal["source_calendar", "source_shifted", "simulation"]

    @field_validator("value", mode="before")
    @classmethod
    def exact_source_date(cls, value):
        if isinstance(value, datetime) or (isinstance(value, str) and len(value) != 10):
            raise ValueError("Source date required without fabricated time")
        if not isinstance(value, (str, date)):
            raise ValueError("Source date required")
        return value


class RelativeTime(Contract):
    basis: Literal["relative_day"]
    value: DecimalString
    time_domain: Literal["source_relative", "simulation"]
    timeline_origin_id: UUID | None = None
    anchor_state_id: UUID | None = None

    @model_validator(mode="after")
    def exactly_one_anchor(self):
        if (self.timeline_origin_id is None) == (self.anchor_state_id is None):
            raise ValueError("Exactly one authorized timeline origin or state anchor required")
        exponent = Decimal(self.value).as_tuple().exponent
        if (
            not isinstance(exponent, int)
            or exponent < -4
            or abs(Decimal(self.value)) >= Decimal("100000000")
        ):
            raise ValueError("Relative day outside numeric(12,4) range")
        return self


class UnknownTime(Contract):
    basis: Literal["unknown"]
    missing_reason: MissingReason
    time_domain: TimeDomain


TimeReference = Annotated[
    TimestampTime | DateTimeReference | RelativeTime | UnknownTime, Field(discriminator="basis")
]


class TimelineOrigin(Contract):
    id: UUID
    project_id: UUID
    patient_id: UUID
    reference_meaning: Annotated[str, Field(min_length=1, max_length=200)]
    time_domain: TimeDomain


class Quantity(Contract):
    value: DecimalString
    unit: Annotated[str, Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9/%._\[\]-]+$")]


class ProvenancedQuantity(Quantity):
    provenance: Provenance


class FoundationEnvelope(Contract):
    schema_version: Literal["foundation/1"] = "foundation/1"
    origin: Provenance
    context: Context
    time: TimeReference
    quantity: Quantity | None = None
    quality: Quality = Quality.PENDING
    availability: Availability = Availability.UNAVAILABLE
    publication: Publication = Publication.DRAFT


class Health(Contract):
    status: Literal["ok"] = "ok"


class ProjectRole(Contract):
    project_id: UUID
    role: Literal["viewer", "editor", "admin"]


class Me(Contract):
    user_id: UUID
    project_roles: list[ProjectRole]


class FoundationStatus(Contract):
    foundation: Literal["available"] = "available"
    clinical_capabilities: Literal["not_implemented"] = "not_implemented"


class Problem(Contract):
    type: str = "about:blank"
    title: str
    status: int
    code: str
    request_id: str
    errors: list[str] = Field(default_factory=list)
