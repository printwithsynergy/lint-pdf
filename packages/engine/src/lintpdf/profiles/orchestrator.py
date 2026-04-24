"""Preflight orchestrator - runs the full preflight pipeline.

Coordinates parsing, semantic model building, content stream interpretation,
analyzer execution, conformance validation, and finding filtering.
"""

from __future__ import annotations

import fnmatch
import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.profiles.schema import PreflightProfile


# Higher rank = more severe. Used by ``CheckConfig.max_severity`` to cap
# findings to a maximum severity (e.g. lintpdf-advisory-only caps everything
# at advisory).
_SEVERITY_RANK: dict[Severity, int] = {
    Severity.ADVISORY: 0,
    Severity.WARNING: 1,
    Severity.ERROR: 2,
}


def _severity_rank(sev: Severity) -> int:
    """Numeric ordering for severity comparison."""
    return _SEVERITY_RANK.get(sev, 0)


@dataclass(frozen=True)
class PreflightSummary:
    """Summary statistics for a preflight run."""

    total_findings: int
    error_count: int
    warning_count: int
    advisory_count: int
    passed: bool
    page_count: int
    file_size_bytes: int


@dataclass(frozen=True)
class PreflightResult:
    """Complete result of a preflight run."""

    job_id: str
    profile_id: str
    findings: list[Finding]
    summary: PreflightSummary
    metadata: dict[str, Any]
    duration_ms: int


def _mm_to_pts(mm: float) -> float:
    """Convert millimeters to points (1mm = 2.834645669 pt)."""
    return mm * 2.834645669


@dataclass(frozen=True)
class ViewerEssentials:
    """Minimal document info the viewer needs, without running analyzers.

    Populated by :func:`extract_viewer_essentials` for the ``minimal`` and
    ``external`` preflight sources. Enough to render the PDF, draw page
    outlines and box overlays, and show metadata without executing the
    27+ analyzer preflight pipeline.
    """

    pdf_version: str
    page_count: int
    is_encrypted: bool
    pages: list[dict[str, Any]]
    info_dict: dict[str, Any]


def extract_viewer_essentials(pdf_bytes: bytes) -> ViewerEssentials:
    """Parse a PDF just enough for viewer use.

    Shares the parser/semantic-builder chain with
    :meth:`PreflightOrchestrator._parse_and_interpret` but skips content
    stream interpretation, analyzer execution, conformance validation, and
    AI analyzers. Returns page geometry (media/crop/trim/bleed boxes,
    rotation, user unit), page count, encryption flag, and the Info dict.
    """
    from lintpdf.parser.pikepdf_adapter import PikePDFAdapter
    from lintpdf.semantic.builder import SemanticModelBuilder

    adapter = PikePDFAdapter()
    pdf_doc = adapter.open(pdf_bytes)
    builder = SemanticModelBuilder(adapter)
    document = builder.build(pdf_doc)

    pages: list[dict[str, Any]] = []
    for page in document.pages:
        pages.append(
            {
                "page_num": page.page_num,
                "rotate": page.rotate,
                "user_unit": page.user_unit,
                "media_box": _box_to_list(page.media_box),
                "crop_box": _box_to_list(page.crop_box),
                "bleed_box": _box_to_list(page.bleed_box),
                "trim_box": _box_to_list(page.trim_box),
                "art_box": _box_to_list(page.art_box),
                "width_pts": page.effective_width,
                "height_pts": page.effective_height,
            }
        )

    return ViewerEssentials(
        pdf_version=document.version,
        page_count=document.page_count,
        is_encrypted=document.is_encrypted,
        pages=pages,
        info_dict={k: str(v) for k, v in (document.info_dict or {}).items()},
    )


def _box_to_list(box: Any) -> list[float] | None:
    """Convert a :class:`PdfBox` to a ``[x0, y0, x1, y1]`` list."""
    if box is None:
        return None
    # PdfBox exposes either ``x0/y0/x1/y1`` attributes or tuple unpacking.
    try:
        return [float(box.x0), float(box.y0), float(box.x1), float(box.y1)]
    except AttributeError:
        try:
            x0, y0, x1, y1 = box
            return [float(x0), float(y0), float(x1), float(y1)]
        except (TypeError, ValueError):
            return None


