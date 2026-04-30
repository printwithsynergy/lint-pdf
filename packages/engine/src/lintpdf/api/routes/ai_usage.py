"""AI usage reporting endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session  # noqa: TC002

from lintpdf.api.ai_schemas import (
    AITrendDataPoint,
    AITrendResponse,
    AIUsageEntry,
    AIUsageResponse,
)
from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import AIUsageLog, Tenant

router = APIRouter(prefix="/api/v1/ai/usage", tags=["x:saas-only", "ai-usage"])


@router.get("", response_model=AIUsageResponse)
async def get_usage(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    category: str | None = Query(default=None),
    feature: str | None = Query(default=None),
    start_date: str | None = Query(default=None, description="ISO date YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="ISO date YYYY-MM-DD"),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> AIUsageResponse:
    """View AI usage report with filtering."""
    from lintpdf.ai.access import check_ai_access

    check_ai_access(tenant, db)

    query = db.query(AIUsageLog).filter(AIUsageLog.tenant_id == tenant.id)

    if category:
        query = query.filter(AIUsageLog.category == category)
    if feature:
        query = query.filter(AIUsageLog.feature == feature)
    if start_date:
        query = query.filter(AIUsageLog.created_at >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(AIUsageLog.created_at <= datetime.fromisoformat(end_date))

    total = query.count()
    offset = (page - 1) * page_size

    logs = query.order_by(AIUsageLog.created_at.desc()).offset(offset).limit(page_size).all()

    # Aggregates
    agg = (
        db.query(
            func.coalesce(func.sum(AIUsageLog.credits_consumed), 0),
            func.coalesce(func.sum(AIUsageLog.cost), 0),
        )
        .filter(AIUsageLog.tenant_id == tenant.id)
        .first()
    )
    total_credits = int(agg[0]) if agg else 0
    total_cost = Decimal(str(agg[1])) if agg else Decimal("0")

    return AIUsageResponse(
        entries=[
            AIUsageEntry(
                id=log.id,
                job_id=log.job_id,
                category=log.category,
                feature=log.feature,
                credits_consumed=log.credits_consumed,
                cost=log.cost,
                processing_time_ms=log.processing_time_ms,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total_credits_consumed=total_credits,
        total_cost=total_cost,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/trends", response_model=AITrendResponse)
async def get_usage_trends(
    period: str = Query(default="30d", description="Period: 7d, 30d, 90d"),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> AITrendResponse:
    """Get AI usage trend data for SPC dashboard."""
    from lintpdf.ai.access import check_ai_access

    check_ai_access(tenant, db)

    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    from datetime import timedelta

    start = start - timedelta(days=days)

    # Get daily aggregates
    from sqlalchemy import Date, cast

    daily = (
        db.query(
            cast(AIUsageLog.created_at, Date).label("date"),
            func.count(func.distinct(AIUsageLog.job_id)).label("ai_jobs"),
            func.sum(AIUsageLog.credits_consumed).label("credits"),
            func.sum(AIUsageLog.cost).label("cost"),
        )
        .filter(
            AIUsageLog.tenant_id == tenant.id,
            AIUsageLog.created_at >= start,
        )
        .group_by(cast(AIUsageLog.created_at, Date))
        .order_by(cast(AIUsageLog.created_at, Date))
        .all()
    )

    data_points = [
        AITrendDataPoint(
            date=str(row.date),
            total_jobs=0,  # Would need Job table join for total jobs
            ai_jobs=row.ai_jobs or 0,
            credits_consumed=row.credits or 0,
            cost=Decimal(str(row.cost or 0)),
            avg_findings_per_job=0.0,
        )
        for row in daily
    ]

    return AITrendResponse(data_points=data_points, period=period)
