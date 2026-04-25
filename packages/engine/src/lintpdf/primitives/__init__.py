"""LintPDF Tier-0 atomic primitives.

Pure-function predicates used by all Tier 1-5 user-facing checks. Per playbook
v2 §10.1 + universe enumeration §4. No side effects; no PDF mutation.

Module organization mirrors universe enumeration §4 categories. Each category
exports its predicates as module-level functions and registers them in
``REGISTRY`` for runtime introspection.

The registry is the foundation for v2 §16 toggle introspection: callers can
enumerate "what predicates exist" without importing every submodule.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

# Registry of (category, name) -> callable for runtime introspection.
# Populated at import time by each category submodule.
REGISTRY: dict[str, dict[str, Callable[..., Any]]] = {}


def register(category: str, name: str, func: Callable[..., Any]) -> Callable[..., Any]:
    """Register a primitive under (category, name). Idempotent."""
    REGISTRY.setdefault(category, {})[name] = func
    return func


# Lazy-import categories to avoid circular imports during module reload.
from lintpdf.primitives import (  # noqa: E402
    color_space,
    geometry,
    image,
    ink,
    object_class,
    page,
    stroke_fill,
    text,
    transparency_stack,
)

__all__ = [
    "REGISTRY",
    "color_space",
    "geometry",
    "image",
    "ink",
    "object_class",
    "page",
    "register",
    "stroke_fill",
    "text",
    "transparency_stack",
]
