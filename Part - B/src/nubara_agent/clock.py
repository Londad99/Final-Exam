from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol
import time


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class ReplayClock:
    """Start at the exam timestamp and advance monotonically so TTLs really expire."""

    def __init__(self, at: datetime):
        self._at = at
        self._start = time.monotonic()

    def now(self) -> datetime:
        return self._at + timedelta(seconds=time.monotonic() - self._start)


class FixedClock:
    """Deterministic clock for demos and tests."""

    def __init__(self, at: datetime) -> None:
        self._at = at

    def now(self) -> datetime:
        return self._at

    def advance(self, seconds: float) -> None:
        self._at += timedelta(seconds=seconds)
