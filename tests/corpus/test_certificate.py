"""Tests for corpus run certificate signing and verification."""

from __future__ import annotations

import uuid

from lintpdf.corpus.certificate import (
    compute_corpus_hash,
    sign_certificate,
    verify_certificate,
)

_KEY = "test-signing-key-32-bytes-minimum!"
_RUN_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_TENANT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def test_sign_and_verify_roundtrip():
    cert = sign_certificate(
        run_id=_RUN_ID,
        tenant_id=_TENANT_ID,
        profile_id="lintpdf-default",
        assay_count=3,
        pass_count=3,
        corpus_hash="abc123",
        signing_key=_KEY,
    )
    assert cert["version"] == "1"
    assert cert["run_id"] == str(_RUN_ID)
    assert cert["assay_count"] == 3
    assert cert["signature"].startswith("sha256:")
    assert verify_certificate(cert, _KEY)


def test_verify_rejects_wrong_key():
    cert = sign_certificate(
        run_id=_RUN_ID,
        tenant_id=_TENANT_ID,
        profile_id="lintpdf-default",
        assay_count=1,
        pass_count=1,
        corpus_hash="abc",
        signing_key=_KEY,
    )
    assert not verify_certificate(cert, "wrong-key")


def test_verify_rejects_tampered_payload():
    cert = sign_certificate(
        run_id=_RUN_ID,
        tenant_id=_TENANT_ID,
        profile_id="lintpdf-default",
        assay_count=1,
        pass_count=1,
        corpus_hash="abc",
        signing_key=_KEY,
    )
    cert["pass_count"] = 99
    assert not verify_certificate(cert, _KEY)


def test_verify_rejects_missing_signature():
    cert = {"version": "1", "run_id": str(_RUN_ID)}
    assert not verify_certificate(cert, _KEY)


def test_corpus_hash_is_order_independent():
    hashes = ["aaaa", "bbbb", "cccc"]
    h1 = compute_corpus_hash(hashes)
    h2 = compute_corpus_hash(list(reversed(hashes)))
    assert h1 == h2


def test_corpus_hash_differs_on_different_inputs():
    h1 = compute_corpus_hash(["aaaa"])
    h2 = compute_corpus_hash(["bbbb"])
    assert h1 != h2
