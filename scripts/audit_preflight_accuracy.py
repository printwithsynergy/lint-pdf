#!/usr/bin/env python3
"""Audit the preflight engine against a golden-PDF corpus.

Walks ``tests/fixtures/accuracy/`` (or any directory passed via
``--corpus``), pairs each ``*.pdf`` with its ``*.expected.json``
annotations, submits each PDF through the live engine, pulls
the findings back, runs ``InternalAuditor`` (Claude Opus 4.7
vision) against them, and writes a markdown report with per-
inspection-id accuracy plus a disputed / missed-finding summary.

Operator-only. Never runs against customer jobs. Requires:

  * ``ANTHROPIC_API_KEY`` in the env
  * ``uv sync --extra ai`` in the engine venv
  * ``LINTPDF_API_BASE`` (default ``https://api.lintpdf.com``) +
    ``LINTPDF_ADMIN_API_KEY`` so we can bootstrap a test tenant

Golden fixture shape (``*.expected.json``)::

    {
      "description": "Amalgam Catalyst wine label, 9-spot",
      "expected_inspection_ids": ["LPDF_INK_003", "PDFX4-001", ...],
      "known_disputed": [],
      "known_missing": []
    }

- ``expected_inspection_ids``: the set the engine must emit (order
  doesn't matter; extras are allowed and get audited).
- ``known_disputed``: IDs we know the engine gets wrong today;
  surfaced as expected-disputes rather than regressions.
- ``known_missing``: findings the AI says the engine should emit
  but doesn't. Drives inspector backlogs.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("audit")


def _post_multipart(url: str, pdf_path: Path, api_key: str, profile_id: str) -> dict:
    """Minimal stdlib multipart-form POST (no requests dep)."""
    import io
    import uuid

    boundary = "----lintpdfaudit" + uuid.uuid4().hex
    body = io.BytesIO()
    b = lambda s: body.write(s.encode() if isinstance(s, str) else s)  # noqa: E731
    b(f"--{boundary}\r\n")
    b(f'Content-Disposition: form-data; name="file"; filename="{pdf_path.name}"\r\n')
    b("Content-Type: application/pdf\r\n\r\n")
    b(pdf_path.read_bytes())
    b(f"\r\n--{boundary}\r\n")
    b('Content-Disposition: form-data; name="profile_id"\r\n\r\n')
    b(profile_id)
    b(f"\r\n--{boundary}\r\n")
    b('Content-Disposition: form-data; name="ai_preset"\r\n\r\n')
    b("full-ai-scan")
    b(f"\r\n--{boundary}--\r\n")
    req = urllib.request.Request(
        url,
        data=body.getvalue(),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())


def _get_job(api_base: str, job_id: str, api_key: str) -> dict:
    url = f"{api_base.rstrip('/')}/api/v1/jobs/{urllib.parse.quote(job_id)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _bootstrap_tenant(api_base: str, admin_key: str) -> str:
    """Create an ephemeral test tenant; return its API key."""
    body = json.dumps(
        {
            "name": f"audit-harness-{int(time.time())}",
            "plan": "enterprise",
            "rate_limit_daily": 500,
            "max_file_size_mb": 500,
        }
    ).encode()
    req = urllib.request.Request(
        f"{api_base.rstrip('/')}/api/v1/admin/tenants",
        data=body,
        method="POST",
        headers={
            "X-Admin-Key": admin_key,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["api_key"]


def _wait_terminal(
    api_base: str, job_id: str, api_key: str, timeout_s: int
) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        body = _get_job(api_base, job_id, api_key)
        if body.get("status") in {"complete", "failed"}:
            return body
        time.sleep(5)
    raise TimeoutError(f"job {job_id} did not terminate within {timeout_s}s")


def _load_fixtures(corpus: Path) -> list[tuple[Path, dict]]:
    """Pair every .pdf with its sibling .expected.json."""
    out: list[tuple[Path, dict]] = []
    for pdf in sorted(corpus.glob("*.pdf")):
        expected = pdf.with_suffix(".expected.json")
        if not expected.exists():
            log.warning("skip: %s has no .expected.json", pdf.name)
            continue
        out.append((pdf, json.loads(expected.read_text())))
    return out


def _findings_from_job(job: dict) -> list[dict]:
    return job.get("findings") or []


def _audit_one(
    pdf_path: Path, job: dict, api_base: str
) -> list[dict[str, Any]]:
    """Run the internal auditor against one job's findings.

    Returns a list of dicts aligned with ``job.findings``:
    ``{inspection_id, severity, page_num, status, rationale}``.
    """
    from siftpdf.audit.internal import InternalAuditor

    # We don't have a SQLAlchemy session here (no DB), so build
    # lightweight objects that quack like ``JobFinding`` for the
    # auditor's ``f.bbox_x0`` / ``f.page_num`` / etc. access.
    class _F:
        def __init__(self, d: dict) -> None:
            self.inspection_id = d.get("inspection_id", "")
            self.severity = d.get("severity", "advisory")
            self.message = d.get("message", "")
            self.page_num = d.get("page_num")
            bb = d.get("bbox")
            self.bbox_x0 = bb[0] if bb else None
            self.bbox_y0 = bb[1] if bb else None
            self.bbox_x1 = bb[2] if bb else None
            self.bbox_y1 = bb[3] if bb else None

    findings = [_F(d) for d in _findings_from_job(job)]
    auditor = InternalAuditor()
    verdicts = auditor.audit(pdf_path.read_bytes(), findings)

    rows = []
    for f, v in zip(_findings_from_job(job), verdicts, strict=False):
        rows.append(
            {
                "inspection_id": f.get("inspection_id"),
                "severity": f.get("severity"),
                "page_num": f.get("page_num"),
                "message": f.get("message", "")[:200],
                "status": v.status if v else "skipped",
                "rationale": (v.rationale if v else None),
            }
        )
    return rows


def _write_report(out_path: Path, runs: list[dict]) -> None:
    """Render the markdown audit report."""
    lines: list[str] = [
        "# Preflight Accuracy Audit",
        "",
        "Claude Opus 4.7 vision verdicts against the golden-PDF corpus. "
        "Status values: `confirmed` (engine correct), `disputed` (engine "
        "wrong), `needs_context` (needs JDF / brand spec), `skipped` "
        "(auditor gave no verdict — treat as manual-review).",
        "",
    ]
    overall = Counter()
    for run in runs:
        for row in run["rows"]:
            overall[row["status"]] += 1
    total = sum(overall.values()) or 1
    lines.append(f"**Corpus files:** {len(runs)}")
    lines.append(f"**Total findings audited:** {total}")
    for status in ("confirmed", "disputed", "needs_context", "error", "skipped"):
        if overall[status]:
            pct = 100 * overall[status] / total
            lines.append(f"  - `{status}`: {overall[status]}  ({pct:.1f} %)")
    lines.append("")

    for run in runs:
        lines.append(f"## {run['pdf'].name}")
        cls = run["expected"].get("class")
        if cls:
            lines.append(f"- **Class:** `{cls}`")
        expected = set(run["expected"].get("expected_inspection_ids", []))
        emitted = {r["inspection_id"] for r in run["rows"]}
        if not expected:
            # Coverage-only fixture — we haven't hand-curated an
            # expected inspection-id set yet. Surface the emitted list
            # so the operator can paste it straight into
            # `expected_inspection_ids` to harden the fixture for the
            # next run.
            lines.append(
                "- **Coverage-only** (no expected_inspection_ids in"
                " fixture yet). Emitted on this run: "
                + ", ".join(sorted(emitted) or ["(none)"]),
            )
        else:
            missing_from_emit = sorted(expected - emitted)
            lines.append(
                f"- **Expected inspection IDs:** {len(expected)}  "
                f"**Emitted:** {len(emitted)}",
            )
            if missing_from_emit:
                lines.append(
                    f"- **MISSING from emit** (engine regression suspected): "
                    f"{', '.join(missing_from_emit)}",
                )
        lines.append("")
        for row in run["rows"]:
            status = row["status"]
            if status in {"confirmed", "skipped"}:
                continue
            lines.append(
                f"- `[{status}]` **{row['inspection_id']}** (p{row['page_num']}, "
                f"{row['severity']}) — {row['rationale'] or '(no rationale)'}",
            )
        lines.append("")

    out_path.write_text("\n".join(lines))
    log.info("report written to %s", out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("audit-accuracy-report.md"))
    parser.add_argument(
        "--api-base", default=os.environ.get("LINTPDF_API_BASE", "https://api.lintpdf.com")
    )
    parser.add_argument(
        "--admin-key", default=os.environ.get("LINTPDF_ADMIN_API_KEY", "")
    )
    parser.add_argument("--profile-id", default="lintpdf-default")
    parser.add_argument("--job-timeout-s", type=int, default=900)
    args = parser.parse_args()

    if not args.admin_key:
        parser.error("LINTPDF_ADMIN_API_KEY env var or --admin-key required")
    if "ANTHROPIC_API_KEY" not in os.environ:
        parser.error("ANTHROPIC_API_KEY required for the internal auditor")

    fixtures = _load_fixtures(args.corpus)
    if not fixtures:
        parser.error(f"no .pdf + .expected.json pairs in {args.corpus}")

    log.info("bootstrapping test tenant against %s", args.api_base)
    tenant_key = _bootstrap_tenant(args.api_base, args.admin_key)

    runs: list[dict] = []
    for pdf, expected in fixtures:
        log.info("submitting %s", pdf.name)
        submit = _post_multipart(
            f"{args.api_base.rstrip('/')}/api/v1/jobs",
            pdf,
            tenant_key,
            args.profile_id,
        )
        job_id = submit["job_id"]
        log.info("  job_id=%s waiting up to %ds", job_id, args.job_timeout_s)
        job = _wait_terminal(args.api_base, job_id, tenant_key, args.job_timeout_s)
        if job.get("status") != "complete":
            log.warning("  job %s ended %s; skipping audit", job_id, job.get("status"))
            continue
        log.info("  auditing %d findings", len(_findings_from_job(job)))
        rows = _audit_one(pdf, job, args.api_base)
        runs.append({"pdf": pdf, "expected": expected, "job_id": job_id, "rows": rows})

    _write_report(args.out, runs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
