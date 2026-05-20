"""Build PathPaintingEvent / TextRenderedEvent from raw PDF content streams.

Called by extract_semantic_document_via_codex to populate the event stream
that event-driven analyzers (HairlineAnalyzer, LegibilityCompositeAnalyzer,
etc.) consume. Uses pikepdf directly to walk each page's content stream with
full graphics-state tracking so events carry resolved coordinates and widths.

Codex's content_ops signal omits colour-setters and line-style operators and
does not resolve the current transformation matrix — not enough to build
accurate events. This module does a full per-page pass using pikepdf, which is
already a transitive dependency via codex-pdf.
"""

from __future__ import annotations

import logging
import math
from io import BytesIO
from typing import Any

logger = logging.getLogger(__name__)

# 6-element affine matrix as (a, b, c, d, e, f)
_CTM = tuple[float, float, float, float, float, float]
_IDENTITY: _CTM = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# Matrix helpers
# ---------------------------------------------------------------------------


def _mul(m: _CTM, n: _CTM) -> _CTM:
    """Return m x n (row-vector convention: new_ctm = old_ctm x delta)."""
    ma, mb, mc, md, me, mf = m
    na, nb, nc, nd, ne, nf = n
    return (
        ma * na + mb * nc,
        ma * nb + mb * nd,
        mc * na + md * nc,
        mc * nb + md * nd,
        me * na + mf * nc + ne,
        me * nb + mf * nd + nf,
    )


