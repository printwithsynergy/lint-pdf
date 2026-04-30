"""Bridge: download the tenant's active ICC profile to a tempfile so the
EPM-A1 analyzer can route through ``is_in_gamut_for_profile`` at job
time.

The dashboard upload (``POST /api/v1/icc-profiles/active``) writes the
profile bytes into object storage at
``icc-profiles/{tenant_id}/active.icc``. The orchestrator's analyzer
takes a filesystem path. This module is the bridge: it pulls bytes
from storage, writes them to a tempfile, and yields the path. The
caller (``run_preflight`` Celery task) wraps orchestrator.run() in
the context manager so the tempfile is unlinked after the run
completes — even on failure.

A missing slot (no upload ever, or the bytes were deleted) yields
``None`` and the analyzer falls back to its default heuristic.
"""

from __future__ import annotations

import contextlib
import logging
import os
import tempfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from siftpdf.api.storage import StorageBackend


logger = logging.getLogger(__name__)


def _key_for(tenant_id: object) -> str:
    return f"icc-profiles/{tenant_id}/active.icc"


@contextlib.contextmanager
def resolve_active_icc_profile(
    tenant_id: object,
    storage: StorageBackend,
) -> Iterator[str | None]:
    """Yield a filesystem path to the tenant's active ICC profile, or None.

    Best-effort: any storage error or missing key yields None and the
    analyzer falls back to the saturated-CMYK heuristic. The tempfile
    is always cleaned up on exit, even on exception.
    """
    key = _key_for(tenant_id)
    content: bytes | None
    try:
        content = storage.download_raw(key)
    except Exception:
        logger.debug(
            "ICC profile resolve: storage.download_raw failed for tenant %s",
            tenant_id,
            exc_info=True,
        )
        content = None

    if not content:
        yield None
        return

    fd, path = tempfile.mkstemp(suffix=".icc", prefix=f"lintpdf-icc-{tenant_id}-")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(content)
        yield path
    finally:
        with contextlib.suppress(OSError):
            os.unlink(path)


__all__ = ["resolve_active_icc_profile"]
