#!/usr/bin/env python3
"""LintPDF preflight engine stress-test harness.

Walks preflight-test-files/ (or any --dir), optionally clones each PDF
`clone-factor` times to reach a target total, and fires every file at
`POST /api/v1/jobs` concurrently with `ai_preset=full-ai-scan`.

Polls to completion, mints public report tokens for every job, and
writes a markdown summary with clickable viewer + report links plus a
scaling-defects appendix built from queue-depth / latency samples.

Designed for hundreds-of-files scale; the 13–15 file base set is just
tier-1. Pass `--clone-factor 8` for a ~100-job tier-2 run.

Usage:
    LINTPDF_ADMIN_KEY=... python3 scripts/stress_preflight_folder.py \
        --dir preflight-test-files \
        --count 100 --clone-factor 8 --workers 50

Stdlib only — no pip install needed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_BASE = os.environ.get("LINTPDF_API_BASE", "https://api.lintpdf.com").rstrip("/")
APP_BASE = os.environ.get("LINTPDF_APP_BASE", "https://app.lintpdf.com").rstrip("/")
REPORTS_BASE = os.environ.get("LINTPDF_REPORTS_BASE", "https://reports.lintpdf.com").rstrip("/")
ADMIN_KEY = os.environ.get("LINTPDF_ADMIN_KEY") or os.environ.get("LINTPDF_ADMIN_API_KEY")


# ---------------------------------------------------------------------------
# HTTP helper (stdlib only)
# ---------------------------------------------------------------------------


class HTTP:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: Any = None,
        raw_body: bytes | None = None,
        content_type: str | None = None,
        timeout: int = 120,
    ) -> tuple[int, Any]:
        url = path if path.startswith("http") else self.base + path
        h = {"Accept": "application/json"}
        if headers:
            h.update(headers)
        body: bytes | None = raw_body
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            h["Content-Type"] = "application/json"
        elif content_type:
            h["Content-Type"] = content_type
        req = urllib.request.Request(url, data=body, method=method.upper(), headers=h)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                code = resp.status
        except urllib.error.HTTPError as exc:
            raw = exc.read() if hasattr(exc, "read") else b""
            code = exc.code
        except urllib.error.URLError as exc:
            return 0, {"error": str(exc.reason)}
        except Exception as exc:  # noqa: BLE001 — network fuzz during stress
            return -1, {"error": repr(exc)}
        result: Any = raw
        try:
            if raw and raw[:1] in (b"{", b"["):
                result = json.loads(raw.decode("utf-8"))
        except Exception:
            result = raw
        return code, result


# ---------------------------------------------------------------------------
# Multipart encoder
# ---------------------------------------------------------------------------


def encode_multipart(
    fields: dict[str, str],
    files: dict[str, tuple[str, bytes, str]],
) -> tuple[bytes, str]:
    boundary = f"----lintpdf-{uuid.uuid4().hex}"
    out = bytearray()
    for name, value in fields.items():
        if value is None:
            continue
        out += f"--{boundary}\r\n".encode()
        out += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        out += str(value).encode("utf-8") + b"\r\n"
    for name, (filename, data, ctype) in files.items():
        safe = filename.replace('"', "_")
        out += f"--{boundary}\r\n".encode()
        out += (
            f'Content-Disposition: form-data; name="{name}"; filename="{safe}"\r\n'
        ).encode()
        out += f"Content-Type: {ctype}\r\n\r\n".encode()
        out += data + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


# ---------------------------------------------------------------------------
# Job bookkeeping
# ---------------------------------------------------------------------------


@dataclass
class JobRecord:
    pdf_path: Path
    submit_name: str
    job_id: str | None = None
    submit_ts: float = 0.0
    submit_http: int = 0
    terminal_ts: float = 0.0
    terminal_status: str = ""
    findings: dict[str, int] = field(default_factory=dict)
    verdict: str = ""
    submit_error: str = ""
    poll_error: str = ""
    viewer_url: str = ""
    html_url: str = ""
    pdf_url: str = ""
    json_url: str = ""
    report_error: str = ""

    @property
    def duration_s(self) -> float:
        if self.submit_ts and self.terminal_ts:
            return round(self.terminal_ts - self.submit_ts, 1)
        return 0.0


# ---------------------------------------------------------------------------
# Admin bootstrap (tenant + API key + AI entitlement + quotas)
# ---------------------------------------------------------------------------


def bootstrap_tenant(http: HTTP) -> tuple[str, str]:
    if not ADMIN_KEY:
        sys.exit("LINTPDF_ADMIN_KEY (or LINTPDF_ADMIN_API_KEY) is required")
    admin = {"X-Admin-Key": ADMIN_KEY}
    label = f"stress-{secrets.token_hex(4)}"
    code, body = http.request(
        "POST",
        "/api/v1/admin/tenants",
        headers=admin,
        json_body={"name": label, "contact_email": f"{label}@example.test", "plan": "scale"},
    )
    if code not in (200, 201) or not isinstance(body, dict):
        sys.exit(f"bootstrap: create tenant failed: {code} {body!r}")
    tenant_id = body["id"]
    code, body = http.request(
        "POST",
        f"/api/v1/admin/tenants/{tenant_id}/keys",
        headers=admin,
        json_body={"label": "stress-suite"},
    )
    if code not in (200, 201) or not isinstance(body, dict):
        sys.exit(f"bootstrap: mint key failed: {code} {body!r}")
    api_key = body["raw_key"]
    # Enable AI + grant generous AI credits + file quota for tier-2/3 runs.
    http.request(
        "PUT",
        f"/api/v1/admin/tenants/{tenant_id}/ai?ai_enabled=true",
        headers=admin,
        json_body={"enabled": True},
    )
    http.request(
        "POST",
        f"/api/v1/admin/tenants/{tenant_id}/ai/credits",
        headers=admin,
        json_body={"credits": 100_000, "expires_in_days": 1},
    )
    http.request(
        "POST",
        f"/api/v1/admin/tenants/{tenant_id}/files/packages",
        headers=admin,
        json_body={"files": 2000, "expires_in_days": 1},
    )
    return tenant_id, api_key


# ---------------------------------------------------------------------------
# Submit / poll / mint
# ---------------------------------------------------------------------------


def submit_job(
    http: HTTP,
    api_key: str,
    rec: JobRecord,
    profile_id: str,
    ai_preset: str,
    *,
    upload_timeout_s: int = 600,
    max_retries: int = 3,
) -> None:
    pdf_bytes = rec.pdf_path.read_bytes()
    fields = {
        "profile_id": profile_id,
        "ai_enabled": "true",
        "ai_categories": "all",
        "ai_preset": ai_preset,
    }
    body, ctype = encode_multipart(
        fields, {"file": (rec.submit_name, pdf_bytes, "application/pdf")}
    )
    rec.submit_ts = time.time()
    last_code = 0
    last_resp: Any = None
    for attempt in range(1, max_retries + 1):
        code, resp = http.request(
            "POST",
            "/api/v1/jobs",
            headers={"Authorization": f"Bearer {api_key}"},
            raw_body=body,
            content_type=ctype,
            timeout=upload_timeout_s,
        )
        last_code, last_resp = code, resp
        if code in (200, 201, 202) and isinstance(resp, dict) and resp.get("job_id"):
            rec.submit_http = code
            rec.job_id = resp["job_id"]
            if attempt > 1:
                rec.submit_error = (
                    f"recovered after {attempt - 1} retry(ies); last error before success"
                )
            return
        # Retry on transient network / edge failures: timeouts (-1), SSL (-1),
        # 503 "DNS cache overflow" / 502 / 504 / 429.
        if code in (-1, 0, 429, 502, 503, 504):
            time.sleep(min(2 ** attempt, 15))
            continue
        break
    rec.submit_http = last_code
    rec.submit_error = f"{last_code}: {last_resp!r}"[:400]


def poll_job(http: HTTP, api_key: str, rec: JobRecord, timeout_s: int) -> None:
    if not rec.job_id:
        return
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        code, body = http.request(
            "GET",
            f"/api/v1/jobs/{rec.job_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        if isinstance(body, dict):
            status = body.get("status", "")
            if status in ("complete", "failed"):
                rec.terminal_ts = time.time()
                rec.terminal_status = status
                summary = body.get("summary") or {}
                if isinstance(summary, dict):
                    rec.findings = {
                        "total": int(summary.get("total_findings") or 0),
                        "error": int(summary.get("error_count") or 0),
                        "warning": int(summary.get("warning_count") or 0),
                        "advisory": int(summary.get("advisory_count") or 0),
                    }
                    rec.verdict = "pass" if summary.get("passed") else "fail"
                return
        time.sleep(5)
    rec.poll_error = f"timeout after {timeout_s}s"


def mint_reports(http: HTTP, api_key: str, rec: JobRecord) -> None:
    if not rec.job_id or rec.terminal_status != "complete":
        return
    code, body = http.request(
        "POST",
        f"/api/v1/jobs/{rec.job_id}/reports",
        headers={"Authorization": f"Bearer {api_key}"},
        json_body={
            "formats": ["html", "pdf", "json", "annotated_pdf"],
            "expiry_days": 7,
            "allow_annotations": False,
            "require_visitor_email": False,
        },
        timeout=60,
    )
    if code not in (200, 201) or not isinstance(body, dict):
        rec.report_error = f"{code}: {body!r}"[:400]
        return
    for entry in body.get("reports", []) or []:
        fmt = entry.get("format")
        url = entry.get("url", "")
        viewer = entry.get("viewer_url", "")
        if fmt == "html":
            rec.html_url = url
            rec.viewer_url = viewer or rec.viewer_url
        elif fmt == "pdf":
            rec.pdf_url = url
        elif fmt == "json":
            rec.json_url = url
        elif fmt == "annotated_pdf" and not rec.pdf_url:
            rec.pdf_url = url
    if not rec.viewer_url:
        # Fall back to the first token we saw.
        for entry in body.get("reports", []) or []:
            tok = entry.get("token")
            if tok:
                rec.viewer_url = f"{APP_BASE}/view/{tok}"
                break


# ---------------------------------------------------------------------------
# Metrics sampler (background thread) + file discovery + cloning
# ---------------------------------------------------------------------------


def sample_metrics(
    http: HTTP, api_key: str, stop: threading.Event, csv_path: Path
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            ["iso_ts", "queue_depth_default", "queue_depth_priority", "workers", "status_http"]
        )
        while not stop.is_set():
            code, body = http.request(
                "GET",
                "/api/v1/status",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15,
            )
            default_q = priority_q = workers = -1
            if isinstance(body, dict):
                queues = body.get("queues") or {}
                if isinstance(queues, dict):
                    default_q = int(queues.get("default") or 0)
                    priority_q = int(queues.get("priority") or 0)
                workers = int(body.get("worker_count") or 0)
            w.writerow(
                [
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    default_q,
                    priority_q,
                    workers,
                    code,
                ]
            )
            f.flush()
            stop.wait(15)


def discover_and_clone(src_dir: Path, total: int, clone_factor: int) -> list[JobRecord]:
    pdfs = sorted(p for p in src_dir.rglob("*.pdf") if p.is_file())
    if not pdfs:
        sys.exit(f"No PDFs found under {src_dir}")
    records: list[JobRecord] = []
    if clone_factor <= 1:
        for p in pdfs[:total]:
            records.append(JobRecord(pdf_path=p, submit_name=p.name))
        return records
    # Fan out: produce clones until we reach `total`. Rename each clone so
    # the engine's Redis `pdf_cache:{file_key}` short-circuit can't collapse
    # them together at the storage layer.
    idx = 0
    out: list[JobRecord] = []
    while len(out) < total:
        base = pdfs[idx % len(pdfs)]
        clone_idx = idx // len(pdfs)
        if clone_idx >= clone_factor:
            break
        # Deterministic suffix so reruns are identifiable.
        digest = hashlib.sha1(f"{base.name}:{clone_idx}".encode()).hexdigest()[:8]
        out.append(
            JobRecord(
                pdf_path=base,
                submit_name=f"{base.stem}__clone-{clone_idx:02d}-{digest}{base.suffix}",
            )
        )
        idx += 1
    return out[:total]


# ---------------------------------------------------------------------------
# Results writer
# ---------------------------------------------------------------------------


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round((pct / 100.0) * (len(s) - 1)))))
    return round(s[k], 1)


def write_results(
    out_path: Path,
    records: list[JobRecord],
    start_ts: float,
    end_ts: float,
    args: argparse.Namespace,
    tenant_id: str,
) -> None:
    complete = [r for r in records if r.terminal_status == "complete"]
    failed = [r for r in records if r.terminal_status == "failed"]
    no_submit = [r for r in records if not r.job_id]
    timed_out = [r for r in records if r.poll_error]
    durations = [r.duration_s for r in complete if r.duration_s > 0]

    lines: list[str] = []
    lines.append("# LintPDF Preflight Stress Test Results\n")
    lines.append(f"- Tenant: `{tenant_id}` (throwaway)")
    lines.append(f"- Profile: `{args.profile}`   AI preset: `{args.ai_preset}`")
    lines.append(f"- Source dir: `{args.dir}`")
    lines.append(f"- Count: **{len(records)}**   Workers: {args.workers}   Clone factor: {args.clone_factor}")
    lines.append(
        f"- Wall clock: **{round(end_ts - start_ts, 1)}s** ({datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat(timespec='seconds')} → {datetime.fromtimestamp(end_ts, tz=timezone.utc).isoformat(timespec='seconds')})"
    )
    lines.append(
        f"- Terminal: **{len(complete)} complete** · {len(failed)} failed · {len(timed_out)} timed out · {len(no_submit)} never submitted"
    )
    if durations:
        lines.append(
            f"- Latency (submit→complete): p50 **{percentile(durations, 50)}s** · p90 {percentile(durations, 90)}s · p99 {percentile(durations, 99)}s · max {max(durations)}s"
        )
    lines.append("\n## Report links (click for manual audit)\n")
    lines.append("| # | File | Duration | Findings (E/W/A) | Verdict | Viewer | HTML | PDF | JSON |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(records, 1):
        f_str = (
            f"{r.findings.get('error',0)}/{r.findings.get('warning',0)}/{r.findings.get('advisory',0)}"
            if r.findings
            else "—"
        )
        verdict = r.verdict or (r.terminal_status or "?")
        viewer = f"[view]({r.viewer_url})" if r.viewer_url else "—"
        html = f"[html]({r.html_url})" if r.html_url else "—"
        pdf_l = f"[pdf]({r.pdf_url})" if r.pdf_url else "—"
        json_l = f"[json]({r.json_url})" if r.json_url else "—"
        # Escape pipes in file names for markdown safety.
        name = r.submit_name.replace("|", "\\|")
        lines.append(
            f"| {i} | `{name}` | {r.duration_s}s | {f_str} | {verdict} | {viewer} | {html} | {pdf_l} | {json_l} |"
        )

    lines.append("\n## Bugs & Slowdowns\n")
    buggy = [r for r in records if r.submit_error or r.poll_error or r.report_error]
    if not buggy and not failed:
        median = percentile(durations, 50) if durations else 0.0
        slow = [r for r in complete if r.duration_s > 2 * median and median > 0]
        if slow:
            lines.append("### Jobs slower than 2× median\n")
            for r in slow:
                lines.append(f"- `{r.submit_name}` — {r.duration_s}s (median {median}s)")
        else:
            lines.append("_None observed._")
    else:
        for r in buggy + [f for f in failed if f not in buggy]:
            problem = r.submit_error or r.poll_error or r.report_error or r.terminal_status
            lines.append(f"- `{r.submit_name}` — {problem}")

    lines.append("\n## Scaling defects (prior-known caps that may have fired)\n")
    lines.append(
        "See `preflight-stress-metrics.csv` for queue-depth/worker-count time-series captured during the run. "
        "Cross-reference spikes with the known ceilings: Modal `max_containers=5`, Celery pool 20, Postgres `max_connections=100`."
    )

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run(args: argparse.Namespace) -> int:
    http = HTTP(API_BASE)
    print(f"[preflight] API={API_BASE}  APP={APP_BASE}")

    print("[preflight] bootstrap throwaway tenant …")
    tenant_id, api_key = bootstrap_tenant(http)
    print(f"[preflight]   tenant_id={tenant_id}  api_key={api_key[:14]}…")

    records = discover_and_clone(Path(args.dir), args.count, args.clone_factor)
    print(f"[preflight] {len(records)} submissions prepared "
          f"(base files: {len({r.pdf_path for r in records})}, clone factor: {args.clone_factor})")

    stop_metrics = threading.Event()
    metrics_thread = threading.Thread(
        target=sample_metrics,
        args=(http, api_key, stop_metrics, Path(args.metrics_out)),
        daemon=True,
    )
    metrics_thread.start()

    start_ts = time.time()

    # Phase 1: submit all jobs in parallel with a slight stagger so we
    # don't melt the edge proxy with N simultaneous 40MB uploads (the
    # first smoke run triggered "503 DNS cache overflow" and SSL EOFs
    # when 15 uploads hit in the same millisecond).
    stagger_ms = max(50, int((args.ramp_up_s * 1000) / max(1, len(records))))
    print(
        f"[preflight] phase 1: submitting {len(records)} jobs  "
        f"(workers={args.workers}, stagger={stagger_ms}ms, ramp={args.ramp_up_s}s) …"
    )
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = []
        for r in records:
            futures.append(
                pool.submit(submit_job, http, api_key, r, args.profile, args.ai_preset)
            )
            time.sleep(stagger_ms / 1000.0)
        for _ in as_completed(futures):
            pass
    submitted = sum(1 for r in records if r.job_id)
    print(f"[preflight]   submitted {submitted}/{len(records)} "
          f"({len(records) - submitted} rejected)")

    # Phase 2: poll all jobs in parallel for terminal state.
    print(f"[preflight] phase 2: polling …  (timeout {args.timeout_s}s/job)")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(poll_job, http, api_key, r, args.timeout_s) for r in records if r.job_id
        ]
        for _ in as_completed(futures):
            pass
    finished = sum(1 for r in records if r.terminal_status)
    print(f"[preflight]   terminal: {finished}/{submitted}")

    # Phase 3: mint report tokens in parallel.
    print("[preflight] phase 3: minting report tokens …")
    with ThreadPoolExecutor(max_workers=min(args.workers, 20)) as pool:
        futures = [pool.submit(mint_reports, http, api_key, r) for r in records]
        for _ in as_completed(futures):
            pass
    with_links = sum(1 for r in records if r.viewer_url)
    print(f"[preflight]   reports minted: {with_links}/{finished}")

    end_ts = time.time()
    stop_metrics.set()
    metrics_thread.join(timeout=5)

    out = Path(args.out)
    write_results(out, records, start_ts, end_ts, args, tenant_id)
    print(f"[preflight] results written → {out.resolve()}")
    return 0 if with_links == len(records) else (1 if with_links == 0 else 0)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    p.add_argument("--dir", default="preflight-test-files", help="source directory to glob for PDFs")
    p.add_argument("--count", type=int, default=100, help="total job submissions (default: 100)")
    p.add_argument(
        "--clone-factor",
        type=int,
        default=8,
        help="fan-out factor: each base PDF is submitted N times under unique names (default: 8)",
    )
    p.add_argument("--workers", type=int, default=50, help="max concurrent workers (default: 50)")
    p.add_argument("--profile", default="lintpdf-default")
    p.add_argument("--ai-preset", default="full-ai-scan")
    p.add_argument("--timeout-s", type=int, default=1800, help="per-job poll timeout (default: 30min)")
    p.add_argument(
        "--ramp-up-s",
        type=int,
        default=10,
        help="time in seconds across which to stagger submissions (default: 10s). "
        "Avoids hammering edge DNS / TCP connection pool with N simultaneous uploads.",
    )
    p.add_argument("--out", default="preflight-stress-results.md")
    p.add_argument("--metrics-out", default="preflight-stress-metrics.csv")
    return p.parse_args()


if __name__ == "__main__":
    sys.exit(run(parse_args()))
