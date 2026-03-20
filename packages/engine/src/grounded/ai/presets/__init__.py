"""AI preset Voyage Plans — pre-built bundles of AI features."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_BUILTIN_DIR = Path(__file__).parent / "builtin"
_presets: dict[str, dict[str, Any]] | None = None


def get_preset(slug: str) -> dict[str, Any] | None:
    """Get a pre-built AI preset by slug."""
    presets = get_all_presets()
    return presets.get(slug)


def get_all_presets() -> dict[str, dict[str, Any]]:
    """Load and return all built-in AI presets."""
    global _presets  # skipcq: PYL-W0603
    if _presets is not None:
        return _presets

    _presets = {}
    if not _BUILTIN_DIR.exists():
        return _presets

    for path in sorted(_BUILTIN_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
            slug = path.stem
            _presets[slug] = data
        except Exception:
            logger.warning("Failed to load AI preset: %s", path)

    return _presets
