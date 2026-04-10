#!/usr/bin/env python3
"""Seed DB with preflight results and start the engine server.

Two-phase:
  Phase 1 — seed: run preflight, generate reports, store tokens in DB
  Phase 2 — serve: start FastAPI with local filesystem storage
"""

import hashlib
import json
import os
import secrets
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

os.environ.setdefault("LINTPDF_DATABASE_URL", "postgresql://lintpdf:lintpdf@localhost:5432/lintpdf")
os.environ.setdefault("DATABASE_URL", "postgresql://lintpdf:lintpdf@localhost:5432/lintpdf")
os.environ.setdefault("LINTPDF_REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("LINTPDF_REPORT_BASE_URL", "http://localhost:8000")
os.environ.setdefault("LINTPDF_CLAMAV_URL", "")
os.environ.setdefault("LINTPDF_SECRET_KEY", "local-dev-secret-key")

PDF_PATH = "/home/user/lint-pdf/packages/web/public/lintpdf_preflight_test_final.pdf"
LOCAL_STORAGE = "/home/user/lint-pdf/packages/engine/.local-storage"
URLS_FILE = "/tmp/lintpdf_report_urls.json"


# ── Local filesystem storage ─────────────────────────────────────────────────

from lintpdf.api.storage import StorageBackend


class LocalFileStorage(StorageBackend):
    def __init__(self, base_dir: str):
        super().__init__()
        self._base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _path(self, key):
        full = os.path.join(self._base_dir, key)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        return full

    def _get_client(self):
        return None

    def upload_pdf(self, tid, jid, data):
        k = f"{tid}/{jid}/input.pdf"
        with open(self._path(k), "wb") as f: f.write(data)
        return k

    def download_pdf(self, fk):
        p = self._path(fk)
        if not os.path.exists(p): raise FileNotFoundError(fk)
        with open(p, "rb") as f: return f.read()

    def upload_results(self, tid, jid, data):
        k = f"{tid}/{jid}/results.json"
        with open(self._path(k), "wb") as f: f.write(data)
        return k

    def upload_report(self, tid, jid, fmt, data):
        k = f"reports/{tid}/{jid}/report.{fmt}"
        with open(self._path(k), "wb") as f: f.write(data)
        return k

    def download_report(self, tid, jid, fmt):
        k = f"reports/{tid}/{jid}/report.{fmt}"
        p = self._path(k)
        if not os.path.exists(p): raise FileNotFoundError(k)
        with open(p, "rb") as f: return f.read()

    def delete_file(self, fk):
        p = self._path(fk)
        if os.path.exists(p): os.remove(p)

    def generate_presigned_url(self, fk, exp=3600):
        return f"http://localhost:8000/storage/{fk}"

    def upload_raw(self, key, data, ct="application/octet-stream"):
        with open(self._path(key), "wb") as f: f.write(data)
        return key

    def download_raw(self, key):
        p = self._path(key)
        return open(p, "rb").read() if os.path.exists(p) else None


def seed():
    """Phase 1: run preflight, store reports, create tokens."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from lintpdf.api.models import Base, Job, JobFinding, JobStatus, ReportToken, Tenant
    from lintpdf.tenants.models import TenantPlan

    engine = create_engine(os.environ["LINTPDF_DATABASE_URL"])
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    # Tenant
    api_key = "lintpdf-local-test-key"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    tenant = db.query(Tenant).filter(Tenant.api_key_hash == api_key_hash).first()
    if not tenant:
        tenant = Tenant(
            id=uuid.uuid4(), name="LintPDF Test Tenant",
            api_key_hash=api_key_hash, plan=TenantPlan.ENTERPRISE,
            rate_limit_daily=1000, max_file_size_mb=500,
        )
        db.add(tenant)
        db.commit()
        print(f"  Tenant created: {tenant.id}")
    else:
        print(f"  Tenant exists:  {tenant.id}")

    # Run preflight
    print(f"\n  Loading PDF ({PDF_PATH})")
    with open(PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    from lintpdf.profiles.orchestrator import PreflightOrchestrator
    from lintpdf.profiles.schema import AIFeatureConfig, PreflightProfile

    profile = PreflightProfile(
        name="Full Preflight + AI", conformance=None, workflow="CMYK",
        checks={"enabled": ["LPDF_*", "PDFX4-*", "PDFX1A-*", "PDFA-*", "AI_*"], "disabled": []},
        thresholds={"min_dpi": 150, "max_dpi": 600, "tac_limit": 300, "min_bleed_mm": 3,
                    "hairline_threshold": 0.25, "small_text_threshold": 6, "safety_margin_mm": 3},
        ai=AIFeatureConfig(enabled=True, categories=["all"], features=[]),
    )

    print("  Running preflight (engine + AI)...")
    t0 = time.time()
    result = orchestrator_result = PreflightOrchestrator(profile, profile_id="full-preflight-ai").run(pdf_bytes)
    elapsed = time.time() - t0
    sm = result.summary
    print(f"  Done in {elapsed:.1f}s — {'PASS' if sm.passed else 'FAIL'} — "
          f"{sm.total_findings} findings ({sm.error_count}E/{sm.warning_count}W/{sm.advisory_count}A)")

    # Job record
    job_id = uuid.UUID(result.job_id)
    storage = LocalFileStorage(LOCAL_STORAGE)
    file_key = storage.upload_pdf(str(tenant.id), str(job_id), pdf_bytes)

    result_json = {
        "job_id": str(job_id), "profile_id": result.profile_id,
        "duration_ms": result.duration_ms,
        "summary": {"total_findings": sm.total_findings, "error_count": sm.error_count,
                     "warning_count": sm.warning_count, "advisory_count": sm.advisory_count,
                     "passed": sm.passed, "page_count": sm.page_count,
                     "file_size_bytes": sm.file_size_bytes},
        "metadata": {**result.metadata, "file_key": file_key},
        "findings": [],
    }

    job = Job(id=job_id, tenant_id=tenant.id, profile_id=result.profile_id,
              status=JobStatus.COMPLETE, file_key=file_key,
              file_name="lintpdf_preflight_test_final.pdf",
              file_size=len(pdf_bytes), result_json=result_json,
              duration_ms=result.duration_ms)
    db.add(job)

    for f in result.findings:
        db.add(JobFinding(
            id=uuid.uuid4(), job_id=job_id,
            inspection_id=f.inspection_id, severity=f.severity.value,
            message=f.message, page_num=f.page_num,
            object_id=f.object_id, object_type=f.object_type,
            source=f.source or "engine", category=f.category,
            details=f.details,
            bbox_x0=f.bbox[0] if f.bbox else None,
            bbox_y0=f.bbox[1] if f.bbox else None,
            bbox_x1=f.bbox[2] if f.bbox else None,
            bbox_y1=f.bbox[3] if f.bbox else None,
        ))
    db.commit()
    print(f"  Job {job_id} + {len(result.findings)} findings stored")

    # Generate reports + tokens
    from lintpdf.reports.engine import ReportEngine
    report_engine = ReportEngine()
    base = os.environ["LINTPDF_REPORT_BASE_URL"]
    tokens = {}

    for fmt in ["html", "pdf"]:
        report_bytes = report_engine.generate(result, fmt, pdf_bytes=pdf_bytes, detail_level="comprehensive")
        storage.upload_report(str(tenant.id), str(job_id), fmt, report_bytes)
        tok = secrets.token_urlsafe(32)
        db.add(ReportToken(
            id=uuid.uuid4(), job_id=job_id, tenant_id=tenant.id,
            token=tok, format=fmt,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            accessed_count=0,
        ))
        tokens[fmt] = tok
        print(f"  {fmt.upper()} report generated + token created")

    db.commit()
    db.close()

    urls = {
        "html": f"{base}/r/{tokens['html']}",
        "pdf": f"{base}/r/{tokens['pdf']}.pdf",
    }
    with open(URLS_FILE, "w") as f:
        json.dump(urls, f)

    return urls


def serve():
    """Phase 2: start FastAPI with local storage."""
    from lintpdf.api.storage import set_storage
    set_storage(LocalFileStorage(LOCAL_STORAGE))

    import uvicorn
    from lintpdf.api.app import create_app
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    if "--serve-only" in sys.argv:
        with open(URLS_FILE) as f:
            urls = json.load(f)
        print(f"\n  Web report:  {urls['html']}")
        print(f"  PDF report:  {urls['pdf']}\n")
        serve()
    else:
        print("\n=== Phase 1: Seed ===")
        urls = seed()
        print(f"\n{'='*70}")
        print(f"  REPORT LINKS")
        print(f"{'='*70}")
        print(f"  Web report:  {urls['html']}")
        print(f"  PDF report:  {urls['pdf']}")
        print(f"{'='*70}")
        print(f"\n=== Phase 2: Serve ===\n")
        serve()
