"""Corpus testing endpoints.

Corpus testing gives developers a golden-master regression suite for
preflight profiles.  Upload "assay" PDFs, set expected findings (or let
the first run bootstrap them), then create a corpus run to verify the
profile still produces the expected output.  Passing runs generate a
signed certificate.

Routes
------
POST   /api/v1/corpus/assays                  — upload an assay PDF
GET    /api/v1/corpus/assays                  — list assays
GET    /api/v1/corpus/assays/{id}             — get assay detail
PATCH  /api/v1/corpus/assays/{id}/expectations — overwrite expected findings
DELETE /api/v1/corpus/assays/{id}             — delete assay

POST   /api/v1/corpus/runs                    — create (queue) a corpus run
GET    /api/v1/corpus/runs                    — list runs
GET    /api/v1/corpus/runs/{id}               — get run status + results
GET    /api/v1/corpus/runs/{id}/certificate   — download signed certificate
"""

from __future__ import annotations

import hashlib
import logging
import uuid as uuid_mod

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from lintpdf.api.auth import get_current_tenant
from lintpdf.api.database import get_db
from lintpdf.api.models import (
    CorpusAssay,
    CorpusAssayStatus,
    CorpusRun,
    CorpusRunAssay,
    CorpusRunStatus,
)
from lintpdf.api.schemas import (
    CorpusAssayExpectationsUpdateRequest,
    CorpusAssayListResponse,
    CorpusAssayResponse,
    CorpusCertificate,
    CorpusExpectedFinding,
    CorpusRunAssayResult,
    CorpusRunCreateRequest,
    CorpusRunCreateResponse,
    CorpusRunListResponse,
    CorpusRunResponse,
)
from lintpdf.api.storage import get_storage
from lintpdf.api.upload_security import PDF_TYPES, validate_upload_streaming
from lintpdf.services.tenant_context import TenantContext  # noqa: TC001

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/corpus", tags=["corpus"])

_MAX_ASSAY_SIZE_MB = 100


def _assay_response(assay: CorpusAssay) -> CorpusAssayResponse:
    expected = None
    if assay.expected_findings_json is not None:
        expected = [
            CorpusExpectedFinding(
                inspection_id=f["inspection_id"],
                severity=f["severity"],
                page_num=f.get("page_num"),
            )
            for f in assay.expected_findings_json
        ]
    return CorpusAssayResponse(
        id=assay.id,
        name=assay.name,
        pdf_hash=assay.pdf_hash,
        expected_findings=expected,
        created_at=assay.created_at,
        updated_at=assay.updated_at,
    )


def _run_assay_result(run_assay: CorpusRunAssay) -> CorpusRunAssayResult:
    return CorpusRunAssayResult(
        assay_id=run_assay.assay_id,
        assay_name=run_assay.assay.name,
        status=run_assay.status.value,
        bootstrapped=run_assay.bootstrapped,
        diff=run_assay.diff_json,
        error_message=run_assay.error_message,
    )


def _run_response(run: CorpusRun) -> CorpusRunResponse:
    cert = None
    if run.certificate_json:
        cert = CorpusCertificate(**run.certificate_json)
    results = [_run_assay_result(ra) for ra in run.run_assays]
    return CorpusRunResponse(
        id=run.id,
        profile_id=run.profile_id,
        status=run.status.value,
        assay_count=run.assay_count,
        pass_count=run.pass_count,
        fail_count=run.fail_count,
        results=results,
        certificate=cert,
        error_message=run.error_message,
        created_at=run.created_at,
        completed_at=run.completed_at,
    )


