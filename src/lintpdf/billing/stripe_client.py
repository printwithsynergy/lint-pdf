"""Thin Stripe REST client used by the engine.

We don't use the ``stripe`` Python SDK because (a) it pulls a large
dep tree, and (b) we only need two endpoints — create a Checkout
session and verify webhook signatures. Keeping it to ``urllib`` and a
hand-rolled HMAC check keeps the Celery worker image small.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger(__name__)

_SIGNATURE_TOLERANCE_SECONDS = 5 * 60


class StripeError(RuntimeError):
    """Generic Stripe API failure."""


@dataclass(frozen=True)
class StripeConfig:
    """Resolved Stripe creds for the current deploy mode."""

    api_key: str
    webhook_secret: str
    sandbox: bool


def load_config() -> StripeConfig:
    """Pick the right Stripe secret based on STRIPE_SANDBOX.

    The monorepo's two services use slightly different conventions —
    the Next.js app keeps separate ``STRIPE_SECRET_KEY`` (live) and
    ``STRIPE_SDB_SECRET_KEY`` (sandbox) so both are present at the
    same time, while the Python engine holds only ``STRIPE_SECRET_KEY``
    and swaps its value based on deploy environment. This resolver
    accommodates both:

    * Sandbox: prefer ``STRIPE_SDB_SECRET_KEY``; fall back to
      ``STRIPE_SECRET_KEY`` (engine convention). Webhook secret picks
      ``STRIPE_SDB_WEBHOOK_SECRET`` if set, else ``STRIPE_WEBHOOK_SECRET``.
    * Live: ``STRIPE_SECRET_KEY`` + ``STRIPE_WEBHOOK_SECRET``.
    """
    sandbox = os.environ.get("STRIPE_SANDBOX", "").strip().lower() == "true"
    if sandbox:
        api_key = (
            os.environ.get("STRIPE_SDB_SECRET_KEY", "").strip()
            or os.environ.get("STRIPE_SECRET_KEY", "").strip()
        )
        webhook_secret = (
            os.environ.get("STRIPE_SDB_WEBHOOK_SECRET", "").strip()
            or os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
        )
    else:
        api_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
        webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    return StripeConfig(api_key=api_key, webhook_secret=webhook_secret, sandbox=sandbox)


def _encode(data: dict[str, Any]) -> bytes:
    """Encode nested ``metadata`` dict using Stripe's bracketed form.

    Stripe expects ``metadata[key]=val`` style rather than JSON; the
    SDK does this under the hood.
    """
    flat: list[tuple[str, str]] = []
    for k, v in data.items():
        if isinstance(v, dict):
            for sk, sv in v.items():
                flat.append((f"{k}[{sk}]", str(sv)))
        elif isinstance(v, list):
            for item in v:
                flat.append((k, str(item)))
        elif v is None:
            continue
        else:
            flat.append((k, str(v)))
    return urllib.parse.urlencode(flat).encode("utf-8")


def _request(
    path: str,
    data: dict[str, Any] | None = None,
    *,
    method: str = "POST",
    config: StripeConfig | None = None,
) -> dict[str, Any]:
    cfg = config or load_config()
    if not cfg.api_key:
        raise StripeError(
            "Stripe API key not configured (STRIPE_SECRET_KEY / STRIPE_SDB_SECRET_KEY)."
        )
    body = _encode(data) if data else None
    url = f"https://api.stripe.com/v1{path}"
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {cfg.api_key}")
    if body is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload: dict[str, Any] = json.loads(resp.read())
            return payload
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise StripeError(f"Stripe {method} {path} → {exc.code}: {detail}") from exc


def create_checkout_session(
    *,
    price_id: str,
    quantity: int = 1,
    success_url: str,
    cancel_url: str,
    customer: str | None = None,
    customer_email: str | None = None,
    client_reference_id: str | None = None,
    metadata: dict[str, str] | None = None,
    config: StripeConfig | None = None,
) -> dict[str, Any]:
    """Create a one-off Stripe Checkout session for a metered-pack purchase."""
    payload: dict[str, Any] = {
        "mode": "payment",
        "line_items": [{"price": price_id, "quantity": quantity}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "payment_intent_data": {"setup_future_usage": "off_session"} if customer else {},
    }
    # line_items is a list-of-dicts; Stripe expects bracketed indexing.
    flat: list[tuple[str, str]] = [
        ("mode", payload["mode"]),
        ("line_items[0][price]", price_id),
        ("line_items[0][quantity]", str(quantity)),
        ("success_url", success_url),
        ("cancel_url", cancel_url),
    ]
    if customer:
        flat.append(("customer", customer))
    elif customer_email:
        flat.append(("customer_email", customer_email))
    if client_reference_id:
        flat.append(("client_reference_id", client_reference_id))
    if metadata:
        for k, v in metadata.items():
            flat.append((f"metadata[{k}]", str(v)))
    body = urllib.parse.urlencode(flat).encode("utf-8")
    cfg = config or load_config()
    req = urllib.request.Request(
        "https://api.stripe.com/v1/checkout/sessions", data=body, method="POST"
    )
    req.add_header("Authorization", f"Bearer {cfg.api_key}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            response: dict[str, Any] = json.loads(resp.read())
            return response
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise StripeError(f"Stripe checkout.create → {exc.code}: {detail}") from exc


def verify_webhook_signature(
    payload: bytes,
    signature_header: str,
    *,
    config: StripeConfig | None = None,
    tolerance_seconds: int = _SIGNATURE_TOLERANCE_SECONDS,
) -> None:
    """Verify Stripe-Signature header on an incoming webhook.

    Raises ``StripeError`` when the header is missing, malformed,
    expired, or the HMAC doesn't match. On success returns None.

    Implements the algorithm described at
    https://stripe.com/docs/webhooks/signatures — we only accept v1
    signatures (which is the current scheme).
    """
    cfg = config or load_config()
    if not cfg.webhook_secret:
        raise StripeError("Stripe webhook secret not configured.")
    if not signature_header:
        raise StripeError("Missing Stripe-Signature header.")

    parts: dict[str, list[str]] = {}
    for chunk in signature_header.split(","):
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            parts.setdefault(k.strip(), []).append(v.strip())

    try:
        timestamp = int(parts.get("t", [""])[0])
    except ValueError as exc:
        raise StripeError("Invalid Stripe-Signature timestamp.") from exc

    v1_signatures: Iterable[str] = parts.get("v1", [])
    if not v1_signatures:
        raise StripeError("No v1 signatures in Stripe-Signature header.")

    signed_payload = f"{timestamp}.".encode() + payload
    expected = hmac.new(cfg.webhook_secret.encode(), signed_payload, hashlib.sha256).hexdigest()

    if not any(hmac.compare_digest(expected, sig) for sig in v1_signatures):
        raise StripeError("Stripe webhook signature mismatch.")

    if abs(int(time.time()) - timestamp) > tolerance_seconds:
        raise StripeError("Stripe webhook timestamp outside tolerance window.")
