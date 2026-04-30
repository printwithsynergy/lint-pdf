#!/usr/bin/env python3
"""Seed DB with preflight results from the test PDF and start the engine server.

This script:
1. Creates a tenant + API key in the local PostgreSQL database
2. Runs preflight on the test PDF (engine + AI)
3. Generates HTML and PDF reports
4. Stores reports in local filesystem storage
5. Creates report tokens in the database
6. Starts the FastAPI server so reports are served at /r/{token} URLs
   — the same route structure as reports.lintpdf.com
"""

import hashlib
import json
import os
import secrets
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Set environment before importing anything from siftpdf
os.environ["LINTPDF_DATABASE_URL"] = "postgresql://lintpdf:lintpdf@localhost:5432/lintpdf"
os.environ["DATABASE_URL"] = "postgresql://lintpdf:lintpdf@localhost:5432/lintpdf"
os.environ["LINTPDF_REDIS_URL"] = "redis://localhost:6379/0"
os.environ["LINTPDF_REPORT_BASE_URL"] = "http://localhost:8000"
os.environ["LINTPDF_CLAMAV_URL"] = ""  # skip ClamAV for local run
os.environ["LINTPDF_SECRET_KEY"] = "local-dev-secret-key"

PDF_PATH = "/home/user/lint-pdf/packages/web/public/lintpdf_preflight_test_final.pdf"
LOCAL_STORAGE_DIR = "/home/user/lint-pdf/packages/engine/.local-storage"

# ── Local filesystem storage backend ──────────────────────────────────────────

from siftpdf.api.storage import StorageBackend


class LocalFileStorage(StorageBackend):
    """Stores files on the local filesystem instead of S3."""

    def __init__(self, base_dir: str) -> None:
        super().__init__()
        self._base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        full = os.path.join(self._base_dir, key)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        return full

    def _get_client(self):
        return None

    def upload_pdf(self, tenant_id, job_id, pdf_bytes):
        key = f"{tenant_id}/{job_id}/input.pdf"
        with open(self._path(key), "wb") as f:
            f.write(pdf_bytes)
        return key

    def download_pdf(self, file_key):
        p = self._path(file_key)
        if not os.path.exists(p):
            raise FileNotFoundError(f"File not found: {file_key}")
        with open(p, "rb") as f:
            return f.read()

    def upload_results(self, tenant_id, job_id, results_json):
        key = f"{tenant_id}/{job_id}/results.json"
        with open(self._path(key), "wb") as f:
            f.write(results_json)
        return key

    def upload_report(self, tenant_id, job_id, fmt, content):
        key = f"reports/{tenant_id}/{job_id}/report.{fmt}"
        with open(self._path(key), "wb") as f:
            f.write(content)
        return key

    def download_report(self, tenant_id, job_id, fmt):
        key = f"reports/{tenant_id}/{job_id}/report.{fmt}"
        p = self._path(key)
        if not os.path.exists(p):
            raise FileNotFoundError(f"Report not found: {key}")
        with open(p, "rb") as f:
            return f.read()

    def delete_file(self, file_key):
        p = self._path(file_key)
        if os.path.exists(p):
            os.remove(p)

    def generate_presigned_url(self, file_key, expires_in=3600):
        return f"http://localhost:8000/storage/{file_key}"

    def upload_raw(self, key, data, content_type="application/octet-stream"):
        with open(self._path(key), "wb") as f:
            f.write(data)
        return key

    def download_raw(self, key):
        p = self._path(key)
        if not os.path.exists(p):
            return None
        with open(p, "rb") as f:
            return f.read()


