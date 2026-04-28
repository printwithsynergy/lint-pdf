"""ContentStreamInterpreter — state machine for PDF content stream operators.

Walks the parsed content stream, tracking graphics state and emitting
semantic events. Analyzers consume events; they never touch raw operators.

Operator priority (from implementation plan):
- CRITICAL (18): q, Q, cm, gs, Do, Tf, Tj, TJ, BT, ET, Tm, sc/scn, SC/SCN,
  cs/CS, rg/RG, k/K, g/G, BI/ID/EI
- IMPORTANT (14): W, W*, m, l, c, v, y, h, re, S, s, f, F, f*, B, B*, b, b*,
  n, Td, TD, T*, ', "
- DEFERRABLE (~60): line style, rendering intent, marked content, etc.

Reference: lintpdf-research/implementation-plan.md Module 3
Reference: ISO 32000-2 section 8 (Graphics), section 9 (Text)
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from lintpdf.semantic.events import (
    ClippingPathSetEvent,
    ColorChangedEvent,
    ContentStreamEvent,
    FormXObjectEnteredEvent,
    ImagePlacedEvent,
    LineStyleChangedEvent,
    OpacityChangedEvent,
    OverprintChangedEvent,
    PathPaintingEvent,
    PrepressStateChangedEvent,
    TextRenderedEvent,
)
from lintpdf.semantic.graphics_state import GraphicsState, TransformationMatrix

logger = logging.getLogger(__name__)

# Maximum Form XObject nesting depth to prevent infinite recursion
_MAX_FORM_XOBJECT_DEPTH = 32


class ContentStreamInterpreter:
    """State machine interpreter for PDF content streams.

    Processes operator/operand pairs from pikepdf's content stream parser,
    maintains the graphics state stack, and emits semantic events.

    Usage:
        interpreter = ContentStreamInterpreter(page_num=1, resources=resources)
        events = interpreter.interpret(instructions)
    """

    def __init__(
        self,
        page_num: int,
        resources: dict[str, Any],
        *,
        nesting_depth: int = 0,
        initial_ctm: TransformationMatrix | None = None,
        visited_forms: frozenset[tuple[int, int]] | None = None,
    ) -> None:
        self._page_num = page_num
        self._resources = resources
        self._nesting_depth = nesting_depth
        self._visited_forms = visited_forms or frozenset()

        # State stack
        initial_state = GraphicsState()
        if initial_ctm is not None:
            initial_state.ctm = initial_ctm
        self._state_stack: list[GraphicsState] = [initial_state]
        self._events: list[ContentStreamEvent] = []
        self._operator_index = 0

        # Text object tracking
        self._in_text_object = False

        # Current path points (for bounding box estimation)
        self._current_path: list[tuple[float, float]] = []

        # Build operator dispatch table
        self._handlers: dict[str, Any] = {
            # Graphics state (CRITICAL)
            "q": self._handle_q,
            "Q": self._handle_Q,
            "cm": self._handle_cm,
            "gs": self._handle_gs,
            # XObject (CRITICAL)
            "Do": self._handle_Do,
            # Text (CRITICAL)
            "BT": self._handle_BT,
            "ET": self._handle_ET,
            "Tf": self._handle_Tf,
            "Tj": self._handle_Tj,
            "TJ": self._handle_TJ,
            "Tm": self._handle_Tm,
            # Color — non-stroking (CRITICAL)
            "sc": self._handle_sc,
            "scn": self._handle_sc,
            "rg": self._handle_rg,
            "k": self._handle_k,
            "g": self._handle_g,
            "cs": self._handle_cs,
            # Color — stroking (CRITICAL)
            "SC": self._handle_SC,
            "SCN": self._handle_SC,
            "RG": self._handle_RG,
            "K": self._handle_K,
            "G": self._handle_G,
            "CS": self._handle_CS,
            # Inline image (CRITICAL)
            "BI_ID_EI": self._handle_inline_image,
            # Path construction (IMPORTANT)
            "m": self._handle_m,
            "l": self._handle_l,
            "c": self._handle_c,
            "v": self._handle_v,
            "y": self._handle_y,
            "h": self._handle_h,
            "re": self._handle_re,
            # Path painting (IMPORTANT)
            "S": self._handle_S,
            "s": self._handle_s,
            "f": self._handle_f,
            "F": self._handle_f,
            "f*": self._handle_f_star,
            "B": self._handle_B,
            "B*": self._handle_B_star,
            "b": self._handle_b,
            "b*": self._handle_b_star,
            "n": self._handle_n,
            # Clipping (IMPORTANT)
            "W": self._handle_W,
            "W*": self._handle_W_star,
            # Text positioning (IMPORTANT)
            "Td": self._handle_Td,
            "TD": self._handle_TD,
            "T*": self._handle_T_star,
            # Text showing (IMPORTANT)
            "'": self._handle_quote,
            '"': self._handle_double_quote,
            # Line width and style (for thin line / hairline detection)
            "w": self._handle_w,
            "J": self._handle_J,
            "j": self._handle_j,
            "d": self._handle_d,
            "M": self._handle_M,
            "i": self._handle_i,
            "ri": self._handle_ri,
        }

    @property
    def state(self) -> GraphicsState:
        """Current graphics state (top of stack)."""
        return self._state_stack[-1]

    def interpret(self, instructions: list[tuple[list[Any], str]]) -> list[ContentStreamEvent]:
        """Interpret content stream instructions and emit events.

        Args:
            instructions: List of (operands, operator_name) from parser.

        Returns:
            List of semantic events.
        """
        for operands, operator in instructions:
            handler = self._handlers.get(operator)
            if handler is not None:
                try:
                    handler(operands)
                except Exception:
                    logger.debug(
                        "Error handling operator %s on page %d at index %d",
                        operator,
                        self._page_num,
                        self._operator_index,
                        exc_info=True,
                    )
            self._operator_index += 1

        # Validate state stack balance
        if len(self._state_stack) != 1:
            logger.warning(
                "Page %d: graphics state stack imbalance (expected 1, got %d after %d operators)",
                self._page_num,
                len(self._state_stack),
                self._operator_index,
            )

        return self._events

    def _emit(self, event: ContentStreamEvent) -> None:
        self._events.append(event)

    # --- CRITICAL: Graphics State ---

    def _handle_q(self, _operands: list[Any]) -> None:
        """Save graphics state (push copy onto stack)."""
        self._state_stack.append(self.state.copy())

    def _handle_Q(self, _operands: list[Any]) -> None:
        """Restore graphics state (pop from stack)."""
        if len(self._state_stack) > 1:
            self._state_stack.pop()
        else:
            logger.warning("Page %d: Q without matching q", self._page_num)

    def _handle_cm(self, operands: list[Any]) -> None:
        """Concatenate matrix to CTM."""
        if len(operands) < 6:
            return
        new_matrix = TransformationMatrix(
            a=float(operands[0]),
            b=float(operands[1]),
            c=float(operands[2]),
            d=float(operands[3]),
            e=float(operands[4]),
            f=float(operands[5]),
        )
        self.state.ctm = new_matrix.multiply(self.state.ctm)

    def _handle_gs(self, operands: list[Any]) -> None:  # skipcq: PY-R1000
        """Set graphics state from ExtGState dictionary."""
        if not operands:
            return
        gs_name = str(operands[0]).lstrip("/")
        ext_gstate = self._resources.get("/ExtGState", {})
        if not isinstance(ext_gstate, dict):
            return
        gs_dict = ext_gstate.get(f"/{gs_name}") or ext_gstate.get(gs_name)
        if not isinstance(gs_dict, dict):
            return

        opacity_changed = False
        s_alpha = None
        ns_alpha = None
        blend_mode = None

        # Stroking alpha (CA)
        ca_upper = gs_dict.get("/CA")
        if ca_upper is not None:
            try:
                self.state.stroking_alpha = float(ca_upper)
                s_alpha = self.state.stroking_alpha
                opacity_changed = True
            except (TypeError, ValueError):
                pass

        # Non-stroking alpha (ca)
        ca_lower = gs_dict.get("/ca")
        if ca_lower is not None:
            try:
                self.state.non_stroking_alpha = float(ca_lower)
                ns_alpha = self.state.non_stroking_alpha
                opacity_changed = True
            except (TypeError, ValueError):
                pass

        # Blend mode (BM)
        bm = gs_dict.get("/BM")
        if bm is not None:
            bm_str = str(bm).lstrip("/")
            self.state.blend_mode = bm_str
            blend_mode = bm_str
            opacity_changed = True

        if opacity_changed:
            self._emit(
                OpacityChangedEvent(
                    operator="gs",
                    page_num=self._page_num,
                    operator_index=self._operator_index,
                    stroking_alpha=s_alpha,
                    non_stroking_alpha=ns_alpha,
                    blend_mode=blend_mode,
                )
            )

        # Overprint
        overprint_changed = False
        op_stroking = None
        op_non_stroking = None
        opm = None

        op_upper = gs_dict.get("/OP")
        if op_upper is not None:
            self.state.overprint_stroking = bool(op_upper)
            op_stroking = self.state.overprint_stroking
            overprint_changed = True

        op_lower = gs_dict.get("/op")
        if op_lower is not None:
            self.state.overprint_non_stroking = bool(op_lower)
            op_non_stroking = self.state.overprint_non_stroking
            overprint_changed = True

        opm_val = gs_dict.get("/OPM")
        if opm_val is not None:
            try:
                self.state.overprint_mode = int(opm_val)
                opm = self.state.overprint_mode
                overprint_changed = True
            except (TypeError, ValueError):
                pass

        if overprint_changed:
            self._emit(
                OverprintChangedEvent(
                    operator="gs",
                    page_num=self._page_num,
                    operator_index=self._operator_index,
                    overprint_stroking=op_stroking,
                    overprint_non_stroking=op_non_stroking,
                    overprint_mode=opm,
                )
            )

        # Line style from ExtGState
        lc = gs_dict.get("/LC")
        if lc is not None:
            with contextlib.suppress(TypeError, ValueError):
                self.state.line_cap = int(lc)

        lj = gs_dict.get("/LJ")
        if lj is not None:
            with contextlib.suppress(TypeError, ValueError):
                self.state.line_join = int(lj)

        ml = gs_dict.get("/ML")
        if ml is not None:
            with contextlib.suppress(TypeError, ValueError):
                self.state.miter_limit = float(ml)

        d_val = gs_dict.get("/D")
        if isinstance(d_val, list) and len(d_val) == 2:
            with contextlib.suppress(TypeError, ValueError):
                if isinstance(d_val[0], list):
                    self.state.dash_pattern = (
                        tuple(float(v) for v in d_val[0]),
                        float(d_val[1]),
                    )

        fl = gs_dict.get("/FL")
        if fl is not None:
            with contextlib.suppress(TypeError, ValueError):
                self.state.flatness = float(fl)

        ri_val = gs_dict.get("/RI")
        if ri_val is not None:
            self.state.rendering_intent = str(ri_val).lstrip("/")

        # Prepress state: halftone, transfer function, BG/UCR
        prepress_changed = False
        ht = gs_dict.get("/HT")
        if ht is not None:
            self.state.has_halftone = True
            prepress_changed = True

        for tr_key in ("/TR", "/TR2"):
            tr = gs_dict.get(tr_key)
            if tr is not None and tr != "/Identity":
                self.state.has_transfer_function = True
                prepress_changed = True
                break

        for bg_ucr_key in ("/BG", "/BG2", "/UCR", "/UCR2"):
            bg_ucr = gs_dict.get(bg_ucr_key)
            if bg_ucr is not None:
                self.state.has_bg_ucr = True
                prepress_changed = True
                break

        if prepress_changed:
            self._emit(
                PrepressStateChangedEvent(
                    operator="gs",
                    page_num=self._page_num,
                    operator_index=self._operator_index,
                    has_halftone=self.state.has_halftone,
                    has_transfer_function=self.state.has_transfer_function,
                    has_bg_ucr=self.state.has_bg_ucr,
                )
            )

    # --- CRITICAL: XObject ---

    def _handle_Do(self, operands: list[Any]) -> None:
        """Invoke an XObject (image or form)."""
        if not operands:
            return
        xobj_name = str(operands[0]).lstrip("/")
        xobjects = self._resources.get("/XObject", {})
        if not isinstance(xobjects, dict):
            return
        xobj = xobjects.get(f"/{xobj_name}") or xobjects.get(xobj_name)
        if not isinstance(xobj, dict):
            return

        subtype = str(xobj.get("/Subtype", "")).lstrip("/")

        if subtype == "Image":
            self._handle_image_xobject(xobj_name, xobj)
        elif subtype == "Form":
            self._handle_form_xobject(xobj_name, xobj)

    def _handle_image_xobject(self, name: str, xobj: dict[str, Any]) -> None:
        """Emit ImagePlacedEvent for an image XObject."""
        width = int(xobj.get("/Width", 0))
        height = int(xobj.get("/Height", 0))
        bpc = int(xobj.get("/BitsPerComponent", 8))
        cs = str(xobj.get("/ColorSpace", "")).lstrip("/")
        has_soft_mask = xobj.get("/SMask") is not None
        has_opi = xobj.get("/OPI") is not None
        has_alternate = xobj.get("/Alternates") is not None

        filters: list[str] = []
        filter_val = xobj.get("/Filter")
        if isinstance(filter_val, str):
            filters = [filter_val.lstrip("/")]
        elif isinstance(filter_val, list):
            filters = [str(f).lstrip("/") for f in filter_val]

        self._emit(
            ImagePlacedEvent(
                operator="Do",
                page_num=self._page_num,
                operator_index=self._operator_index,
                image_name=name,
                ctm=TransformationMatrix(
                    self.state.ctm.a,
                    self.state.ctm.b,
                    self.state.ctm.c,
                    self.state.ctm.d,
                    self.state.ctm.e,
                    self.state.ctm.f,
                ),
                pixel_width=width,
                pixel_height=height,
                bits_per_component=bpc,
                color_space=cs,
                filters=tuple(filters),
                has_soft_mask=has_soft_mask,
                has_opi=has_opi,
                has_alternate=has_alternate,
            )
        )

    def _handle_form_xobject(self, name: str, xobj: dict[str, Any]) -> None:
        """Handle Form XObject: emit event and recursively interpret."""
        if self._nesting_depth >= _MAX_FORM_XOBJECT_DEPTH:
            logger.warning(
                "Page %d: Form XObject depth limit (%d) reached at %s",
                self._page_num,
                _MAX_FORM_XOBJECT_DEPTH,
                name,
            )
            return

        # Cycle detection — not feasible with dict-based resources
        # (no obj_num available), so rely on depth limit

        # Parse form matrix
        form_matrix = TransformationMatrix()
        matrix_val = xobj.get("/Matrix")
        if isinstance(matrix_val, list) and len(matrix_val) == 6:
            with contextlib.suppress(TypeError, ValueError):
                form_matrix = TransformationMatrix(
                    a=float(matrix_val[0]),
                    b=float(matrix_val[1]),
                    c=float(matrix_val[2]),
                    d=float(matrix_val[3]),
                    e=float(matrix_val[4]),
                    f=float(matrix_val[5]),
                )

        # Effective CTM = form_matrix x current CTM
        effective_ctm = form_matrix.multiply(self.state.ctm)

        self._emit(
            FormXObjectEnteredEvent(
                operator="Do",
                page_num=self._page_num,
                operator_index=self._operator_index,
                form_name=name,
                form_matrix=form_matrix,
                ctm=effective_ctm,
                nesting_depth=self._nesting_depth + 1,
            )
        )

        # Merge form resources with page resources (form overrides)
        form_resources = xobj.get("/Resources", {})
        if isinstance(form_resources, dict):
            merged = dict(self._resources)
            for key, value in form_resources.items():
                if isinstance(value, dict) and isinstance(merged.get(key), dict):
                    merged_sub = dict(merged[key])
                    merged_sub.update(value)
                    merged[key] = merged_sub
                else:
                    merged[key] = value
        else:
            merged = self._resources

        # Note: actual recursive interpretation of the form's content stream
        # requires access to the raw pikepdf stream data, which we don't have
        # from the dict-based resources. The interpreter works with pre-parsed
        # instructions. In a full pipeline, the SemanticModel builder would
        # invoke the adapter to parse the form's content stream and feed it
        # back through a nested interpreter.

    # --- CRITICAL: Text ---

    def _handle_BT(self, _operands: list[Any]) -> None:
        """Begin text object."""
        self._in_text_object = True
        self.state.text_matrix = TransformationMatrix()
        self.state.text_line_matrix = TransformationMatrix()

    def _handle_ET(self, _operands: list[Any]) -> None:
        """End text object."""
        self._in_text_object = False

    def _handle_Tf(self, operands: list[Any]) -> None:
        """Set text font and size."""
        if len(operands) < 2:
            return
        self.state.font_name = str(operands[0]).lstrip("/")
        with contextlib.suppress(TypeError, ValueError):
            self.state.font_size = float(operands[1])

    def _handle_Tj(self, operands: list[Any]) -> None:
        """Show text string."""
        self._emit_text_event("Tj")

    def _handle_TJ(self, operands: list[Any]) -> None:
        """Show text array (with positioning adjustments)."""
        self._emit_text_event("TJ")

    def _handle_Tm(self, operands: list[Any]) -> None:
        """Set text matrix."""
        if len(operands) < 6:
            return
        self.state.text_matrix = TransformationMatrix(
            a=float(operands[0]),
            b=float(operands[1]),
            c=float(operands[2]),
            d=float(operands[3]),
            e=float(operands[4]),
            f=float(operands[5]),
        )
        self.state.text_line_matrix = TransformationMatrix(
            a=float(operands[0]),
            b=float(operands[1]),
            c=float(operands[2]),
            d=float(operands[3]),
            e=float(operands[4]),
            f=float(operands[5]),
        )

    def _emit_text_event(self, operator: str) -> None:
        """Emit a TextRenderedEvent with current state."""
        self._emit(
            TextRenderedEvent(
                operator=operator,
                page_num=self._page_num,
                operator_index=self._operator_index,
                font_name=self.state.font_name or "",
                font_size=self.state.font_size,
                ctm=TransformationMatrix(
                    self.state.ctm.a,
                    self.state.ctm.b,
                    self.state.ctm.c,
                    self.state.ctm.d,
                    self.state.ctm.e,
                    self.state.ctm.f,
                ),
                text_matrix=TransformationMatrix(
                    self.state.text_matrix.a,
                    self.state.text_matrix.b,
                    self.state.text_matrix.c,
                    self.state.text_matrix.d,
                    self.state.text_matrix.e,
                    self.state.text_matrix.f,
                ),
                color_space=self.state.non_stroking_color_space,
                color_values=tuple(self.state.non_stroking_color),
                opacity=self.state.non_stroking_alpha,
                rendering_mode=self.state.text_rendering_mode,
                rendering_intent=self.state.rendering_intent,
                bbox=self._text_bbox(),
            )
        )

    def _text_bbox(self) -> tuple[float, float, float, float] | None:
        """Approximate bbox for the current text-rendering state.

        The interpreter doesn't have the rendered glyph string at this
        point (the text operator splits out operands upstream and the
        glyph widths live in the font resource), so an exact bbox would
        require a font-metrics lookup per Tj/TJ call. Instead, anchor
        the bbox at the current text-matrix origin and size it by the
        effective font size, applying the CTM so the bbox is in
        user-space points.

        This is coarse but sufficient for the annotated-PDF overlay —
        the reviewer sees a square where the text starts, which is
        vastly better than the previous behaviour (no bbox at all, so
        no overlay rendered). Analyzers that need exact character
        extents can still fall back to ``event.text_matrix`` +
        ``event.font_size`` for their own computation.
        """
        size = self.state.font_size
        if size <= 0:
            return None
        tm = self.state.text_matrix
        m = self.state.ctm

        # Anchor in text space is (0, 0); end-of-line anchor we'll treat as
        # (size, size) — a conservative square box. This is just an
        # annotation hint, not a measurement.
        def xform(x: float, y: float) -> tuple[float, float]:
            # tx = tm(x,y) then ctm(tx)
            tx = tm.a * x + tm.c * y + tm.e
            ty = tm.b * x + tm.d * y + tm.f
            ux = m.a * tx + m.c * ty + m.e
            uy = m.b * tx + m.d * ty + m.f
            return ux, uy

        corners = [xform(0, 0), xform(size, 0), xform(size, size), xform(0, size)]
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        return (min(xs), min(ys), max(xs), max(ys))

    # --- CRITICAL: Color (non-stroking) ---

    def _handle_sc(self, operands: list[Any]) -> None:
        """Set non-stroking color (sc/scn)."""
        if operands:
            self.state.non_stroking_color = [float(v) for v in operands]
            self._emit(
                ColorChangedEvent(
                    operator="sc",
                    page_num=self._page_num,
                    operator_index=self._operator_index,
                    stroking=False,
                    color_space=self.state.non_stroking_color_space,
                    color_values=tuple(self.state.non_stroking_color),
                )
            )

    def _handle_rg(self, operands: list[Any]) -> None:
        """Set non-stroking RGB color."""
        if len(operands) >= 3:
            self.state.non_stroking_color_space = "DeviceRGB"
            self.state.non_stroking_color = [float(v) for v in operands[:3]]
            self._emit(
                ColorChangedEvent(
                    operator="rg",
                    page_num=self._page_num,
                    operator_index=self._operator_index,
                    stroking=False,
                    color_space="DeviceRGB",
                    color_values=tuple(self.state.non_stroking_color),
                )
            )

    def _handle_k(self, operands: list[Any]) -> None:
        """Set non-stroking CMYK color."""
        if len(operands) >= 4:
            self.state.non_stroking_color_space = "DeviceCMYK"
            self.state.non_stroking_color = [float(v) for v in operands[:4]]
            self._emit(
                ColorChangedEvent(
                    operator="k",
                    page_num=self._page_num,
                    operator_index=self._operator_index,
                    stroking=False,
                    color_space="DeviceCMYK",
                    color_values=tuple(self.state.non_stroking_color),
                )
            )

    def _handle_g(self, operands: list[Any]) -> None:
        """Set non-stroking gray color."""
        if len(operands) >= 1:
            self.state.non_stroking_color_space = "DeviceGray"
            self.state.non_stroking_color = [float(operands[0])]
            self._emit(
                ColorChangedEvent(
                    operator="g",
                    page_num=self._page_num,
                    operator_index=self._operator_index,
                    stroking=False,
                    color_space="DeviceGray",
                    color_values=tuple(self.state.non_stroking_color),
                )
            )

    def _handle_cs(self, operands: list[Any]) -> None:
        """Set non-stroking color space."""
        if operands:
            self.state.non_stroking_color_space = str(operands[0]).lstrip("/")

    # --- CRITICAL: Color (stroking) ---

    def _handle_SC(self, operands: list[Any]) -> None:
        """Set stroking color (SC/SCN)."""
        if operands:
            self.state.stroking_color = [float(v) for v in operands]
            self._emit(
                ColorChangedEvent(
                    operator="SC",
                    page_num=self._page_num,
                    operator_index=self._operator_index,
                    stroking=True,
                    color_space=self.state.stroking_color_space,
                    color_values=tuple(self.state.stroking_color),
                )
            )

    def _handle_RG(self, operands: list[Any]) -> None:
        """Set stroking RGB color."""
        if len(operands) >= 3:
            self.state.stroking_color_space = "DeviceRGB"
            self.state.stroking_color = [float(v) for v in operands[:3]]
            self._emit(
                ColorChangedEvent(
                    operator="RG",
                    page_num=self._page_num,
                    operator_index=self._operator_index,
                    stroking=True,
                    color_space="DeviceRGB",
                    color_values=tuple(self.state.stroking_color),
                )
            )

    def _handle_K(self, operands: list[Any]) -> None:
        """Set stroking CMYK color."""
        if len(operands) >= 4:
            self.state.stroking_color_space = "DeviceCMYK"
            self.state.stroking_color = [float(v) for v in operands[:4]]
            self._emit(
                ColorChangedEvent(
                    operator="K",
                    page_num=self._page_num,
                    operator_index=self._operator_index,
                    stroking=True,
                    color_space="DeviceCMYK",
                    color_values=tuple(self.state.stroking_color),
                )
            )

    def _handle_G(self, operands: list[Any]) -> None:
        """Set stroking gray color."""
        if len(operands) >= 1:
            self.state.stroking_color_space = "DeviceGray"
            self.state.stroking_color = [float(operands[0])]
            self._emit(
                ColorChangedEvent(
                    operator="G",
                    page_num=self._page_num,
                    operator_index=self._operator_index,
                    stroking=True,
                    color_space="DeviceGray",
                    color_values=tuple(self.state.stroking_color),
                )
            )

    def _handle_CS(self, operands: list[Any]) -> None:
        """Set stroking color space."""
        if operands:
            self.state.stroking_color_space = str(operands[0]).lstrip("/")

    # --- CRITICAL: Inline image ---

    def _handle_inline_image(self, _operands: list[Any]) -> None:
        """Handle inline image (BI/ID/EI parsed by pikepdf)."""
        self._emit(
            ImagePlacedEvent(
                operator="BI_ID_EI",
                page_num=self._page_num,
                operator_index=self._operator_index,
                image_name=f"inline_{self._operator_index}",
                ctm=TransformationMatrix(
                    self.state.ctm.a,
                    self.state.ctm.b,
                    self.state.ctm.c,
                    self.state.ctm.d,
                    self.state.ctm.e,
                    self.state.ctm.f,
                ),
                pixel_width=0,
                pixel_height=0,
                is_inline=True,
            )
        )

    # --- IMPORTANT: Path construction ---

    def _handle_m(self, operands: list[Any]) -> None:
        """Move to (start new subpath)."""
        if len(operands) >= 2:
            self._current_path = [(float(operands[0]), float(operands[1]))]

    def _handle_l(self, operands: list[Any]) -> None:
        """Line to."""
        if len(operands) >= 2:
            self._current_path.append((float(operands[0]), float(operands[1])))

    def _handle_c(self, operands: list[Any]) -> None:
        """Cubic Bezier curve (3 control points)."""
        if len(operands) >= 6:
            self._current_path.append((float(operands[4]), float(operands[5])))

    def _handle_v(self, operands: list[Any]) -> None:
        """Cubic Bezier (initial point replicated)."""
        if len(operands) >= 4:
            self._current_path.append((float(operands[2]), float(operands[3])))

    def _handle_y(self, operands: list[Any]) -> None:
        """Cubic Bezier (final point replicated)."""
        if len(operands) >= 4:
            self._current_path.append((float(operands[2]), float(operands[3])))

    def _handle_h(self, _operands: list[Any]) -> None:
        """Close subpath (line back to start)."""
        pass  # Path already has start point

    def _handle_re(self, operands: list[Any]) -> None:
        """Rectangle (x, y, width, height)."""
        if len(operands) >= 4:
            x, y = float(operands[0]), float(operands[1])
            w, h = float(operands[2]), float(operands[3])
            self._current_path = [
                (x, y),
                (x + w, y),
                (x + w, y + h),
                (x, y + h),
            ]

    # --- IMPORTANT: Path painting ---

    def _emit_path_event(
        self, operator: str, *, fill: bool, stroke: bool, even_odd: bool = False
    ) -> None:
        """Emit PathPaintingEvent and clear current path."""
        bbox = self._path_bbox()
        self._emit(
            PathPaintingEvent(
                operator=operator,
                page_num=self._page_num,
                operator_index=self._operator_index,
                fill=fill,
                stroke=stroke,
                even_odd=even_odd,
                fill_color_space=self.state.non_stroking_color_space if fill else "",
                fill_color_values=tuple(self.state.non_stroking_color) if fill else (),
                stroke_color_space=self.state.stroking_color_space if stroke else "",
                stroke_color_values=tuple(self.state.stroking_color) if stroke else (),
                line_width=self.state.line_width,
                line_cap=self.state.line_cap,
                line_join=self.state.line_join,
                dash_pattern=self.state.dash_pattern,
                bbox=bbox,
            )
        )
        self._current_path = []

    def _path_bbox(self) -> tuple[float, float, float, float] | None:
        """Axis-aligned bounding box of ``self._current_path`` in user space.

        Returns ``None`` for empty paths. Transforms each control point by
        the current CTM so the bbox is in the same coordinate space the
        viewer and annotated PDF overlay expect (PDF user-space points,
        lower-left origin).

        Curve control points are approximated by their anchors only —
        that's correct for straight segments and a conservative lower
        bound for Beziers. Good enough for "where on the page is this
        finding" rendering; exact curve bounds aren't worth the cost.
        """
        if not self._current_path:
            return None
        m = self.state.ctm
        xs: list[float] = []
        ys: list[float] = []
        for px, py in self._current_path:
            # Apply CTM: [x'] = [a c e][x]  y' = b*x + d*y + f
            x = m.a * px + m.c * py + m.e
            y = m.b * px + m.d * py + m.f
            xs.append(x)
            ys.append(y)
        return (min(xs), min(ys), max(xs), max(ys))

    def _handle_S(self, _operands: list[Any]) -> None:
        """Stroke path."""
        self._emit_path_event("S", fill=False, stroke=True)

    def _handle_s(self, _operands: list[Any]) -> None:
        """Close and stroke path."""
        self._emit_path_event("s", fill=False, stroke=True)

    def _handle_f(self, _operands: list[Any]) -> None:
        """Fill path (nonzero winding)."""
        self._emit_path_event("f", fill=True, stroke=False)

    def _handle_f_star(self, _operands: list[Any]) -> None:
        """Fill path (even-odd rule)."""
        self._emit_path_event("f*", fill=True, stroke=False, even_odd=True)

    def _handle_B(self, _operands: list[Any]) -> None:
        """Fill and stroke (nonzero winding)."""
        self._emit_path_event("B", fill=True, stroke=True)

    def _handle_B_star(self, _operands: list[Any]) -> None:
        """Fill and stroke (even-odd rule)."""
        self._emit_path_event("B*", fill=True, stroke=True, even_odd=True)

    def _handle_b(self, _operands: list[Any]) -> None:
        """Close, fill, and stroke (nonzero winding)."""
        self._emit_path_event("b", fill=True, stroke=True)

    def _handle_b_star(self, _operands: list[Any]) -> None:
        """Close, fill, and stroke (even-odd rule)."""
        self._emit_path_event("b*", fill=True, stroke=True, even_odd=True)

    def _handle_n(self, _operands: list[Any]) -> None:
        """End path without filling or stroking (used with clipping)."""
        self._current_path = []

    # --- IMPORTANT: Clipping ---

    def _handle_W(self, _operands: list[Any]) -> None:
        """Intersect clipping path (nonzero winding)."""
        self._emit(
            ClippingPathSetEvent(
                operator="W",
                page_num=self._page_num,
                operator_index=self._operator_index,
                even_odd=False,
            )
        )

    def _handle_W_star(self, _operands: list[Any]) -> None:
        """Intersect clipping path (even-odd rule)."""
        self._emit(
            ClippingPathSetEvent(
                operator="W*",
                page_num=self._page_num,
                operator_index=self._operator_index,
                even_odd=True,
            )
        )

    # --- IMPORTANT: Text positioning ---

    def _handle_Td(self, operands: list[Any]) -> None:
        """Move text position."""
        if len(operands) >= 2:
            tx, ty = float(operands[0]), float(operands[1])
            translate = TransformationMatrix.translation(tx, ty)
            self.state.text_line_matrix = translate.multiply(self.state.text_line_matrix)
            self.state.text_matrix = TransformationMatrix(
                self.state.text_line_matrix.a,
                self.state.text_line_matrix.b,
                self.state.text_line_matrix.c,
                self.state.text_line_matrix.d,
                self.state.text_line_matrix.e,
                self.state.text_line_matrix.f,
            )

    def _handle_TD(self, operands: list[Any]) -> None:
        """Move text position and set leading."""
        if len(operands) >= 2:
            self.state.text_leading = -float(operands[1])
            self._handle_Td(operands)

    def _handle_T_star(self, _operands: list[Any]) -> None:
        """Move to start of next text line (uses TL)."""
        self._handle_Td([0, -self.state.text_leading])

    # --- IMPORTANT: Text showing (with line advance) ---

    def _handle_quote(self, operands: list[Any]) -> None:
        """Move to next line and show string (')."""
        self._handle_T_star([])
        self._emit_text_event("'")

    def _handle_double_quote(self, operands: list[Any]) -> None:
        """Set word/char spacing, move to next line, show string (")."""
        if len(operands) >= 3:
            try:
                self.state.word_spacing = float(operands[0])
                self.state.char_spacing = float(operands[1])
            except (TypeError, ValueError):
                pass
        self._handle_T_star([])
        self._emit_text_event('"')

    # --- Line width ---

    def _handle_w(self, operands: list[Any]) -> None:
        """Set line width."""
        if operands:
            with contextlib.suppress(TypeError, ValueError):
                self.state.line_width = float(operands[0])

    # --- Line style operators ---

    def _handle_J(self, operands: list[Any]) -> None:
        """Set line cap style."""
        if operands:
            with contextlib.suppress(TypeError, ValueError):
                self.state.line_cap = int(operands[0])
                self._emit_line_style_event("J", line_cap=self.state.line_cap)

    def _handle_j(self, operands: list[Any]) -> None:
        """Set line join style."""
        if operands:
            with contextlib.suppress(TypeError, ValueError):
                self.state.line_join = int(operands[0])
                self._emit_line_style_event("j", line_join=self.state.line_join)

    def _handle_d(self, operands: list[Any]) -> None:
        """Set dash pattern."""
        if len(operands) >= 2:
            with contextlib.suppress(TypeError, ValueError):
                array = operands[0]
                phase = float(operands[1])
                if isinstance(array, list):
                    dash_array = tuple(float(v) for v in array)
                    self.state.dash_pattern = (dash_array, phase)
                    self._emit_line_style_event("d", dash_pattern=self.state.dash_pattern)

    def _handle_M(self, operands: list[Any]) -> None:
        """Set miter limit."""
        if operands:
            with contextlib.suppress(TypeError, ValueError):
                self.state.miter_limit = float(operands[0])
                self._emit_line_style_event("M", miter_limit=self.state.miter_limit)

    def _handle_i(self, operands: list[Any]) -> None:
        """Set flatness tolerance."""
        if operands:
            with contextlib.suppress(TypeError, ValueError):
                self.state.flatness = float(operands[0])

    def _handle_ri(self, operands: list[Any]) -> None:
        """Set rendering intent."""
        if operands:
            self.state.rendering_intent = str(operands[0]).lstrip("/")
            self._emit_line_style_event("ri", rendering_intent=self.state.rendering_intent)

    def _emit_line_style_event(
        self,
        operator: str,
        *,
        line_cap: int | None = None,
        line_join: int | None = None,
        dash_pattern: tuple[tuple[float, ...], float] | None = None,
        miter_limit: float | None = None,
        rendering_intent: str | None = None,
    ) -> None:
        """Emit a LineStyleChangedEvent."""
        self._emit(
            LineStyleChangedEvent(
                operator=operator,
                page_num=self._page_num,
                operator_index=self._operator_index,
                line_cap=line_cap,
                line_join=line_join,
                dash_pattern=dash_pattern,
                miter_limit=miter_limit,
                rendering_intent=rendering_intent,
            )
        )
