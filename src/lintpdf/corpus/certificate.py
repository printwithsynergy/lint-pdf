"""Corpus run certificate signing and verification.

A certificate is a JSON document that proves a profile produced the
expected findings on a known corpus at a specific point in time.  It is
signed with HMAC-SHA256 using the ``LINTPDF_CORPUS_SIGNING_KEY``
environment variable (annual rotation recommended; old certs remain
verifiable only against the key that signed them).

When ``LINTPDF_CORPUS_SIGNING_KEY`` is unset the certificate is
omitted from the run response rather than silently produced with a
trivially-forgeable signature.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import uuid


def _canonical_payload(cert: dict[str, Any]) -> bytes:
    """Deterministic JSON serialisation of the signable fields."""
    signable = {k: v for k, v in cert.items() if k != "signature"}
    return json.dumps(signable, sort_keys=True, separators=(",", ":")).encode()


def sign_certificate(
    *,
    run_id: uuid.UUID,
    tenant_id: uuid.UUID,
    profile_id: str,
    assay_count: int,
    pass_count: int,
    corpus_hash: str,
    signing_key: str,
) -> dict[str, Any]:
    """Build and sign a corpus run certificate.

    Returns a dict ready to be stored as ``CorpusRun.certificate_json``.
    """
    cert: dict[str, Any] = {
        "version": "1",
        "run_id": str(run_id),
        "tenant_id": str(tenant_id),
        "profile_id": profile_id,
        "assay_count": assay_count,
        "pass_count": pass_count,
        "corpus_hash": corpus_hash,
        "issued_at": datetime.now(UTC).isoformat(),
    }
    payload = _canonical_payload(cert)
    sig = hmac.new(signing_key.encode(), payload, hashlib.sha256).hexdigest()
    cert["signature"] = f"sha256:{sig}"
    return cert


def verify_certificate(cert: dict[str, Any], signing_key: str) -> bool:
    """Return True iff the certificate's HMAC signature is valid."""
    sig_field = cert.get("signature", "")
    if not sig_field.startswith("sha256:"):
        return False
    expected_hex = sig_field[len("sha256:") :]
    payload = _canonical_payload(cert)
    actual_hex = hmac.new(signing_key.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_hex, actual_hex)


def compute_corpus_hash(assay_pdf_hashes: list[str]) -> str:
    """Stable hash of the assay set — SHA-256 of the sorted PDF hashes."""
    combined = ",".join(sorted(assay_pdf_hashes))
    return hashlib.sha256(combined.encode()).hexdigest()
