"""``EmailService`` — route-layer email surface (Phase 5 W2).

Engine route handlers (``jobs.py``, ``viewer.py``, ``annotations.py``)
fire transactional emails on certain state transitions: a tenant going
into overage, a rate-limit warning, a one-off report share, an
annotation reply notification.

The Protocol declared here lets routes accept the email service via
``Depends(get_email_service)``. The default factory returns a
``NoOpEmailService`` so the OSS engine boots standalone with no
mailer configured and engine routes silently skip the send. The SaaS
shell overrides the factory via FastAPI's ``app.dependency_overrides``
to wire the real Resend-backed implementation living in
``lintpdf_saas.email.service``.

Migrating a callsite:

.. code-block:: python

    # In a route handler
    from lintpdf.services.email import EmailService, get_email_service
    @router.post("/jobs")
    async def submit_job(
        ...,
        email: EmailService = Depends(get_email_service),
    ):
        ...
        email.send_overage_started(
            to=tenant.contact_email, tenant_name=tenant.name,
        )

Methods on the Protocol are intentionally narrow: only the message
types that engine-side route handlers actually fire. SaaS-only
helpers (``send_api_key_issued``, ``send_job_complete``,
``send_trial_report_email``, the approval-chain notifications) are
called from SaaS-only routes (``trial.py``, ``approvals/service.py``)
and stay in ``lintpdf_saas.email.service`` directly -- they never
touch this Protocol.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailResult:
    """Outcome of a transactional send. Mirrors ``lintpdf_saas.email.service.EmailResult`` 1:1.

    ``success`` is ``True`` only on confirmed delivery to the upstream
    mailer. ``email_id`` is populated on success; ``error`` carries the
    provider error string on failure or the reason a stub skipped.
    """

    success: bool
    email_id: str | None = None
    error: str | None = None


class EmailService(Protocol):
    """Engine-route email surface.

    Each method targets a specific message type. The SaaS host
    implementation routes to Resend; the OSS no-op stub returns
    ``EmailResult(status="skipped")``. Route handlers should never
    branch on the result — failed sends are logged but never block
    the response path.
    """

    def send_overage_started(
        self,
        *,
        to: str,
        tenant_name: str,
        used: int,
        limit: int,
        rate_cents: int,
        cost_cents: int,
    ) -> EmailResult: ...

    def send_rate_limit_warning(
        self,
        *,
        to: str,
        tenant_name: str,
        used: int,
        limit: int,
    ) -> EmailResult: ...

    def send_report(
        self,
        *,
        to: str,
        tenant_name: str,
        job_id: str,
        report_url: str,
        finding_count: int,
        passed: bool,
        brand_name: str = "LintPDF",
        brand_primary_color: str = "#0ea5e9",
    ) -> EmailResult: ...

    def send_annotation_comment(
        self,
        *,
        to: str,
        commenter_email: str,
        file_name: str,
        body_excerpt: str,
        deep_link_url: str,
        brand_name: str = "LintPDF",
        brand_primary_color: str = "#1e3a8a",
    ) -> EmailResult: ...


class NoOpEmailService:
    """Default implementation. Logs the send intent at ``debug`` level
    and returns ``success=False`` with an explanatory ``error`` so
    callsites that bail on failure see a sensible reason. Used when
    the OSS engine boots standalone or when running tests that don't
    need a real mailer.
    """

    def _skip(self, method: str, **kwargs: Any) -> EmailResult:
        logger.debug("email.%s skipped (no service wired): %s", method, kwargs)
        return EmailResult(success=False, error="email service not configured")

    def send_overage_started(self, **kwargs: Any) -> EmailResult:
        return self._skip("send_overage_started", **kwargs)

    def send_rate_limit_warning(self, **kwargs: Any) -> EmailResult:
        return self._skip("send_rate_limit_warning", **kwargs)

    def send_report(self, **kwargs: Any) -> EmailResult:
        return self._skip("send_report", **kwargs)

    def send_annotation_comment(self, **kwargs: Any) -> EmailResult:
        return self._skip("send_annotation_comment", **kwargs)


_default_factory = NoOpEmailService


def get_email_service() -> EmailService:
    """FastAPI dependency factory.

    The default returns a ``NoOpEmailService``. SaaS hosts override
    this in their app factory:

        app.dependency_overrides[get_email_service] = lambda: SaaSEmailService()

    Tests that need to assert email-send intent can override with a
    spy implementation in the same way.
    """

    return _default_factory()
