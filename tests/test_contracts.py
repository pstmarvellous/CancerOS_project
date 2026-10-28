from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from canceros.contracts import Provenance, Quantity, RelativeTime, TimeReference, derived_origin


@pytest.mark.parametrize(
    "value", [0, 1.2, "NaN", "Infinity", "1e3", "01", "1.1234567890", "1000000000000000"]
)
def test_invalid_decimal(value):
    with pytest.raises(ValidationError):
        Quantity(value=value, unit="mm3")


def test_decimal_and_synthetic_origin_preserved():
    assert Quantity(value="0.000000001", unit="mm3").model_dump()["value"] == "0.000000001"
    assert derived_origin(Provenance.SYNTHETIC_GENERATED) == Provenance.SYNTHETIC_GENERATED
    assert derived_origin(Provenance.REAL_OBSERVED) == Provenance.REAL_DERIVED
    assert derived_origin(Provenance.MODEL_PREDICTED) == Provenance.MODEL_PREDICTED


@pytest.mark.parametrize(
    "data",
    [
        {"basis": "relative_day", "value": "0", "time_domain": "source_relative"},
        {"basis": "timestamp", "value": "2026-01-01T00:00:00", "time_domain": "source_calendar"},
        {"basis": "timestamp", "value": 12345, "time_domain": "source_calendar"},
        {"basis": "date", "value": "2026-01-01T00:00:00Z", "time_domain": "source_calendar"},
        {
            "basis": "unknown",
            "missing_reason": "unknown",
            "value": "0",
            "time_domain": "source_relative",
        },
    ],
)
def test_invalid_time(data):
    with pytest.raises(ValidationError):
        TypeAdapter(TimeReference).validate_python(data)


def test_relative_root_without_calendar_date():
    value = RelativeTime(
        basis="relative_day", value="0", time_domain="source_relative", timeline_origin_id=uuid4()
    )
    assert value.model_dump(mode="json")["value"] == "0"
    with pytest.raises(ValidationError):
        RelativeTime(
            basis="relative_day",
            value="0",
            time_domain="source_relative",
            timeline_origin_id=uuid4(),
            anchor_state_id=uuid4(),
        )
