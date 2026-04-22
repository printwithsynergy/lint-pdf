"""Unit tests for ``lintpdf.audit.customer.CustomerAuditor``.

Mocks the Modal endpoint via ``urllib.request.urlopen`` so the tests
don't need a live deploy. Covers:

* Missing endpoint URL → RuntimeError on construction.
* Empty findings → no HTTP call.
* Happy path: two findings, endpoint returns verdicts keyed by
  finding_index, results align correctly.
* Out-of-order response verdicts land on the right finding.
* Transport failure (URLError) → whole batch stays None (not
  "error" rows, so the DB columns stay NULL).
* Unknown status value in a verdict is ignored (result stays None).
"""

from __future__ import annotations

import json
import urllib.error
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest


@dataclass
class _FakeFinding:
    inspection_id: str = "LPDF_TEST_001"
    severity: str = "advisory"
    message: str = "Test finding"
    page_num: int | None = 1
    bbox_x0: float | None = None
    bbox_y0: float | None = None
    bbox_x1: float | None = None
    bbox_y1: float | None = None


@pytest.fixture(autouse=True)
def _stub_renderer(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    from lintpdf.ai import rendering

    mock = MagicMock(return_value=b"\x89PNG\r\n\x1a\n-fake")
    monkeypatch.setattr(rendering, "render_page_to_image", mock)
    return mock


def _fake_response(body: dict) -> object:
    """Build an object that mimics ``urllib`` response context-manager."""
    raw = json.dumps(body).encode("utf-8")

    class _Resp:
        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def read(self) -> bytes:
            return raw

    return _Resp()


class TestConstruction:
    @staticmethod
    def test_missing_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("LINTPDF_AUDIT_MODAL_URL", raising=False)
        from lintpdf.audit.customer import CustomerAuditor

        with pytest.raises(RuntimeError, match="LINTPDF_AUDIT_MODAL_URL"):
            CustomerAuditor()

    @staticmethod
    def test_explicit_url_bypasses_env(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("LINTPDF_AUDIT_MODAL_URL", raising=False)
        from lintpdf.audit.customer import CustomerAuditor

        auditor = CustomerAuditor(endpoint_url="https://stub.modal.run/")
        assert auditor._url == "https://stub.modal.run"  # type: ignore[attr-defined]


class TestAudit:
    @staticmethod
    def test_empty_findings_no_http(
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        called = MagicMock()
        monkeypatch.setattr("urllib.request.urlopen", called)

        from lintpdf.audit.customer import CustomerAuditor

        auditor = CustomerAuditor(endpoint_url="https://stub.modal.run")
        assert auditor.audit(b"%PDF-1.4", []) == []
        called.assert_not_called()

    @staticmethod
    def test_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "urllib.request.urlopen",
            MagicMock(
                return_value=_fake_response(
                    {
                        "verdicts": [
                            {"finding_index": 0, "status": "confirmed", "rationale": "ok"},
                            {"finding_index": 1, "status": "disputed", "rationale": "no overprint visible"},
                        ]
                    }
                )
            ),
        )

        from lintpdf.audit.customer import CustomerAuditor

        out = CustomerAuditor(endpoint_url="https://stub.modal.run").audit(
            b"%PDF-fake",
            [_FakeFinding(page_num=1), _FakeFinding(page_num=1, severity="warning")],
        )
        assert out[0] is not None and out[0].status == "confirmed"
        assert out[1] is not None and out[1].status == "disputed"
        assert out[1].model == "modal:qwen2-vl-7b"

    @staticmethod
    def test_out_of_order_response(monkeypatch: pytest.MonkeyPatch) -> None:
        """Verdicts arrive in reverse order; should still align."""
        monkeypatch.setattr(
            "urllib.request.urlopen",
            MagicMock(
                return_value=_fake_response(
                    {
                        "verdicts": [
                            {"finding_index": 1, "status": "disputed", "rationale": "r1"},
                            {"finding_index": 0, "status": "confirmed", "rationale": "r0"},
                        ]
                    }
                )
            ),
        )

        from lintpdf.audit.customer import CustomerAuditor

        out = CustomerAuditor(endpoint_url="https://stub.modal.run").audit(
            b"%PDF-fake",
            [_FakeFinding(page_num=1), _FakeFinding(page_num=1)],
        )
        assert out[0] is not None and out[0].status == "confirmed"
        assert out[0].rationale == "r0"
        assert out[1] is not None and out[1].status == "disputed"

    @staticmethod
    def test_transport_error_leaves_none(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "urllib.request.urlopen",
            MagicMock(side_effect=urllib.error.URLError("connection refused")),
        )

        from lintpdf.audit.customer import CustomerAuditor

        out = CustomerAuditor(endpoint_url="https://stub.modal.run").audit(
            b"%PDF-fake",
            [_FakeFinding(page_num=1), _FakeFinding(page_num=1)],
        )
        assert out == [None, None]

    @staticmethod
    def test_unknown_status_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "urllib.request.urlopen",
            MagicMock(
                return_value=_fake_response(
                    {
                        "verdicts": [
                            # Gibberish status — auditor should drop.
                            {"finding_index": 0, "status": "sparkle", "rationale": "?"},
                            {"finding_index": 1, "status": "confirmed", "rationale": "ok"},
                        ]
                    }
                )
            ),
        )

        from lintpdf.audit.customer import CustomerAuditor

        out = CustomerAuditor(endpoint_url="https://stub.modal.run").audit(
            b"%PDF-fake",
            [_FakeFinding(page_num=1), _FakeFinding(page_num=1)],
        )
        assert out[0] is None
        assert out[1] is not None and out[1].status == "confirmed"
