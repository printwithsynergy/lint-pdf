"""Shared helpers for the codex_signals readers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lintpdf.plugin.protocol import AnalyzerContext


def codex_payload(ctx: AnalyzerContext) -> dict[str, Any] | None:
    """Return the codex document payload threaded into ``ctx.config``.

    The orchestrator fetches the codex document once per preflight run
    and stuffs it into ``ctx.config["codex_payload"]`` so every reader
    sees the same snapshot. Returns ``None`` when codex is unreachable
    (orchestrator already logged the exception); readers default to
    emitting zero findings in that case.
    """
    raw = ctx.config.get("codex_payload")
    if isinstance(raw, dict):
        return raw
    return None


def codex_pages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    pages = payload.get("pages")
    if isinstance(pages, list):
        return [p for p in pages if isinstance(p, dict)]
    return []


def codex_ai_skipped(payload: dict[str, Any]) -> bool:
    """True when codex flagged that AI didn't run (disabled / skipped
    / missing_credentials).

    Used by readers to suppress their "no signals found" finding when
    the empty payload is by design, not by data — avoids a false
    "AI ran and found nothing" signal in the demo.
    """
    warnings = payload.get("extraction_warnings")
    if not isinstance(warnings, list):
        return False
    for w in warnings:
        if not isinstance(w, dict):
            continue
        code = w.get("code")
        if code in {"ai_disabled", "ai_skipped", "ai_missing_credentials"}:
            return True
    return False