# ---------------------------------------------------------------------------
# Assay endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/assays",
    response_model=CorpusAssayResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "File is not a valid PDF or exceeds size limit."},
        401: {"description": "Missing or invalid API key."},
    },
)
async def create_assay(
    file: UploadFile = File(..., description="PDF file to register as an assay fixture."),
    name: str = Form(..., description="Human-readable name for this assay."),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> CorpusAssayResponse:
    """Register a PDF as a corpus assay fixture.

    The PDF is stored in object storage.  If you don't supply
    `expected_findings`, the first corpus run will bootstrap the baseline
    automatically.
    """
    max_bytes = _MAX_ASSAY_SIZE_MB * 1024 * 1024
    spool, _file_size = await validate_upload_streaming(
        file, allowed_types=PDF_TYPES, max_size_bytes=max_bytes
    )

    pdf_bytes = spool.read()
    spool.close()

    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    assay_id = uuid_mod.uuid4()
    storage_key = f"corpus/{tenant.id}/{assay_id}/input.pdf"

    storage = get_storage()
    import asyncio

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: storage.upload_raw(storage_key, pdf_bytes, content_type="application/pdf"),
    )

    assay = CorpusAssay(
        id=assay_id,
        tenant_id=tenant.id,
        name=name,
        pdf_storage_key=storage_key,
        pdf_hash=pdf_hash,
        expected_findings_json=None,
    )
    db.add(assay)
    db.commit()
    db.refresh(assay)
    return _assay_response(assay)


@router.get(
    "/assays",
    response_model=CorpusAssayListResponse,
    responses={
        401: {"description": "Missing or invalid API key."},
    },
)
def list_assays(
    offset: int = Query(default=0, ge=0, description="Pagination offset."),
    limit: int = Query(default=50, ge=1, le=200, description="Page size."),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> CorpusAssayListResponse:
    """List all corpus assays for the authenticated tenant."""
    q = db.query(CorpusAssay).filter(CorpusAssay.tenant_id == tenant.id)
    total = q.count()
    assays = q.order_by(CorpusAssay.created_at.desc()).offset(offset).limit(limit).all()
    return CorpusAssayListResponse(
        assays=[_assay_response(a) for a in assays],
        total=total,
    )


@router.get(
    "/assays/{assay_id}",
    response_model=CorpusAssayResponse,
    responses={
        401: {"description": "Missing or invalid API key."},
        404: {"description": "Assay not found."},
    },
)
def get_assay(
    assay_id: uuid_mod.UUID,
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> CorpusAssayResponse:
    """Get a single corpus assay by ID."""
    assay = (
        db.query(CorpusAssay)
        .filter(CorpusAssay.id == assay_id, CorpusAssay.tenant_id == tenant.id)
        .first()
    )
    if assay is None:
        raise HTTPException(status_code=404, detail="Assay not found.")
    return _assay_response(assay)


@router.patch(
    "/assays/{assay_id}/expectations",
    response_model=CorpusAssayResponse,
    responses={
        401: {"description": "Missing or invalid API key."},
        404: {"description": "Assay not found."},
    },
)
def update_assay_expectations(
    assay_id: uuid_mod.UUID,
    body: CorpusAssayExpectationsUpdateRequest,
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> CorpusAssayResponse:
    """Overwrite the expected findings for an assay.

    Pass `null` for `expected_findings` to reset the assay to bootstrap
    mode — the next run will re-derive the baseline from engine output.
    """
    assay = (
        db.query(CorpusAssay)
        .filter(CorpusAssay.id == assay_id, CorpusAssay.tenant_id == tenant.id)
        .first()
    )
    if assay is None:
        raise HTTPException(status_code=404, detail="Assay not found.")

    if body.expected_findings is None:
        assay.expected_findings_json = None
    else:
        assay.expected_findings_json = [
            {
                "inspection_id": f.inspection_id,
                "severity": f.severity,
                "page_num": f.page_num,
            }
            for f in body.expected_findings
        ]

    db.commit()
    db.refresh(assay)
    return _assay_response(assay)


@router.delete(
    "/assays/{assay_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Missing or invalid API key."},
        404: {"description": "Assay not found."},
    },
)
def delete_assay(
    assay_id: uuid_mod.UUID,
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> None:
    """Delete a corpus assay and its stored PDF.

    This does not delete corpus runs that referenced this assay — their
    historical results are preserved.
    """
    assay = (
        db.query(CorpusAssay)
        .filter(CorpusAssay.id == assay_id, CorpusAssay.tenant_id == tenant.id)
        .first()
    )
    if assay is None:
        raise HTTPException(status_code=404, detail="Assay not found.")

    storage = get_storage()
    try:
        storage.delete_file(assay.pdf_storage_key)
    except Exception:
        logger.warning("delete_assay: could not delete PDF from storage for assay %s", assay_id)

    db.delete(assay)
    db.commit()


# ---------------------------------------------------------------------------
# Run endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/runs",
    response_model=CorpusRunCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        401: {"description": "Missing or invalid API key."},
        404: {"description": "One or more assay IDs not found."},
        422: {"description": "Invalid request body."},
    },
)
def create_run(
    body: CorpusRunCreateRequest,
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> CorpusRunCreateResponse:
    """Queue a corpus run.

    All provided assay IDs must belong to the authenticated tenant.
    The run executes asynchronously; poll `GET /corpus/runs/{id}` for
    status or subscribe to `corpus_run.completed` / `corpus_run.failed`
    webhook events.
    """
    assays = (
        db.query(CorpusAssay)
        .filter(
            CorpusAssay.id.in_(body.assay_ids),
            CorpusAssay.tenant_id == tenant.id,
        )
        .all()
    )
    found_ids = {a.id for a in assays}
    missing = [str(aid) for aid in body.assay_ids if aid not in found_ids]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Assay(s) not found: {', '.join(missing)}",
        )

    run_id = uuid_mod.uuid4()
    run = CorpusRun(
        id=run_id,
        tenant_id=tenant.id,
        profile_id=body.profile_id,
        status=CorpusRunStatus.PENDING,
        assay_count=len(assays),
    )
    db.add(run)
    db.flush()

    for assay in assays:
        db.add(
            CorpusRunAssay(
                run_id=run.id,
                assay_id=assay.id,
                status=CorpusAssayStatus.PENDING,
            )
        )

    db.commit()

    from lintpdf.queue.tasks import execute_corpus_run

    execute_corpus_run.apply_async(args=[str(run_id)], queue="priority")

    return CorpusRunCreateResponse(run_id=run_id)


