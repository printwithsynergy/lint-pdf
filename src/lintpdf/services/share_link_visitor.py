"""``ShareLinkVisitorService`` — anonymous-viewer audit-trail capture (W6c-4).

Used by ``lintpdf.api.routes.annotations`` to upsert a row in the
``share_link_visitors`` table when an anonymous viewer identifies
themselves with an email before annotating a shared report. SaaS-only
audit table; OSS default is a pure no-op (no lead-gen / audit trail
on OSS-only deploys — anonymous viewers still annotate, the call just
doesn't record who).

Hosted SaaS overrides via ``set_share_link_visitor_service`` at boot.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from fastapi import Request
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ShareLinkVisitorService(Protocol):
    """Capture an anonymous share-link viewer's identification."""

    def capture(self, token: str, email: str, request: Request, db: Session) -> bool:
        """Upsert; return ``True`` on first capture for (token, email).

        Callers use the return value to fire ``share_link.visited`` webhooks
        only on the first visit per pair.
        """
        ...


class DefaultShareLinkVisitorService:
    """Pure no-op default. OSS engine has no lead-gen audit concept.

    Returns ``False`` (not first visit) so the webhook never fires on
    OSS-only deploys — keeps the OSS engine free of any anonymous-
    visitor side effects.
    """

    def capture(self, token: str, email: str, request: Request, db: Session) -> bool:
        return False


_service: ShareLinkVisitorService | None = None


def get_share_link_visitor_service() -> ShareLinkVisitorService:
    global _service
    if _service is None:
        _service = DefaultShareLinkVisitorService()
    return _service


def set_share_link_visitor_service(service: ShareLinkVisitorService | None) -> None:
    global _service
    _service = service
