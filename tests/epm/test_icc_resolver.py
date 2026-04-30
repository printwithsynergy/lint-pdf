"""Tests for ``siftpdf.epm.icc_resolver.resolve_active_icc_profile``.

The resolver bridges object-storage (where the dashboard upload lands)
to the orchestrator's analyzer layer (which takes a filesystem path).
Behaviours pinned here:

* a missing slot yields ``None`` (analyzer falls back to heuristic),
* a populated slot yields a path whose bytes match what storage holds,
* the tempfile is unlinked on context exit even if the caller raised,
* a flaky storage backend yields ``None`` and does not propagate.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from siftpdf.epm.icc_resolver import resolve_active_icc_profile


class _StubStorage:
    """Just enough of ``StorageBackend`` for the resolver."""

    def __init__(self, payload: bytes | None = None, raise_on_download: bool = False) -> None:
        self._payload = payload
        self._raise = raise_on_download
        self.downloaded_keys: list[str] = []

    def download_raw(self, key: str) -> bytes:
        self.downloaded_keys.append(key)
        if self._raise:
            raise RuntimeError("simulated storage flake")
        if self._payload is None:
            raise FileNotFoundError(key)
        return self._payload


def test_missing_slot_yields_none() -> None:
    storage = _StubStorage(payload=None)
    with resolve_active_icc_profile("tenant-abc", storage) as path:
        assert path is None
    # The resolver must have asked storage with the canonical key shape.
    assert storage.downloaded_keys == ["icc-profiles/tenant-abc/active.icc"]


def test_storage_error_yields_none() -> None:
    storage = _StubStorage(raise_on_download=True)
    with resolve_active_icc_profile("tenant-abc", storage) as path:
        assert path is None


def test_populated_slot_yields_tempfile_with_bytes() -> None:
    payload = bytes(range(64))
    storage = _StubStorage(payload=payload)
    yielded_path: str | None = None
    with resolve_active_icc_profile("tenant-xyz", storage) as path:
        assert path is not None
        yielded_path = path
        assert Path(path).read_bytes() == payload
        # Tempfile naming pattern: lintpdf-icc-<tenant>-…icc
        assert "lintpdf-icc-tenant-xyz-" in os.path.basename(path)
        assert path.endswith(".icc")
    # Cleanup happened on exit.
    assert yielded_path is not None
    assert not Path(yielded_path).exists()


def test_tempfile_cleaned_up_when_caller_raises() -> None:
    payload = b"\x00" * 32
    storage = _StubStorage(payload=payload)
    captured_path: str | None = None
    with (
        pytest.raises(RuntimeError, match="boom"),
        resolve_active_icc_profile("tenant-raise", storage) as path,
    ):
        assert path is not None
        captured_path = path
        raise RuntimeError("boom")
    assert captured_path is not None
    assert not Path(captured_path).exists()


def test_empty_payload_treated_as_missing() -> None:
    storage = _StubStorage(payload=b"")
    with resolve_active_icc_profile("tenant-empty", storage) as path:
        assert path is None
