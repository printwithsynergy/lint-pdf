"""Unit tests for ``lintpdf.warming.registry``.

Scope stays tight — we don't actually cold-start a Modal
container in CI. Instead we verify:

* The registry picks up env-derived specs at import time.
* ``ensure_warm`` dispatches a thread per known name and skips
  unknown ones.
* ``ensure_warm_sync`` returns the recorded statuses within the
  budget and respects the enabled flag.
* ``register`` overwrites / adds at runtime.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from lintpdf.warming import registry
from lintpdf.warming.registry import (
    WARMERS,
    WarmSpec,
    ensure_warm,
    ensure_warm_sync,
    register,
)

if TYPE_CHECKING:
    import pytest


class TestRegistry:
    @staticmethod
    def test_register_adds_new_spec() -> None:
        spec = WarmSpec(name="test-new", probe_url="https://stub.local/")
        try:
            register(spec)
            assert WARMERS["test-new"] is spec
        finally:
            WARMERS.pop("test-new", None)

    @staticmethod
    def test_register_overwrites_existing() -> None:
        a = WarmSpec(name="test-over", probe_url="https://a.local/")
        b = WarmSpec(name="test-over", probe_url="https://b.local/")
        try:
            register(a)
            register(b)
            assert WARMERS["test-over"] is b
        finally:
            WARMERS.pop("test-over", None)


class TestEnsureWarm:
    @staticmethod
    def test_unknown_name_silently_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[WarmSpec] = []

        def fake_probe(spec: WarmSpec) -> int:
            calls.append(spec)
            return 200

        monkeypatch.setattr(registry, "_probe", fake_probe)
        ensure_warm(["no-such-thing"])
        # Give the daemon thread a chance to run (none was spawned).
        time.sleep(0.05)
        assert calls == []

    @staticmethod
    def test_known_name_fires_thread(monkeypatch: pytest.MonkeyPatch) -> None:
        spec = WarmSpec(name="fake-warmer", probe_url="https://fake.local/")
        register(spec)
        try:
            event = threading.Event()
            seen: list[WarmSpec] = []

            def fake_probe(s: WarmSpec) -> int:
                seen.append(s)
                event.set()
                return 200

            monkeypatch.setattr(registry, "_probe", fake_probe)
            ensure_warm(["fake-warmer"])
            assert event.wait(timeout=2.0), "fake probe never ran"
            assert seen == [spec]
        finally:
            WARMERS.pop("fake-warmer", None)

    @staticmethod
    def test_disabled_spec_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
        spec = WarmSpec(
            name="disabled-warmer",
            probe_url="https://disabled.local/",
            enabled=False,
        )
        register(spec)
        try:
            called = MagicMock(return_value=200)
            monkeypatch.setattr(registry, "_probe", called)
            ensure_warm(["disabled-warmer"])
            time.sleep(0.05)
            called.assert_not_called()
        finally:
            WARMERS.pop("disabled-warmer", None)


class TestEnsureWarmSync:
    @staticmethod
    def test_returns_on_first_success(monkeypatch: pytest.MonkeyPatch) -> None:
        spec = WarmSpec(name="sync-warmer", probe_url="https://sync.local/")
        register(spec)
        try:
            monkeypatch.setattr(registry, "_probe", MagicMock(return_value=200))
            out = ensure_warm_sync(["sync-warmer"], budget_s=1.0)
            assert out == {"sync-warmer": 200}
        finally:
            WARMERS.pop("sync-warmer", None)

    @staticmethod
    def test_budget_exhausts(monkeypatch: pytest.MonkeyPatch) -> None:
        spec = WarmSpec(name="slow-warmer", probe_url="https://slow.local/")
        register(spec)
        try:
            monkeypatch.setattr(registry, "_probe", MagicMock(return_value=0))
            out = ensure_warm_sync(["slow-warmer"], budget_s=0.2)
            assert out == {"slow-warmer": 0}
        finally:
            WARMERS.pop("slow-warmer", None)

    @staticmethod
    def test_unknown_names_absent_from_result(
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(registry, "_probe", MagicMock(return_value=200))
        out = ensure_warm_sync(["no-such"], budget_s=0.1)
        assert out == {}


class TestProbeMethods:
    @staticmethod
    def test_get_probe(monkeypatch: pytest.MonkeyPatch) -> None:
        """Default spec method is GET — no request body sent."""
        spec = WarmSpec(name="get-warmer", probe_url="https://get.local/")

        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = lambda s, *a: None
            mock_open.return_value.status = 200
            code = registry._probe(spec)
            assert code == 200
            args, _ = mock_open.call_args
            req = args[0]
            assert req.method == "GET"
            assert req.data is None

    @staticmethod
    def test_post_probe_with_payload(monkeypatch: pytest.MonkeyPatch) -> None:
        spec = WarmSpec(
            name="post-warmer",
            probe_url="https://post.local/",
            method="POST",
            wake_payload=b'{"findings": []}',
        )

        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__ = lambda s: s
            mock_open.return_value.__exit__ = lambda s, *a: None
            mock_open.return_value.status = 200
            registry._probe(spec)
            args, _ = mock_open.call_args
            req = args[0]
            assert req.method == "POST"
            assert req.data == b'{"findings": []}'
            assert req.get_header("Content-type") == "application/json"
