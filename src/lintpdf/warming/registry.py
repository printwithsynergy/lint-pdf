"""Warmer registry + public API for the wake-on-need pattern.

Kept intentionally tiny:

* :class:`WarmSpec` — how to probe / wake one dependency.
* :data:`WARMERS` — registry populated at import time from env vars
  so adding or removing a service is an env-config change, not a
  code edit.
* :func:`ensure_warm` — fire-and-forget parallel pings; returns
  immediately (the caller continues with its own work).
* :func:`ensure_warm_sync` — bounded-wait version that blocks until
  every probe returns 200 or the budget elapses. Use sparingly
  (only for paths where proceeding without the dependency warm
  would be worse than the wall-clock wait).
"""

from __future__ import annotations

import logging
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WarmSpec:
    """How to wake one scale-to-zero dependency.

    * ``name`` — stable key callers reference (e.g. ``"audit"``).
    * ``probe_url`` — cheap GET endpoint. Returning 200 means the
      container is warm; 5xx / timeout means cold (wake it).
    * ``method`` / ``wake_payload`` — how to hit the service when it
      needs waking. Modal / Railway both wake on any inbound HTTP,
      so GET a health endpoint is usually enough; POST with an
      empty payload works for services without a GET ready path.
    * ``timeout_s`` — socket timeout for the probe. Too low and a
      slow-but-warm container false-positives as cold; too high
      and the caller's fire-and-forget thread dangles longer than
      necessary.
    * ``enabled`` — flip to False when the dep is disabled by env
      (e.g. `LINTPDF_SIMILARITY_MODAL_URL` unset → similarity
      warmer skipped).
    """

    name: str
    probe_url: str
    method: str = "GET"
    wake_payload: bytes | None = None
    timeout_s: float = 3.0
    enabled: bool = True
    # Optional hook that runs just before the probe fires — lets a
    # spec lazily rebuild its URL from env (useful for Modal URLs
    # that only show up after a deploy).
    resolve: Callable[[], WarmSpec | None] | None = field(default=None, compare=False)


def _similarity_spec() -> WarmSpec | None:
    # The one Modal survivor after the wholesale Claude pivot:
    # OpenCLIP embedding for the duplicate-detector inspector.
    url = os.environ.get("LINTPDF_SIMILARITY_MODAL_URL")
    if not url:
        return None
    return WarmSpec(
        name="similarity",
        probe_url=url.rstrip("/") + "/ready",
        method="GET",
        timeout_s=3.0,
    )


def _engine_spec() -> WarmSpec | None:
    # The engine itself is the caller in Celery tasks, but the
    # ingress service (when split) will need to warm the engine on
    # admin calls. Derived from LINTPDF_ENGINE_INTERNAL_URL so only
    # deployments that have the ingress/engine split surface this
    # spec — single-service deploys skip it.
    url = os.environ.get("LINTPDF_ENGINE_INTERNAL_URL")
    if not url:
        return None
    return WarmSpec(
        name="engine",
        probe_url=url.rstrip("/") + "/ready",
        method="GET",
        timeout_s=3.0,
    )


def _initial_registry() -> dict[str, WarmSpec]:
    out: dict[str, WarmSpec] = {}
    for factory in (_similarity_spec, _engine_spec):
        spec = factory()
        if spec is not None:
            out[spec.name] = spec
    return out


WARMERS: dict[str, WarmSpec] = _initial_registry()


def register(spec: WarmSpec) -> None:
    """Add / overwrite a ``WarmSpec`` at runtime.

    Exists so tests + one-off scripts can inject a custom warmer
    without patching the module state directly.
    """
    WARMERS[spec.name] = spec


def _probe(spec: WarmSpec) -> int:
    """Issue one probe, return the HTTP status (0 on transport fail)."""
    try:
        req = urllib.request.Request(
            spec.probe_url,
            method=spec.method,
            data=spec.wake_payload,
            headers=({"Content-Type": "application/json"} if spec.wake_payload is not None else {}),
        )
        with urllib.request.urlopen(req, timeout=spec.timeout_s) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(getattr(exc, "code", 0))
    except Exception:
        return 0


def ensure_warm(names: list[str]) -> None:
    """Fire a fire-and-forget warm-up probe for each name in ``names``.

    Returns immediately. Each probe runs in its own daemon thread
    so the caller's main thread never blocks. The probe's purpose
    is to make the dependency *start* warming; the actual request
    the caller is about to fire may still wait briefly, but the
    container boot happens in parallel with the caller's own work
    between now and the real call.

    Unknown names are silently skipped — not an error because the
    caller doesn't know which deps are configured on this
    deployment (e.g. the ingress/engine split is only live on
    some envs).
    """
    for name in names:
        spec = WARMERS.get(name)
        if spec is None or not spec.enabled:
            continue
        thread = threading.Thread(
            target=_probe,
            args=(spec,),
            daemon=True,
            name=f"warm-{name}",
        )
        thread.start()
        logger.debug("warm: fired probe for %s → %s", name, spec.probe_url)


def ensure_warm_sync(names: list[str], *, budget_s: float = 30.0) -> dict[str, int]:
    """Block until every dependency reports 2xx or the budget elapses.

    Returns a ``{name: status}`` map so the caller can log failures.
    Use for paths where running the real call without the dep warm
    would waste more wall clock than waiting here.
    """
    deadline = time.monotonic() + budget_s
    results: dict[str, int] = {}
    remaining = {
        name: spec
        for name, spec in ((n, WARMERS.get(n)) for n in names)
        if spec is not None and spec.enabled
    }

    while remaining and time.monotonic() < deadline:
        for name, spec in list(remaining.items()):
            code = _probe(spec)
            if 200 <= code < 300:
                results[name] = code
                remaining.pop(name)
        if remaining:
            # Second-level back-off — Modal cold starts take ~60 s
            # for Qwen2-VL; polling every 2 s avoids hammering.
            time.sleep(min(2.0, max(0.0, deadline - time.monotonic())))

    for name in remaining:
        results[name] = 0
    return results
