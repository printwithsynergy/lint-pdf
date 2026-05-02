"""Minimal fake Redis client used across rate-limit tests.

Originally lived inline in `tests/api/test_usage.py`; that module
was extracted to lintpdf_saas in W5g, so the helper now sits in a
neutral testutils location that any test in either repo can import.
"""

from __future__ import annotations


class FakeRedis:
    """Minimal fake Redis for rate-limiter tests.

    Implements the small subset the production rate limiter calls:
    ``get``, ``set`` (with ``nx`` + ``ex``), ``incr``, ``expire``,
    and the eval-script path the limiter uses for atomic
    increment-with-TTL.
    """

    def __init__(self) -> None:
        self._data: dict[str, int | str] = {}
        self._ttls: dict[str, int] = {}

    def get(self, key: str) -> int | str | None:
        return self._data.get(key)

    def set(self, key: str, value: str, *, nx: bool = False, ex: int | None = None) -> bool | None:
        if nx and key in self._data:
            return None
        self._data[key] = value
        if ex is not None:
            self._ttls[key] = ex
        return True

    def incr(self, key: str) -> int:
        self._data[key] = int(self._data.get(key, 0)) + 1
        return int(self._data[key])

    def expire(self, key: str, ttl: int) -> None:
        self._ttls[key] = ttl

    def eval(self, script: str, numkeys: int, *args: object) -> int:
        key = str(args[0])
        ttl = int(args[1])
        current = self.incr(key)
        if current == 1:
            self.expire(key, ttl)
        return current
