"""Batch operations API endpoints.

Allows submitting multiple PDFs for preflight in a single request,
checking batch status, and getting aggregated results.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/batch", tags=["batch"])


class BatchSubmitRequest(BaseModel):
    """Request to submit a batch of PDFs for preflight."""

    profile_id: str = Field(description="Voyage Plan profile ID to use for all jobs.")
    file_keys: list[str] = Field(description="List of S3 file keys to process.")
    webhook_url: str | None = Field(default=None, description="Webhook URL for batch completion.")
    priority: bool = Field(default=False, description="Use priority processing queue.")
    tags: dict[str, str] = Field(default_factory=dict, description="Tags to apply to all jobs.")


class BatchJobInfo(BaseModel):
    """Information about a single job in a batch."""

    job_id: str
    file_key: str
    status: str = "pending"


class BatchSubmitResponse(BaseModel):
    """Response after submitting a batch."""

    batch_id: str
    job_count: int
    jobs: list[BatchJobInfo]
    status: str = "submitted"


class BatchStatusResponse(BaseModel):
    """Status of a batch operation."""

    batch_id: str
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    pending_jobs: int
    status: str  # submitted, processing, complete, partial_failure
    summary: dict[str, Any] | None = None


@router.post("/submit", response_model=BatchSubmitResponse)
async def submit_batch(request: BatchSubmitRequest) -> BatchSubmitResponse:
    """Submit a batch of PDFs for preflight processing."""
    batch_id = str(uuid.uuid4())
    jobs: list[BatchJobInfo] = []

    for file_key in request.file_keys:
        job_id = str(uuid.uuid4())
        jobs.append(
            BatchJobInfo(
                job_id=job_id,
                file_key=file_key,
                status="pending",
            )
        )

    # In production: create BatchJob + Job records, enqueue tasks
    return BatchSubmitResponse(
        batch_id=batch_id,
        job_count=len(jobs),
        jobs=jobs,
    )


@router.get("/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: str) -> BatchStatusResponse:
    """Get the status of a batch operation."""
    # Stub — production: query BatchJob + jobs
    raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")


@router.get("/{batch_id}/summary")
async def get_batch_summary(batch_id: str) -> dict[str, Any]:
    """Get aggregated summary of all completed jobs in a batch."""
    raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
