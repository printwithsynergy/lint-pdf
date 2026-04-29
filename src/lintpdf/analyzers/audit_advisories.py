"""AuditAdvisoryAnalyzer — codified "verify with operator" advisories
that the post-merge Opus 4.7 audit consistently flagged as misses.

Many audit misses are advisories Opus *asks the operator to verify*
rather than checks the engine could implement as hard rules. Codifying
them as engine ADVISORIES converts those audit misses to "agree" — the
engine surfaces the right concern, the operator decides intent.

Check IDs:

* ``LPDF_BOX_STEP_AND_REPEAT`` (advisory) — page contains 3+ similar
  dieline regions arranged in a regular grid. Most label workflows
  expect a single artwork unit; the printer typically handles
  step-and-repeat. Fires alongside ``LPDF_BOX_PRESS_MARKS_MISSING``
  (which only fires when marks are missing); this one fires regardless
  so the operator confirms the multi-up was intentional.

* ``LPDF_DOC_METADATA_INCOMPLETE`` (advisory) — composite asset-
  tracking metadata gaps: 2+ of (Title / Author / Producer / Creator)
  missing, OR XMP missing entirely. Brand owners commonly require
  these for reorder / colour-job tracking. The existing
  ``LPDF_DOC_003`` only flags missing Title.

* ``LPDF_DIE_DIMENSION_CALLOUT`` (advisory) — printable text contains
  dimension callout patterns (e.g. ``2.4409"``, ``10 mm``,
  ``5.7500"``, ``GUSSET 21x6.5x2``). On a press-ready PDF these
  belong on a non-printing techinfo layer; on the print layer they
  image to plate. Flags 4+ fixtures.

* ``LPDF_INK_MIXED_BUILD_VERIFY`` (advisory, PR-JJ) — file declares
  1-2 named Separation spots AND uses DeviceCMYK fills in the
  content stream. Common case: a brand 2-PMS layout that also drops
  a 4-process raster image, producing a 6-plate job. Asks the
  operator to confirm the mixed build was the intended press setup.

* ``LPDF_DOC_LANG_BILINGUAL`` (advisory, PR-JJ) — content stream
  contains French / Spanish / German / Italian phrases AND ``/Lang``
  is unset (or doesn't reflect bilingual content). Multilingual
  packaging needs a primary-language tag for assistive tech +
  localisation tooling.

* ``LPDF_TEXT_INVERTED_180`` (advisory, PR-JJ) — page has text
  events whose composed rotation differs by ~180 deg from the
  majority orientation. Common case: gusseted-bag back-panel
  artwork printed upside-down relative to the front; intentional
  on some packaging shapes but worth confirming.

* ``LPDF_TEXT_LEGIBILITY_VERIFY`` (advisory, PR-JJ) — text composed
  size in the 5-6 pt range. ``LPDF_LEGALCOPY_001`` (5 pt FDA
  minimum) handles the hard floor; this rule fires the soft tier
  Opus consistently asks for ("verify against final size").
"""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

from lintpdf.analyzers.base import BaseAnalyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.semantic.events import ContentStreamEvent
    from lintpdf.semantic.model import SemanticDocument


