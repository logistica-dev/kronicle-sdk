# tests/utils/test_date_generator.py
import random
from datetime import datetime, timedelta, timezone
from itertools import islice

import pytest

from kronicle_sdk.models.iso_datetime import IsoDateTime
from kronicle_sdk.utils.date_generator import DateGenerator


@pytest.fixture(autouse=True)
def _restore_global_random_state():
    """DateGenerator seeds the global random module: restore it after each test."""
    state = random.getstate()
    yield
    random.setstate(state)


class TestConstruction:
    def test_start_string_is_normalized(self):
        gen = DateGenerator(start="2025-01-01T00:00:00Z", increment=60, jitter_percent=0)
        assert isinstance(gen.current, IsoDateTime)
        assert gen.current == IsoDateTime.normalize_value("2025-01-01T00:00:00Z")

    def test_partial_iso_start(self):
        gen = DateGenerator(start="2025", increment=36000, jitter_percent=0)
        assert gen.current == IsoDateTime.normalize_value("2025-01-01")

    def test_start_datetime(self):
        dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
        gen = DateGenerator(start=dt, increment=1, jitter_percent=0)
        assert gen.current == dt

    def test_start_defaults_to_now(self):
        gen = DateGenerator(increment=1, jitter_percent=0)
        assert isinstance(gen.current, IsoDateTime)
        assert abs(gen.current - IsoDateTime.now()) < timedelta(seconds=5)

    def test_invalid_start_raises(self):
        with pytest.raises(ValueError, match="Cannot normalize type 'int'"):
            DateGenerator(start=123, increment=1)  # type: ignore

    @pytest.mark.parametrize(
        ("increment", "expected"),
        [
            (60, timedelta(seconds=60)),
            (2.5, timedelta(seconds=2.5)),
            (timedelta(minutes=5), timedelta(minutes=5)),
            (None, timedelta(seconds=1)),
        ],
    )
    def test_increment_normalized_to_timedelta(self, increment, expected):
        gen = DateGenerator(start="2025-01-01T00:00:00Z", increment=increment, jitter_percent=0)
        assert gen.increment == expected

    def test_default_jitter_percent(self):
        gen = DateGenerator(start="2025-01-01T00:00:00Z", increment=100)
        assert gen.jitter_percent == 0.1
        assert gen.jitter == timedelta(seconds=10)


class TestGet:
    def test_returns_current_then_advances(self):
        gen = DateGenerator(start="2025-01-01T00:00:00Z", increment=60, jitter_percent=0)
        first, second, third = gen.get(), gen.get(), gen.get()
        assert first == IsoDateTime.normalize_value("2025-01-01T00:00:00Z")
        assert second - first == timedelta(seconds=60)
        assert third - second == timedelta(seconds=60)

    def test_zero_jitter_percent_disables_jitter(self):
        gen = DateGenerator(start="2025-01-01T00:00:00Z", increment=60, jitter_percent=0)
        assert gen.jitter_percent == 0
        assert gen.jitter == timedelta(0)

    def test_default_jitter_stays_within_bounds(self):
        gen = DateGenerator(start="2025-01-01T00:00:00Z", increment=60)
        first, second = gen.get(), gen.get()
        delta = (second - first).total_seconds()
        # jitter is ±10% of the increment by default
        assert 60 * 0.9 - 1e-6 <= delta <= 60 * 1.1 + 1e-6, delta

    def test_returns_isodatetime(self):
        gen = DateGenerator(start="2025-01-01T00:00:00Z", increment=1, jitter_percent=0)
        assert isinstance(gen.get(), IsoDateTime)

    def test_jitter_stays_within_bounds(self):
        gen = DateGenerator(start="2025-01-01T00:00:00Z", increment=10, jitter_percent=0.5, seed=42)
        values = [gen.get() for _ in range(30)]
        deltas = [(b - a).total_seconds() for a, b in zip(values, values[1:], strict=False)]
        assert deltas, "expected at least two values"
        # increment (10s) ± jitter (±50% = ±5s)
        assert all(5 - 1e-6 <= d <= 15 + 1e-6 for d in deltas), deltas

    def test_seed_is_reproducible(self):
        def sequence():
            gen = DateGenerator(start="2025-01-01T00:00:00Z", increment=60, jitter_percent=0.5, seed=7)
            return [str(gen.get()) for _ in range(10)]

        assert sequence() == sequence()


class TestComputeJitter:
    def test_jitter_stays_within_bounds(self):
        gen = DateGenerator(start="2025-01-01T00:00:00Z", increment=10, jitter_percent=0.5, seed=42)
        for _ in range(50):
            jitter = gen._compute_jitter()
            assert timedelta(seconds=-5) <= jitter <= timedelta(seconds=5)

    def test_none_jitter_returns_zero(self):
        # Defensive branch: unreachable through __init__ (jitter is always a
        # timedelta), so the attribute is forced here.
        gen = DateGenerator(start="2025-01-01T00:00:00Z", increment=60, jitter_percent=0)
        gen.jitter = None  # type: ignore
        assert gen._compute_jitter() == timedelta(0)


class TestPeek:
    def test_peek_does_not_advance(self):
        gen = DateGenerator(start="2025-01-01T00:00:00Z", increment=60, jitter_percent=0)
        start = gen.current
        preview = gen.peek()
        assert gen.current == start
        assert preview == IsoDateTime.normalize_value("2025-01-01T00:01:00Z")
        # stable without jitter
        assert gen.peek() == preview
        # get() returns the un-advanced value
        assert gen.get() == start


class TestReset:
    def test_reset_moves_clock(self):
        gen = DateGenerator(start="2025-01-01T00:00:00Z", increment=60, jitter_percent=0)
        gen.get()
        gen.reset("2030-06-15T12:00:00Z")
        assert gen.current == IsoDateTime.normalize_value("2030-06-15T12:00:00Z")
        assert gen.get() == IsoDateTime.normalize_value("2030-06-15T12:00:00Z")


class TestIteration:
    def test_yields_increasing_dates(self):
        gen = DateGenerator(start="2025-01-01T00:00:00Z", increment=60, jitter_percent=0)
        values = list(islice(gen, 4))
        assert len(values) == 4
        assert values[0] == IsoDateTime.normalize_value("2025-01-01T00:00:00Z")
        assert all(b - a == timedelta(seconds=60) for a, b in zip(values, values[1:], strict=False))
