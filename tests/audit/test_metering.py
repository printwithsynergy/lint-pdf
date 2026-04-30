"""Unit tests for metering + quota (WS-G)."""

from __future__ import annotations

from lintpdf.audit.metering import compute_cost_cents
from lintpdf.audit.quota import is_over_quota


class _Ent:
    def __init__(self, cents: int) -> None:
        self.monthly_ai_credits = cents


class TestComputeCostCents:
    @staticmethod
    def test_tiny_haiku_call_rounds_up_to_one_cent() -> None:
        # 100 input + 50 output at Haiku rates is a fraction of a cent.
        cost = compute_cost_cents(
            model="claude-haiku-4-5",
            input_tokens=100,
            output_tokens=50,
        )
        assert cost == 1

    @staticmethod
    def test_zero_tokens_is_zero_cents() -> None:
        cost = compute_cost_cents(
            model="claude-haiku-4-5",
            input_tokens=0,
            output_tokens=0,
        )
        assert cost == 0

    @staticmethod
    def test_larger_haiku_call_computes_sane_value() -> None:
        # 1M input + 500k output at Haiku = $0.80 + $2.00 = $2.80 = 280 cents.
        cost = compute_cost_cents(
            model="claude-haiku-4-5",
            input_tokens=1_000_000,
            output_tokens=500_000,
        )
        assert cost == 280

    @staticmethod
    def test_sonnet_more_expensive_than_haiku_for_same_tokens() -> None:
        sonnet = compute_cost_cents(
            model="claude-sonnet-4-6",
            input_tokens=100_000,
            output_tokens=10_000,
        )
        haiku = compute_cost_cents(
            model="claude-haiku-4-5",
            input_tokens=100_000,
            output_tokens=10_000,
        )
        assert sonnet > haiku

    @staticmethod
    def test_unknown_model_falls_back_to_haiku_pricing() -> None:
        unknown = compute_cost_cents(
            model="claude-whatever", input_tokens=1_000_000, output_tokens=0
        )
        haiku = compute_cost_cents(
            model="claude-haiku-4-5", input_tokens=1_000_000, output_tokens=0
        )
        assert unknown == haiku

    @staticmethod
    def test_cache_tokens_reduce_cost_relative_to_fresh_input() -> None:
        cached = compute_cost_cents(
            model="claude-haiku-4-5",
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=1_000_000,
        )
        fresh = compute_cost_cents(
            model="claude-haiku-4-5",
            input_tokens=1_000_000,
            output_tokens=0,
        )
        # Cache reads cost 10% of fresh input.
        assert cached < fresh
        assert cached == max(1, fresh // 10)


class TestQuota:
    @staticmethod
    def test_zero_cap_treats_any_usage_as_under() -> None:
        # Zero cap means "no AI budget" — but is_over_quota returns
        # False so the feature-locked finding (not the quota finding)
        # is the thing that fires. Prevents double-chips.
        assert is_over_quota(_Ent(0), 10000) is False

    @staticmethod
    def test_usage_below_cap_is_ok() -> None:
        assert is_over_quota(_Ent(500), 499) is False

    @staticmethod
    def test_usage_equal_to_cap_is_over() -> None:
        assert is_over_quota(_Ent(500), 500) is True

    @staticmethod
    def test_usage_above_cap_is_over() -> None:
        assert is_over_quota(_Ent(500), 501) is True