def main():
    # ── 1. Initialize database ────────────────────────────────────────────────
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from siftpdf.api.models import (
        Base,
        Job,
        JobFinding,
        JobStatus,
        ReportToken,
        Tenant,
    )
    from siftpdf.tenants.models import TenantPlan

    db_url = os.environ["LINTPDF_DATABASE_URL"]
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # ── 2. Create tenant ──────────────────────────────────────────────────────
    api_key = "lintpdf-local-test-key"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    tenant = db.query(Tenant).filter(Tenant.api_key_hash == api_key_hash).first()
    if tenant is None:
        tenant = Tenant(
            id=uuid.uuid4(),
            name="LintPDF Test Tenant",
            api_key_hash=api_key_hash,
            plan=TenantPlan.ENTERPRISE,
            rate_limit_daily=1000,
            max_file_size_mb=500,
            contact_email="test@lintpdf.com",
        )
        db.add(tenant)
        db.commit()
        print(f"Created tenant: {tenant.id}")
    else:
        print(f"Using existing tenant: {tenant.id}")

    # ── 3. Run preflight ──────────────────────────────────────────────────────
    print(f"\nLoading PDF: {PDF_PATH}")
    with open(PDF_PATH, "rb") as f:
        pdf_bytes = f.read()
    print(f"  File size: {len(pdf_bytes):,} bytes")

    from siftpdf.profiles.orchestrator import PreflightOrchestrator
    from siftpdf.profiles.schema import AIFeatureConfig, PreflightProfile

    profile = PreflightProfile(
        name="Full Preflight + AI",
        conformance=None,
        workflow="CMYK",
        checks={
            "enabled": ["LPDF_*", "PDFX4-*", "PDFX1A-*", "PDFA-*", "AI_*"],
            "disabled": [],
            "severity_overrides": {},
        },
        thresholds={
            "min_dpi": 150.0,
            "max_dpi": 600.0,
            "tac_limit": 300.0,
            "min_bleed_mm": 3.0,
            "hairline_threshold": 0.25,
            "small_text_threshold": 6.0,
            "safety_margin_mm": 3.0,
        },
        ai=AIFeatureConfig(enabled=True, categories=["all"], features=[]),
    )

    print("\nRunning preflight checks (engine + AI)...")
    start = time.time()
    orchestrator = PreflightOrchestrator(profile, profile_id="full-preflight-ai")
    result = orchestrator.run(pdf_bytes)
    elapsed = time.time() - start
    print(f"  Completed in {elapsed:.1f}s")

    s = result.summary
    print(f"\n  Verdict:   {'PASS' if s.passed else 'FAIL'}")
    print(
        f"  Findings:  {s.total_findings} ({s.error_count}E / {s.warning_count}W / {s.advisory_count}A)"
    )

    # ── 4. Create job record ──────────────────────────────────────────────────
    job_id = uuid.UUID(result.job_id)

    # Store the original PDF
    storage = LocalFileStorage(LOCAL_STORAGE_DIR)
    file_key = storage.upload_pdf(str(tenant.id), str(job_id), pdf_bytes)

    result_json = {
        "job_id": str(job_id),
        "profile_id": result.profile_id,
        "duration_ms": result.duration_ms,
        "summary": {
            "total_findings": s.total_findings,
            "error_count": s.error_count,
            "warning_count": s.warning_count,
            "advisory_count": s.advisory_count,
            "passed": s.passed,
            "page_count": s.page_count,
            "file_size_bytes": s.file_size_bytes,
        },
        "metadata": {
            **result.metadata,
            "file_key": file_key,
        },
        "findings": [],
    }

    job = Job(
        id=job_id,
        tenant_id=tenant.id,
        profile_id=result.profile_id,
        status=JobStatus.COMPLETE,
        file_key=file_key,
        file_name="lintpdf_preflight_test_final.pdf",
        file_size_bytes=len(pdf_bytes),
        result_json=result_json,
        duration_ms=result.duration_ms,
    )
    db.add(job)

    # ── 5. Create finding records ─────────────────────────────────────────────
    for f in result.findings:
        finding = JobFinding(
            id=uuid.uuid4(),
            job_id=job_id,
            inspection_id=f.inspection_id,
            severity=f.severity.value,
            message=f.message,
            page_num=f.page_num,
            object_id=f.object_id,
            object_type=f.object_type,
            source=f.source or "engine",
            category=f.category,
            details=f.details,
            bbox_x0=f.bbox[0] if f.bbox else None,
            bbox_y0=f.bbox[1] if f.bbox else None,
            bbox_x1=f.bbox[2] if f.bbox else None,
            bbox_y1=f.bbox[3] if f.bbox else None,
        )
        db.add(finding)

    db.commit()
    print(f"\n  Job created: {job_id}")
    print(f"  {len(result.findings)} findings stored")

    # ── 6. Generate reports ───────────────────────────────────────────────────
    from siftpdf.reports.engine import ReportEngine

    report_engine = ReportEngine()
    base_url = os.environ["LINTPDF_REPORT_BASE_URL"]

    tokens = {}
    for fmt in ["html", "pdf"]:
        print(f"\n  Generating {fmt.upper()} report...")
        report_bytes = report_engine.generate(
            result,
            fmt,
            pdf_bytes=pdf_bytes,
            detail_level="comprehensive",
        )

        # Store in local filesystem
        storage.upload_report(str(tenant.id), str(job_id), fmt, report_bytes)

        # Create token
        token_str = secrets.token_urlsafe(32)
        report_token = ReportToken(
            id=uuid.uuid4(),
            job_id=job_id,
            tenant_id=tenant.id,
            token=token_str,
            format=fmt,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            accessed_count=0,
        )
        db.add(report_token)
        tokens[fmt] = token_str

    db.commit()
    db.close()

    # ── 7. Print report URLs ──────────────────────────────────────────────────
    html_url = f"{base_url}/r/{tokens['html']}"
    pdf_url = f"{base_url}/r/{tokens['pdf']}.pdf"

    print(f"\n{'=' * 70}")
    print(f"  REPORT LINKS (reports.lintpdf.com format)")
    print(f"{'=' * 70}")
    print(f"  Web report:  {html_url}")
    print(f"  PDF report:  {pdf_url}")
    print(f"{'=' * 70}")

    # ── 8. Patch storage and start server ─────────────────────────────────────
    from siftpdf.api.storage import set_storage

    set_storage(storage)

    print(f"\n  Starting engine server on port 8000...")
    print(f"  Reports will be served at the URLs above.\n")

    import uvicorn
    from siftpdf.api.app import create_app

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