@router.get(
    "/runs",
    response_model=CorpusRunListResponse,
    responses={
        401: {"description": "Missing or invalid API key."},
    },
)
def list_runs(
    offset: int = Query(default=0, ge=0, description="Pagination offset."),
    limit: int = Query(default=50, ge=1, le=200, description="Page size."),
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> CorpusRunListResponse:
    """List corpus runs for the authenticated tenant."""
    from sqlalchemy.orm import selectinload

    q = db.query(CorpusRun).filter(CorpusRun.tenant_id == tenant.id)
    total = q.count()
    runs = (
        q.options(selectinload(CorpusRun.run_assays).selectinload(CorpusRunAssay.assay))
        .order_by(CorpusRun.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return CorpusRunListResponse(
        runs=[_run_response(r) for r in runs],
        total=total,
    )


@router.get(
    "/runs/{run_id}",
    response_model=CorpusRunResponse,
    responses={
        401: {"description": "Missing or invalid API key."},
        404: {"description": "Run not found."},
    },
)
def get_run(
    run_id: uuid_mod.UUID,
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> CorpusRunResponse:
    """Get corpus run status and per-assay results."""
    from sqlalchemy.orm import selectinload

    run = (
        db.query(CorpusRun)
        .options(selectinload(CorpusRun.run_assays).selectinload(CorpusRunAssay.assay))
        .filter(CorpusRun.id == run_id, CorpusRun.tenant_id == tenant.id)
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Corpus run not found.")
    return _run_response(run)


@router.get(
    "/runs/{run_id}/certificate",
    response_model=CorpusCertificate,
    responses={
        401: {"description": "Missing or invalid API key."},
        404: {"description": "Run not found or no certificate available."},
    },
)
def get_certificate(
    run_id: uuid_mod.UUID,
    tenant: TenantContext = Depends(get_current_tenant),
    db: Session = Depends(get_db),
) -> CorpusCertificate:
    """Download the signed run certificate.

    Only available when the run passed and `LINTPDF_CORPUS_SIGNING_KEY`
    was configured at the time the run completed.
    """
    run = (
        db.query(CorpusRun)
        .filter(CorpusRun.id == run_id, CorpusRun.tenant_id == tenant.id)
        .first()
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Corpus run not found.")
    if not run.certificate_json:
        raise HTTPException(
            status_code=404,
            detail=(
                "No certificate for this run. Certificates are only issued "
                "when all assays pass and LINTPDF_CORPUS_SIGNING_KEY is set."
            ),
        )
    return CorpusCertificate(**run.certificate_json)
