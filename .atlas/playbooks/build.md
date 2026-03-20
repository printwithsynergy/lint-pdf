---
title: Build Playbook
tags: [playbook, build, phases]
phases: 9
---

# Build Playbook — LintPDF

## Phase 1: Parser Layer [COMPLETE]

- GRD-001: Project scaffold and CI setup
- GRD-002: ParserAdapter abstract base class
- GRD-003: PikePDFAdapter implementation
- GRD-004: Test corpus setup (deferred)

## Phase 2: Semantic Model [COMPLETE]

- GRD-005: SemanticModel dataclasses (PdfBox, PdfFont, PdfColorSpace, PdfImage, SemanticPage, SemanticDocument)
- GRD-006: SemanticModel builder (inheritance resolution, font/color extraction)

## Phase 3: Content Stream Interpreter [COMPLETE]

- GRD-007: GraphicsState + TransformationMatrix
- GRD-008: Content stream semantic events (9 event types)
- GRD-009: ContentStreamInterpreter core (18 CRITICAL operators)
- GRD-010: Form XObject recursion with depth limit
- GRD-011: IMPORTANT operators (14 operators)

## Phase 4: Analyzers

- GRD-012: ImageAnalyzer with DPI calculation
- GRD-013: FontAnalyzer (10-point check list)
- GRD-014: ColorAnalyzer with TAC calculation
- GRD-015: TransparencyAnalyzer
- GRD-016: OverprintAnalyzer
- GRD-017: PageGeometryAnalyzer

## Phase 5: Conformance Validators

- GRD-018: PDF/X-4 validator (92 checks)
- GRD-019: PDF/A validator via veraPDF sidecar

## Phase 6: Rule Engine + Flight Plans

- GRD-020: RuleRegistry and @rule decorator
- GRD-021: Built-in rule functions (17 MVP checks)
- GRD-022: FlightPlanLoader and ProfileRegistry

## Phase 7: API + Queue + Tenants

- GRD-023: FastAPI app with core endpoints
- GRD-024: Celery task queue
- GRD-025: Multi-tenancy with API key auth
- GRD-026: Radio webhook delivery
- GRD-027: ReportGenerator (Flight Log output)

## Phase 8: Deployment

- GRD-028: Docker + Railway deployment

## Phase 9: Launch Prep

- GRD-029: API documentation and SDK generation
- GRD-030: Regression test suite
