# GROUNDED RESEARCH DELIVERABLES
## Phase 7 — Complete PDF Preflight Engine Foundation

**Project:** Grounded — Detection-Only PDF Preflight Engine (SaaS)
**Status:** Research Complete — Ready for Engineering Implementation
**Date:** 2026-03-11
**Total Research Output:** 1,720 lines synthesis + implementation planning

---

## DOCUMENT INVENTORY

### SYNTHESIS DOCUMENT (255 lines)
**File:** `/synthesis.md`
- **Purpose:** Executive summary, research consolidation, critical outputs for engineering
- **Contents:**
  - Executive summary of LintPDF's competitive positioning
  - Complete inventory of all 11 research deliverables (Phases 1-7)
  - Critical research outputs: PDF/X-4 check catalog, technology stack decisions, GWG profiles, content stream interpreter spec, rule engine design, MVP definition
  - Knowledge gaps and constraints
  - Technical risks and mitigations
  - Competitive positioning vs. 4 major competitors
  - Next steps for engineering (12-week roadmap)

### IMPLEMENTATION PLAN (1,465 lines)
**File:** `/implementation-plan.md`
- **Purpose:** Comprehensive engineering playbook with detailed module specifications
- **Contents:**
  - Module dependency graph (7-layer architecture)
  - 9-phase build sequence (Parser → Semantic → Analysis → RuleEngine → Reports → API → Integration → Deployment → Launch)
  - 18 detailed module specifications with interfaces, dependencies, test strategies
  - MVP definition (17 checks)
  - Check implementation priority (MVP + Phase 2 expansion)
  - Risk register with ISO spec references
  - Pricing tier feature mapping

---

## RESEARCH DELIVERABLES (11 DOCUMENTS)

### Phase 1: PDF Fundamentals
1. **01-pdf-file-structure.md** (6.6 KB) — Six PDF file structure variants, all parser-normalized
2. **02-pdf-object-model.md** (14 KB) — 9 object types, catalog/page tree, resource inheritance

### Phase 2: Technology Deep Dives
3. **03-content-streams-graphics-state.md** (13 KB) — 40+ operators, CTM tracking, graphics state machine
4. **04-color-spaces.md** (11 KB) — 11 color space families, TAC calculation, overprint modes
5. **05-font-technology.md** (9.4 KB) — 5 font types, embedding/subsetting detection
6. **06-images.md** (8.5 KB) — Image resolution, DPI formula, compression filters
7. **07-08-transparency-overprint.md** (10 KB) — 16 blend modes, overprint safety patterns

### Phase 3-4: Standards & Competitive Analysis
8. **09-10-11-conformance-standards.md** (37 KB) — PDF/X (92 checks), PDF/A (versions 1-4), GWG (14 variants)
9. **12-16-open-source-assessment.md** (49 KB) — Parser evaluation, pikepdf selection rationale
10. **17-19-competitive-intelligence.md** (30 KB) — 4 competitor analysis, market positioning

### Phase 5: Test Infrastructure
11. **20-test-corpus-assembly.md** (91 KB) — 5,000+ test files, CI integration strategy

### Phase 6: Architecture
- **adr/ARCHITECTURE_DECISIONS.md** — 4 ADRs: Parser adapter, Content stream interpreter, Rule engine, Async API

### Phase 7: Specification
- **specs/iso15930-7-pdfx4.md** — Complete PDF/X-4 specification mapping (92 checks, ISO clauses, validation methods)

---

## KEY FINDINGS FOR IMPLEMENTATION

### 1. PDF/X-4 Check Catalog (92 CRITICAL CHECKS)
All checks extracted from ISO 15930-7:2010 with:
- **31 CRITICAL** checks (file invalid if failed)
- **27 HIGH** checks (major conformance issues)
- **18 MEDIUM** checks (significant violations)
- **12 LOW** checks (recommendations)
- **4 INFORMATIONAL** checks (feature notes)