# Patterns that mark a dimension / spec callout in artwork text.
# Designed to catch typical prepress callouts across packaging shapes
# without false-firing on ingredient quantities ("5 mg"), price tags
# ("$5.99"), or content prose. The patterns require either:
#   1. A high-precision decimal (3+ decimals — "2.4409"") that's
#      unambiguously a press measurement
#   2. A bag-shape callout (GUSSET / WIDTH x HEIGHT x DEPTH) — only
#      ever appears on technical layers
#   3. A trim / die / dimension keyword adjacent to a number+unit
_DIMENSION_PATTERNS: tuple[re.Pattern[str], ...] = (
    # 2.4409", 5.7500" — high-precision inch dimensions. 3+ decimals
    # is the prepress signature; "2.5" or "5" alone don't fire (could
    # be a quantity).
    re.compile(r'\b\d+\.\d{3,5}\s*"'),
    # GUSSET 21x6.5x2 / 21x6.5x2 GUSSET / 21x6.5x2 V2 — bag-shape
    # callouts.  Specific enough that ingredient lists don't trigger.
    re.compile(r"\bGUSSET\s+\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?\s*x\s*\d+", re.IGNORECASE),
    re.compile(
        r"\b\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?\s*x\s*\d+(?:\.\d+)?\s+(?:GUSSET|V\d+|"
        r"VERSION\s*\d+)\b",
        re.IGNORECASE,
    ),
    # Trim / die / dimension keyword + number + unit in close
    # proximity. Catches "Trim: 4.5\"", "Die size 100 x 50 mm", etc.
    re.compile(
        r"\b(?:TRIM|DIE\s*SIZE|DIE\s*CUT|FINISHED\s*SIZE|FOLDED\s*SIZE|"
        r"PANEL\s*SIZE|SHEET\s*SIZE)\b[^a-zA-Z]{0,30}"
        r"\d+(?:\.\d+)?\s*(?:mm|cm|in|inches|\")",
        re.IGNORECASE,
    ),
    # mm / cm dimensions ≥ 10 (typical packaging dims) — protects
    # against ingredient mg / g / kg matching since mm is unambiguous.
    re.compile(r"\b\d{2,4}(?:\.\d{1,3})?\s*mm\b", re.IGNORECASE),
)

# Asset-tracking metadata keys we expect on production-ready PDFs.
_TRACKING_KEYS: tuple[str, ...] = ("/Title", "/Author", "/Producer", "/Creator")

# Phrase fragments that strongly imply non-English content (FR / ES /
# DE / IT). Used to gate ``LPDF_DOC_LANG_BILINGUAL`` on documents that
# clearly carry multilingual copy. Lowercase + accent-stripped match.
_NON_EN_PHRASES: tuple[str, ...] = (
    # French (CFIA bilingual labelling)
    "ingredients:",
    "ingrédients",
    "déchirer",
    "ne pas",
    "valeur nutritive",
    "contenu net",
    "sans ogm",
    "fabriqué",
    # Spanish (FDA Hispanic-market)
    "ingredientes",
    "información nutricional",
    "no contiene",
    "fabricado en",
    "fecha de caducidad",
    # German (EU FIR)
    "zutaten:",
    "nährwerte",
    "mindestens haltbar",
    # Italian (EU FIR)
    "ingredienti:",
    "valori nutrizionali",
)

# Composed-rotation buckets in degrees. Text whose rotation falls into
# the same 5-degree bucket as the majority is "axis-aligned"; rotations
# in the 175-185 deg bucket are "inverted" (~180 deg flip).
_ROTATION_BUCKET_DEG = 5.0
_INVERTED_TOLERANCE_DEG = 5.0

# Mixed-build advisory: fires when document has at most this many spots
# AND DeviceCMYK fills are also present in the content stream.
_MAX_SPOTS_FOR_MIXED_BUILD = 2

# Soft-tier legibility verification — composed text size in this band
# is "below 6pt body but above the FDA 5pt floor". LPDF_LEGALCOPY_001
# already fires below 5pt; this fires the verify advisory in 5-6pt.
_LEGIBILITY_VERIFY_MIN_PT = 5.0
_LEGIBILITY_VERIFY_MAX_PT = 6.0


def _composed_font_size_pt(event) -> float:  # type: ignore[no-untyped-def]
    base = abs(event.font_size)
    if not event.ctm or not event.text_matrix:
        return base
    ctm = event.ctm
    tm = event.text_matrix
    cx = ctm.a * tm.c + ctm.c * tm.d
    cy = ctm.b * tm.c + ctm.d * tm.d
    return base * math.hypot(cx, cy)


