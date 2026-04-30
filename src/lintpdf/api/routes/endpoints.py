"""Legacy /api/v1/endpoints* surface — HARD-REMOVED (PR 26).

The legacy CustomEndpoint vanity-slug surface is gone. Every URL
under ``/api/v1/endpoints*`` returns ``HTTP 410 Gone`` with a
structured payload pointing the caller at the Workflows substrate.

Migration guide:
https://lintpdf.com/docs/migration-endpoints-to-workflows

The retained module is a thin shim that registers the same path
patterns the legacy router used so existing integrations get a
clear, structured failure (410 + Link header) instead of a 404.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/v1/endpoints", tags=["legacy"])


_GONE_BODY: dict[str, Any] = {
    "detail": (
        "The /api/v1/endpoints surface has been removed. Use "
        "/api/v1/workflows instead. See "
        "https://lintpdf.com/docs/migration-endpoints-to-workflows "
        "for migration steps."
    ),
    "replacement": "/api/v1/workflows",
    "migration_guide": ("https://lintpdf.com/docs/migration-endpoints-to-workflows"),
}


def _gone() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_410_GONE,
        content=_GONE_BODY,
        headers={
            "Link": '</api/v1/workflows>; rel="successor-version"',
        },
    )


# Register handlers on every method/path the legacy surface exposed
# so callers get a structured 410 instead of a 404 on a misspelled
# path. The catch-all rest:path entry covers nested routes
# (/{slug}/submit, /{id}/test, etc.) without reproducing them.


@router.get("")
@router.get("/")
async def list_endpoints_gone() -> JSONResponse:
    return _gone()


@router.post("")
@router.post("/")
async def create_endpoint_gone() -> JSONResponse:
    return _gone()


@router.api_route(
    "/{rest:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def any_endpoint_path_gone(rest: str) -> JSONResponse:
    del rest
    return _gone()


__all__ = ["router"]
