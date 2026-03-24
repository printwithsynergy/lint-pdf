"""Tests for authentication utilities."""

from __future__ import annotations

from lintpdf.api.auth import generate_api_key, hash_api_key


class TestApiKeyGeneration:
    @staticmethod
    def test_generate_api_key_format() -> None:
        key = generate_api_key()
        assert key.startswith("lpdf_")
        assert len(key) > 10

    @staticmethod
    def test_generate_unique_keys() -> None:
        keys = {generate_api_key() for _ in range(10)}
        assert len(keys) == 10  # All unique

    @staticmethod
    def test_hash_api_key_deterministic() -> None:
        key = "lpdf_test_key_123"
        assert hash_api_key(key) == hash_api_key(key)

    @staticmethod
    def test_hash_api_key_different_for_different_keys() -> None:
        assert hash_api_key("key_a") != hash_api_key("key_b")

    @staticmethod
    def test_hash_api_key_is_hex() -> None:
        h = hash_api_key("test")
        assert len(h) == 64  # SHA-256 hex digest
        assert all(c in "0123456789abcdef" for c in h)
