"""Comprehensive tests for Pydantic API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from lintpdf.api.schemas import (
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
    @staticmethod
    def test_defaults() -> None:
        h = HealthResponse(status="ok")
        assert h.status == "ok"
        assert h.service == "lintpdf"

    @staticmethod
    def test_custom_service() -> None:
        h = HealthResponse(status="ok", service="custom")
        assert h.service == "custom"


class TestStatusResponse:
    @staticmethod
    def test_defaults() -> None:
        s = StatusResponse(status="ok")
        assert s.version == "0.1.0"
        assert s.database == "unknown"
        assert s.redis == "unknown"
        assert s.queue_depth == 0
        assert s.worker_count == 0

    @staticmethod
    def test_all_fields() -> None:
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
    @staticmethod
    def test_basic() -> None:
        uid = uuid.uuid4()
        r = JobCreateResponse(job_id=uid)
        assert r.job_id == uid
        assert r.status == "pending"
        assert r.message == "Job submitted successfully"

    @staticmethod
    def test_serialization() -> None:
        uid = uuid.uuid4()
        r = JobCreateResponse(job_id=uid)
        d = r.model_dump(mode="json")
        assert d["job_id"] == str(uid)


class TestFindingResponse:
    @staticmethod
    def test_minimal() -> None:
        f = FindingResponse(
            id="00000000-0000-0000-0000-000000000001",
            inspection_id="INK001",
            severity="error",
            message="Bad ink",
        )
        assert f.page_num is None
        assert f.details is None

    @staticmethod
    def test_with_details() -> None:
        f = FindingResponse(
            id="00000000-0000-0000-0000-000000000002",
            inspection_id="RES001",
            severity="advisory",
            message="Low DPI",
            page_num=3,
            details={"dpi": 72},
        )
        assert f.details["dpi"] == 72
        assert f.page_num == 3

    @staticmethod
    def test_ai_explanation_fields_default_null() -> None:
        f = FindingResponse(
            id="00000000-0000-0000-0000-000000000003",
            inspection_id="X",
            severity="error",
            message="m",
        )
        assert f.ai_explanation is None
        assert f.ai_explanation_model is None
        assert f.ai_explanation_at is None
        assert f.effective_decision is None

    @staticmethod
    def test_ai_explanation_populated() -> None:
        now = datetime.now(timezone.utc)
        f = FindingResponse(
            id="00000000-0000-0000-0000-000000000004",
            inspection_id="X",
            severity="error",
            message="m",
            ai_explanation="This finding indicates ...",
            ai_explanation_model="claude-haiku-4-5",
            ai_explanation_at=now,
            effective_decision={
                "decision_type": "waive",
                "decided_at": now.isoformat(),
                "decided_by_user_id": "u1",
            },
        )
        assert f.ai_explanation_model == "claude-haiku-4-5"
        assert f.effective_decision["decision_type"] == "waive"


class TestJobSummaryResponse:
    @staticmethod
    def test_all_fields() -> None:
        s = JobSummaryResponse(
            total_findings=5,
            error_count=1,
            warning_count=2,
            advisory_count=2,
            passed=False,
            page_count=10,
            file_size_bytes=50000,
        )
        assert s.total_findings == 5
        assert s.passed is False


class TestJobResponse:
    @staticmethod
    def test_pending_job() -> None:
        now = datetime.now(timezone.utc)
        r = JobResponse(
            job_id=uuid.uuid4(),
            status="pending",
            profile_id="lintpdf-default",
            file_name="test.pdf",
            file_size=1024,
            created_at=now,
        )
        assert r.summary is None
        assert r.findings is None
        assert r.page_count is None

    @staticmethod
    def test_complete_job() -> None:
        now = datetime.now(timezone.utc)
        r = JobResponse(
            job_id=uuid.uuid4(),
            status="complete",
            profile_id="lintpdf-default",
            file_name="test.pdf",
            file_size=1024,
            created_at=now,
            completed_at=now,
            duration_ms=500,
            summary=JobSummaryResponse(
                total_findings=0,
                error_count=0,
                warning_count=0,
                advisory_count=0,
                passed=True,
                page_count=1,
                file_size_bytes=1024,
            ),
            findings=[],
        )
        assert r.summary.passed is True
        assert r.findings == []

    @staticmethod
    def test_failed_job() -> None:
        r = JobResponse(
            job_id=uuid.uuid4(),
            status="failed",
            profile_id="lintpdf-default",
            file_name="test.pdf",
            file_size=1024,
            created_at=datetime.now(timezone.utc),
            error_message="Parser error",
        )
        assert r.error_message == "Parser error"

    @staticmethod
    def test_epm_verdict_and_decisions_count_default_null() -> None:
        r = JobResponse(
            job_id=uuid.uuid4(),
            status="pending",
            profile_id="lintpdf-default",
            file_name="x.pdf",
            file_size=1,
            created_at=datetime.now(timezone.utc),
        )
        assert r.epm_verdict is None
        assert r.decisions_count is None

    @staticmethod
    def test_epm_verdict_populated() -> None:
        r = JobResponse(
            job_id=uuid.uuid4(),
            status="complete",
            profile_id="lintpdf-default",
            file_name="x.pdf",
            file_size=1,
            created_at=datetime.now(timezone.utc),
            epm_verdict={
                "tier": "marginal",
                "rejection_drivers": [],
                "advisories": [],
                "recommends_indichrome": False,
                "legacy_codes_fired": [],
                "epm_findings_count": 0,
            },
            decisions_count=3,
        )
        assert r.epm_verdict["tier"] == "marginal"
        assert r.decisions_count == 3


class TestJobListResponse:
    @staticmethod
    def test_empty() -> None:
        r = JobListResponse(jobs=[], total=0, page=1, page_size=20)
        assert r.total == 0

    @staticmethod
    def test_with_jobs() -> None:
        now = datetime.now(timezone.utc)
        jobs = [
            JobResponse(
                job_id=uuid.uuid4(),
                status="pending",
                profile_id="lintpdf-default",
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
    @staticmethod
    def test_defaults() -> None:
        p = ProfileSummaryResponse(profile_id="test", name="Test")
        assert p.workflow == "CMYK"
        assert p.is_builtin is True
        assert p.description == ""

    @staticmethod
    def test_custom_profile() -> None:
        p = ProfileSummaryResponse(
            profile_id="custom",
            name="Custom",
            is_builtin=False,
            workflow="RGB",
        )
        assert p.is_builtin is False
        assert p.workflow == "RGB"


class TestProfileCreateRequest:
    @staticmethod
    def test_valid_kebab_case() -> None:
        r = ProfileCreateRequest(
            profile_id="my-custom-profile",
            preflight_profile={"name": "Test"},
        )
        assert r.profile_id == "my-custom-profile"

    @staticmethod
    def test_rejects_uppercase() -> None:
        with pytest.raises(ValidationError):
            ProfileCreateRequest(
                profile_id="MyProfile",
                preflight_profile={"name": "Bad"},
            )

    @staticmethod
    def test_rejects_spaces() -> None:
        with pytest.raises(ValidationError):
            ProfileCreateRequest(
                profile_id="has spaces",
                preflight_profile={"name": "Bad"},
            )

    @staticmethod
    def test_rejects_empty() -> None:
        with pytest.raises(ValidationError):
            ProfileCreateRequest(profile_id="", preflight_profile={"name": "Bad"})

    @staticmethod
    def test_rejects_single_char() -> None:
        with pytest.raises(ValidationError):
            ProfileCreateRequest(profile_id="x", preflight_profile={"name": "Bad"})

    @staticmethod
    def test_rejects_leading_hyphen() -> None:
        with pytest.raises(ValidationError):
            ProfileCreateRequest(
                profile_id="-leading",
                preflight_profile={"name": "Bad"},
            )

    @staticmethod
    def test_rejects_trailing_hyphen() -> None:
        with pytest.raises(ValidationError):
            ProfileCreateRequest(
                profile_id="trailing-",
                preflight_profile={"name": "Bad"},
            )

    @staticmethod
    def test_allows_numbers() -> None:
        r = ProfileCreateRequest(
            profile_id="profile-v2",
            preflight_profile={"name": "V2"},
        )
        assert r.profile_id == "profile-v2"


class TestProfileCreateResponse:
    @staticmethod
    def test_defaults() -> None:
        r = ProfileCreateResponse(profile_id="test-id")
        assert r.message == "Profile created successfully"


class TestProfileDetailResponse:
    @staticmethod
    def test_defaults() -> None:
        r = ProfileDetailResponse(profile_id="test", name="Test")
        assert r.version == "1.0"
        assert r.is_builtin is True
        assert r.checks == {}
        assert r.thresholds == {}


class TestProfileListResponse:
    @staticmethod
    def test_empty() -> None:
        r = ProfileListResponse(profiles=[])
        assert r.profiles == []


# -----------------------------------------------------------------------
# Webhook schemas
# -----------------------------------------------------------------------


class TestWebhookCreateRequest:
    @staticmethod
    def test_with_url_only() -> None:
        r = WebhookCreateRequest(url="https://example.com/hook")
        assert r.url == "https://example.com/hook"
        assert "job.completed" in r.events
        assert "job.failed" in r.events

    @staticmethod
    def test_custom_events() -> None:
        r = WebhookCreateRequest(
            url="https://example.com/hook",
            events=["job.completed"],
        )
        assert r.events == ["job.completed"]


class TestWebhookResponse:
    @staticmethod
    def test_all_fields() -> None:
        now = datetime.now(timezone.utc)
        r = WebhookResponse(
            id=uuid.uuid4(),
            url="https://example.com/hook",
            events=["job.completed"],
            is_active=True,
            created_at=now,
        )
        assert r.is_active is True


class TestWebhookUpdateRequest:
    @staticmethod
    def test_all_none_by_default() -> None:
        r = WebhookUpdateRequest()
        assert r.url is None
        assert r.events is None
        assert r.is_active is None

    @staticmethod
    def test_partial_update() -> None:
        r = WebhookUpdateRequest(is_active=False)
        assert r.is_active is False
        assert r.url is None


class TestWebhookListResponse:
    @staticmethod
    def test_empty() -> None:
        r = WebhookListResponse(webhooks=[])
        assert r.webhooks == []
