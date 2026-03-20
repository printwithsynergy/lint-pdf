"""Comprehensive tests for Pydantic API schemas."""

from __future__ import annotations

# skipcq: PYL-R0201
import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from grounded.api.schemas import (
    FindingResponse,
    HealthResponse,
    JobCreateResponse,
    JobListResponse,
    JobResponse,
    JobSummaryResponse,
    ProfileCreateRequest,
    ProfileCreateResponse,
    ProfileDetailResponse,
    ProfileListResponse,
    ProfileSummaryResponse,
    StatusResponse,
    WebhookCreateRequest,
    WebhookListResponse,
    WebhookResponse,
    WebhookUpdateRequest,
)

# -----------------------------------------------------------------------
# Health schemas
# -----------------------------------------------------------------------


class TestHealthResponse:
    def test_defaults(self) -> None:
        h = HealthResponse(status="ok")
        assert h.status == "ok"
        assert h.service == "grounded"

    def test_custom_service(self) -> None:
        h = HealthResponse(status="ok", service="custom")
        assert h.service == "custom"


class TestStatusResponse:
    def test_defaults(self) -> None:
        s = StatusResponse(status="ok")
        assert s.version == "0.1.0"
        assert s.database == "unknown"
        assert s.redis == "unknown"
        assert s.queue_depth == 0
        assert s.worker_count == 0

    def test_all_fields(self) -> None:
        s = StatusResponse(
            status="degraded",
            database="connected",
            redis="error",
            queue_depth=5,
            worker_count=2,
        )
        assert s.status == "degraded"
        assert s.queue_depth == 5


# -----------------------------------------------------------------------
# Job schemas
# -----------------------------------------------------------------------


class TestJobCreateResponse:
    def test_basic(self) -> None:
        uid = uuid.uuid4()
        r = JobCreateResponse(job_id=uid)
        assert r.job_id == uid
        assert r.status == "pending"
        assert r.message == "Job submitted successfully"

    def test_serialization(self) -> None:
        uid = uuid.uuid4()
        r = JobCreateResponse(job_id=uid)
        d = r.model_dump(mode="json")
        assert d["job_id"] == str(uid)


class TestFindingResponse:
    def test_minimal(self) -> None:
        f = FindingResponse(inspection_id="INK001", severity="aground", message="Bad ink")
        assert f.page_num is None
        assert f.details is None

    def test_with_details(self) -> None:
        f = FindingResponse(
            inspection_id="RES001",
            severity="advisory",
            message="Low DPI",
            page_num=3,
            details={"dpi": 72},
        )
        assert f.details["dpi"] == 72
        assert f.page_num == 3


class TestJobSummaryResponse:
    def test_all_fields(self) -> None:
        s = JobSummaryResponse(
            total_findings=5,
            aground_count=1,
            squall_count=2,
            advisory_count=2,
            passed=False,
            page_count=10,
            file_size_bytes=50000,
        )
        assert s.total_findings == 5
        assert s.passed is False


class TestJobResponse:
    def test_pending_job(self) -> None:
        now = datetime.now(UTC)
        r = JobResponse(
            job_id=uuid.uuid4(),
            status="pending",
            profile_id="grounded-default",
            file_name="test.pdf",
            file_size=1024,
            created_at=now,
        )
        assert r.summary is None
        assert r.findings is None
        assert r.page_count is None

    def test_complete_job(self) -> None:
        now = datetime.now(UTC)
        r = JobResponse(
            job_id=uuid.uuid4(),
            status="complete",
            profile_id="grounded-default",
            file_name="test.pdf",
            file_size=1024,
            created_at=now,
            completed_at=now,
            duration_ms=500,
            summary=JobSummaryResponse(
                total_findings=0,
                aground_count=0,
                squall_count=0,
                advisory_count=0,
                passed=True,
                page_count=1,
                file_size_bytes=1024,
            ),
            findings=[],
        )
        assert r.summary.passed is True
        assert r.findings == []

    def test_failed_job(self) -> None:
        r = JobResponse(
            job_id=uuid.uuid4(),
            status="failed",
            profile_id="grounded-default",
            file_name="test.pdf",
            file_size=1024,
            created_at=datetime.now(UTC),
            error_message="Parser error",
        )
        assert r.error_message == "Parser error"


