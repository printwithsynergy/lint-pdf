"""Document and metadata predicates — Tier-0 Batch 10.

Per universe enumeration §4.10. Predicates over a Document (or Catalog +
Info dict) describing PDF version, conformance flags (PDF/X, PDF/A,
PDF/UA), and structural objects (AcroForm, JavaScript, embedded files,
output intents, signatures, linearization).

XMP detection: looks for a /Metadata stream on the Catalog and parses the
RDF for namespace tags (``pdfaid:part``, ``pdfx:GTS_PDFXVersion``,
``pdfuaid:part``). When the XMP stream is absent, falls back to legacy
Info dict entries (``/GTS_PDFXVersion``).
"""

from __future__ import annotations

import re
from typing import Any

from siftpdf.primitives import register


def _get(obj: Any, *keys: str, default: Any = None) -> Any:
    """Fetch by attribute or Mapping with /-prefix fallback."""
    if obj is None:
        return default
    for k in keys:
        if hasattr(obj, k):
            v = getattr(obj, k)
            if v is not None:
                return v
        if hasattr(obj, "get"):
            v = obj.get(k)
            if v is not None:
                return v
            v = obj.get("/" + k)
            if v is not None:
                return v
    return default


def _catalog(doc: Any) -> Any:
    """Return Catalog (a.k.a. Root) or doc itself when none distinguishable."""
    cat = _get(doc, "catalog", "Catalog", "Root")
    return cat if cat is not None else doc


def _info(doc: Any) -> Any:
    """Return /Info dictionary."""
    return _get(doc, "info", "Info") or {}


def _xmp_text(doc: Any) -> str | None:
    """Return XMP/RDF text payload from Catalog /Metadata stream, if any."""
    catalog = _catalog(doc)
    md = _get(catalog, "metadata", "Metadata")
    if md is None:
        return None
    if isinstance(md, str):
        return md
    if isinstance(md, bytes):
        return md.decode("utf-8", errors="replace")
    text = _get(md, "text", "data", "stream")
    if isinstance(text, str):
        return text
    if isinstance(text, bytes):
        return text.decode("utf-8", errors="replace")
    return None


# ---- pdf version --------------------------------------------------------


def pdf_version(doc: Any) -> str | None:
    """Return PDF spec version as ``"1.7"`` / ``"2.0"`` or None."""
    v = _get(doc, "pdf_version", "version")
    if v is None:
        catalog = _catalog(doc)
        v = _get(catalog, "Version")
    if v is None:
        return None
    return str(v).lstrip("/")


# ---- PDF/X ------------------------------------------------------------


_PDFX_RE = re.compile(r"PDF/?X[-_]?(\d+[a-z]*)", re.IGNORECASE)


def pdf_x_part(doc: Any) -> str | None:
    """Return the PDF/X part identifier (e.g. ``"PDF/X-4"``) or None."""
    info = _info(doc)
    candidate = _get(info, "GTS_PDFXVersion", "GTS_PDFXConformance") or _get(
        _catalog(doc), "GTS_PDFXVersion"
    )
    if candidate is None:
        text = _xmp_text(doc)
        if text:
            match = _PDFX_RE.search(text)
            if match:
                return f"PDF/X-{match.group(1)}"
        return None
    return str(candidate).lstrip("/")


def is_pdf_x(doc: Any) -> bool:
    """True iff the document declares any PDF/X conformance."""
    return pdf_x_part(doc) is not None


# ---- PDF/A ------------------------------------------------------------


_PDFA_PART_RE = re.compile(r"pdfaid:part>\s*(\d+)", re.IGNORECASE)
_PDFA_CONF_RE = re.compile(r"pdfaid:conformance>\s*([A-Za-z])", re.IGNORECASE)


def pdf_a_part(doc: Any) -> str | None:
    """Return the PDF/A part+conformance (e.g. ``"PDF/A-2b"``) or None."""
    text = _xmp_text(doc)
    if text:
        part = _PDFA_PART_RE.search(text)
        conf = _PDFA_CONF_RE.search(text)
        if part:
            level = conf.group(1).lower() if conf else ""
            return f"PDF/A-{part.group(1)}{level}"
    direct = _get(doc, "pdf_a_part", "pdfa_part")
    return str(direct) if direct else None


def is_pdf_a(doc: Any) -> bool:
    """True iff the document declares any PDF/A conformance."""
    return pdf_a_part(doc) is not None


# ---- PDF/UA (accessibility variant) -----------------------------------


