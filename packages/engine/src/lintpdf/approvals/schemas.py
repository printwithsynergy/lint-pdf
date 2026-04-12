"""Pydantic schemas for approval chain API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class ApproverConfig(BaseModel):
    email: str
    name: str | None = None
    role: str | None = None


class StepConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    approvers: list[ApproverConfig] = Field(..., min_length=1)
    require_all: bool = False
    webhook_url: str | None = None
    timeout_hours: int | None = Field(None, ge=0, le=720)  # 30 days max
    on_timeout: Literal["reject", "advance", "notify"] = "notify"


class TemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    is_default: bool = False
    steps: list[StepConfig] = Field(..., min_length=1)


class TemplateUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    is_default: bool | None = None
    steps: list[StepConfig] | None = None


class TemplateResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: str | None
    is_default: bool
    steps: list[dict]
    created_at: datetime
    updated_at: datetime


class AttachChainRequest(BaseModel):
    template_id: str | None = None
    steps: list[StepConfig] | None = None


class StepResponse(BaseModel):
    id: str
    step_index: int
    step_name: str
    approver_email: str
    decision: str
    notes: str | None
    decided_at: datetime | None


class ChainResponse(BaseModel):
    id: str
    job_id: str
    template_id: str | None
    status: str
    current_step: int
    steps: list[dict]
    step_history: list[StepResponse]
    created_at: datetime
    completed_at: datetime | None


class DecideRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    notes: str | None = None
