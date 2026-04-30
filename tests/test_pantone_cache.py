"""Tests for Pantone override Redis cache layer."""

from __future__ import annotations

from unittest.mock import MagicMock

from siftpdf.profiles.icc.pantone_cache import (
    get_overrides,
    invalidate,
    set_overrides,
)

_SAMPLE_OVERRIDES = {
    "PANTONE 485 C": {"lab": [51.27, 73.08, 63.24], "cmyk_bridge": [0, 91, 100, 0]},
    "PANTONE 286 C": {"lab": [27.86, 17.24, -58.96], "cmyk_bridge": [100, 66, 0, 2]},
}


class TestGetOverrides:
    def test_returns_none_when_redis_is_none(self):
        assert get_overrides(None, "tenant-1") is None

    def test_returns_none_on_cache_miss(self):
        redis = MagicMock()
        redis.get.return_value = None
        assert get_overrides(redis, "tenant-1") is None

    def test_returns_data_on_cache_hit(self):
        import json

        redis = MagicMock()
        redis.get.return_value = json.dumps(_SAMPLE_OVERRIDES)
        result = get_overrides(redis, "tenant-1")
        assert result == _SAMPLE_OVERRIDES

    def test_returns_none_on_redis_error(self):
        redis = MagicMock()
        redis.get.side_effect = ConnectionError("Connection refused")
        assert get_overrides(redis, "tenant-1") is None


class TestSetOverrides:
    def test_noop_when_redis_is_none(self):
        set_overrides(None, "tenant-1", _SAMPLE_OVERRIDES)  # should not raise

    def test_calls_setex_with_correct_args(self):
        import json

        redis = MagicMock()
        set_overrides(redis, "tenant-1", _SAMPLE_OVERRIDES)
        redis.setex.assert_called_once()
        args = redis.setex.call_args[0]
        assert args[0] == "pantone_overrides:tenant-1"
        assert args[1] == 3600
        assert json.loads(args[2]) == _SAMPLE_OVERRIDES

    def test_silently_handles_redis_error(self):
        redis = MagicMock()
        redis.setex.side_effect = ConnectionError("Connection refused")
        set_overrides(redis, "tenant-1", _SAMPLE_OVERRIDES)  # should not raise


class TestInvalidate:
    def test_noop_when_redis_is_none(self):
        invalidate(None, "tenant-1")  # should not raise

    def test_calls_delete_with_correct_key(self):
        redis = MagicMock()
        invalidate(redis, "tenant-1")
        redis.delete.assert_called_once_with("pantone_overrides:tenant-1")

    def test_silently_handles_redis_error(self):
        redis = MagicMock()
        redis.delete.side_effect = ConnectionError("Connection refused")
        invalidate(redis, "tenant-1")  # should not raise


class TestCacheRoundTrip:
    def test_set_then_get_returns_same_data(self):
        """Simulates full round-trip: set → get returns the same overrides."""

        store: dict[str, str] = {}

        redis = MagicMock()
        redis.setex.side_effect = lambda key, ttl, value: store.__setitem__(key, value)
        redis.get.side_effect = lambda key: store.get(key)

        set_overrides(redis, "tenant-1", _SAMPLE_OVERRIDES)
        result = get_overrides(redis, "tenant-1")
        assert result == _SAMPLE_OVERRIDES

    def test_invalidate_clears_cache(self):
        """After invalidation, get returns None."""
        store: dict[str, str] = {}

        redis = MagicMock()
        redis.setex.side_effect = lambda key, ttl, value: store.__setitem__(key, value)
        redis.get.side_effect = lambda key: store.get(key)
        redis.delete.side_effect = lambda key: store.pop(key, None)

        set_overrides(redis, "tenant-1", _SAMPLE_OVERRIDES)
        invalidate(redis, "tenant-1")
        result = get_overrides(redis, "tenant-1")
        assert result is None