def _pt(m: _CTM, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def _scale_y(m: _CTM) -> float:
    """Approximate y-axis scale factor — used for effective line-width."""
    return math.sqrt(m[2] * m[2] + m[3] * m[3]) or 1.0


def _scale_uniform(m: _CTM) -> float:
    sx = math.sqrt(m[0] * m[0] + m[1] * m[1])
    sy = math.sqrt(m[2] * m[2] + m[3] * m[3])
    return math.sqrt((sx * sx + sy * sy) / 2.0) or 1.0


def _to_tm(m: _CTM) -> Any:
    from lintpdf.semantic.graphics_state import TransformationMatrix

    return TransformationMatrix(a=m[0], b=m[1], c=m[2], d=m[3], e=m[4], f=m[5])


# ---------------------------------------------------------------------------
# Safe operand coercion
# ---------------------------------------------------------------------------


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _i(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _name(v: Any) -> str:
    return str(v).lstrip("/")


def _str_len(v: Any) -> int:
    """Estimate glyph count from a PDF string operand."""
    if isinstance(v, (bytes, bytearray)):
        return len(v)
    try:
        return len(str(v))
    except Exception:
        return 1


def _str_val(v: Any) -> str:
    """Decode a PDF string operand to a plain string if it is ASCII-safe.

    Returns "" for CID/hex blobs where the bytes don't map to printable
    text (those carry glyph indices, not characters).
    """
    raw: bytes | None = None
    if isinstance(v, (bytes, bytearray)):
        raw = bytes(v)
    else:
        try:
            raw = bytes(v)
        except Exception:
            try:
                s = str(v)
                return s if s.isprintable() else ""
            except Exception:
                return ""
    if raw is None:
        return ""
    try:
        text = raw.decode("latin-1")
        # Reject if more than 20% non-printable ASCII — likely CID indices
        printable = sum(1 for c in text if c.isprintable())
        if len(text) > 0 and printable / len(text) < 0.8:
            return ""
        return text
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_events_from_pdf(pdf_bytes: bytes) -> list[Any]:
    """Walk every page of *pdf_bytes* and return semantic events.

    Returns an empty list on any failure so callers degrade gracefully.
    """
    try:
        import pikepdf  # transitive dep via codex-pdf
    except ImportError:
        logger.warning("pikepdf not available; event stream will be empty")
        return []
    try:
        return _extract(pdf_bytes, pikepdf)
    except Exception:
        logger.exception("codex event extraction failed; returning empty list")
        return []


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


def _extract(pdf_bytes: bytes, pikepdf: Any) -> list[Any]:
    events: list[Any] = []
    with pikepdf.open(BytesIO(pdf_bytes)) as pdf:
        for idx, page in enumerate(pdf.pages):
            try:
                walker = _Walker(idx + 1, page, pikepdf)
                walker.walk()
                events.extend(walker.events)
            except Exception:
                logger.debug("page %d event extraction failed", idx + 1, exc_info=True)
    return events


class _Walker:
    """Walks one PDF page's content stream and collects semantic events."""

    __slots__ = (
        "cs_to_spot",
        "ctm",
        "dash_pattern",
        "events",
        "extgstate_res",
        "fill_cs",
        "fill_opacity",
        "fill_vals",
        "font_name",
        "font_size",
        "gs_stack",
        "in_text",
        "line_cap",
        "line_join",
        "line_width",
        "op_non_stroking",
        "op_stroking",
        "opm",
        "page",
        "page_num",
        "path_pts",
        "path_start",
        "pikepdf",
        "rendering_mode",
        "stroke_cs",
        "stroke_opacity",
        "stroke_vals",
        "text_leading",
        "text_line_matrix",
        "text_matrix",
    )

    def __init__(self, page_num: int, page: Any, pikepdf: Any) -> None:
        self.page_num = page_num
        self.page = page
        self.pikepdf = pikepdf
        self.events: list[Any] = []

        self.ctm: _CTM = _IDENTITY
        self.gs_stack: list[dict[str, Any]] = []
        self.line_width = 1.0
        self.line_cap = 0
        self.line_join = 0
        self.dash_pattern: tuple[tuple[float, ...], float] = ((), 0.0)
        self.stroke_cs = "DeviceGray"
        self.stroke_vals: tuple[float, ...] = (0.0,)
        self.fill_cs = "DeviceGray"
        self.fill_vals: tuple[float, ...] = (0.0,)
        self.stroke_opacity = 1.0
        self.fill_opacity = 1.0
        self.op_stroking = False
        self.op_non_stroking = False
        self.opm = 0

        self.path_pts: list[tuple[float, float]] = []
        self.path_start: tuple[float, float] | None = None

        self.in_text = False
        self.font_name = ""
        self.font_size = 12.0
        self.text_matrix: _CTM = _IDENTITY
        self.text_line_matrix: _CTM = _IDENTITY
        self.text_leading = 0.0
        self.rendering_mode = 0

        self.extgstate_res = _extgstate(page)
        self.cs_to_spot = _cs_to_spot(page)

    # ------------------------------------------------------------------

    def walk(self) -> None:
        try:
            instructions = list(self.pikepdf.parse_content_stream(self.page))
        except Exception:
            return
        for op_idx, inst in enumerate(instructions):
            try:
                op = str(getattr(inst, "operator", ""))
                operands = list(getattr(inst, "operands", []))
                self._op(op, operands, op_idx)
            except Exception:
                continue

    # ------------------------------------------------------------------
    # Graphics state
    # ------------------------------------------------------------------

    def _save(self) -> None:
        self.gs_stack.append(
            {
                "ctm": self.ctm,
                "lw": self.line_width,
                "lc": self.line_cap,
                "lj": self.line_join,
                "dp": self.dash_pattern,
                "scs": self.stroke_cs,
                "sv": self.stroke_vals,
                "fcs": self.fill_cs,
                "fv": self.fill_vals,
                "so": self.stroke_opacity,
                "fo": self.fill_opacity,
                "ops": self.op_stroking,
                "opn": self.op_non_stroking,
                "opm": self.opm,
            }
        )

    def _restore(self) -> None:
        if not self.gs_stack:
            return
        s = self.gs_stack.pop()
        self.ctm = s["ctm"]
        self.line_width = s["lw"]
        self.line_cap = s["lc"]
        self.line_join = s["lj"]
        self.dash_pattern = s["dp"]
        self.stroke_cs = s["scs"]
        self.stroke_vals = s["sv"]
        self.fill_cs = s["fcs"]
        self.fill_vals = s["fv"]
        self.stroke_opacity = s["so"]
        self.fill_opacity = s["fo"]
        self.op_stroking = s["ops"]
        self.op_non_stroking = s["opn"]
        self.opm = s["opm"]

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _pt(self, x: float, y: float) -> None:
        self.path_pts.append(_pt(self.ctm, x, y))

    def _path_bbox(self) -> tuple[float, float, float, float] | None:
        if not self.path_pts:
            return None
        xs = [p[0] for p in self.path_pts]
        ys = [p[1] for p in self.path_pts]
        return (min(xs), min(ys), max(xs), max(ys))

    def _effective_lw(self) -> float:
        return self.line_width * _scale_uniform(self.ctm)

    def _paint(self, fill: bool, stroke: bool, even_odd: bool, op_idx: int) -> None:
        from lintpdf.semantic.events import PathPaintingEvent

        bbox = self._path_bbox()
        self.events.append(
            PathPaintingEvent(
                operator="B" if fill and stroke else ("f" if fill else "S"),
                page_num=self.page_num,
                operator_index=op_idx,
                fill=fill,
                stroke=stroke,
                even_odd=even_odd,
                fill_color_space=self.fill_cs if fill else "",
                fill_color_values=self.fill_vals if fill else (),
                stroke_color_space=self.stroke_cs if stroke else "",
                stroke_color_values=self.stroke_vals if stroke else (),
                line_width=self._effective_lw(),
                line_cap=self.line_cap,
                line_join=self.line_join,
                dash_pattern=self.dash_pattern,
                point_count=len(self.path_pts),
                bbox=bbox,
            )
        )
        self.path_pts.clear()
        self.path_start = None

    # ------------------------------------------------------------------
    # Text helpers
    # ------------------------------------------------------------------

    def _move_text(self, tx: float, ty: float) -> None:
        self.text_line_matrix = _mul(self.text_line_matrix, (1.0, 0.0, 0.0, 1.0, tx, ty))
        self.text_matrix = self.text_line_matrix

    def _text_bbox(self, text_len: int) -> tuple[float, float, float, float] | None:
        combined = _mul(self.text_matrix, self.ctm)
        ox, oy = _pt(combined, 0.0, 0.0)
        # Approximate width using ~0.55 em per glyph, height = font_size
        w = max(text_len, 1) * self.font_size * 0.55
        h = max(self.font_size, 1.0)
        ex, ey = _pt(combined, w, h)
        x0, x1 = min(ox, ex), max(ox, ex)
        y0, y1 = min(oy, ey), max(oy, ey)
        if x1 <= x0 or y1 <= y0:
            return None
        return (x0, y0, x1, y1)

    def _emit_color(self, op: str, op_idx: int, *, stroking: bool) -> None:
        from lintpdf.semantic.events import ColorChangedEvent

        cs = self.stroke_cs if stroking else self.fill_cs
        vals = self.stroke_vals if stroking else self.fill_vals
        self.events.append(
            ColorChangedEvent(
                operator=op,
                page_num=self.page_num,
                operator_index=op_idx,
                color_space=cs,
                color_values=vals,
                stroking=stroking,
            )
        )

    def _emit_text(self, text_len: int, op_idx: int, raw_text: str = "") -> None:
        if not self.in_text or self.font_size <= 0:
            return
        from lintpdf.semantic.events import TextRenderedEvent

        self.events.append(
            TextRenderedEvent(
                operator="Tj",
                page_num=self.page_num,
                operator_index=op_idx,
                font_name=self.font_name,
                font_size=self.font_size,
                ctm=_to_tm(self.ctm),
                text_matrix=_to_tm(self.text_matrix),
                color_space=self.fill_cs,
                color_values=self.fill_vals,
                opacity=self.fill_opacity,
                rendering_mode=self.rendering_mode,
                bbox=self._text_bbox(text_len),
                raw_text=raw_text,
            )
        )

    # ------------------------------------------------------------------
    # Operator dispatch
    # ------------------------------------------------------------------

    def _op(self, op: str, ops: list[Any], idx: int) -> None:
        # graphics state
        if op == "q":
            self._save()
        elif op == "Q":
            self._restore()
        elif op == "cm" and len(ops) == 6:
            delta = tuple(_f(v) for v in ops)
            self.ctm = _mul(self.ctm, delta)  # type: ignore[arg-type]
        elif op == "w" and ops:
            self.line_width = max(0.0, _f(ops[0]))
        elif op == "J" and ops:
            self.line_cap = _i(ops[0])
        elif op == "j" and ops:
            self.line_join = _i(ops[0])
        elif op == "d" and len(ops) >= 2:
            try:
                arr = tuple(_f(v) for v in ops[0])
                self.dash_pattern = (arr, _f(ops[1]))
            except Exception:
                pass
        elif op == "gs" and ops:
            gs = self.extgstate_res.get(_name(ops[0]), {})
            if "LW" in gs:
                self.line_width = max(0.0, _f(gs["LW"]))
            if "LC" in gs:
                self.line_cap = _i(gs["LC"])
            if "LJ" in gs:
                self.line_join = _i(gs["LJ"])
            if "CA" in gs:
                self.stroke_opacity = _f(gs["CA"], 1.0)
            if "ca" in gs:
                self.fill_opacity = _f(gs["ca"], 1.0)
            # Emit OverprintChangedEvent when OP/op/OPM appear in the dict.
            if "OP" in gs or "op" in gs or "OPM" in gs:
                from lintpdf.semantic.events import OverprintChangedEvent

                new_ops = bool(gs["OP"]) if "OP" in gs else self.op_stroking
                new_opn = bool(gs["op"]) if "op" in gs else self.op_non_stroking
                new_opm = int(gs["OPM"]) if "OPM" in gs else self.opm
                self.op_stroking = new_ops
                self.op_non_stroking = new_opn
                self.opm = new_opm
                self.events.append(
                    OverprintChangedEvent(
                        operator="gs",
                        page_num=self.page_num,
                        operator_index=idx,
                        overprint_stroking=new_ops,
                        overprint_non_stroking=new_opn,
                        overprint_mode=new_opm,
                    )
                )

        # colour — update state and emit ColorChangedEvent so overprint
        # analyzers (LPDF_OVER_001/004/006/008) can see color transitions.
        elif op == "g" and ops:
            self.fill_cs, self.fill_vals = "DeviceGray", (_f(ops[0]),)
            self._emit_color(op, idx, stroking=False)
        elif op == "G" and ops:
            self.stroke_cs, self.stroke_vals = "DeviceGray", (_f(ops[0]),)
            self._emit_color(op, idx, stroking=True)
        elif op == "rg" and len(ops) >= 3:
            self.fill_cs = "DeviceRGB"
            self.fill_vals = tuple(_f(v) for v in ops[:3])
            self._emit_color(op, idx, stroking=False)
        elif op == "RG" and len(ops) >= 3:
            self.stroke_cs = "DeviceRGB"
            self.stroke_vals = tuple(_f(v) for v in ops[:3])
            self._emit_color(op, idx, stroking=True)
        elif op == "k" and len(ops) >= 4:
            self.fill_cs = "DeviceCMYK"
            self.fill_vals = tuple(_f(v) for v in ops[:4])
            self._emit_color(op, idx, stroking=False)
        elif op == "K" and len(ops) >= 4:
            self.stroke_cs = "DeviceCMYK"
            self.stroke_vals = tuple(_f(v) for v in ops[:4])
            self._emit_color(op, idx, stroking=True)
        elif op == "cs" and ops:
            cs = _name(ops[0])
            self.fill_cs = self.cs_to_spot.get(cs, cs)
        elif op == "CS" and ops:
            cs = _name(ops[0])
            self.stroke_cs = self.cs_to_spot.get(cs, cs)
        elif op in ("sc", "scn"):
            self.fill_vals = tuple(_f(v) for v in ops if isinstance(v, (int, float)))
            self._emit_color(op, idx, stroking=False)
        elif op in ("SC", "SCN"):
            self.stroke_vals = tuple(_f(v) for v in ops if isinstance(v, (int, float)))
            self._emit_color(op, idx, stroking=True)

        # path construction
        elif op == "m" and len(ops) >= 2:
            x, y = _f(ops[0]), _f(ops[1])
            self.path_start = (x, y)
            self._pt(x, y)
        elif op == "l" and len(ops) >= 2:
            self._pt(_f(ops[0]), _f(ops[1]))
        elif op == "c" and len(ops) >= 6:
            for i in (0, 2, 4):
                self._pt(_f(ops[i]), _f(ops[i + 1]))
        elif op in ("v", "y") and len(ops) >= 4:
            self._pt(_f(ops[0]), _f(ops[1]))
            self._pt(_f(ops[2]), _f(ops[3]))
        elif op == "re" and len(ops) >= 4:
            rx, ry, rw, rh = _f(ops[0]), _f(ops[1]), _f(ops[2]), _f(ops[3])
            self.path_start = (rx, ry)
            for cx, cy in ((rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh)):
                self._pt(cx, cy)
        elif op == "h" and self.path_start:
            self._pt(*self.path_start)

        # path painting
        elif op == "S":
            self._paint(False, True, False, idx)
        elif op == "s":
            if self.path_start:
                self._pt(*self.path_start)
            self._paint(False, True, False, idx)
        elif op in ("f", "F"):
            self._paint(True, False, False, idx)
        elif op == "f*":
            self._paint(True, False, True, idx)
        elif op == "B":
            self._paint(True, True, False, idx)
        elif op == "B*":
            self._paint(True, True, True, idx)
        elif op == "b":
            if self.path_start:
                self._pt(*self.path_start)
            self._paint(True, True, False, idx)
        elif op == "b*":
            if self.path_start:
                self._pt(*self.path_start)
            self._paint(True, True, True, idx)
        elif op == "n":
            self.path_pts.clear()
            self.path_start = None

        # text state
        elif op == "BT":
            self.in_text = True
            self.text_matrix = _IDENTITY
            self.text_line_matrix = _IDENTITY
        elif op == "ET":
            self.in_text = False
        elif op == "Tf" and len(ops) >= 2:
            self.font_name = _name(ops[0])
            self.font_size = max(0.0, _f(ops[1]))
        elif op == "Tm" and len(ops) >= 6:
            m = tuple(_f(v) for v in ops[:6])
            self.text_matrix = m  # type: ignore[assignment]
            self.text_line_matrix = m  # type: ignore[assignment]
        elif op == "Td" and len(ops) >= 2:
            self._move_text(_f(ops[0]), _f(ops[1]))
        elif op == "TD" and len(ops) >= 2:
            tx, ty = _f(ops[0]), _f(ops[1])
            self.text_leading = -ty
            self._move_text(tx, ty)
        elif op == "T*":
            self._move_text(0.0, -self.text_leading)
        elif op == "TL" and ops:
            self.text_leading = _f(ops[0])
        elif op == "Tr" and ops:
            self.rendering_mode = _i(ops[0])
        elif op == "Tj" and ops:
            self._emit_text(_str_len(ops[0]), idx, _str_val(ops[0]))
        elif op == "TJ" and ops:
            try:
                parts = [item for item in ops[0] if not isinstance(item, (int, float))]
                total = sum(_str_len(item) for item in parts)
                joined = "".join(_str_val(item) for item in parts)
            except Exception:
                total = 1
                joined = ""
            self._emit_text(max(total, 1), idx, joined)
        elif op in ("'", '"'):
            self._move_text(0.0, -self.text_leading)
            src = ops[-1] if ops else b""
            self._emit_text(_str_len(src), idx, _str_val(src))


# ---------------------------------------------------------------------------
# Resource extraction helpers
# ---------------------------------------------------------------------------


def _extgstate(page: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    try:
        res = page.get("/Resources") if hasattr(page, "get") else None
        gs_dict = res.get("/ExtGState") if res and hasattr(res, "get") else None
        if gs_dict is None:
            return out
        for key, val in gs_dict.items():
            name = str(key).lstrip("/")
            entry: dict[str, Any] = {}
            if not hasattr(val, "get"):
                out[name] = entry
                continue
            import contextlib

            for k, conv in (
                ("/LW", float),
                ("/LC", int),
                ("/LJ", int),
                ("/CA", float),
                ("/ca", float),
                ("/OP", bool),
                ("/op", bool),
                ("/OPM", int),
            ):
                v = val.get(k)
                if v is not None:
                    with contextlib.suppress(Exception):
                        entry[k.lstrip("/")] = conv(v)
            out[name] = entry
    except Exception:
        pass
    return out


def _cs_to_spot(page: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        res = page.get("/Resources") if hasattr(page, "get") else None
        cs_dict = res.get("/ColorSpace") if res and hasattr(res, "get") else None
        if cs_dict is None:
            return out
        for key, val in cs_dict.items():
            try:
                if str(val[0]).lstrip("/") == "Separation":
                    out[str(key).lstrip("/")] = str(val[1]).lstrip("/")
            except Exception:
                pass
    except Exception:
        pass
    return out