_PDFUA_RE = re.compile(r"pdfuaid:part>\s*(\d+)", re.IGNORECASE)


def is_pdf_va(doc: Any) -> bool:
    """True iff the document declares PDF/UA (accessibility) conformance."""
    text = _xmp_text(doc)
    if text and _PDFUA_RE.search(text):
        return True
    return bool(_get(doc, "is_pdf_ua", "pdf_ua"))


# ---- structural objects ------------------------------------------------


def has_xmp(doc: Any) -> bool:
    """True iff the Catalog has a /Metadata stream."""
    catalog = _catalog(doc)
    return _get(catalog, "metadata", "Metadata") is not None


def acroform_present(doc: Any) -> bool:
    """True iff Catalog /AcroForm has a non-empty /Fields array."""
    catalog = _catalog(doc)
    acroform = _get(catalog, "acroform", "AcroForm")
    if acroform is None:
        return False
    fields = _get(acroform, "Fields", "fields")
    if fields is None:
        return False
    try:
        return len(fields) > 0
    except TypeError:
        return bool(fields)


def has_javascript(doc: Any) -> bool:
    """True iff the document has JavaScript (Names tree or action JS)."""
    catalog = _catalog(doc)
    names = _get(catalog, "names", "Names")
    if names is not None and _get(names, "JavaScript", "javascript") is not None:
        return True
    if _get(catalog, "OpenAction", "open_action") is not None:
        oa = _get(catalog, "OpenAction", "open_action")
        if _get(oa, "S") in ("/JavaScript", "JavaScript"):
            return True
    return bool(_get(doc, "has_javascript"))


def has_embedded_files(doc: Any) -> bool:
    """True iff the document has /EmbeddedFiles in the Names tree."""
    catalog = _catalog(doc)
    names = _get(catalog, "names", "Names")
    if names is None:
        return False
    return _get(names, "EmbeddedFiles", "embedded_files") is not None


def has_output_intent(doc: Any) -> bool:
    """True iff the Catalog has a non-empty /OutputIntents array."""
    catalog = _catalog(doc)
    oi = _get(catalog, "output_intents", "OutputIntents")
    if oi is None:
        return False
    try:
        return len(oi) > 0
    except TypeError:
        return bool(oi)


def output_intent_subtype(doc: Any) -> str | None:
    """Return the first /OutputIntent's /S subtype (e.g. ``"GTS_PDFX"``)."""
    catalog = _catalog(doc)
    oi = _get(catalog, "output_intents", "OutputIntents")
    if oi is None:
        return None
    try:
        first = oi[0]
    except (IndexError, TypeError, KeyError):
        return None
    if first is None:
        return None
    s = _get(first, "S", "subtype")
    return str(s).lstrip("/") if s is not None else None


def is_linearized(doc: Any) -> bool:
    """True iff the document is linearized (Fast Web View)."""
    return bool(_get(doc, "is_linearized", "linearized"))


def signature_count(doc: Any) -> int:
    """Return the number of digital signatures in the AcroForm tree."""
    n = _get(doc, "signature_count", "signatures")
    if isinstance(n, int):
        return n
    if hasattr(n, "__len__"):
        try:
            return len(n)
        except TypeError:
            return 0
    catalog = _catalog(doc)
    acroform = _get(catalog, "acroform", "AcroForm")
    if acroform is None:
        return 0
    fields = _get(acroform, "Fields", "fields") or []
    count = 0
    try:
        for f in fields:
            ft = _get(f, "FT", "field_type")
            if str(ft).lstrip("/") == "Sig":
                count += 1
    except TypeError:
        return 0
    return count


# ---- registry ---------------------------------------------------------

for _name in (
    "pdf_version",
    "is_pdf_x",
    "pdf_x_part",
    "is_pdf_a",
    "pdf_a_part",
    "is_pdf_va",
    "has_xmp",
    "acroform_present",
    "has_javascript",
    "has_embedded_files",
    "has_output_intent",
    "output_intent_subtype",
    "is_linearized",
    "signature_count",
):
    register("doc", _name, globals()[_name])

del _name


__all__ = [
    "acroform_present",
    "has_embedded_files",
    "has_javascript",
    "has_output_intent",
    "has_xmp",
    "is_linearized",
    "is_pdf_a",
    "is_pdf_va",
    "is_pdf_x",
    "output_intent_subtype",
    "pdf_a_part",
    "pdf_version",
    "pdf_x_part",
    "signature_count",
]
