"""Unit tests for ``siftpdf.audit.outage``.

Uses ``fakeredis`` when available (optional test dep); otherwise the
module's fail-open guard kicks in and the tests assert that
recorded outcomes stay invisible (``is_outage() == False``) when
Redis is unreachable.
"""

from __future__ import annotations

from unittest.mock import patch

from siftpdf.audit import outage


class _MemoryRedis:
    """Minimum viable Redis stand-in for the three commands we use."""

    def __init__(self) -> None:
        self._lists: dict[str, list[str]] = {}
        self._kv: dict[str, str] = {}

    # pipeline ------------------------------------------------------

    def pipeline(self) -> _MemoryRedis:
        return self

    def execute(self) -> None:
        return None

    # list ops ------------------------------------------------------

    def lpush(self, key: str, value: str) -> None:
        self._lists.setdefault(key, []).insert(0, value)

    def ltrim(self, key: str, start: int, stop: int) -> None:
        self._lists[key] = self._lists.get(key, [])[start : stop + 1]

    def lrange(self, key: str, start: int, stop: int) -> list[str]:
        return self._lists.get(key, [])[start : stop + 1]

    # kv ops --------------------------------------------------------

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._kv[key] = value

    def get(self, key: str) -> str | None:
        return self._kv.get(key)

    def delete(self, key: str) -> None:
        self._kv.pop(key, None)


def _install_memory_redis() -> _MemoryRedis:
    client = _MemoryRedis()
    outage._redis_client._cached = client  # type: ignore[attr-defined]
    return client


def _reset() -> None:
    outage._redis_client._cached = None  # type: ignore[attr-defined]


class TestOutage:
    @staticmethod
    def test_fail_open_without_redis() -> None:
        """With no client, record is a no-op and is_outage returns False."""
        _reset()
        with patch.object(outage, "_redis_client", return_value=None):
            outage.record_outcome(False)
            assert outage.is_outage() is False

    @staticmethod
    def test_healthy_window_stays_ok() -> None:
        _install_memory_redis()
        for _ in range(20):
            outage.record_outcome(True)
        assert outage.is_outage() is False
        _reset()

    @staticmethod
    def test_window_degrades_above_threshold() -> None:
        _install_memory_redis()
        # 11 fails + 9 passes in the last 20 calls → over threshold.
        for _ in range(9):
            outage.record_outcome(True)
        for _ in range(11):
            outage.record_outcome(False)
        assert outage.is_outage() is True
        _reset()

    @staticmethod
    def test_window_recovers_when_successes_push_failures_off() -> None:
        _install_memory_redis()
        # Seed with 11 failures — window fills with oldest entries at the tail.
        for _ in range(11):
            outage.record_outcome(False)
        for _ in range(9):
            outage.record_outcome(True)
        assert outage.is_outage() is True  # Still degraded — window has 11 fails.
        # Now push 11 more successes — failures fall off the tail.
        for _ in range(11):
            outage.record_outcome(True)
        assert outage.is_outage() is False
        _reset()

    @staticmethod
    def test_partial_window_does_not_flag() -> None:
        """Under 20 samples, degraded signal is withheld."""
        _install_memory_redis()
        for _ in range(5):
            outage.record_outcome(False)
        assert outage.is_outage() is False
        _reset()

    @staticmethod
    def test_override_pins_state_on_and_off() -> None:
        _install_memory_redis()
        outage.override(True)
        assert outage.is_outage() is True
        outage.override(False)
        assert outage.is_outage() is False
        _reset()
