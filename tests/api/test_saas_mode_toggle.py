"""W5a — `LINTPDF_SAAS_MODE` toggle + import-tolerance regression tests.

These tests verify the three states the deployment-surface gate
supports:

1. ``LINTPDF_SAAS_MODE=true`` + SaaS modules importable (the hosted
   default) — every router is mounted.
2. ``LINTPDF_SAAS_MODE=false`` (explicit OSS deploy) — only the
   engine-surface routers are mounted.
3. ``LINTPDF_SAAS_MODE=true`` requested but SaaS modules absent
   (post-W5-physical-extraction OSS install) — the runtime falls
   back to OSS surface and logs a warning.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


def _route_paths(app) -> set[str]:
    """Collect every mounted route path."""
    return {getattr(r, "path", "") for r in app.routes}


# OSS-always routes that must be mounted regardless of SAAS_MODE.
_OSS_ALWAYS_ROUTES = (
    "/health",
    "/ready",
    "/api/v1/jobs",
    "/api/v1/profiles",
)

# SaaS-only routes that must NOT mount when SAAS_MODE=false (or when
# the SaaS-only modules aren't importable). Use prefixes from routers
# that are still physically in OSS (admin, trial) — pre-W5-physical
# extractions like admin_health were moved to lint-pdf-saas, so
# checking those prefixes from inside a unit test on the OSS package
# would always fail.
_SAAS_ONLY_ROUTES = (
    "/api/v1/admin",
    "/api/v1/trial",
)


@pytest.fixture
def _reset_app_module(monkeypatch):
    """Force a fresh import of ``lintpdf.api.app`` so module-level
    branches re-evaluate against the current env."""
    import sys

    # Drop the cached module so the import block runs again.
    sys.modules.pop("lintpdf.api.app", None)
    yield
    sys.modules.pop("lintpdf.api.app", None)


def test_default_saas_mode_mounts_everything(_reset_app_module, monkeypatch):
    monkeypatch.delenv("LINTPDF_SAAS_MODE", raising=False)

    from lintpdf.api.app import create_app

    app = create_app()
    paths = _route_paths(app)

    for route in _OSS_ALWAYS_ROUTES:
        assert any(p.startswith(route) for p in paths), (
            f"OSS-always route {route!r} should be mounted in default mode"
        )

    # At least one SaaS-only route should be present in default mode.
    assert any(any(p.startswith(r) for p in paths) for r in _SAAS_ONLY_ROUTES), (
        "default LINTPDF_SAAS_MODE should mount SaaS-only routes"
    )


def test_explicit_oss_mode_skips_saas_routes(_reset_app_module, monkeypatch):
    monkeypatch.setenv("LINTPDF_SAAS_MODE", "false")

    from lintpdf.api.app import create_app

    app = create_app()
    paths = _route_paths(app)

    for route in _OSS_ALWAYS_ROUTES:
        assert any(p.startswith(route) for p in paths), (
            f"OSS-always route {route!r} should be mounted in OSS mode"
        )

    for route in _SAAS_ONLY_ROUTES:
        assert not any(p.startswith(route) for p in paths), (
            f"SaaS-only route {route!r} must NOT mount when LINTPDF_SAAS_MODE=false"
        )


def test_missing_saas_modules_fallback_to_oss(_reset_app_module, monkeypatch, caplog):
    """W5 post-extraction simulation: SAAS_MODE=true requested but
    the SaaS-only route modules aren't importable. The engine must
    fall back to OSS surface and log a clear warning rather than
    failing to boot.
    """
    monkeypatch.setenv("LINTPDF_SAAS_MODE", "true")

    # Import once to load defaults, then force the availability flag
    # to False as if the modules were physically absent.
    import lintpdf.api.app as app_mod

    with (
        patch.object(app_mod, "_SAAS_ROUTES_AVAILABLE", False),
        patch.object(app_mod, "_SAAS_IMPORT_ERROR", "simulated post-extraction"),
        caplog.at_level("WARNING", logger="lintpdf.api.app"),
    ):
        app = app_mod.create_app()

    paths = _route_paths(app)

    for route in _OSS_ALWAYS_ROUTES:
        assert any(p.startswith(route) for p in paths), (
            f"OSS-always route {route!r} should still mount when SaaS modules are absent"
        )

    for route in _SAAS_ONLY_ROUTES:
        assert not any(p.startswith(route) for p in paths), (
            f"SaaS-only route {route!r} must NOT mount when SaaS modules are absent"
        )

    # The fallback warning is the user-visible signal.
    assert any(
        "SaaS-only route modules are unavailable" in rec.message for rec in caplog.records
    ), "expected a fallback warning when SAAS_MODE=true but modules absent"
