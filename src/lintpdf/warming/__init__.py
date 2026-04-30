"""System-wide cold-start warmer registry.

Every scale-to-zero dependency the platform talks to registers a
``WarmSpec`` here. Callers that are about to need one of them call
:func:`ensure_warm` before starting their own heavy work; the
warmer fires a fire-and-forget HTTPS probe at each spec, which
Modal / Railway see as an incoming request and use to start pulling
a container. By the time the caller's own critical path reaches
the dependency, the container is warming / warm, so the cold-start
tax lands *in parallel* with work the caller was going to do anyway.

## Why not just call the endpoint?

The real first call still cold-starts the container. Firing the
warm-up earlier in the caller's pipeline just shifts where the
90-second boot sits relative to other work — if the caller has 5
minutes of deterministic preflight to do, kicking the warm-up at
second 0 means the container is warm by the time the AI phase
starts at second 300.

## Registry

Single source of truth. Tests + docs + ops runbooks all key off
this dict. Adding a new scale-to-zero service means one entry.
"""

from __future__ import annotations

from lintpdf.warming.registry import (
    WARMERS,
    WarmSpec,
    ensure_warm,
    ensure_warm_sync,
    register,
)

__all__ = [
    "WARMERS",
    "WarmSpec",
    "ensure_warm",
    "ensure_warm_sync",
    "register",
]
