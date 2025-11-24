# dt_storage/types/date_generator.py

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Optional

from kronicle.models.iso_datetime import IsoDateTime
from kronicle.utils.log import log_d


class DateGenerator:
    """
    Stateful date generator.

    Each call to .get() returns an IsoDateTime that increments from the
    previous value by a base increment + optional random jitter.

    Example:
        gen = DateGenerator("2025-01-01T00:00:00Z", increment=timedelta(seconds=60))
        gen.get()  # 2025-01-01T00:00:00Z
        gen.get()  # 2025-01-01T00:01:00Z
        gen.get()  # 2025-01-01T00:02:00Z
    """

    def __init__(
        self,
        start: Optional[datetime | str | IsoDateTime] = None,
        *,
        increment: timedelta | float | None,
        jitter_percent: float | None = None,
        seed: int | None = None,
    ):
        """
        Args:
            start: starting timestamp. If None, uses IsoDateTime.now().
            increment: the base step.
            jitter: optional absolute jitter (± jitter).
            jitter_percent: jitter as percentage of increment (e.g., 0.1 = ±10%).
            seed: optional random seed for reproducible sequences.
        """
        if seed is not None:
            random.seed(seed)

        if start is None:
            start = IsoDateTime.now()
        else:
            start = IsoDateTime.normalize_value(start)

        self.current = start
        self.increment = increment if isinstance(increment, timedelta) else timedelta(seconds=increment or 1)

        self.jitter_percent = jitter_percent or 0.1
        self.jitter = self.jitter_percent * self.increment

    # --------------------------------------------------------
    # Internal helper
    # --------------------------------------------------------
    def _compute_jitter(self) -> timedelta:
        """
        Compute random jitter in the interval [-jitter, +jitter].
        """
        if self.jitter is None:
            return timedelta(0)

        # jitter.total_seconds() * uniform(-1, 1)
        seconds = self.jitter.total_seconds() * random.uniform(-1, 1)
        return timedelta(seconds=seconds)

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------
    def get(self) -> IsoDateTime:
        """
        Returns the current date, then increments it.
        """
        out = self.current

        # Compute next timestamp
        new_dt = out + self.increment + self._compute_jitter()

        # Always return IsoDateTime
        self.current = IsoDateTime.normalize_value(new_dt)
        return out

    def peek(self) -> IsoDateTime:
        """
        Preview the next value without advancing the generator.
        """
        return IsoDateTime.normalize_value(self.current + self.increment + self._compute_jitter())

    def reset(self, new_start: datetime | str | IsoDateTime):
        """
        Reset the internal clock.
        """
        self.current = IsoDateTime.normalize_value(new_start)

    def __iter__(self):
        """Allows: for t in gen: ..."""
        while True:
            yield self.get()


# ----------------------------------------------------------------------
# Main test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    here = "dategen.test"
    date_gen = DateGenerator(start="2025", increment=36000, jitter_percent=0.3)
    log_d(here, date_gen.get())
    log_d(here, date_gen.get())
    log_d(here, date_gen.get())
    log_d(here, date_gen.get())
    log_d(here, date_gen.get())
    log_d(here, date_gen.get())
    log_d(here, date_gen.get())
    log_d(here, date_gen.get())
    log_d(here, date_gen.get())
    log_d(here, date_gen.get())
    log_d(here, date_gen.get())