class PreflightOrchestrator:
    """Executes the full preflight pipeline for a given profile.

    Pipeline:
    1. Parse PDF via adapter
    2. Build semantic model
    3. Interpret content streams -> events
    4. Run enabled analyzers with configured thresholds
    5. Run conformance validator (if configured)
    6. Run AI analyzers (if AI enabled in profile)
    7. Apply severity overrides
    8. Filter disabled checks
    9. Return PreflightResult
    """

    def __init__(
        self,
        profile: PreflightProfile,
        profile_id: str = "custom",
        ai_config: Any | None = None,
        pdf_bytes: bytes | None = None,
        custom_pantone_overrides: dict[str, Any] | None = None,
        brand_spec: Any | None = None,
    ) -> None:
        self._plan = profile
        self._profile_id = profile_id
        self._ai_config = ai_config
        self._pdf_bytes = pdf_bytes
        self._custom_pantone_overrides = custom_pantone_overrides
        # ``brand_spec`` is a :class:`ResolvedBrandSpec` produced by the
        # resolver (or ``None`` when nothing in the chain matches). It's
        # a frozen dataclass, not the SQLAlchemy row, so analyzers can
        # hold onto it past session teardown without risking
        # autoflush-on-mutate surprises.
        self._brand_spec = brand_spec

    def _ai_config_with_brand_spec(self) -> Any | None:
        """Return an AI config shim carrying the resolved BrandSpec's
        palette.

        AI analyzers read ``ai_config.brand_palette`` directly. When a
        BrandSpec has been resolved for this job we need that attribute
        to reflect the spec's colours rather than the legacy
        ``TenantAIConfig.brand_palette`` column. Rather than mutate the
        live ORM object (which would flush on the next commit), we
        build a lightweight ``SimpleNamespace`` that proxies the
        attributes the analyzers read. When no spec is resolved we
        return the original ``ai_config`` unchanged so nothing changes
        for tenants still on the legacy column.
        """
        if self._brand_spec is None:
            return self._ai_config
        if self._ai_config is None:
            from types import SimpleNamespace

            return SimpleNamespace(
                brand_palette=list(self._brand_spec.colors),
                # ΔE thresholds come from the tenant's default when the
                # caller hasn't supplied an AI config; the analyzer's
                # ``getattr(..., default)`` pattern handles the absence.
            )
        from types import SimpleNamespace

        keep = {
            "brand_palette": list(self._brand_spec.colors),
        }
        # Shallow-copy every attribute the analyzer may read so the
        # shim behaves like ``self._ai_config`` apart from the
        # overridden palette. ``vars()`` on a SQLAlchemy object is
        # noisy; we copy explicit attributes instead.
        for attr in (
            "delta_e_warning_threshold",
            "delta_e_error_threshold",
            "reference_logos",
            "custom_dictionary",
            "severity_labels",
            "industry_type",
            "regulatory_market",
            "tenant_id",
        ):
            if hasattr(self._ai_config, attr):
                keep[attr] = getattr(self._ai_config, attr)
        return SimpleNamespace(**keep)

    def run(self, pdf_bytes: bytes) -> PreflightResult:
        """Execute full preflight pipeline on raw PDF bytes."""
        start = time.monotonic()
        job_id = str(uuid.uuid4())

        # Store pdf_bytes for AI analyzers
        if self._pdf_bytes is None:
            self._pdf_bytes = pdf_bytes

        # Step 1-3: Parse, build model, interpret
        document, events = self._parse_and_interpret(pdf_bytes)

        # Step 4: Run analyzers
        raw_findings: list[Finding] = []
        for analyzer in self._create_analyzers():
            raw_findings.extend(analyzer.analyze(document, events))

        # Step 5: Run conformance validator
        if self._plan.conformance == "pdfx4":
            from lintpdf.conformance.pdfx4 import PdfX4Validator

            validator = PdfX4Validator()
            raw_findings.extend(validator.validate(document, events, raw_findings))
        elif self._plan.conformance in ("pdfx1a", "pdfx1a2003"):
            from lintpdf.conformance.pdfx1a import PdfX1aValidator

            validator = PdfX1aValidator()
            raw_findings.extend(validator.validate(document, events, raw_findings))
        elif self._plan.conformance in ("pdfx3", "pdfx32003"):
            from lintpdf.conformance.pdfx3 import PdfX3Validator

            validator = PdfX3Validator()
            raw_findings.extend(validator.validate(document, events, raw_findings))
        elif self._plan.conformance in ("pdfa1b", "pdfa2b", "pdfa3b"):
            from lintpdf.conformance.pdfa import PdfAValidator

            _level_map = {"pdfa1b": "1b", "pdfa2b": "2b", "pdfa3b": "3b"}
            validator = PdfAValidator(level=_level_map[self._plan.conformance])
            raw_findings.extend(validator.validate(document, events, raw_findings))

        # Step 6: Run AI analyzers (if AI enabled in profile)
        ai_findings = self._run_ai_analyzers(document, events, pdf_bytes)
        raw_findings.extend(ai_findings)

        # Step 7-8: Filter and override
        findings = self._apply_overrides_and_filter(raw_findings)

        # Step 9: Compute Color Quality Score
        color_score_data: dict[str, Any] | None = None
        try:
            from lintpdf.color_score import compute_color_quality_score

            weights = self._plan.thresholds.color_score_weights
            color_result = compute_color_quality_score(findings, weights=weights)
            color_score_data = {
                "color_quality_score": color_result.score,
                "color_quality_grade": color_result.grade,
                "color_score_breakdown": color_result.breakdown,
            }
        except Exception:
            pass

        # Step 9b: Enrich findings with bounding boxes from events
        findings = self._enrich_bboxes(findings, events)

        # Step 10: Build result
        duration_ms = int((time.monotonic() - start) * 1000)
        summary = self._build_summary(findings, document.page_count, len(pdf_bytes))

        metadata: dict[str, Any] = {
            "pdf_version": document.version,
            "page_count": document.page_count,
            "is_encrypted": document.is_encrypted,
            "conformance": self._plan.conformance,
            "workflow": self._plan.workflow,
            "ai_enabled": self._plan.ai.enabled if self._plan.ai else False,
            "ai_findings_count": len(ai_findings),
        }
        if color_score_data:
            metadata.update(color_score_data)

        return PreflightResult(
            job_id=job_id,
            profile_id=self._profile_id,
            findings=findings,
            summary=summary,
            metadata=metadata,
            duration_ms=duration_ms,
        )

    def run_on_document(
        self,
        document: Any,
        events: list[Any],
        file_size_bytes: int = 0,
    ) -> PreflightResult:
        """Run preflight on an already-parsed SemanticDocument.

        Useful for testing and when the document is already available.
        """
        start = time.monotonic()
        job_id = str(uuid.uuid4())

        raw_findings: list[Finding] = []
        for analyzer in self._create_analyzers():
            raw_findings.extend(analyzer.analyze(document, events))

        if self._plan.conformance == "pdfx4":
            from lintpdf.conformance.pdfx4 import PdfX4Validator

            validator = PdfX4Validator()
            raw_findings.extend(validator.validate(document, events, raw_findings))
        elif self._plan.conformance in ("pdfx1a", "pdfx1a2003"):
            from lintpdf.conformance.pdfx1a import PdfX1aValidator

            validator = PdfX1aValidator()
            raw_findings.extend(validator.validate(document, events, raw_findings))
        elif self._plan.conformance in ("pdfx3", "pdfx32003"):
            from lintpdf.conformance.pdfx3 import PdfX3Validator

            validator = PdfX3Validator()
            raw_findings.extend(validator.validate(document, events, raw_findings))
        elif self._plan.conformance in ("pdfa1b", "pdfa2b", "pdfa3b"):
            from lintpdf.conformance.pdfa import PdfAValidator

            _level_map = {"pdfa1b": "1b", "pdfa2b": "2b", "pdfa3b": "3b"}
            validator = PdfAValidator(level=_level_map[self._plan.conformance])
            raw_findings.extend(validator.validate(document, events, raw_findings))

        findings = self._apply_overrides_and_filter(raw_findings)
        duration_ms = int((time.monotonic() - start) * 1000)
        summary = self._build_summary(findings, document.page_count, file_size_bytes)

        return PreflightResult(
            job_id=job_id,
            profile_id=self._profile_id,
            findings=findings,
            summary=summary,
            metadata={
                "pdf_version": document.version,
                "page_count": document.page_count,
                "is_encrypted": document.is_encrypted,
                "conformance": self._plan.conformance,
                "workflow": self._plan.workflow,
            },
            duration_ms=duration_ms,
        )

    def _run_ai_analyzers(  # skipcq: PY-R1000
        self,
        document: Any,
        events: list[Any],
        pdf_bytes: bytes,
    ) -> list[Finding]:
        """Run AI analyzers if AI is enabled in the profile.

        Always emits a single ``AI_SCAN_001`` advisory marker when at least
        one AI analyzer ran (even if all of them returned zero findings) so
        the report contains an audit trail of the AI scan and so callers
        can detect "AI ran" by filtering for ``source == 'ai'``.
        """
        import logging

        logger = logging.getLogger(__name__)

        if not self._plan.ai or not self._plan.ai.enabled:
            return []

        try:
            from lintpdf.ai.registry import get_ai_analyzers

            categories = self._plan.ai.categories if self._plan.ai.categories else None
            features = self._plan.ai.features if self._plan.ai.features else None

            analyzers = get_ai_analyzers(categories=categories, features=features)
            if not analyzers:
                return []

            # Overlay the resolved BrandSpec's palette onto a
            # detached shim so the AI analyzers (which read
            # ``ai_config.brand_palette``) see the same colours the
            # standard analyzers gate on. We deliberately avoid
            # mutating ``self._ai_config`` — it's still attached to
            # the DB session at the caller and a flush would
            # accidentally persist the overlay.
            ai_config_for_analyzers = self._ai_config_with_brand_spec()

            ai_findings: list[Finding] = []
            ran_categories: set[str] = set()
            ran_features: list[str] = []
            for analyzer in analyzers:
                try:
                    findings = analyzer.analyze(
                        document, events, pdf_bytes, ai_config_for_analyzers
                    )
                    ai_findings.extend(findings)
                    ran_categories.add(analyzer.category)
                    ran_features.append(analyzer.feature_slug)
                except Exception:
                    logger.exception(
                        "AI analyzer %s.%s failed",
                        analyzer.category,
                        analyzer.feature_slug,
                    )

            # Emit an audit-trail marker so the report records that the AI
            # pipeline ran. Users (and the E2E test contract) can rely on
            # ``source == 'ai'`` being present whenever AI was enabled.
            if ran_features:
                ai_findings.append(
                    Finding(
                        inspection_id="AI_SCAN_001",
                        severity=Severity.ADVISORY,
                        message=(
                            f"AI scan completed: ran {len(ran_features)} "
                            f"analyzer(s) across {len(ran_categories)} "
                            f"category(ies); emitted {len(ai_findings)} "
                            "finding(s)."
                        ),
                        page_num=0,
                        details={
                            "categories": sorted(ran_categories),
                            "features": ran_features,
                            "findings_count": len(ai_findings),
                        },
                        source="ai",
                        category="ai_scan",
                    )
                )

            return ai_findings

        except ImportError:
            logger.debug("AI analyzer modules not available")
            return []
        except Exception:
            logger.exception("AI analyzer pipeline failed")
            return []

    @staticmethod
    def _parse_and_interpret(pdf_bytes: bytes) -> tuple[Any, list[Any]]:
        """Parse PDF and return (SemanticDocument, events)."""
        from lintpdf.parser.pikepdf_adapter import PikePDFAdapter
        from lintpdf.semantic.builder import SemanticModelBuilder
        from lintpdf.semantic.interpreter import ContentStreamInterpreter

        adapter = PikePDFAdapter()
        pdf_doc = adapter.open(pdf_bytes)
        builder = SemanticModelBuilder(adapter)
        document = builder.build(pdf_doc)

        events: list[Any] = []
        for pdf_page in pdf_doc.pages:
            instructions = adapter.parse_content_stream(pdf_page)
            if instructions:
                # Find the matching semantic page for resources
                sem_page = document.pages[pdf_page.page_num - 1]
                interpreter = ContentStreamInterpreter(
                    page_num=pdf_page.page_num,
                    resources=sem_page.resources or {},
                )
                page_events = interpreter.interpret(instructions)
                events.extend(page_events)

        return document, events

    def _create_analyzers(self) -> list[Any]:
        """Create analyzer instances with configured thresholds."""
        from lintpdf.analyzers import (
            AccessibilityAnalyzer,
            AdvancedColorAnalyzer,
            AnnotationAnalyzer,
            BarcodeAnalyzer,
            ColorAnalyzer,
            DocumentAnalyzer,
            FontAnalyzer,
            HairlineAnalyzer,
            IccProfileAnalyzer,
            ImageAnalyzer,
            InkCoverageAnalyzer,
            MetadataAnalyzer,
            OverprintAnalyzer,
            PageGeometryAnalyzer,
            PrepressAnalyzer,
            ProcessingStepAnalyzer,
            SpotColorAnalyzer,
            StructureAnalyzer,
            TransparencyAnalyzer,
        )

        t = self._plan.thresholds
        bleed_pts = _mm_to_pts(t.min_bleed_mm)
        safety_pts = _mm_to_pts(t.safety_margin_mm)

        # WS-7: gate the ambiguous pure-K / knockout advisories on
        # the presence of a brand colour palette. Without it we
        # can't tell whether a large pure-K fill was intentional,
        # and the rules generate thousands of "might be wrong, can't
        # tell" findings per page on vector-dense artwork.
        #
        # WS-11: the resolved :class:`ResolvedBrandSpec` (from
        # ``lintpdf.brand_specs.resolver``) is the authoritative
        # source of "is there a brand palette?" — the legacy
        # ``ai_config.brand_palette`` column is a fallback for
        # tenants whose migration hasn't touched their row yet.
        brand_palette_present = False
        if (
            self._brand_spec is not None and getattr(self._brand_spec, "has_colors", False)
        ) or getattr(self._ai_config, "brand_palette", None):
            brand_palette_present = True

        analyzers: list[Any] = [
            ImageAnalyzer(min_dpi=t.min_dpi, max_dpi=t.max_dpi),
            ColorAnalyzer(
                tac_limit=t.tac_limit,
                brand_palette_present=brand_palette_present,
            ),
            FontAnalyzer(),
            PageGeometryAnalyzer(min_bleed_pts=bleed_pts, safety_margin_pts=safety_pts),
            HairlineAnalyzer(
                hairline_threshold=t.hairline_threshold,
                small_text_threshold=t.small_text_threshold,
            ),
            TransparencyAnalyzer(),
            OverprintAnalyzer(),
            DocumentAnalyzer(),
            StructureAnalyzer(),
            AnnotationAnalyzer(),
            MetadataAnalyzer(),
            PrepressAnalyzer(),
            BarcodeAnalyzer(
                barcode_min_dpi=t.barcode_min_dpi,
                barcode_min_grade=t.barcode_min_grade,
                barcode_quiet_zone_mm=t.barcode_quiet_zone_mm,
            ),
            AccessibilityAnalyzer(),
            ProcessingStepAnalyzer(),
            # Color management analyzers
            IccProfileAnalyzer(),
            SpotColorAnalyzer(custom_pantone_data=self._custom_pantone_overrides),
            InkCoverageAnalyzer(tac_limit=t.tac_limit),
            AdvancedColorAnalyzer(
                rich_black_c=t.rich_black_c,
                rich_black_m=t.rich_black_m,
                rich_black_y=t.rich_black_y,
                rich_black_k=t.rich_black_k,
                brand_palette_present=brand_palette_present,
                # WS-8: hand the raw PDF bytes to the analyzer so
                # the pixel gate on LPDF_ADV_005 can re-check the
                # composited render. ``self._pdf_bytes`` was
                # stashed in ``run()`` on first entry.
                pdf_bytes=self._pdf_bytes,
            ),
        ]

        # Conditionally add ECG and EPM analyzers
        if t.ecg_mode:
            try:
                from lintpdf.analyzers.ecg_analyzer import EcgAnalyzer

                analyzers.append(EcgAnalyzer(tac_limit=t.ecg_tac_limit))
            except ImportError:
                pass

        if t.epm_mode:
            try:
                from lintpdf.analyzers.epm_analyzer import EpmAnalyzer

                analyzers.append(EpmAnalyzer(cmy_tac_threshold=t.cmy_tac_threshold))
            except ImportError:
                pass

        # Standards compliance analyzer (always enabled)
        try:
            from lintpdf.analyzers.standards_compliance import StandardsComplianceAnalyzer

            analyzers.append(StandardsComplianceAnalyzer())
        except ImportError:
            pass

        # Packaging analyzer (if packaging profile active)
        if self._profile_id and "packaging" in self._profile_id:
            try:
                from lintpdf.analyzers.packaging import PackagingAnalyzer

                analyzers.append(PackagingAnalyzer())
            except ImportError:
                pass

        # Gamut analyzer (if gamut checking enabled)
        if t.gamut_check and t.target_output_condition:
            try:
                from lintpdf.analyzers.gamut_analyzer import GamutAnalyzer

                analyzers.append(GamutAnalyzer(target_condition=t.target_output_condition))
            except ImportError:
                pass

        return analyzers

    def _apply_overrides_and_filter(self, findings: list[Finding]) -> list[Finding]:
        """Apply severity overrides, conditional rules, and filter disabled checks."""
        from lintpdf.rules.engine import CheckContext, evaluate_conditions

        result: list[Finding] = []
        per_check = self._plan.checks.per_check
        total_pages = self._page_count if hasattr(self, "_page_count") else 0

        for finding in findings:
            # AI findings (source == "ai") are gated separately by
            # ``profile.ai.enabled`` and use ``AI_*`` inspection IDs that
            # would never match the default ``LPDF_*`` enabled patterns.
            # Exempt them from the pattern filter so they actually surface
            # when AI is enabled. ``checks.disabled`` and
            # ``severity_overrides[id] == "ignore"`` still apply via the
            # explicit ``is_check_enabled`` checks below.
            if finding.source == "ai":
                if any(
                    fnmatch.fnmatch(finding.inspection_id, pattern)
                    for pattern in self._plan.checks.disabled
                ):
                    continue
                if self._plan.checks.severity_overrides.get(finding.inspection_id) == "ignore":
                    continue
            elif not self._plan.is_check_enabled(finding.inspection_id):
                continue

            # Per-check disabled
            check_config = per_check.get(finding.inspection_id)
            if check_config is not None and not check_config.enabled:
                continue

            # Evaluate conditional rules
            if check_config is not None and check_config.conditions:
                context = CheckContext(
                    page_num=finding.page_num,
                    total_pages=total_pages,
                    object_type=finding.object_type or "",
                    object_id=finding.object_id or "",
                    source=finding.source,
                    category=finding.category,
                    severity=finding.severity.value,
                    inspection_id=finding.inspection_id,
                    details=finding.details,
                )
                condition_result = evaluate_conditions(
                    context,
                    [c.model_dump() for c in check_config.conditions],
                )
                if not condition_result.include:
                    continue
                if condition_result.severity_override:
                    try:
                        new_severity = Severity(condition_result.severity_override)
                        finding = Finding(
                            inspection_id=finding.inspection_id,
                            severity=new_severity,
                            message=finding.message,
                            page_num=finding.page_num,
                            details=finding.details,
                            iso_clause=finding.iso_clause,
                            object_id=finding.object_id,
                            object_type=finding.object_type,
                            bbox=finding.bbox,
                            source=finding.source,
                            category=finding.category,
                        )
                    except ValueError:
                        pass

            # Legacy severity overrides (still applied after conditions)
            override = self._plan.get_severity_override(finding.inspection_id)
            if override and override != "ignore":
                try:
                    new_severity = Severity(override)
                except ValueError:
                    new_severity = finding.severity

                finding = Finding(
                    inspection_id=finding.inspection_id,
                    severity=new_severity,
                    message=finding.message,
                    page_num=finding.page_num,
                    details=finding.details,
                    iso_clause=finding.iso_clause,
                    object_id=finding.object_id,
                    object_type=finding.object_type,
                    bbox=finding.bbox,
                    source=finding.source,
                    category=finding.category,
                )

            # Profile-wide severity cap (e.g. lintpdf-advisory-only forces all
            # findings down to "advisory"). Applied last so per-check overrides
            # are still capped if they exceed the ceiling.
            cap = self._plan.checks.max_severity
            if cap:
                try:
                    cap_sev = Severity(cap)
                except ValueError:
                    cap_sev = None
                if cap_sev is not None and _severity_rank(finding.severity) > _severity_rank(
                    cap_sev
                ):
                    finding = Finding(
                        inspection_id=finding.inspection_id,
                        severity=cap_sev,
                        message=finding.message,
                        page_num=finding.page_num,
                        details=finding.details,
                        iso_clause=finding.iso_clause,
                        object_id=finding.object_id,
                        object_type=finding.object_type,
                        bbox=finding.bbox,
                        source=finding.source,
                        category=finding.category,
                    )

            result.append(finding)

        return result

    @staticmethod
    def _enrich_bboxes(findings: list[Finding], events: list[Any]) -> list[Finding]:
        """Enrich findings with bounding boxes from content stream events.

        Matches findings to events by page_num + object_id. For images,
        the bbox is derived from the CTM. For text, it uses the event's
        existing bbox field. Findings that already have a bbox are not
        modified.
        """
        from lintpdf.semantic.events import (
            ImagePlacedEvent,
            PathPaintingEvent,
            TextRenderedEvent,
        )

        # Build lookup: (page_num, object_id_or_font) → bbox
        event_bboxes: dict[tuple[int, str], tuple[float, float, float, float]] = {}

        for ev in events:
            if isinstance(ev, ImagePlacedEvent):
                # Derive bbox from CTM: image occupies a 1x1 unit square
                # transformed by the CTM.
                ctm = ev.ctm
                if hasattr(ctm, "a"):
                    x = ctm.e if hasattr(ctm, "e") else 0
                    y = ctm.f if hasattr(ctm, "f") else 0
                    w = abs(ctm.a) if hasattr(ctm, "a") else 0
                    h = abs(ctm.d) if hasattr(ctm, "d") else 0
                    if w > 0 and h > 0:
                        event_bboxes[(ev.page_num, ev.image_name)] = (x, y, x + w, y + h)
                elif isinstance(ctm, (list, tuple)) and len(ctm) >= 6:
                    x, y = float(ctm[4]), float(ctm[5])
                    w, h = abs(float(ctm[0])), abs(float(ctm[3]))
                    if w > 0 and h > 0:
                        event_bboxes[(ev.page_num, ev.image_name)] = (x, y, x + w, y + h)

            elif isinstance(ev, TextRenderedEvent) and ev.bbox:
                event_bboxes[(ev.page_num, ev.font_name)] = ev.bbox

            elif isinstance(ev, PathPaintingEvent):
                if hasattr(ev, "bbox") and ev.bbox:
                    key = f"path_{ev.operator_index}"
                    event_bboxes[(ev.page_num, key)] = ev.bbox

        if not event_bboxes:
            return findings

        enriched: list[Finding] = []
        for f in findings:
            if f.bbox is not None or f.page_num < 1:
                enriched.append(f)
                continue

            # Try to match by (page_num, object_id)
            bbox = None
            if f.object_id:
                bbox = event_bboxes.get((f.page_num, f.object_id))

            # Fallback: match by object_id prefix (e.g., "FormXob.abc" → "abc")
            if bbox is None and f.object_id and "." in f.object_id:
                short_id = f.object_id.split(".")[-1]
                bbox = event_bboxes.get((f.page_num, short_id))

            # Fallback: match font name from details
            if bbox is None and f.details:
                font = f.details.get("font_name", "")
                if font:
                    bbox = event_bboxes.get((f.page_num, font))

            if bbox is not None:
                enriched.append(
                    Finding(
                        inspection_id=f.inspection_id,
                        severity=f.severity,
                        message=f.message,
                        page_num=f.page_num,
                        details=f.details,
                        iso_clause=f.iso_clause,
                        object_id=f.object_id,
                        object_type=f.object_type,
                        bbox=bbox,
                        source=f.source,
                        category=f.category,
                    )
                )
            else:
                enriched.append(f)

        return enriched

    @staticmethod
    def _build_summary(
        findings: list[Finding], page_count: int, file_size_bytes: int
    ) -> PreflightSummary:
        """Build summary from filtered findings."""
        errors = sum(1 for f in findings if f.severity == Severity.ERROR)
        warnings = sum(1 for f in findings if f.severity == Severity.WARNING)
        advisory = sum(1 for f in findings if f.severity == Severity.ADVISORY)

        return PreflightSummary(
            total_findings=len(findings),
            error_count=errors,
            warning_count=warnings,
            advisory_count=advisory,
            passed=errors == 0,
            page_count=page_count,
            file_size_bytes=file_size_bytes,
        )
