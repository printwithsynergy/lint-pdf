"""Route-layer service Protocols.

Phase 1 introduced ``lintpdf/plugin/services.py`` for analyzer-side
service injection (``ctx.services.metering``, ``ctx.services.cost_cap``,
etc.). Phase 5 extends the same pattern to the route layer: route
handlers stop importing SaaS-coupled modules directly and instead
accept services via FastAPI's ``Depends(...)`` mechanism.

Default factories return no-op stubs so the OSS engine boots
standalone with no SaaS dependencies. The SaaS shell overrides the
factory via ``app.dependency_overrides`` to wire its real
implementations:

    # In lint-pdf-saas
    from lintpdf.services.email import get_email_service
    from lintpdf_saas.email.service import SaaSEmailService

    app.dependency_overrides[get_email_service] = lambda: SaaSEmailService()

This module starts with ``EmailService`` (Phase 5 W2). Subsequent
phases add ``BillingService``, ``AuthService`` (the auth dependency
override is the most consequential), ``WebhookService``,
``CustomDomainService``, etc.
"""

from __future__ import annotations
