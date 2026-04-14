"""Viewer annotations — authenticated + public share-link CRUD.

Backs the Mark Up toolbar group in the interactive viewer. Anonymous
share-link visitors can read annotations without gating, but creating
or modifying requires both ``allow_annotations=true`` on the token
record and an ``X-Visitor-Email`` header identifying the writer.
"""

from __future__ import annotations

import hashlib
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import (
    Job,
    ReportToken,
    ShareLinkVisitor,
    Tenant,
    ViewerAnnotation,
)

router = APIRouter()

_ALLOWED_KINDS = {"rect", "circle", "arrow", "freehand", "note"}


class AnnotationCreateRequest(BaseModel):
    page_num: int = Field(..., ge=1, description="1-indexed page number")
    kind: str = Field(..., description='"rect" | "circle" | "arrow" | "freehand" | "note"')
    geometry: dict[str, Any] = Field(..., description="Primitive geometry in PDF points")
    color: str = Field(default="#dc2626", max_length=16)
    text: str | None = Field(default=None, max_length=2000)


class AnnotationUpdateRequest(BaseModel):
    geometry: dict[str, Any] | None = None
    color: str | None = Field(default=None, max_length=16)
    text: str | None = Field(default=None, max_length=2000)


class AnnotationResponse(BaseModel):
    id: str
    job_id: str
    page_num: int
    kind: str
    geometry: dict[str, Any]
    color: str
    text: str | None
    author_email: str
    created_at: str
    updated_at: str


def _to_response(row: ViewerAnnotation) -> AnnotationResponse:
    return AnnotationResponse(
        id=str(row.id),
        job_id=str(row.job_id),
        page_num=row.page_num,
        kind=row.kind,
        geometry=row.geometry_json,
        color=row.color,
        text=row.text,
        author_email=row.author_email,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
    )


def _validate_kind(kind: str) -> None:
    if kind not in _ALLOWED_KINDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"kind must be one of: {', '.join(sorted(_ALLOWED_KINDS))}",
        )


