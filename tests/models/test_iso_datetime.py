# tests/models/test_iso_datetime.py
import json
import time
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import BaseModel

from kronicle_sdk.models.iso_datetime import IsoDateTime, now, now_local, now_utc

LOCAL_TZ = datetime.now().astimezone().tzinfo


class Event(BaseModel):
    timestamp: IsoDateTime


class TestConstruction:
    def test_naive_input_stays_naive_tzinfo(self):
        # Quirk: __new__ routes through to_iso_datetime, which short-circuits for
        # IsoDateTime instances. So the "naive -> local tz" default documented on
        # the class does NOT actually apply at construction time; tzinfo stays None.
        value = IsoDateTime(2025, 9, 17, 20, 0, 0)
        assert isinstance(value, IsoDateTime)
        assert value.tzinfo is None

    def test_aware_input_preserves_tzinfo(self):
        value = IsoDateTime(2025, 9, 17, 20, 0, 0, tzinfo=timezone.utc)
        assert value.tzinfo is timezone.utc

    def test_str_uses_local_offset(self):
        value = IsoDateTime(2025, 9, 17, 20, 0, 0)
        assert str(value) == value.iso_str()
        assert datetime.fromisoformat(str(value)).tzinfo is not None

    def test_repr_is_quoted_iso(self):
        value = IsoDateTime(2025, 9, 17, 20, 0, 0)
        assert repr(value) == repr(value.iso_str())


class TestFormatting:
    def test_iso_str(self):
        value = IsoDateTime(2025, 9, 17, 20, 0, 0, tzinfo=timezone.utc)
        assert value.iso_str() == "2025-09-17T20:00:00+00:00"

    def test_iso_utc_shifts_to_utc(self):
        value = IsoDateTime(2025, 9, 17, 20, 0, 0, tzinfo=timezone(timedelta(hours=2)))
        assert value.iso_utc() == "2025-09-17T18:00:00+00:00"

    def test_iso_local(self):
        value = IsoDateTime(2025, 9, 17, 20, 0, 0, tzinfo=timezone.utc)
        assert value.iso_local() == value.astimezone().isoformat()


class TestNowHelpers:
    def test_now_default_is_naive(self):
        # Bug: `super().now(tz)` is bound to `cls` (IsoDateTime), so it already
        # returns an IsoDateTime and to_iso_datetime short-circuits. With no tz
        # the result stays naive instead of defaulting to the local timezone.
        value = IsoDateTime.now()
        assert isinstance(value, IsoDateTime)
        assert value.tzinfo is None

    def test_now_with_tz(self):
        value = IsoDateTime.now(timezone.utc)
        assert value.tzinfo is timezone.utc

    def test_now_utc(self):
        value = IsoDateTime.now_utc()
        assert isinstance(value, IsoDateTime)
        assert value.tzinfo is timezone.utc
        assert value.iso_utc() == value.iso_str()

    def test_now_local(self):
        value = IsoDateTime.now_local()
        assert isinstance(value, IsoDateTime)
        assert value.tzinfo is not None

    def test_now_log_format(self):
        parsed = datetime.strptime(IsoDateTime.now_log(), "%Y-%m-%d %H:%M:%S")
        assert parsed.year >= 2000

    def test_now_timestamp_matches_clock(self):
        assert abs(IsoDateTime.now_timestamp() - time.time()) < 5


class TestToIsoDateTime:
    def test_isodatetime_passthrough(self):
        value = IsoDateTime(2025, 1, 1)
        assert IsoDateTime.to_iso_datetime(value) is value

    def test_naive_datetime_gets_local_tz(self):
        converted = IsoDateTime.to_iso_datetime(datetime(2025, 9, 17, 20, 0, 0))
        assert isinstance(converted, IsoDateTime)
        assert converted.tzinfo == LOCAL_TZ

    def test_aware_datetime_preserves_tz(self):
        converted = IsoDateTime.to_iso_datetime(datetime(2025, 9, 17, 20, 0, 0, tzinfo=timezone.utc))
        assert converted.tzinfo is timezone.utc


