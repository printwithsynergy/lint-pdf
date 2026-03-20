# GROUNDED SYNTHESIS REPORT
## Phase 7: Research Consolidation and Implementation Roadmap

**Project:** Grounded — Detection-Only PDF Preflight Engine (SaaS)
**Date:** 2026-03-11
**Status:** Research Complete — Ready for Engineering Phase

---

## EXECUTIVE SUMMARY

Grounded is a **detection-only PDF preflight API** combining:
- **Comprehensive Inspection Depth**: 92 PDF/X-4 checks + 150+ PDF/A checks + GWG profiles (14 variants)
- **Pure Detection Philosophy**: No corrections, no side effects. Simple mental model for developers.
- **Transparent Pricing**: Per-check model with generous free tier
- **Fast Onboarding**: 5-minute setup, instant API keys
- **Spec-Driven Validation**: Every rule traces to ISO clause references

---

## RESEARCH DELIVERABLES SUMMARY

### Phases 1-3: PDF Fundamentals and Technologies
- **01-pdf-file-structure.md**: 6 file structure variants, all handled by pikepdf
- **02-pdf-object-model.md**: 9 object types, document structure, page boxes
- **03-content-streams-graphics-state.md**: 40+ operators, CTM tracking, DPI formula
- **04-color-spaces.md**: 11 color space families, TAC calculation, overprint rules
- **05-font-technology.md**: 5 font types, embedding detection, subsetting identifier
- **06-images.md**: DPI calculation (EffectiveDPI = 72 / CTM_scale)
- **07-08-transparency-overprint.md**: 16 blend modes (8 safe, 8 risky), OPM interactions

### Phases 4-5: Standards, Competitive Analysis, Test Infrastructure
- **09-10-11-conformance-standards.md**: PDF/X-4 (92 checks), PDF/A (versions 1-4), GWG (14 variants)
- **12-16-open-source-assessment.md**: pikepdf is the only production-grade pure-Python parser
- **17-19-competitive-intelligence.md**: Competitive positioning vs. pdfRest, ConvertAPI, pdfToolbox, PitStop
- **20-test-corpus-assembly.md**: 5,000+ test files (veraPDF, Isartor, Bavaria, GWG)

### Phase 6: Architecture Decisions
- **ADR-001**: PDFParserAdapter pattern (pikepdf + adapter abstraction)
- **ADR-002**: ContentStreamInterpreter state machine (semantic events)
- **ADR-003**: Rule Engine with Flight Plans (JSON profiles, pure Python rules)
- **ADR-004**: Async API with Celery + Redis (job queue, webhooks)

### Phase 7: Complete Specification
- **iso15930-7-pdfx4.md**: All 92 PDF/X-4 checks mapped to ISO clauses, validation methods, severity levels

---

## CRITICAL RESEARCH OUTPUTS FOR ENGINEERING

### 1. PDF/X-4 Check Catalog (92 Checks)
**Organized by Category**:
- File Structure & Metadata (11 checks): PDF version, trailer ID, XMP, Info dictionary
- Output Intent (8 checks): GTS_PDFX requirement, ICC profile embedding/external reference
- Color Spaces (9 checks): Device space restriction, ICC requirement, prohibited spaces
- Fonts (6 checks): Embedding requirement, subsetting limits, CIDFont support
- Transparency (4 checks): Blend mode support, soft mask validation, color management
- Page Boxes (8 checks): TrimBox, BleedBox, ArtBox presence and hierarchy
- Annotations (4 checks): Print flag, allowed types, form field prohibition
- Encryption & Security (2 checks): No encryption, no JavaScript
- Optional Content (3 checks): OCG definitions, visibility, resource references
- Restricted Features (5 checks): No external files, templates, embedded files
- Graphics & Images (6 checks): Color space, bit depth, resolution, soft masks
- Image Compression (6 checks): JPEG baseline, allowed filters, no LZW
- Resource Dictionaries (4 checks): Reference validity, ExtGState, Shading dictionaries
- Reader & Validation (7 checks): Conformance detectability, reader capability
- Variants & Exchange (4 checks): PDF/X-4 vs. PDF/X-4p consistency

