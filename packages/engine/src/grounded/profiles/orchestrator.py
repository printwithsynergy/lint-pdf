"""Preflight orchestrator - runs the full preflight pipeline.

Coordinates parsing, semantic model building, content stream interpretation,
analyzer execution, conformance validation, and finding filtering.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from grounded.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from grounded.profiles.schema import VoyagePlan


@dataclass(frozen=True)
class PreflightSummary:
    """Summary statistics for a preflight run."""

    total_findings: int
    aground_count: int
    squall_count: int
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


class PreflightOrchestrator:
    """Executes the full preflight pipeline for a given voyage plan.

    Pipeline:
    1. Parse PDF via adapter
    2. Build semantic model
    3. Interpret content streams -> events
    4. Run enabled analyzers with configured thresholds
    5. Run conformance validator (if configured)
    6. Run AI analyzers (if AI enabled in voyage plan)
    7. Apply severity overrides
    8. Filter disabled checks
    9. Return PreflightResult
    """

    def __init__(
        self,
        voyage_plan: VoyagePlan,
        profile_id: str = "custom",
        ai_config: Any | None = None,
        pdf_bytes: bytes | None = None,
    ) -> None:
        self._plan = voyage_plan
        self._profile_id = profile_id
        self._ai_config = ai_config
        self._pdf_bytes = pdf_bytes

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
            from grounded.conformance.pdfx4 import PdfX4Validator

            validator = PdfX4Validator()
            raw_findings.extend(validator.validate(document, events, raw_findings))

        # Step 6: Run AI analyzers (if AI enabled in voyage plan)
        ai_findings = self._run_ai_analyzers(document, events, pdf_bytes)
        raw_findings.extend(ai_findings)

        # Step 7-8: Filter and override
        findings = self._apply_overrides_and_filter(raw_findings)

        # Step 9: Build result
        duration_ms = int((time.monotonic() - start) * 1000)
        summary = self._build_summary(findings, document.page_count, len(pdf_bytes))

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
                "ai_enabled": self._plan.ai.enabled if self._plan.ai else False,
                "ai_findings_count": len(ai_findings),
            },
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
            from grounded.conformance.pdfx4 import PdfX4Validator

            validator = PdfX4Validator()
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
        """Run AI analyzers if AI is enabled in the voyage plan."""
        import logging

        logger = logging.getLogger(__name__)

        if not self._plan.ai or not self._plan.ai.enabled:
            return []

        try:
            from grounded.ai.registry import get_ai_analyzers

            categories = self._plan.ai.categories if self._plan.ai.categories else None
            features = self._plan.ai.features if self._plan.ai.features else None

            analyzers = get_ai_analyzers(categories=categories, features=features)
            if not analyzers:
                return []

            ai_findings: list[Finding] = []
            for analyzer in analyzers:
                try:
                    findings = analyzer.analyze(document, events, pdf_bytes, self._ai_config)
                    ai_findings.extend(findings)
                except Exception:
                    logger.exception(
                        "AI analyzer %s.%s failed",
                        analyzer.category,
                        analyzer.feature_slug,
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
        from grounded.parser.pikepdf_adapter import PikePDFAdapter
        from grounded.semantic.builder import SemanticModelBuilder
        from grounded.semantic.interpreter import ContentStreamInterpreter

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
        from grounded.analyzers import (
            AccessibilityAnalyzer,
            AnnotationAnalyzer,
            BarcodeAnalyzer,
            ColorAnalyzer,
            DocumentAnalyzer,
            FontAnalyzer,
            HairlineAnalyzer,
            ImageAnalyzer,
            MetadataAnalyzer,
            OverprintAnalyzer,
            PageGeometryAnalyzer,
            PrepressAnalyzer,
            ProcessingStepAnalyzer,
            StructureAnalyzer,
            TransparencyAnalyzer,
        )

        t = self._plan.thresholds
        bleed_pts = _mm_to_pts(t.min_bleed_mm)
        safety_pts = _mm_to_pts(t.safety_margin_mm)

        return [
            ImageAnalyzer(min_dpi=t.min_dpi, max_dpi=t.max_dpi),
            ColorAnalyzer(tac_limit=t.tac_limit),
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
        ]

    def _apply_overrides_and_filter(self, findings: list[Finding]) -> list[Finding]:
        """Apply severity overrides and filter disabled checks."""
        result: list[Finding] = []

        for finding in findings:
            if not self._plan.is_check_enabled(finding.inspection_id):
                continue

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
                )

            result.append(finding)

        return result

    @staticmethod
    def _build_summary(
        findings: list[Finding], page_count: int, file_size_bytes: int
    ) -> PreflightSummary:
        """Build summary from filtered findings."""
        aground = sum(1 for f in findings if f.severity == Severity.AGROUND)
        squall = sum(1 for f in findings if f.severity == Severity.SQUALL)
        advisory = sum(1 for f in findings if f.severity == Severity.ADVISORY)

        return PreflightSummary(
            total_findings=len(findings),
            aground_count=aground,
            squall_count=squall,
            advisory_count=advisory,
            passed=aground == 0,
            page_count=page_count,
            file_size_bytes=file_size_bytes,
        )
