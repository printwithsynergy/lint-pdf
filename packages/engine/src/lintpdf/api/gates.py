"""Consistent 403 envelopes for plan-upgrade gates.

All tier gates return the same JSON body so the app UI can render a single
``UpgradePrompt`` component regardless of which gate triggered.
"""

from __future__ import annotations

from typing import Literal

from fastapi import HTTPException, status

GateName = Literal[
    "preflight_source",
    "capability_fillin",
    "annotations",
    "report_format",
]


def plan_upgrade_required(
    *,
    gate: GateName,
    current_plan: str,
    required_plan: str,
    message: str,
) -> HTTPException:
    """Build a 403 HTTPException with the canonical upgrade envelope.

    The app dashboard catches ``error == "plan_upgrade_required"`` and renders
    an inline upgrade CTA instead of a generic toast.
    """
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "plan_upgrade_required",
            "message": message,
            "required_plan": required_plan,
            "current_plan": current_plan,
            "gate": gate,
            "upgrade_url": "/pricing",
        },
    )
