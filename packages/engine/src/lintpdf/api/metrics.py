"""Prometheus metrics endpoint + per-request instrumentation.

Bulk-files step 11. Exposes four counters/histograms that cover the
bulk-files-scale observability gap CLAUDE.md called out:

- ``lintpdf_http_requests_total{method, path_template, status}`` —
  raw request counter; catches 5xx spikes + route-level traffic.
- ``lintpdf_http_request_duration_seconds{method, path_template}`` —
  histogram for p50/p90/p99 latency by route.
- ``lintpdf_uploads_in_flight`` — gauge of PDF uploads currently
  being streamed to R2. Tracks the memory pressure pattern that
  wedged tier-1 before the streaming fix.
- ``lintpdf_job_terminal_total{status}`` — counter of jobs reaching
  complete / failed terminal state, incremented by the worker.

The handler at ``GET /metrics`` is mounted unconditionally — even on
the control-plane-only service — so external scrapers (Grafana Cloud,
Prometheus, DataDog agent, etc.) always have a stable endpoint.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.types import ASGIApp, Receive, Scope, Send

if TYPE_CHECKING:
    from fastapi import FastAPI

# Module-level registry so tests can inspect + reset without monkeypatching
# the global prometheus_client.REGISTRY.
REGISTRY = CollectorRegistry(auto_describe=True)

# Default buckets cover 5ms → 30s — the useful dynamic range for HTTP
# + report-mint + admin calls. Upload endpoints can exceed 30s; they
# land in the +Inf bucket and trigger an "operations long tail" alert
# in the scraping stack rather than showing up as a discrete bucket.
_DEFAULT_BUCKETS = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0,
)

HTTP_REQUESTS = Counter(
    "lintpdf_http_requests_total",
    "HTTP request count labeled by method, path template, and status class.",
    labelnames=("method", "path_template", "status"),
    registry=REGISTRY,
)

HTTP_DURATION = Histogram(
    "lintpdf_http_request_duration_seconds",
    "HTTP request duration (seconds) from first-byte-in to last-byte-out.",
    labelnames=("method", "path_template"),
    buckets=_DEFAULT_BUCKETS,
    registry=REGISTRY,
)

UPLOADS_IN_FLIGHT = Gauge(
    "lintpdf_uploads_in_flight",
    "Number of PDF uploads currently being streamed through "
    "validate_upload_streaming. Use as the canonical memory-pressure signal.",
    registry=REGISTRY,
)

JOB_TERMINAL = Counter(
    "lintpdf_job_terminal_total",
    "Jobs reaching a terminal state, labeled by outcome.",
    labelnames=("status",),
    registry=REGISTRY,
)


class PrometheusMiddleware:
    """ASGI middleware that records request count + duration.

    Uses Starlette's resolved ``scope['route'].path`` (the path template
    with parameter placeholders, e.g. ``/api/v1/jobs/{job_id}``) so
    per-route cardinality stays bounded. Falls back to the raw path
    only when no route matched — that's 404 traffic we want to see.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_holder = {"code": 500}

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                status_holder["code"] = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - start
            route = scope.get("route")
            path_template = (
                getattr(route, "path", None) or scope.get("path", "/") or "/"
            )
            method = scope.get("method", "GET")
            code = status_holder["code"]
            status_class = f"{code // 100}xx"
            HTTP_REQUESTS.labels(method=method, path_template=path_template, status=status_class).inc()
            HTTP_DURATION.labels(method=method, path_template=path_template).observe(elapsed)


def mount_metrics(app: FastAPI) -> None:
    """Attach the middleware + /metrics route to a FastAPI app.

    Called from ``create_app()`` before router mount so every request
    is instrumented. The /metrics endpoint is plain text per the
    Prometheus exposition format; content type is
    ``text/plain; version=0.0.4; charset=utf-8``.
    """
    from fastapi import Response

    app.add_middleware(PrometheusMiddleware)

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )
