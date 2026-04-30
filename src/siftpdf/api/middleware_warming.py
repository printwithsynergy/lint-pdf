"""Wake-on-need middleware.

Inspects the incoming request path and fires fire-and-forget warm-up
probes at scale-to-zero dependencies that the matched handler is
about to touch. By the time the handler actually makes its
downstream call, Modal / engine containers are already warming in
parallel with the handler's own work (R2 upload, DB insert, Celery
dispatch).

Routes → warmers mapping is a coarse path-prefix table so the
middleware stays O(1) per request; fine-grained control (e.g.
"only warm audit if the tenant is entitled") sits further in at
the handler level where the tenant context already resolves.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request
    from starlette.responses import Response

logger = logging.getLogger(__name__)


# Path-prefix → warmer-name map. Longest prefix wins. Entries only
# cover handlers that (a) actually touch a scale-to-zero dep on
# their critical path and (b) benefit from the ~60-90 s head start.
# Read-only status / health / list endpoints intentionally skip —
# they don't need Modal and firing a warmer on every `/ready` poll
# would burn a container unnecessarily.
_PATH_WARMERS: list[tuple[str, list[str]]] = [
    # Preflight submit — the job will hit the AI inference app and
    # (for entitled tenants) the audit app at the tail of the task.
    # Kick both now so they're warm by the time the deterministic
    # engine phase finishes.
    ("/api/v1/jobs", ["inference", "audit"]),
    ("/api/v1/batch/submit", ["inference", "audit"]),
    ("/api/v1/endpoints/", ["inference", "audit"]),
    ("/api/v1/trial/submit", ["inference", "audit"]),
    # Explicit audit rerun — the endpoint itself IS the caller that
    # hits Modal audit, so wake it before the handler runs.
    ("/api/v1/jobs/", ["audit"]),  # matches /jobs/{id}/audit:rerun + detail reads
    # AI configuration endpoints sometimes call the inference app
    # to validate credentials / logos.
    ("/api/v1/ai/", ["inference"]),
]


class WakeOnNeedMiddleware(BaseHTTPMiddleware):
    """Fire warm-up probes for scale-to-zero deps on matching routes."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path or ""
        # Only POSTs to submit endpoints kick warmers — read paths
        # don't benefit and would churn Modal.
        if request.method == "POST":
            warmers = self._resolve(path)
            if warmers:
                try:
                    from siftpdf.warming import ensure_warm

                    ensure_warm(warmers)
                except Exception:  # pragma: no cover — warmers never fail requests
                    logger.exception("warm: ensure_warm threw inside middleware")
        return await call_next(request)

    @staticmethod
    def _resolve(path: str) -> list[str]:
        best_prefix = ""
        best_names: list[str] = []
        for prefix, names in _PATH_WARMERS:
            if path.startswith(prefix) and len(prefix) > len(best_prefix):
                best_prefix = prefix
                best_names = names
        return best_names