class TestParsePartialIso:
    def test_year_only(self):
        value = IsoDateTime._parse_partial_iso("2025")
        assert (value.year, value.month, value.day) == (2025, 1, 1)

    def test_year_month(self):
        value = IsoDateTime._parse_partial_iso("2025-06")
        assert (value.year, value.month, value.day) == (2025, 6, 1)

    def test_full_date(self):
        value = IsoDateTime._parse_partial_iso("2025-06-15")
        assert (value.year, value.month, value.day) == (2025, 6, 15)


class TestNormalizeValue:
    def test_isodatetime_passthrough(self):
        value = IsoDateTime(2025, 1, 1)
        assert IsoDateTime.normalize_value(value) is value

    def test_datetime_object_converted(self):
        value = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
        converted = IsoDateTime.normalize_value(value)
        assert isinstance(converted, IsoDateTime)
        assert converted == value

    def test_iso_string_aware(self):
        value = IsoDateTime.normalize_value("2025-09-17T20:00:00+02:00")
        assert value.utcoffset() == timedelta(hours=2)

    def test_iso_string_z_suffix(self):
        value = IsoDateTime.normalize_value("2025-09-17T20:00:00Z")
        assert value.utcoffset() == timedelta(0)

    def test_iso_string_naive_stays_naive(self):
        # Bug: `cls.fromisoformat(...)` already returns an IsoDateTime, so the
        # `if dt.tzinfo is None` guard calls to_iso_datetime(dt), which short-
        # circuits for IsoDateTime instances. The documented "naive -> local tz"
        # normalization therefore does NOT happen for naive strings.
        value = IsoDateTime.normalize_value("2025-09-17T20:00:00")
        assert value.tzinfo is None

    def test_partial_year_string(self):
        value = IsoDateTime.normalize_value("2025")
        assert (value.year, value.month, value.day) == (2025, 1, 1)

    def test_partial_year_month_string(self):
        value = IsoDateTime.normalize_value("2025-06")
        assert (value.year, value.month, value.day) == (2025, 6, 1)

    def test_unparseable_string_raises(self):
        with pytest.raises(ValueError, match="Cannot parse datetime from 'not-a-date'"):
            IsoDateTime.normalize_value("not-a-date")

    def test_invalid_partial_month_raises_wrapped(self):
        with pytest.raises(ValueError, match="Cannot parse datetime"):
            IsoDateTime.normalize_value("2025-13")

    def test_unsupported_type_raises(self):
        with pytest.raises(ValueError, match="Cannot normalize type 'int'"):
            IsoDateTime.normalize_value(42)


class TestPydanticIntegration:
    def test_naive_string_input(self):
        event = Event(timestamp="2025-09-17T20:00:00")  # type: ignore  # type: ignore
        assert isinstance(event.timestamp, IsoDateTime)
        assert event.timestamp.tzinfo is not None

    def test_aware_string_input(self):
        event = Event(timestamp="2025-09-17T20:00:00+02:00")  # type: ignore  # type: ignore
        assert isinstance(event.timestamp, IsoDateTime)
        assert event.timestamp.utcoffset() == timedelta(hours=2)

    def test_datetime_object_input(self):
        event = Event(timestamp=datetime(2025, 9, 17, 20, 0, 0, tzinfo=timezone.utc))  # type: ignore  # type: ignore
        assert isinstance(event.timestamp, IsoDateTime)
        assert event.timestamp.tzinfo is not None

    def test_json_serialization_uses_local(self):
        event = Event(timestamp=datetime(2025, 9, 17, 20, 0, 0, tzinfo=timezone.utc))  # type: ignore  # type: ignore
        assert json.loads(event.model_dump_json())["timestamp"] == event.timestamp.iso_local()

    def test_python_serialization(self):
        event = Event(timestamp=datetime(2025, 9, 17, 20, 0, 0, tzinfo=timezone.utc))  # type: ignore  # type: ignore
        assert event.model_dump()["timestamp"] == event.timestamp.iso_local()


class TestModuleHelpers:
    def test_now(self):
        value = now()
        assert isinstance(value, IsoDateTime)

    def test_now_local(self):
        value = now_local()
        assert isinstance(value, IsoDateTime)
        assert value.tzinfo is not None

    def test_now_utc(self):
        value = now_utc()
        assert isinstance(value, IsoDateTime)
        assert value.tzinfo is timezone.utc