**Severity Distribution**:
- CRITICAL (31): File invalid if failed
- HIGH (27): Major conformance issues
- MEDIUM (18): Significant violations
- LOW (12): Recommendations
- INFORMATIONAL (4): Feature notes

### 2. Technology Stack Decisions

**Parser**: pikepdf (QPDF wrapper)
- Rationale: 15+ years battle-tested, excellent error recovery, handles all variants
- Alternative considered: PyPDF2 (rejected: slow, weak error recovery)

**API Framework**: FastAPI
- Rationale: Async-native, OpenAPI 3.1 auto-generation, excellent DX

**Job Queue**: Celery + Redis
- Rationale: Industry-standard, horizontal scaling, webhook support

**Database**: PostgreSQL
- Rationale: ACID compliance for job state, transaction safety, JSONB metadata

**File Storage**: Cloudflare R2
- Rationale: Cost-effective, S3-compatible, integrated CDN

**Deployment**: Railway
- Rationale: Simple Dockerfile deployment, Celery worker support, cost-transparent

### 3. GWG Profile Architecture (14 Variants)

**Flight Plan System** allows:
- Rule selection and composition
- Severity overrides per variant
- Threshold customization (e.g., "≥95% of images need alt text")
- Segment-specific rules (offset vs. digital vs. packaging)

**Variant Coverage**:
1. Sheetfed Offset (300% TAC)
2. Web Offset (260-280% TAC)
3. Newspaper (200-240% TAC)
4. Digital Print Electrophotographic (100% per color)
5. Digital Print Inkjet (device-specific)
6. Packaging (260-300% TAC)
7. Flexography (100-150% TAC)
8. Gravure (100-150% TAC)
9. Sign & Display (50-300 DPI context-dependent)
+ RGB, Transparency, and Spot Color variants

### 4. Content Stream Interpreter Specification

**State Machine Maintains**:
- CTM (Current Transformation Matrix): 6-element array tracking position, scale, rotation
- Color: fill/stroke color values
- Color Space: DeviceRGB, DeviceCMYK, etc.
- Opacity: fill alpha (ca) and stroke alpha (CA)
- Blend Mode: all 16 PDF-defined modes
- Overprint Settings: OP, op, OPM flags
- Font State: current font, size, scaling
- Clipping Path: current clip region

**Emitted Events**:
- ImagePlaced(page_num, bbox, color_space, width, height)
- TextRendered(page_num, bbox, font_name, size, color, opacity)
- ColorChanged(fill_or_stroke, color_space, values)
- OpacityChanged(ca_or_CA, value)
- OverprintModeChanged(mode)
- TransparencyGroupEntered(bbox, colorspace, knockout)
- FormXObjectEntered(name, bounding_box, nested_depth)
- PathOperator(operator, operands, bbox)
- ClippingPathSet(bbox, rule_evenodd)

### 5. Rule Engine with Flight Plans

**Rule Design**:
```python
@rule(analyzer=ContentStreamAnalyzer, name="text_with_transparency")
def check_text_with_transparency(analyzer_output) -> List[Finding]:
    """Pure function returning findings or empty list"""
    findings = []
    for text_event in analyzer_output.text_rendered_events:
        if text_event.opacity < 1.0 and text_event.background_has_transparency:
            findings.append(Finding(
                inspection_id="text_with_transparency",
                severity="delay",
                message=f"Text with opacity {text_event.opacity} over transparent bg",
                page_num=text_event.page_num,
                details={"opacity": text_event.opacity, "font": text_event.font_name}
            ))
    return findings
```

**Flight Plan (JSON Profile)**:
```json
{
  "id": "gwg-variant-4-cmyk",
  "name": "GWG Variant 4 (CMYK Color Space)",
  "rules": [
    {"name": "text_with_transparency", "enabled": true, "severity_override": "no-fly"},
    {"name": "images_must_have_intent", "enabled": true, "threshold": 0.95},
    {"name": "cmyk_color_space_required", "enabled": true}
  ]
}
```

### 6. MVP Definition (17 Checks)