# ---------------------------------------------------------------------------
# Authenticated (dashboard) endpoints
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}/annotations", response_model=list[AnnotationResponse])
async def list_annotations_auth(
    job_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> list[AnnotationResponse]:
    """List all annotations for a job (tenant-scoped)."""
    try:
        jid = uuid_mod.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found.") from None

    job = db.query(Job).filter(Job.id == jid, Job.tenant_id == tenant.id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    rows = (
        db.query(ViewerAnnotation)
        .filter(ViewerAnnotation.job_id == jid)
        .order_by(ViewerAnnotation.created_at.asc())
        .all()
    )
    return [_to_response(r) for r in rows]


@router.post(
    "/jobs/{job_id}/annotations",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_annotation_auth(
    job_id: str,
    body: AnnotationCreateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> AnnotationResponse:
    """Create an annotation on a job page (authenticated dashboard writer)."""
    _validate_kind(body.kind)
    try:
        jid = uuid_mod.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job not found.") from None

    job = db.query(Job).filter(Job.id == jid, Job.tenant_id == tenant.id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    row = ViewerAnnotation(
        id=uuid_mod.uuid4(),
        job_id=jid,
        tenant_id=tenant.id,
        share_token=None,
        page_num=body.page_num,
        kind=body.kind,
        geometry_json=body.geometry,
        color=body.color,
        text=body.text,
        author_email=tenant.contact_email or "dashboard@lintpdf",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.patch("/jobs/{job_id}/annotations/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation_auth(
    job_id: str,
    annotation_id: str,
    body: AnnotationUpdateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> AnnotationResponse:
    try:
        aid = uuid_mod.UUID(annotation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Annotation not found.") from None

    row = (
        db.query(ViewerAnnotation)
        .filter(
            ViewerAnnotation.id == aid,
            ViewerAnnotation.tenant_id == tenant.id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Annotation not found.")

    if body.geometry is not None:
        row.geometry_json = body.geometry
    if body.color is not None:
        row.color = body.color
    if body.text is not None:
        row.text = body.text
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.delete(
    "/jobs/{job_id}/annotations/{annotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_annotation_auth(
    job_id: str,
    annotation_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> None:
    try:
        aid = uuid_mod.UUID(annotation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Annotation not found.") from None

    row = (
        db.query(ViewerAnnotation)
        .filter(
            ViewerAnnotation.id == aid,
            ViewerAnnotation.tenant_id == tenant.id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    db.delete(row)
    db.commit()


# ---------------------------------------------------------------------------
# Public share-link endpoints
# ---------------------------------------------------------------------------


def _resolve_token(token: str, db: Session) -> ReportToken:
    rec = db.query(ReportToken).filter(ReportToken.token == token).first()
    if rec is None:
        raise HTTPException(status_code=404, detail="Token not found.")
    if rec.expires_at is not None and datetime.now(timezone.utc) > rec.expires_at:
        raise HTTPException(status_code=410, detail="Token has expired.")
    return rec


def _capture_visitor(token: str, email: str, request: Request, db: Session) -> None:
    """Upsert a share-link visitor row so we have an audit trail.

    Hashes the client IP (do not store raw). A missing client address
    (e.g. behind a proxy with no X-Forwarded-For handled upstream) is
    fine — we still record the email.
    """
    ip = (request.client.host if request.client else "") or ""
    ip_hash = hashlib.sha256(ip.encode()).hexdigest() if ip else None
    ua = request.headers.get("user-agent", "")[:512] or None

    existing = (
        db.query(ShareLinkVisitor)
        .filter(
            ShareLinkVisitor.share_token == token,
            ShareLinkVisitor.visitor_email == email.lower(),
        )
        .first()
    )
    if existing is None:
        db.add(
            ShareLinkVisitor(
                id=uuid_mod.uuid4(),
                share_token=token,
                visitor_email=email.lower(),
                ip_hash=ip_hash,
                user_agent=ua,
            )
        )
    else:
        existing.last_seen_at = datetime.now(timezone.utc)
        if ip_hash:
            existing.ip_hash = ip_hash
        if ua:
            existing.user_agent = ua


def _require_visitor_email(request: Request) -> str:
    email = (request.headers.get("x-visitor-email") or "").strip().lower()
    if not email or "@" not in email or len(email) > 255:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Annotation requires a visitor email. Provide 'X-Visitor-Email: you@example.com'."
            ),
        )
    return email


@router.get("/public/{token}/annotations", response_model=list[AnnotationResponse])
async def list_annotations_public(
    token: str, db: Session = Depends(get_db)
) -> list[AnnotationResponse]:
    """List annotations for a share-link job (unauthenticated read)."""
    rec = _resolve_token(token, db)
    rows = (
        db.query(ViewerAnnotation)
        .filter(ViewerAnnotation.job_id == rec.job_id)
        .order_by(ViewerAnnotation.created_at.asc())
        .all()
    )
    return [_to_response(r) for r in rows]


@router.post(
    "/public/{token}/annotations",
    response_model=AnnotationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_annotation_public(
    token: str,
    body: AnnotationCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AnnotationResponse:
    """Create an annotation via a share-link token.

    Requires the token's ``allow_annotations`` flag to be set (minted by
    the issuing tenant) and an ``X-Visitor-Email`` header identifying
    the writer. The email is recorded once per token+email pair in
    ``share_link_visitors`` for audit.
    """
    _validate_kind(body.kind)
    rec = _resolve_token(token, db)
    if not rec.allow_annotations:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This share link is read-only.",
        )
    email = _require_visitor_email(request)
    _capture_visitor(token, email, request, db)

    row = ViewerAnnotation(
        id=uuid_mod.uuid4(),
        job_id=rec.job_id,
        tenant_id=rec.tenant_id,
        share_token=token,
        page_num=body.page_num,
        kind=body.kind,
        geometry_json=body.geometry,
        color=body.color,
        text=body.text,
        author_email=email,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.patch(
    "/public/{token}/annotations/{annotation_id}",
    response_model=AnnotationResponse,
)
async def update_annotation_public(
    token: str,
    annotation_id: str,
    body: AnnotationUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AnnotationResponse:
    rec = _resolve_token(token, db)
    if not rec.allow_annotations:
        raise HTTPException(status_code=403, detail="This share link is read-only.")
    email = _require_visitor_email(request)
    _capture_visitor(token, email, request, db)

    try:
        aid = uuid_mod.UUID(annotation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Annotation not found.") from None

    row = (
        db.query(ViewerAnnotation)
        .filter(
            ViewerAnnotation.id == aid,
            ViewerAnnotation.share_token == token,
            ViewerAnnotation.author_email == email,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Annotation not found.")

    if body.geometry is not None:
        row.geometry_json = body.geometry
    if body.color is not None:
        row.color = body.color
    if body.text is not None:
        row.text = body.text
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.delete(
    "/public/{token}/annotations/{annotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_annotation_public(
    token: str,
    annotation_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    rec = _resolve_token(token, db)
    if not rec.allow_annotations:
        raise HTTPException(status_code=403, detail="This share link is read-only.")
    email = _require_visitor_email(request)
    _capture_visitor(token, email, request, db)

    try:
        aid = uuid_mod.UUID(annotation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Annotation not found.") from None

    row = (
        db.query(ViewerAnnotation)
        .filter(
            ViewerAnnotation.id == aid,
            ViewerAnnotation.share_token == token,
            ViewerAnnotation.author_email == email,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    db.delete(row)
    db.commit()
