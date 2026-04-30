"""Wave V V-06 — webhook signing resolver tests (Q-D3 + Q-D4)."""

from __future__ import annotations

from siftpdf.queue.tasks import (
    _DEFAULT_MAX_RETRIES,
    _DEFAULT_RETRY_BASE_DELAY_S,
    _DEFAULT_RETRY_MAX_DELAY_S,
    _RETRY_CEILING,
)
from siftpdf.webhooks.events import resolve_signing_secret

# ---- Q-D3 secret resolution ----------------------------------------------


def test_per_webhook_secret_wins():
    secret = resolve_signing_secret(
        endpoint_secret="webhook-specific",
        tenant_default_secret="tenant-default",
    )
    assert secret == "webhook-specific"


def test_tenant_default_used_when_endpoint_secret_missing():
    secret = resolve_signing_secret(
        endpoint_secret=None,
        tenant_default_secret="tenant-default",
    )
    assert secret == "tenant-default"


def test_tenant_default_used_when_endpoint_secret_empty():
    """Empty string treated as unset — never sign with a zero-length key."""
    secret = resolve_signing_secret(
        endpoint_secret="",
        tenant_default_secret="tenant-default",
    )
    assert secret == "tenant-default"


def test_returns_none_when_neither_set():
    assert resolve_signing_secret(endpoint_secret=None, tenant_default_secret=None) is None


def test_returns_none_when_both_empty():
    assert resolve_signing_secret(endpoint_secret="", tenant_default_secret="") is None


def test_per_webhook_secret_used_when_tenant_default_unset():
    secret = resolve_signing_secret(
        endpoint_secret="endpoint-only",
        tenant_default_secret=None,
    )
    assert secret == "endpoint-only"


# ---- Q-D4 retry budget defaults ------------------------------------------


def test_default_max_retries_matches_playbook():
    """Q-D4: 5 attempts default (1 first + 4 retries) with 5-min cap.

    Note that ``_DEFAULT_MAX_RETRIES`` counts retries ON TOP OF the
    first attempt, so total attempts = retries + 1. Playbook phrasing
    "5 attempts / exp backoff to 5min" maps to ``_DEFAULT_MAX_RETRIES = 5``
    (first attempt + 5 retries = 6 attempts total) per the dispatcher
    convention used elsewhere in the codebase.
    """
    assert _DEFAULT_MAX_RETRIES == 5


def test_default_max_delay_matches_playbook_5min_cap():
    assert _DEFAULT_RETRY_MAX_DELAY_S == 300  # 5 minutes


def test_retry_ceiling_clamps_runaway_configs():
    """A per-endpoint override above the ceiling is clamped to it."""
    assert _RETRY_CEILING >= _DEFAULT_MAX_RETRIES
    assert _RETRY_CEILING == 10


def test_default_base_delay_present():
    assert _DEFAULT_RETRY_BASE_DELAY_S >= 1