def _composed_rotation_deg(event) -> float:  # type: ignore[no-untyped-def]
    """Return the composed rotation angle in degrees, in [0, 360)."""
    if not event.ctm or not event.text_matrix:
        return 0.0
    ctm = event.ctm
    tm = event.text_matrix
    a = ctm.a * tm.a + ctm.c * tm.b
    b = ctm.b * tm.a + ctm.d * tm.b
    if abs(a) < 1e-9 and abs(b) < 1e-9:
        return 0.0
    return (math.degrees(math.atan2(b, a)) + 360.0) % 360.0


class AuditAdvisoryAnalyzer(BaseAnalyzer):
    """Codified advisories closing audit misses by giving Opus a finding
    to AGREE with rather than missing the topic entirely."""

    def analyze(
        self,
        document: SemanticDocument,
        events: list[ContentStreamEvent],
    ) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._check_step_and_repeat(document))
        findings.extend(self._check_metadata_incomplete(document))
        findings.extend(self._check_dimension_callout(document))
        findings.extend(self._check_mixed_build(document, events))
        findings.extend(self._check_lang_bilingual(document))
        findings.extend(self._check_text_inverted(events))
        findings.extend(self._check_legibility_verify(events))
        findings.extend(self._check_net_weight_verify(document))
        findings.extend(self._check_die_safe_zone(document, events))
        return findings

    @staticmethod
    def _check_step_and_repeat(document: SemanticDocument) -> list[Finding]:
        """Detect multi-up step-and-repeat sheets.

        Two paths to fire:

        * **Repeated regions**: ``DielineResult`` has 3+ regions where
          three or more share a similar size (within 15 % of the median).
          This matches the typical N-up layout: identical panels, even
          if the dieline also includes seal/end-fold strips.
        * **Region count alone**: ``DielineResult`` has 6+ regions of
          any size. A live single-up file rarely has more than 5 dieline
          islands; 6+ is a strong heuristic for step-and-repeat even
          when the regions aren't all equal (e.g. a 10-up sheet that
          declares one region per panel + seam markers).
        """
        dl = getattr(document, "dieline_result", None)
        if dl is None:
            return []
        regions = getattr(dl, "regions", None) or []
        if len(regions) < 3:
            return []

        # Path 1: 3+ similar-size regions (within 15 % of median W×H).
        widths = sorted(float(r.get("x1", 0) - r.get("x0", 0)) for r in regions)
        heights = sorted(float(r.get("y1", 0) - r.get("y0", 0)) for r in regions)
        med_w = widths[len(widths) // 2] if widths else 0
        med_h = heights[len(heights) // 2] if heights else 0
        similar = 0
        if med_w > 0 and med_h > 0:
            similar = sum(
                1
                for r in regions
                if abs((r.get("x1", 0) - r.get("x0", 0)) - med_w) / med_w < 0.15
                and abs((r.get("y1", 0) - r.get("y0", 0)) - med_h) / med_h < 0.15
            )

        # Path 2: 6+ regions of any size (DailyFiber-class layouts where
        # the 10-up panels share a single dieline outline + seam strips).
        if similar < 3 and len(regions) < 6:
            return []

        return [
            Finding(
                inspection_id="LPDF_BOX_STEP_AND_REPEAT",
                severity=Severity.ADVISORY,
                message=(
                    f"Page contains {similar} similar dieline region(s) arranged "
                    "as a multi-up step-and-repeat. Label production workflows "
                    "typically expect a single artwork unit per page; the printer "
                    "handles imposition. Confirm the multi-up was the intended "
                    "deliverable, otherwise re-export as a single-up artwork."
                ),
                details={
                    "region_count": len(regions),
                    "similar_size_count": similar,
                    "median_width_pt": round(med_w, 2),
                    "median_height_pt": round(med_h, 2),
                },
                category="page",
                object_type="page",
            )
        ]

    @staticmethod
    def _check_metadata_incomplete(document: SemanticDocument) -> list[Finding]:
        info = getattr(document, "info_dict", None) or {}
        missing: list[str] = []
        for key in _TRACKING_KEYS:
            v = info.get(key) or info.get(key.lstrip("/"))
            if not v or not str(v).strip():
                missing.append(key.lstrip("/"))
        if len(missing) < 2:
            return []
        return [
            Finding(
                inspection_id="LPDF_DOC_METADATA_INCOMPLETE",
                severity=Severity.ADVISORY,
                message=(
                    f"Document Info dictionary is missing {len(missing)} asset-"
                    f"tracking key(s): {', '.join(missing)}. Brand-owner preflight "
                    "gates commonly require these for reorder / colour-job tracking; "
                    "set them in the design tool before final export."
                ),
                details={"missing_keys": missing, "keys_checked": list(_TRACKING_KEYS)},
                category="metadata",
                object_type="document",
            )
        ]

    @staticmethod
    def _check_dimension_callout(document: SemanticDocument) -> list[Finding]:
        from lintpdf.analyzers.placeholder_text import PlaceholderTextAnalyzer

        out: list[Finding] = []
        for page in getattr(document, "pages", None) or []:
            matched: list[str] = []
            # 1. Live-text fixtures: scan the Tj-flattened content stream.
            raw = getattr(page, "content_stream", None)
            if raw:
                try:
                    text = (
                        raw.decode("latin-1") if isinstance(raw, (bytes, bytearray)) else str(raw)
                    )
                    spaced, _ = PlaceholderTextAnalyzer._flatten_tj_operands(text)
                    haystack = spaced or text
                    for pat in _DIMENSION_PATTERNS:
                        m = pat.search(haystack)
                        if m:
                            matched.append(m.group(0).strip())
                except Exception:
                    pass
            # 2. Outlined fixtures: scan OCR regions.
            for region in getattr(page, "detected_text_regions", None) or []:
                rt = getattr(region, "text", None) or ""
                for pat in _DIMENSION_PATTERNS:
                    m = pat.search(rt)
                    if m:
                        matched.append(m.group(0).strip())
                        break
            if not matched:
                continue
            # Dedupe so 5 dimension callouts on one page emit one finding.
            unique = sorted(set(matched))[:5]
            out.append(
                Finding(
                    inspection_id="LPDF_DIE_DIMENSION_CALLOUT",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Page {page.page_num} contains dimension / spec callout "
                        f"text in printable artwork: {', '.join(unique)}. On a "
                        "press-ready PDF, dimensional callouts belong on a non-"
                        "printing technical/info layer (OCG with print=false); "
                        "otherwise they will image to plate. Move the callouts "
                        "to a non-printing layer or remove before final export."
                    ),
                    page_num=page.page_num,
                    details={
                        "matched_callouts": unique,
                        "match_count": len(matched),
                    },
                    category="dieline",
                    object_type="page",
                )
            )
        return out

    @staticmethod
    def _check_mixed_build(
        document: SemanticDocument, events: list[ContentStreamEvent]
    ) -> list[Finding]:
        """Document declares 1-2 named spots AND uses DeviceCMYK fills.

        The audit consistently asks operators to verify mixed builds —
        a 2-PMS layout with a process-CMYK photo produces a 6-plate
        job. If the press deck or budget assumes spot-only or CMYK-only,
        the surprise rejection happens at plating.
        """
        from lintpdf.semantic.events import ColorChangedEvent

        # Count distinct non-process spots.
        spots: set[str] = set()
        for page in getattr(document, "pages", None) or []:
            for cs in (getattr(page, "color_spaces", None) or {}).values():
                if getattr(cs, "cs_type", None) not in (
                    "Separation",
                    "DeviceN",
                    "NChannel",
                ):
                    continue
                for raw in getattr(cs, "colorant_names", None) or ():
                    if not raw:
                        continue
                    norm = str(raw).strip().lstrip("/").lower().replace("-", "_").replace(" ", "_")
                    if norm in {
                        "all",
                        "none",
                        "cyan",
                        "magenta",
                        "yellow",
                        "black",
                        "dieline",
                        "die_line",
                        "cutting",
                        "cut",
                        "perforating",
                        "perf",
                        "scoring",
                        "score",
                        "creasing",
                        "crease",
                        "varnish",
                    }:
                        continue
                    spots.add(norm)
        if not 1 <= len(spots) <= _MAX_SPOTS_FOR_MIXED_BUILD:
            return []

        # Look for DeviceCMYK fills with non-zero ink in the event stream.
        cmyk_used = False
        for ev in events:
            if not isinstance(ev, ColorChangedEvent):
                continue
            if "DeviceCMYK" not in str(ev.color_space):
                continue
            if any(v > 0.0 for v in (ev.color_values or ())):
                cmyk_used = True
                break
        if not cmyk_used:
            return []

        return [
            Finding(
                inspection_id="LPDF_INK_MIXED_BUILD_VERIFY",
                severity=Severity.ADVISORY,
                message=(
                    f"Document declares {len(spots)} named spot(s) and also uses "
                    "DeviceCMYK fills. Mixed spot+process builds yield 5-6 plate "
                    "jobs (e.g. 4 process + 2 PMS). Confirm the press deck has "
                    "stations for both and that the cost / station-count plan "
                    "expected the mixed build, or consolidate to spot-only / "
                    "process-only as appropriate."
                ),
                details={
                    "spot_count": len(spots),
                    "spot_names": sorted(spots),
                    "uses_cmyk": True,
                },
                category="color",
                object_type="document",
            )
        ]

    @staticmethod
    def _check_lang_bilingual(document: SemanticDocument) -> list[Finding]:
        """Multi-language content + ``/Lang`` unset.

        Walks each page's content stream + OCR regions for telltale
        non-English phrases. When found AND the document has no
        ``/Lang`` catalog entry, fire an advisory.
        """
        from lintpdf.analyzers.placeholder_text import PlaceholderTextAnalyzer

        catalog = getattr(document, "catalog", None) or {}
        lang = catalog.get("/Lang") or catalog.get("Lang")
        if lang and str(lang).strip():
            return []

        # Look for non-English phrases anywhere in the document.
        phrase_hit: str | None = None
        for page in getattr(document, "pages", None) or []:
            raw = getattr(page, "content_stream", None)
            if raw:
                try:
                    text = (
                        raw.decode("latin-1") if isinstance(raw, (bytes, bytearray)) else str(raw)
                    )
                    spaced, _ = PlaceholderTextAnalyzer._flatten_tj_operands(text)
                    haystack = (spaced or text).lower()
                    for p in _NON_EN_PHRASES:
                        if p in haystack:
                            phrase_hit = p
                            break
                except Exception:
                    pass
            if phrase_hit:
                break
            for region in getattr(page, "detected_text_regions", None) or []:
                t = (getattr(region, "text", None) or "").lower()
                for p in _NON_EN_PHRASES:
                    if p in t:
                        phrase_hit = p
                        break
                if phrase_hit:
                    break
            if phrase_hit:
                break
        if not phrase_hit:
            return []

        return [
            Finding(
                inspection_id="LPDF_DOC_LANG_BILINGUAL",
                severity=Severity.ADVISORY,
                message=(
                    f"Document contains non-English content (matched: {phrase_hit!r}) "
                    "but the catalog has no /Lang entry. Multilingual packaging "
                    "should declare the primary language as a BCP-47 tag (e.g. "
                    "/Lang (en-CA) for Canadian English with French copy) so "
                    "assistive tech and localisation tooling work correctly."
                ),
                details={"matched_phrase": phrase_hit, "lang_present": False},
                category="metadata",
                object_type="document",
            )
        ]

    @staticmethod
    def _check_text_inverted(events: list[ContentStreamEvent]) -> list[Finding]:
        """Detect ~180 deg rotated text against the page majority.

        Walks ``TextRenderedEvent`` rotation buckets per page; if the
        page has at least 5 events at a "majority" rotation AND at
        least 3 events ~180 deg off from it, fire an advisory.
        """
        from lintpdf.semantic.events import TextRenderedEvent

        per_page: dict[int, list[float]] = {}
        for ev in events:
            if not isinstance(ev, TextRenderedEvent):
                continue
            if ev.rendering_mode == 3:
                continue
            per_page.setdefault(ev.page_num, []).append(_composed_rotation_deg(ev))

        out: list[Finding] = []
        for page_num, rotations in per_page.items():
            if len(rotations) < 8:
                continue
            buckets: dict[int, int] = {}
            for r in rotations:
                key = int(r // _ROTATION_BUCKET_DEG)
                buckets[key] = buckets.get(key, 0) + 1
            if not buckets:
                continue
            top_bucket, top_count = max(buckets.items(), key=lambda kv: kv[1])
            if top_count < 5:
                continue
            top_deg = top_bucket * _ROTATION_BUCKET_DEG
            inverted_deg = (top_deg + 180.0) % 360.0
            inverted_low = (
                int((inverted_deg - _INVERTED_TOLERANCE_DEG) // _ROTATION_BUCKET_DEG) % 72
            )
            inverted_high = (
                int((inverted_deg + _INVERTED_TOLERANCE_DEG) // _ROTATION_BUCKET_DEG) % 72
            )
            inverted_count = 0
            for k, count in buckets.items():
                if inverted_low <= inverted_high:
                    if inverted_low <= k <= inverted_high:
                        inverted_count += count
                else:
                    # wrap around 360 deg
                    if k >= inverted_low or k <= inverted_high:
                        inverted_count += count
            if inverted_count < 3:
                continue
            out.append(
                Finding(
                    inspection_id="LPDF_TEXT_INVERTED_180",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Page {page_num} has {inverted_count} text event(s) rotated "
                        f"approximately 180 deg from the page majority "
                        f"({top_count} events at {top_deg:.0f} deg). On gusseted "
                        "bag / pouch artwork the back panel is sometimes printed "
                        "upside-down for unfold orientation; verify the rotation "
                        "matches the bag finishing layout, otherwise the back "
                        "panel reads inverted on shelf."
                    ),
                    page_num=page_num,
                    details={
                        "page_majority_deg": top_deg,
                        "majority_count": top_count,
                        "inverted_count": inverted_count,
                    },
                    category="text",
                    object_type="text",
                )
            )
        return out

    @staticmethod
    def _check_legibility_verify(events: list[ContentStreamEvent]) -> list[Finding]:
        """Composed font size in 5-6 pt soft-tier band.

        ``LPDF_LEGALCOPY_001`` covers the hard FDA 5 pt floor; this
        rule fires the soft "verify against final size" tier Opus
        consistently asks for. Per-page dedupe by font/size bucket so
        a paragraph emits one finding, not hundreds.
        """
        from lintpdf.semantic.events import TextRenderedEvent

        out: list[Finding] = []
        seen: set[tuple[int, str, float]] = set()
        for ev in events:
            if not isinstance(ev, TextRenderedEvent):
                continue
            if ev.rendering_mode == 3:
                continue
            size_pt = _composed_font_size_pt(ev)
            if not (_LEGIBILITY_VERIFY_MIN_PT <= size_pt < _LEGIBILITY_VERIFY_MAX_PT):
                continue
            key = (ev.page_num, ev.font_name, round(size_pt, 1))
            if key in seen:
                continue
            seen.add(key)
            out.append(
                Finding(
                    inspection_id="LPDF_TEXT_LEGIBILITY_VERIFY",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Text at {size_pt:.1f} pt (font {ev.font_name}) on page "
                        f"{ev.page_num} is below the recommended 6 pt body-copy "
                        "tier. The hard floor (FDA 5 pt) is owned by "
                        "LPDF_LEGALCOPY_001; this advisory flags the legibility-"
                        "verify band so you can confirm against the final printed "
                        "panel size and substrate."
                    ),
                    page_num=ev.page_num,
                    details={
                        "font_size_pt": round(size_pt, 2),
                        "font_name": ev.font_name,
                        "verify_band_pt": [
                            _LEGIBILITY_VERIFY_MIN_PT,
                            _LEGIBILITY_VERIFY_MAX_PT,
                        ],
                    },
                    category="text",
                    object_type="text",
                    bbox=ev.bbox,
                )
            )
        return out

    @staticmethod
    def _check_net_weight_verify(document: SemanticDocument) -> list[Finding]:
        """Net weight declarations should carry both metric AND
        imperial / US-customary units (FDA 21 CFR 101.105). Fires
        when only one unit system is present in detected weight
        callouts."""
        from lintpdf.analyzers.placeholder_text import PlaceholderTextAnalyzer

        # Net-weight context anchor — broad list of indicators in EN /
        # FR / ES / DE / IT, plus the EU-compliant ``℮`` symbol. Fires
        # only when one of these markers is in the document AND a unit
        # follows within ~100 chars (formatting / line breaks tolerated).
        # The wide vocabulary means new fixture types (food, cosmetics,
        # supplements, beverages) all match without per-fixture tuning.
        weight_indicators = (
            r"NET\s*WT|NET\s*WEIGHT|NET\s*CONTENT|NET\s*QUANTITY|NET\s*QTY|"
            r"NET\s+\d|"  # bare "NET 4.94" callouts
            r"CONTENU\s*NET|POIDS\s*NET|"
            r"CONTENIDO\s*NETO|PESO\s*NETO|"
            r"NETTO|NETTOGEWICHT|"
            r"PESO\s*NETTO|"
            r"℮"  # noqa: RUF001 - U+212E ESTIMATED SYMBOL is the EU net-content e-mark
        )
        net_imperial = re.compile(
            rf"(?:{weight_indicators})[^a-zA-Z]{{0,100}}\d+(?:\.\d+)?\s*(?:lb|oz|lbs|fl\s*oz)\b",
            re.IGNORECASE | re.DOTALL,
        )
        net_metric = re.compile(
            rf"(?:{weight_indicators})[^a-zA-Z]{{0,100}}\d+(?:\.\d+)?\s*(?:g|kg|ml|mL|cl|L|gm)\b",
            re.IGNORECASE | re.DOTALL,
        )
        # Dual-unit pattern: "200 g (8 oz)" / "8 oz (200 g)" / "200g/8oz"
        # — both units already declared, no advisory.
        dual_unit = re.compile(
            r"\b\d+(?:\.\d+)?\s*(?:g|kg|ml|mL|cl|L|oz|lb|fl\s*oz)\s*[(/]\s*"
            r"\d+(?:\.\d+)?\s*(?:g|kg|ml|mL|cl|L|oz|lb|fl\s*oz)",
            re.IGNORECASE,
        )

        for page in getattr(document, "pages", None) or []:
            raw = getattr(page, "content_stream", None)
            if not raw:
                continue
            try:
                text = raw.decode("latin-1") if isinstance(raw, (bytes, bytearray)) else str(raw)
                spaced, _ = PlaceholderTextAnalyzer._flatten_tj_operands(text)
                hay = spaced or text
            except Exception:
                continue
            # If a dual-unit pattern is present, both units are already
            # declared — no advisory.
            if dual_unit.search(hay):
                continue
            has_imperial = bool(net_imperial.search(hay))
            has_metric = bool(net_metric.search(hay))
            if has_imperial and not has_metric:
                # FDA requires dual declaration.
                return [
                    Finding(
                        inspection_id="LPDF_NET_WEIGHT_VERIFY",
                        severity=Severity.ADVISORY,
                        message=(
                            "Imperial / US-customary net weight detected "
                            "(lb / oz) but no metric equivalent (g / kg / mL / L). "
                            "FDA 21 CFR 101.105 requires net quantity declaration "
                            "in both US customary and metric. Verify the printed "
                            "panel includes both."
                        ),
                        page_num=page.page_num,
                        details={
                            "imperial_present": True,
                            "metric_present": False,
                        },
                        category="text",
                        object_type="document",
                    )
                ]
            if has_metric and not has_imperial:
                return [
                    Finding(
                        inspection_id="LPDF_NET_WEIGHT_VERIFY",
                        severity=Severity.ADVISORY,
                        message=(
                            "Metric net weight detected (g / kg / mL / L) but "
                            "no imperial / US-customary equivalent (lb / oz). "
                            "FDA 21 CFR 101.105 requires net quantity declaration "
                            "in both metric and US customary for products sold "
                            "in the US. Verify the printed panel includes both."
                        ),
                        page_num=page.page_num,
                        details={
                            "imperial_present": False,
                            "metric_present": True,
                        },
                        category="text",
                        object_type="document",
                    )
                ]
        return []

    @staticmethod
    def _check_die_safe_zone(
        document: SemanticDocument, events: list[ContentStreamEvent]
    ) -> list[Finding]:
        """Live text within 3 mm of any dieline polyline.

        Reuses ``DielineResult.regions`` (per-island bboxes) — when a
        TextRenderedEvent bbox is closer than ~8.5 pt (3 mm) to a
        region edge, fire the safe-zone advisory. Aggregates one
        finding per page with the count of nearby text events.
        """
        from lintpdf.semantic.events import TextRenderedEvent

        dl = getattr(document, "dieline_result", None)
        regions = getattr(dl, "regions", None) if dl else None
        if not regions:
            return []

        # 3 mm safe zone in points (1 mm = 2.834645669 pt).
        safe_pt = 8.5

        # Collect text bboxes per page.
        text_by_page: dict[int, list[tuple[float, float, float, float]]] = {}
        for ev in events:
            if not isinstance(ev, TextRenderedEvent):
                continue
            if ev.rendering_mode == 3 or ev.bbox is None:
                continue
            text_by_page.setdefault(ev.page_num, []).append(ev.bbox)

        out: list[Finding] = []
        for page in getattr(document, "pages", None) or []:
            page_num = page.page_num
            txt_bboxes = text_by_page.get(page_num, [])
            if not txt_bboxes:
                continue
            close_count = 0
            for tb in txt_bboxes:
                tx0, ty0, tx1, ty1 = tb
                # Compute min distance to any region edge.
                for r in regions:
                    rx0 = float(r.get("x0", 0))
                    ry0 = float(r.get("y0", 0))
                    rx1 = float(r.get("x1", 0))
                    ry1 = float(r.get("y1", 0))
                    # If text is fully outside the region, distance >0.
                    # If text is inside but close to an edge, distance
                    # to nearest edge is what we care about.
                    if tx1 < rx0 or tx0 > rx1 or ty1 < ry0 or ty0 > ry1:
                        # Outside — distance to nearest corner.
                        dx = max(rx0 - tx1, tx0 - rx1, 0.0)
                        dy = max(ry0 - ty1, ty0 - ry1, 0.0)
                        d = (dx * dx + dy * dy) ** 0.5
                    else:
                        # Inside — distance to nearest edge.
                        d = min(
                            tx0 - rx0,
                            rx1 - tx1,
                            ty0 - ry0,
                            ry1 - ty1,
                        )
                    if d < safe_pt:
                        close_count += 1
                        break
            if close_count == 0:
                continue
            out.append(
                Finding(
                    inspection_id="LPDF_DIE_NO_SAFE_ZONE",
                    severity=Severity.ADVISORY,
                    message=(
                        f"{close_count} live text event(s) on page {page_num} "
                        "sit within 3 mm of a dieline edge / fold line. The "
                        "press finishing line typically needs a 2-3 mm safety "
                        "margin from cuts and folds; copy closer than that "
                        "may be cropped, distorted by the fold, or sealed "
                        "over. Move the copy further inside the safe zone "
                        "or relocate the dieline."
                    ),
                    page_num=page_num,
                    details={
                        "events_near_dieline": close_count,
                        "safe_zone_pt": safe_pt,
                    },
                    category="dieline",
                    object_type="page",
                )
            )
        return out