**Organized by:** File Structure, Metadata, Output Intent, Color Spaces, Fonts, Transparency, Page Boxes, Annotations, Security, Optional Content, Restricted Features, Graphics/Images, Compression, Resources, Validation, Variants

### 2. MVP Definition (17 CHECKS)
Covers ~200 PDF/X-4 requirements (20% spec depth, 80% real-world issues):
1. Font embedding detection
2. Font subsetting validation
3. Image DPI calculation
4. Image color space matching
5. Prohibited color space detection (Lab, CalGray, CalRGB)
6. ICC profile requirement for RGB/Gray
7. Spot color backing color validation
8. TrimBox/BleedBox presence
9. BleedBox hierarchy validation
10. Risky blend mode detection
11. Transparency + Overprint conflict
12. PDF/X-4 conformance check
13. XMP metadata validation
14. Info dictionary requirement
15. Encryption/JavaScript prohibition
16. Form field detection
17. Layer/Optional content detection

### 3. Technology Stack
| Component | Selection | Rationale |
|-----------|-----------|-----------|
| Parser | pikepdf (QPDF) | 15+ years battle-tested, excellent error recovery |
| API Framework | FastAPI | Async-native, OpenAPI 3.1, excellent DX |
| Job Queue | Celery + Redis | Industry-standard, horizontal scaling |
| Database | PostgreSQL | ACID compliance, JSONB metadata |
| File Storage | Cloudflare R2 | Cost-effective, S3-compatible, CDN |
| Deployment | Railway | Simple Docker deployment, Celery support |

### 4. Content Stream Interpreter State Machine
Maintains:
- **CTM** (Current Transformation Matrix) — 6-element array for position, scale, rotation, skew
- **Color** — fill/stroke values per color space
- **Opacity** — alpha values (0.0–1.0)
- **Blend Mode** — all 16 PDF-defined modes
- **Overprint** — OP, op, OPM flags
- **Font** — current font, size, scaling
- **Clipping** — active clip region

Emits semantic events:
- ImagePlaced, TextRendered, ColorChanged, OpacityChanged, OverprintModeChanged, TransparencyGroupEntered, FormXObjectEntered, PathOperator, ClippingPathSet

### 5. GWG Profile Architecture (14 Variants)
Flight Plans (JSON profiles) enable:
- **Rule composition** — select subset of checks per variant
- **Severity overrides** — adjust severity per variant
- **Threshold customization** — set segment-specific limits
- **Context-aware checks** — different rules for offset vs. digital vs. packaging

Covers 9 print segments:
1. Sheetfed Offset (300% TAC)
2. Web Offset (260-280% TAC)
3. Newspaper (200-240% TAC)
4. Digital Print Electrophotographic (100% per color)
5. Digital Print Inkjet (device-specific)
6. Packaging (260-300% TAC)
7. Flexography (100-150% TAC)
8. Gravure (100-150% TAC)
9. Sign & Display (50-300 DPI context-dependent)

---

## CRITICAL TECHNICAL DECISIONS

### ADR-001: PDF Parser Strategy
**Decision:** Use pikepdf (QPDF wrapper) with adapter pattern abstraction
- **Rationale:** Mature, reliable, handles all PDF variants and malformations
- **Alternative:** PyPDF2 (rejected: slower, weaker error recovery)
- **Implementation:** ParserAdapter abstract interface, PikePDFAdapter concrete implementation
- **Consequence:** Isolates parser from inspection logic; allows future parser swaps

### ADR-002: Content Stream Interpretation
**Decision:** Build custom semantic interpreter (state machine) emitting high-level events
- **Rationale:** No off-the-shelf library handles deep content stream analysis needed for preflight
- **Alternative:** Regex-based parsing (rejected: fragile, doesn't handle state)
- **Implementation:** GraphicsState stack, CTM accumulation, operator-to-event mapping
- **Consequence:** Complex development (80-120 hrs), but enables all downstream analysis

### ADR-003: Rule Engine with Profiles
**Decision:** Pure Python functions (rules) composed via JSON profiles (Flight Plans)
- **Rationale:** Flexible, version-controllable, tenant-customizable
- **Alternative:** Monolithic rule set (inflexible), DSL (overkill)
- **Implementation:** RuleRegistry, FlightPlanLoader, ProfileRegistry
- **Consequence:** Enables GWG variants, custom tenant rules, easy feature expansion

### ADR-004: Async Processing
**Decision:** Celery task queue with Redis broker, FastAPI HTTP layer, webhook callbacks
- **Rationale:** Large PDFs (100MB+) take 10-30 seconds; synchronous API would timeout
- **Alternative:** Sync API (inadequate for real-world PDFs)
- **Implementation:** Job submission → queue → worker → results → webhook/polling
- **Consequence:** Scalable architecture; 202 Accepted response for immediate user feedback

---

## REMAINING UNKNOWNS & RISK MITIGATIONS

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| ContentStreamInterpreter state machine bugs | HIGH | HIGH | Unit test every operator; GWG corpus acceptance test |
| pikepdf failures on malformed PDFs | HIGH | MEDIUM | Try-catch exceptions; convert to graceful findings |
| PDF/X-4 check misinterpretation | MEDIUM | HIGH | Peer review each check; cross-validate vs. veraPDF |
| ICC profile validation complexity | MEDIUM | MEDIUM | Use external ICC library; validate N value |
| Rule composition edge cases | MEDIUM | MEDIUM | Dependency checker; profile composition tests |
| Async job timeouts on huge PDFs | LOW | MEDIUM | Benchmark extreme cases; adjust time_limit |

---

## NEXT STEPS FOR ENGINEERING TEAMS

### Week 1-2: Foundation
1. Read all 11 research deliverables (focus on synthesis + ADRs)
2. Design ParserAdapter interface + PikePDFAdapter implementation
3. Design SemanticModel classes (PdfDocument, PdfPage, PdfFont, etc.)

### Week 3-4: Core Engine
1. Implement ContentStreamInterpreter state machine (streaming architecture)
2. Implement GraphicsState and q/Q operator stack
3. Implement CTM accumulation and multiplication (Form XObject recursion)

### Week 5-8: Analysis Layer
1. Implement 17 MVP checks (FontAnalyzer, ImageAnalyzer, ColorAnalyzer, etc.)
2. Run against GWG test corpus (260 files) — acceptance test
3. Validate DPI calculations, color space detection, font embedding

### Week 9-10: API & Deployment
1. Implement FastAPI endpoints + Celery task queue
2. Implement report generation (JSON/XML/HTML/PDF via WeasyPrint)
3. Deploy to Railway with PostgreSQL + Redis + R2 storage

### Week 11-12: Launch Preparation
1. Generate SDK libraries (Python, Node, Go)
2. Public API testing and documentation
3. Marketing materials and launch checklist

---

## QUICK REFERENCE: INSPECTION IDs

**Font Checks (GRD_FONT_xxx)**:
- 001: Unembedded font
- 002: Font subsetting violation

**Image Checks (GRD_IMG_xxx)**:
- 001: Low resolution (<150 DPI)
- 002: Color space mismatch

**Color Checks (GRD_COLOR_xxx)**:
- 001: Prohibited color space
- 002: Missing ICC profile
- 003: Spot color backing color

**Page Box Checks (GRD_BOX_xxx)**:
- 001: Missing TrimBox/BleedBox
- 002: BleedBox hierarchy violation

**Transparency Checks (GRD_TRANS_xxx)**:
- 001: Risky blend mode
- 002: Transparency + Overprint conflict

**Compliance Checks (GRD_COMP_xxx)**:
- 001: PDF/X-4 conformance
- 002: XMP metadata
- 003: Info dictionary
- 004: Encryption/JavaScript

**Structure Checks (GRD_STRUCT_xxx)**:
- 001: Form field detection
- 002: Layer detection

---

**Document Version:** 1.0
**Status:** Ready for Engineering Implementation
**Date:** 2026-03-11

For questions or clarifications on any research deliverable, refer to the specific document section or ADR noted above.