**In Scope for Initial Launch**:
1. GRD_FONT_001: Font embedding required
2. GRD_FONT_002: Font subsetting ≥100 chars
3. GRD_IMG_001: Image DPI ≥150 (warning <300)
4. GRD_IMG_002: Image color space match
5. GRD_COLOR_001: Prohibited color spaces (Lab, CalGray, CalRGB)
6. GRD_COLOR_002: DeviceRGB/Gray requires ICC in PDF/X-4
7. GRD_COLOR_003: Spot color backing color
8. GRD_BOX_001: TrimBox and BleedBox present
9. GRD_BOX_002: BleedBox ≥ TrimBox
10. GRD_TRANS_001: Risky blend modes detected
11. GRD_TRANS_002: Transparency + Overprint conflict
12. GRD_COMP_001: PDF/X-4 conformance check
13. GRD_COMP_002: XMP metadata + GTS_PDFXVersion
14. GRD_COMP_003: Document Info dictionary
15. GRD_COMP_004: No encryption, no JavaScript
16. GRD_STRUCT_001: Form field detection
17. GRD_STRUCT_002: Layer/Optional content detection

**Coverage**: ~200 PDF/X-4 requirements (20% depth, 80% real-world issues)

---

## KNOWLEDGE GAPS AND CONSTRAINTS

### Remaining Unknowns
1. **Exact ICC Profile Validation**: Requires ICC.1 spec beyond PDF scope; mitigation: use external ICC library
2. **Real-World Generator Edge Cases**: Resolved via GWG test corpus integration (Phase 5)
3. **Content Stream Operator Ambiguities**: Edge cases surface during test suite runs
4. **Performance on Extreme PDFs**: Streaming interpreter designed for memory efficiency
5. **Tenant-Specific Rule Sandboxing**: Implement whitelist parser + restricted_python library

### Technical Risks
1. **ContentStreamInterpreter Correctness** (HIGH): Unit test every operator, run against GWG corpus
2. **pikepdf Stability on Malformed PDFs** (HIGH): Wrap in try-catch, convert to graceful findings
3. **PDF/X-4 Check Validation** (MEDIUM): Peer review each check, cross-validate against veraPDF
4. **Rule Composition Complexity** (MEDIUM): Implement dependency checker, profile composition tests
5. **Async Job Timeout** (MEDIUM): Benchmark large PDFs, adjust time_limit if needed
6. **ICC Profile Component Mismatch** (LOW): Validate N value against declared color space

---

## COMPETITIVE POSITIONING SUMMARY

### vs. pdfRest
- **Strength**: Better preflight depth (92 checks vs. ~20), no per-call overhead
- **Strategy**: "pdfRest++ for print workflows"

### vs. ConvertAPI
- **Strength**: Pure inspection (not correction-mixing), transparent pricing, better DX
- **Strategy**: "For integrators who want control"

### vs. Callas pdfToolbox Cloud
- **Strength**: Faster onboarding (5 min vs. 30+ min), simpler API, no OEM partnership required
- **Strategy**: "Grounded for SMBs; pdfToolbox for enterprise"

### vs. Enfocus PitStop Container
- **Strength**: No Docker required, faster setup, transparent pricing
- **Strategy**: "Grounded for developers; PitStop for established shops"

### Differentiation
1. **Simplicity**: Pure detection (prevents lock-in)
2. **Pricing Transparency**: $29/mo flat (not enterprise negotiation)
3. **Developer Velocity**: 5-min onboarding, free tier, OpenAPI 3.1 SDKs
4. **Spec Compliance**: Every check traces to ISO clause

---

## NEXT STEPS FOR ENGINEERING

1. **Week 1-2**: Review all research deliverables; design ParserAdapter + SemanticModel
2. **Week 3-4**: Implement ContentStreamInterpreter state machine
3. **Week 5-8**: Build 17 MVP checks with test corpus integration
4. **Week 9-10**: Launch API, report generation, multi-tenancy
5. **Week 11-12**: QA, documentation, public API testing

---

**Document Version**: 1.0
**Status**: Ready for Engineering Implementation
**Date**: 2026-03-11
