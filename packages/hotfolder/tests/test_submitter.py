"""Tests for the submitter — API calls, file routing, sidecar writing."""

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx

from lintpdf_hotfolder.submitter import Submitter


def _make_submitter(
    ready_queue: queue.Queue[Path],
    tmp_path: Path,
    shutdown: threading.Event,
) -> Submitter:
    """Create a submitter with test directories."""
    return Submitter(
        ready_queue=ready_queue,
        api_key="lpdf_test_key",
        base_url="https://api.lintpdf.com",
        profile="gwg-sheetfed",
        pass_dir=tmp_path / "pass",
        fail_dir=tmp_path / "fail",
        error_dir=tmp_path / "error",
        write_sidecar=True,
        poll_interval=0.1,
        shutdown_event=shutdown,
    )


def _mock_submit_response(job_id: str = "test-job-123") -> httpx.Response:
    resp = httpx.Response(
        status_code=202,
        json={"id": job_id, "status": "pending"},
        request=httpx.Request("POST", "https://api.lintpdf.com/api/v1/jobs"),
    )
    return resp


def _mock_poll_response(passed: bool = True) -> httpx.Response:
    return httpx.Response(
        status_code=200,
        json={
            "id": "test-job-123",
            "status": "complete",
            "profile_id": "gwg-sheetfed",
            "summary": {
                "passed": passed,
                "error_count": 0 if passed else 2,
                "warning_count": 0 if passed else 1,
                "advisory_count": 1,
                "total_findings": 1 if passed else 4,
            },
            "findings": []
            if passed
            else [
                {
                    "inspection_id": "GRD_FONT_001",
                    "severity": "error",
                    "message": "Font not embedded",
                    "page_num": 1,
                }
            ],
        },
        request=httpx.Request(
            "GET", "https://api.lintpdf.com/api/v1/jobs/test-job-123"
        ),
    )


@patch("lintpdf_hotfolder.submitter.httpx")
def test_pass_routes_to_pass_dir(mock_httpx: MagicMock, tmp_path: Path):
    """A passing file is moved to the pass directory with a sidecar."""
    mock_httpx.post.return_value = _mock_submit_response()
    mock_httpx.get.return_value = _mock_poll_response(passed=True)
    mock_httpx.HTTPError = httpx.HTTPError

    q: queue.Queue[Path] = queue.Queue()
    shutdown = threading.Event()
    sub = _make_submitter(q, tmp_path, shutdown)

    test_file = tmp_path / "good.pdf"
    test_file.write_bytes(b"%PDF-1.4 good content")

    sub._process_file(test_file)

    pass_dir = tmp_path / "pass"
    assert (pass_dir / "good.pdf").exists()
    sidecar = pass_dir / "good.pdf.lintpdf.json"
    assert sidecar.exists()
    data = json.loads(sidecar.read_text())
    assert data["passed"] is True
    assert data["job_id"] == "test-job-123"


@patch("lintpdf_hotfolder.submitter.httpx")
def test_fail_routes_to_fail_dir(mock_httpx: MagicMock, tmp_path: Path):
    """A failing file is moved to the fail directory with findings in sidecar."""
    mock_httpx.post.return_value = _mock_submit_response()
    mock_httpx.get.return_value = _mock_poll_response(passed=False)
    mock_httpx.HTTPError = httpx.HTTPError

    q: queue.Queue[Path] = queue.Queue()
    shutdown = threading.Event()
    sub = _make_submitter(q, tmp_path, shutdown)

    test_file = tmp_path / "bad.pdf"
    test_file.write_bytes(b"%PDF-1.4 bad content")

    sub._process_file(test_file)

    fail_dir = tmp_path / "fail"
    assert (fail_dir / "bad.pdf").exists()
    sidecar = fail_dir / "bad.pdf.lintpdf.json"
    assert sidecar.exists()
    data = json.loads(sidecar.read_text())
    assert data["passed"] is False
    assert data["summary"]["error_count"] == 2
    assert len(data["findings"]) == 1


@patch("lintpdf_hotfolder.submitter.httpx")
def test_submit_error_routes_to_error_dir(mock_httpx: MagicMock, tmp_path: Path):
    """A file that fails to submit is moved to the error directory."""
    mock_httpx.post.side_effect = httpx.ConnectError("Connection refused")
    mock_httpx.HTTPError = httpx.HTTPError

    q: queue.Queue[Path] = queue.Queue()
    shutdown = threading.Event()
    sub = _make_submitter(q, tmp_path, shutdown)

    test_file = tmp_path / "unreachable.pdf"
    test_file.write_bytes(b"%PDF-1.4 content")

    sub._process_file(test_file)

    error_dir = tmp_path / "error"
    assert (error_dir / "unreachable.pdf").exists()
    sidecar = error_dir / "unreachable.pdf.lintpdf.json"
    assert sidecar.exists()
    data = json.loads(sidecar.read_text())
    assert "error" in data


@patch("lintpdf_hotfolder.submitter.httpx")
def test_name_collision_handled(mock_httpx: MagicMock, tmp_path: Path):
    """If a file with the same name exists in the destination, a suffix is added."""
    mock_httpx.post.return_value = _mock_submit_response()
    mock_httpx.get.return_value = _mock_poll_response(passed=True)
    mock_httpx.HTTPError = httpx.HTTPError

    q: queue.Queue[Path] = queue.Queue()
    shutdown = threading.Event()
    sub = _make_submitter(q, tmp_path, shutdown)

    pass_dir = tmp_path / "pass"
    pass_dir.mkdir()
    (pass_dir / "dup.pdf").write_bytes(b"existing")

    test_file = tmp_path / "dup.pdf"
    test_file.write_bytes(b"%PDF-1.4 duplicate name")

    sub._process_file(test_file)

    assert (pass_dir / "dup_1.pdf").exists()
