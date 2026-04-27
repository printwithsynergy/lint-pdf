"""End-to-end engine smoke (PR 18 closer — matches scripts/smoke-preflight-v2.sh).

Hits a running engine instance (``LINTPDF_API_URL`` / ``LINTPDF_API_KEY``)
to confirm the v2 contract is wired:

  1. Submit a fixture PDF.
  2. Poll until terminal.
  3. Mint HTML / PDF / JSON / annotated PDF reports.
  4. Read the EPM verdict.
  5. Optionally explain a finding (skipped without LINTPDF_SMOKE_EXPLAIN=1
     since real Claude calls cost money).

Skipped automatically when LINTPDF_API_KEY is not set, so the suite stays
silent in repos that don't have a smoke target configured.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
import pytest

API_URL = os.environ.get("LINTPDF_API_URL", "https://api.lintpdf.com").rstrip("/")
API_KEY = os.environ.get("LINTPDF_API_KEY", "")
PROFILE_ID = os.environ.get("LINTPDF_PROFILE_ID", "lintpdf-default")
SMOKE_EXPLAIN = os.environ.get("LINTPDF_SMOKE_EXPLAIN", "0") == "1"

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "packages"
    / "engine"
    / "tests"
    / "fixtures"
    / "test-sample.pdf"
)

pytestmark = pytest.mark.skipif(
    not API_KEY,
    reason="LINTPDF_API_KEY not set — engine smoke is opt-in",
)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}"}


def _poll_until_terminal(client: httpx.Client, job_id: str, *, deadline_s: int = 300) -> dict:
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        resp = client.get(
            f"{API_URL}/api/v1/jobs/{job_id}",
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") in ("complete", "failed"):
            return data
        time.sleep(2)
    pytest.fail(f"job {job_id} did not reach terminal state within {deadline_s}s")


def test_smoke_e2e_against_live_engine() -> None:
    assert FIXTURE.exists(), f"missing fixture: {FIXTURE}"

    with httpx.Client() as client:
        # 1. submit
        with FIXTURE.open("rb") as fh:
            submit_resp = client.post(
                f"{API_URL}/api/v1/jobs",
                headers=_headers(),
                files={"file": (FIXTURE.name, fh, "application/pdf")},
                data={"profile_id": PROFILE_ID},
                timeout=120,
            )
        submit_resp.raise_for_status()
        job_id = submit_resp.json()["job_id"]

        # 2. poll
        result = _poll_until_terminal(client, job_id)
        assert result["status"] == "complete", (
            f"job ended with status={result['status']!r}"
        )

        # 3. mint reports
        mint_resp = client.post(
            f"{API_URL}/api/v1/jobs/{job_id}/reports",
            headers=_headers(),
            json={"formats": ["html", "pdf", "json", "annotated_pdf"]},
            timeout=120,
        )
        mint_resp.raise_for_status()
        formats_seen = {r["format"] for r in mint_resp.json().get("reports", [])}
        assert {"html", "pdf", "json", "annotated_pdf"}.issubset(formats_seen), (
            f"expected all 4 report formats; got {formats_seen}"
        )

        # 4. EPM verdict
        epm_resp = client.get(
            f"{API_URL}/api/v1/jobs/{job_id}/epm",
            headers=_headers(),
            timeout=30,
        )
        epm_resp.raise_for_status()
        epm = epm_resp.json()
        assert "tier" in epm
        assert epm["tier"] in {"pass", "pass_with_advisory", "marginal", "reject"}

        # 5. explain (optional — costs money against real Claude)
        if SMOKE_EXPLAIN:
            findings = result.get("findings") or []
            if findings:
                fid = findings[0].get("id")
                if fid:
                    expl_resp = client.post(
                        f"{API_URL}/api/v1/jobs/{job_id}/findings/{fid}/explain",
                        headers=_headers(),
                        timeout=60,
                    )
                    # 402 (cost-cap exceeded) is a valid terminal — don't fail.
                    if expl_resp.status_code == 200:
                        body = expl_resp.json()
                        assert "explanation" in body or "text" in body
                    elif expl_resp.status_code == 402:
                        pytest.skip("cost cap exceeded — explain path verified up to gate")
                    else:
                        expl_resp.raise_for_status()