class TestJobListResponse:
    def test_empty(self) -> None:
        r = JobListResponse(jobs=[], total=0, page=1, page_size=20)
        assert r.total == 0

    def test_with_jobs(self) -> None:
        now = datetime.now(UTC)
        jobs = [
            JobResponse(
                job_id=uuid.uuid4(),
                status="pending",
                profile_id="grounded-default",
                file_name=f"file{i}.pdf",
                file_size=100,
                created_at=now,
            )
            for i in range(3)
        ]
        r = JobListResponse(jobs=jobs, total=3, page=1, page_size=20)
        assert len(r.jobs) == 3


# -----------------------------------------------------------------------
# Profile schemas
# -----------------------------------------------------------------------


class TestProfileSummaryResponse:
    def test_defaults(self) -> None:
        p = ProfileSummaryResponse(profile_id="test", name="Test")
        assert p.workflow == "CMYK"
        assert p.is_builtin is True
        assert p.description == ""

    def test_custom_profile(self) -> None:
        p = ProfileSummaryResponse(
            profile_id="custom",
            name="Custom",
            is_builtin=False,
            workflow="RGB",
        )
        assert p.is_builtin is False
        assert p.workflow == "RGB"


class TestProfileCreateRequest:
    def test_valid_kebab_case(self) -> None:
        r = ProfileCreateRequest(
            profile_id="my-custom-profile",
            voyage_plan={"name": "Test"},
        )
        assert r.profile_id == "my-custom-profile"

    def test_rejects_uppercase(self) -> None:
        with pytest.raises(ValidationError):
            ProfileCreateRequest(
                profile_id="MyProfile",
                voyage_plan={"name": "Bad"},
            )

    def test_rejects_spaces(self) -> None:
        with pytest.raises(ValidationError):
            ProfileCreateRequest(
                profile_id="has spaces",
                voyage_plan={"name": "Bad"},
            )

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError):
            ProfileCreateRequest(profile_id="", voyage_plan={"name": "Bad"})

    def test_rejects_single_char(self) -> None:
        with pytest.raises(ValidationError):
            ProfileCreateRequest(profile_id="x", voyage_plan={"name": "Bad"})

    def test_rejects_leading_hyphen(self) -> None:
        with pytest.raises(ValidationError):
            ProfileCreateRequest(
                profile_id="-leading",
                voyage_plan={"name": "Bad"},
            )

    def test_rejects_trailing_hyphen(self) -> None:
        with pytest.raises(ValidationError):
            ProfileCreateRequest(
                profile_id="trailing-",
                voyage_plan={"name": "Bad"},
            )

    def test_allows_numbers(self) -> None:
        r = ProfileCreateRequest(
            profile_id="profile-v2",
            voyage_plan={"name": "V2"},
        )
        assert r.profile_id == "profile-v2"


class TestProfileCreateResponse:
    def test_defaults(self) -> None:
        r = ProfileCreateResponse(profile_id="test-id")
        assert r.message == "Profile created successfully"


class TestProfileDetailResponse:
    def test_defaults(self) -> None:
        r = ProfileDetailResponse(profile_id="test", name="Test")
        assert r.version == "1.0"
        assert r.is_builtin is True
        assert r.checks == {}
        assert r.thresholds == {}


class TestProfileListResponse:
    def test_empty(self) -> None:
        r = ProfileListResponse(profiles=[])
        assert r.profiles == []


# -----------------------------------------------------------------------
# Webhook schemas
# -----------------------------------------------------------------------


class TestWebhookCreateRequest:
    def test_with_url_only(self) -> None:
        r = WebhookCreateRequest(url="https://example.com/hook")
        assert r.url == "https://example.com/hook"
        assert "job.completed" in r.events
        assert "job.failed" in r.events

    def test_custom_events(self) -> None:
        r = WebhookCreateRequest(
            url="https://example.com/hook",
            events=["job.completed"],
        )
        assert r.events == ["job.completed"]


class TestWebhookResponse:
    def test_all_fields(self) -> None:
        now = datetime.now(UTC)
        r = WebhookResponse(
            id=uuid.uuid4(),
            url="https://example.com/hook",
            events=["job.completed"],
            is_active=True,
            created_at=now,
        )
        assert r.is_active is True


class TestWebhookUpdateRequest:
    def test_all_none_by_default(self) -> None:
        r = WebhookUpdateRequest()
        assert r.url is None
        assert r.events is None
        assert r.is_active is None

    def test_partial_update(self) -> None:
        r = WebhookUpdateRequest(is_active=False)
        assert r.is_active is False
        assert r.url is None


class TestWebhookListResponse:
    def test_empty(self) -> None:
        r = WebhookListResponse(webhooks=[])
        assert r.webhooks == []
