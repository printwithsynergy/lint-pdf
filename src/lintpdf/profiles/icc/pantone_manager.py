"""Pantone reference manager — thin adapter on top of codex_pdf.color.

As of codex-pdf 1.4.0 the Pantone reference catalogue and ΔE2000
implementation moved into :mod:`codex_pdf.color`. This module is now
a deprecation-friendly façade that adapts the codex API back into the
``PantoneManager`` / ``PantoneReference`` / ``DeltaEResult`` shapes
used by the LPDF_SPOT_002 / LPDF_SPOT_006 analyzers. New consumers
should call :func:`codex_pdf.color.lookup_pantone_spot` directly; the
class form is preserved only because the analyzer still wires in
custom tenant overrides via the manager constructor.

The bundled ``pantone_reference.json`` was deleted in this same
release — codex owns the source-of-truth file.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from codex_pdf.color import (
    PantoneEntry,
    delta_e_2000,
    lookup_pantone_spot,
    normalize_pantone_name,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PantoneReference:
    """Reference data for a single Pantone color (lint-side adapter shape)."""

    name: str
    lab: tuple[float, float, float]
    cmyk_bridge: tuple[float, float, float, float] | None
    library: str | None = None
    lab_source: str | None = None
    cmyk_source: str | None = None

    @classmethod
    def from_codex(cls, entry: PantoneEntry, *, name_override: str | None = None) -> "PantoneReference":
        if entry.lab is None:
            raise ValueError(f"Pantone entry {entry.name!r} has no Lab value")
        return cls(
            name=name_override or entry.name,
            lab=entry.lab,
            cmyk_bridge=entry.cmyk_bridge,
            library=entry.library,
            lab_source=entry.lab_source,
            cmyk_source=entry.cmyk_source,
        )


@dataclass(frozen=True)
class DeltaEResult:
    """Result of a Pantone fallback Delta-E validation."""

    delta_e: float
    reference_lab: tuple[float, float, float]
    fallback_lab: tuple[float, float, float]
    pantone_name: str
    acceptable: bool


class PantoneManager:
    """Tenant-aware Pantone lookup + ΔE validation.

    Wraps the codex authority so analyzer call sites keep their
    historical method signatures. ``custom_overrides`` works the same
    as before — a tenant-specific dict that beats the bundled codex
    catalogue.
    """

    def __init__(self, custom_overrides: dict[str, dict[str, Any]] | None = None) -> None:
        if custom_overrides:
            self._overrides: dict[str, dict[str, Any]] = {
                normalize_pantone_name(k): v for k, v in custom_overrides.items()
            }
        else:
            self._overrides = {}

    def lookup(self, name: str) -> PantoneReference | None:
        entry = lookup_pantone_spot(name, extra_overrides=self._overrides or None)
        if entry is None or entry.lab is None:
            return None
        return PantoneReference.from_codex(entry, name_override=name)

    def has_color(self, name: str) -> bool:
        return self.lookup(name) is not None

    def validate_cmyk_fallback(
        self,
        pantone_name: str,
        cmyk_values: tuple[float, float, float, float],
        icc_profile_bytes: bytes | None = None,
        warning_threshold: float = 5.0,
        advisory_threshold: float = 2.0,  # noqa: ARG002 — kept for API stability
    ) -> DeltaEResult | None:
        ref = self.lookup(pantone_name)
        if ref is None:
            return None
        fallback_lab = self._cmyk_to_lab(cmyk_values, icc_profile_bytes)
        de = delta_e_2000(ref.lab, fallback_lab)
        return DeltaEResult(
            delta_e=round(de, 2),
            reference_lab=ref.lab,
            fallback_lab=fallback_lab,
            pantone_name=pantone_name,
            acceptable=de <= warning_threshold,
        )

    @staticmethod
    def _cmyk_to_lab(
        cmyk: tuple[float, float, float, float],
        icc_profile_bytes: bytes | None,
    ) -> tuple[float, float, float]:
        from lintpdf.analyzers.gamut_analyzer import cmyk_to_lab

        return cmyk_to_lab(
            cmyk[0],
            cmyk[1],
            cmyk[2],
            cmyk[3],
            icc_profile_bytes=icc_profile_bytes,
        )
