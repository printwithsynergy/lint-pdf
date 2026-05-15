"""Tests for report generation service."""

from __future__ import annotations

import uuid
from unittest.mock import patch

from lintpdf.api.storage import InMemoryStorage
from lintpdf.reports.service import BrandingContext, ReportService

_FAKE_HTML = b"<html><head><title>Preflight Report</title></head><body>Preflight Report</body></html>"


class _FakeDB:
    """Minimal fake DB session for testing ReportService."""

    def __init__(self) -> None:
        self._objects: list[object] = []
        self._committed = False

    def add(self, obj: object) -> None:
        self._objects.append(obj)

    def commit(self) -> None:
        self._committed = True

    def query(self, model: type) -> _FakeQuery:
        return _FakeQuery(self._objects, model)

    def delete(self, obj: object) -> None:
        self._objects = [o for o in self._objects if o is not obj]


class _FakeQuery:
    def __init__(self, objects: list[object], model: type) -> None:
        self._objects = objects
        self._model = model
        self._filters: list[object] = []

    def filter(self, *args: object) -> _FakeQuery:
        return self

    def first(self) -> object | None:
        for obj in self._objects:
            if isinstance(obj, self._model):
                return obj
        return None

    def all(self) -> list[object]:
        return [o for o in self._objects if isinstance(o, self._model)]


class TestBrandingContext:
    @staticmethod
    def test_defaults() -> None:
        branding = BrandingContext()
        assert branding.name == "LintPDF"
        assert branding.primary_color == "#1a3a7a"
        assert branding.footer_text == "Powered by LintPDF"

    @staticmethod
    def test_custom_branding() -> None:
        branding = BrandingContext(
            name="Custom Corp",
            logo_url="https://example.com/logo.png",
            primary_color="#ff0000",
            footer_text=None,
        )
        assert branding.name == "Custom Corp"
        assert branding.footer_text is None


class TestReportService:
    @staticmethod
    def _make_result_json() -> dict:
        return {
            "job_id": str(uuid.uuid4()),
            "profile_id": "lintpdf-default",
            "duration_ms": 42,
            "summary": {
                "total_findings": 1,
                "error_count": 1,
                "warning_count": 0,
                "advisory_count": 0,
                "passed": False,
                "page_count": 1,
                "file_size_bytes": 1024,
            },
            "metadata": {
                "pdf_version": "1.7",
                "is_encrypted": False,
                "conformance": None,
            },
            "findings": [
                {
                    "inspection_id": "LPDF_FONT_001",
                    "severity": "error",
                    "message": "Font not embedded",
                    "page_num": 1,
                    "object_id": None,
                    "object_type": None,
                },
            ],
        }

    def test_generate_html_report(self) -> None:
        storage = InMemoryStorage()
        db = _FakeDB()
        service = ReportService(storage, db)

        result_json = self._make_result_json()
        job_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())

        with patch("lintpdf.reports.lens_client.render_html", return_value=_FAKE_HTML):
            result = service.generate_and_store(
                job_id=job_id,
                tenant_id=tenant_id,
                result_json=result_json,
                formats=["html"],
                expiry_days=30,
            )

        assert len(result.reports) == 1
        assert result.reports[0]["format"] == "html"
        assert "/r/" in result.reports[0]["url"]
        assert result.reports[0]["expires_at"] is not None

        # Verify bytes were stored (lens-server owns the content; we just store what it returns)
        key = f"reports/{tenant_id}/{job_id}/report.html"
        assert key in storage._files
        assert storage._files[key] == _FAKE_HTML

    def test_generate_with_branding(self) -> None:
        storage = InMemoryStorage()
        db = _FakeDB()
        service = ReportService(storage, db)

        result_json = self._make_result_json()
        job_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())

        branding = BrandingContext(
            name="Acme Print",
            primary_color="#ff6600",
            footer_text=None,
        )

        with patch("lintpdf.reports.lens_client.render_html", return_value=_FAKE_HTML) as mock_render:
            result = service.generate_and_store(
                job_id=job_id,
                tenant_id=tenant_id,
                result_json=result_json,
                formats=["html"],
                branding=branding,
            )

        assert len(result.reports) == 1
        # Branding is passed to lens-server in the context dict, not embedded in stored HTML
        call_kwargs = mock_render.call_args[1]
        assert call_kwargs["branding"]["name"] == "Acme Print"
        assert call_kwargs["branding"]["primary_color"] == "#ff6600"
        assert call_kwargs["branding"]["footer_text"] is None

    def test_generate_no_expiry(self) -> None:
        storage = InMemoryStorage()
        db = _FakeDB()
        service = ReportService(storage, db)

        result_json = self._make_result_json()
        with patch("lintpdf.reports.lens_client.render_html", return_value=_FAKE_HTML):
            result = service.generate_and_store(
                job_id=str(uuid.uuid4()),
                tenant_id=str(uuid.uuid4()),
                result_json=result_json,
                formats=["html"],
                expiry_days=None,
            )

        assert result.reports[0]["expires_at"] is None
