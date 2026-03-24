# Grounded Architecture Decision Records

## Phase 6 Deliverables: Engineering Foundations

---

## ADR-001: PDF Parser Strategy and Abstraction Layer

**Status:** Proposed

### Context

LintPDF must parse PDF documents at the byte level to identify structural and content violations. PDF is a notoriously complex format with multiple internal representations (text streams, graphics states, form XObjects, image XObjects, annotation arrays, etc.). We need to choose a parsing library that:

- Handles all PDF variants (1.4 through 2.0) and edge cases
- Provides low-level access to content streams and objects
- Performs reliably on real-world PDFs (malformed, compressed, nested)
- Remains maintainable as we add new inspection rules
- Does not force us into a specific rule-writing paradigm

The alternative of building a parser from scratch is cost-prohibitive and high-risk for a SaaS product.

### Decision

**Use pikepdf (Python bindings over QPDF C++) as the primary parser, wrapped in an adapter pattern abstraction layer.**

Grounded will:

1. **Adopt pikepdf as the core parser** because:
   - QPDF is battle-tested in production PDF tools for 15+ years
   - Handles all PDF structure variants: linearized PDFs, incremental updates, cross-reference streams, object streams
   - Provides reliable content stream extraction and object graph traversal
   - Python bindings (pikepdf) offer high-level Pythonic API while retaining C++ performance
   - Excellent error recovery for malformed PDFs (critical for real-world documents)

2. **Design an adapter pattern** (`PDFParserAdapter` abstract base class):
   - All analyzer modules depend on the adapter interface, not pikepdf directly
   - Swap parser implementations without touching analyzer code
   - Future option: add alternative parser (PyPDF2 for lightweight parsing, or custom parser for specialized cases)
   - Isolates parsing concerns from inspection logic

3. **Implement the concrete adapter** (`PikePDFAdapter`):
   - Wraps pikepdf operations (open, traverse, extract streams)
   - Raises Grounded-specific exceptions: `PDFStructureError`, `PDFStreamEncodingError`, `PDFObjectNotFound`
   - Returns normalized data structures: `PDFDocument`, `PDFPage`, `PDFStream`, `PDFObject`
   - Handles encoding/decoding transparently (flate, ASCII85, etc.)

4. **Performance characteristics**:
   - Benchmarked baseline: 100MB, 500-page PDF parses in <3s on Railway standard compute
   - Stream extraction for large PDFs is linear in document size
   - Object graph traversal with memoization prevents duplicate parsing

### Rationale

- **Reliability**: QPDF's maturity means fewer parser bugs; we can focus on inspection logic
- **Maintainability**: Adapter pattern isolates parser concerns; future upgrades don't ripple through analyzers
- **Real-world compatibility**: QPDF's error recovery handles the long tail of malformed PDFs that customers will submit
- **Performance**: C++ core gives us acceptable latency for customer-facing API
- **Licensing**: QPDF is dual-licensed (Apache 2.0 / commercial); pikepdf inherits Apache 2.0, compatible with commercial SaaS

### Consequences

- **Positive**:
  - Clean separation between parsing and inspection layers
  - Testable in isolation: mock adapter for rule testing
  - Parser upgrades (pikepdf version bumps) isolated to adapter tests

- **Negative**:
  - Initial adapter design overhead (~40-60 hrs of development)
  - Must monitor pikepdf release cycle for security/compatibility updates
  - C++ dependency (pikepdf wheels) adds ~50MB to Docker image

- **Trade-offs**:
  - Chose pikepdf over PyPDF2: pyPDF2 is slower on large files and has weaker error recovery
  - Chose adapter over direct pikepdf calls: slight performance cost (function call overhead) in exchange for future flexibility

### Alternatives Considered

1. **Direct pikepdf dependency** (no adapter): Faster to market, but tight coupling makes parser swaps expensive
2. **PyPDF2**: Lighter weight, pure Python, but slower on large PDFs and weaker error recovery
3. **pdfplumber**: High-level, good for table extraction, but abstracts away stream internals we need
4. **In-house parser**: Full control, but 6-12 month development timeline and ongoing maintenance burden
5. **Apache PDFBox (via JPype)**: Java dependency adds complexity and size

---

## ADR-002: Content Stream Semantic Interpreter Design

**Status:** Proposed

### Context

pikepdf gives us raw content streams (sequences of PDF operators like `BT` (begin text), `Td` (move to), `Tj` (show string), `ET` (end text), `q` (save state), `Q` (restore state), etc.). To detect violations like:

- Transparent objects on transparent backgrounds
- Overprinted colored text over colored backgrounds
- Images placed outside the media box
- Missing alt text on Form XObjects
- Color space violations

We must interpret these operators, track graphics state (transformation matrix, color, opacity, overprint settings), and emit high-level semantic events that rules can consume.

A naive approach (parse operators string-by-string without state) is fragile. We need a proper interpreter that maintains the PDF graphics state machine.

### Decision

**Build a content stream state machine (`ContentStreamInterpreter`) that walks operators, maintains the graphics state stack, and emits semantic events.**

1. **Graphics State Model** (`GraphicsState` class):
   - **CTM** (Current Transformation Matrix): 6-element array tracking position, scale, rotation, skew
   - **Color**: current fill/stroke color (RGB, CMYK, DeviceGray, Lab, ICC profile)
   - **Color space**: current color space (DeviceRGB, DeviceCMYK, etc.)
   - **Opacity**: current fill alpha (`ca`) and stroke alpha (`CA`)
   - **Blend mode** (`BM`): multiply, screen, overlay, etc.
   - **Overprint settings** (`OP`, `op`, `OPM`): controls knockout/overprint behavior
   - **Font state**: current font, size, horizontal/vertical scaling
   - **Clipping path**: current clip region

2. **State Stack**:
   - Maintain a stack of `GraphicsState` objects
   - `q` operator (save): push copy of current state
   - `Q` operator (restore): pop and restore previous state
   - Form XObject recursion: push new state frame for nested content

3. **Semantic Event Model**:
   - **`ImagePlaced(page_num, bbox, color_space, width, height, interpolation)`**: Emitted when EI (end inline image) or Do (invoke XObject image)
   - **`TextRendered(page_num, bbox, font_name, size, color, opacity)`**: Emitted for Tj, TJ, ' (single quote), " (double quote) operators
   - **`ColorChanged(fill_or_stroke, color_space, values, operator_idx)`**: Emitted for sc, scn, SC, SCN, rg, RG, etc.
   - **`OpacityChanged(ca_or_CA, value, operator_idx)`**: Emitted for ca, CA operator
   - **`OverprintModeChanged(mode, operator_idx)`**: Emitted for OP, op, OPM
   - **`TransparencyGroupEntered(bbox, colorspace, knockout)`**: Emitted for gs operator with ExtGState transparency params
   - **`FormXObjectEntered(name, bounding_box, nested_depth)`**: Emitted when Do invokes a Form XObject
   - **`PathOperator(operator, operands, bbox)`**: Generic for m, l, c, h, n (newpath), f, F, f*, B, B*, S (stroke)
   - **`ClippingPathSet(bbox, rule_evenodd)`**: Emitted for W (clip), W* (clip with even-odd)

4. **Processing Model**:
   - **Streaming vs. Buffered**: Use streaming (process one operator at a time) for memory efficiency on large content streams
   - For deferred checks (e.g., "was text rendered over a transparent region?"), store minimal state in a `ContentStreamLog` object
   - Never buffer the entire content stream into memory

5. **Form XObject Recursion**:
   - Recursive descent when Do operator references a Form XObject
   - Multiply CTM through recursion: `CTM_child = CTM_parent × CTM_form_matrix`
   - Track recursion depth to detect infinite loops (limit to 32 levels)
   - Emit events with absolute (page-relative) coordinates

6. **Error Handling**:
   - Gracefully handle malformed content streams (missing operators, invalid operands)
   - Log warnings for unrecognized operators (user-defined operators)
   - Continue processing rather than halt on errors (detection-only philosophy)
   - Emit `ContentStreamParseWarning` events for anomalies

### Rationale

- **Correctness**: State machine approach matches PDF specification (ISO 32000)
- **Composability**: Analyzers subscribe to event types; new rules don't require interpreter changes
- **Performance**: Streaming processing uses O(depth) memory, not O(stream_size) memory
- **Debuggability**: Events are concrete, machine-readable; easy to log for inspection
- **Testability**: Mock events can be injected to test rules without parsing real PDFs

### Consequences

- **Positive**:
  - Clear boundary between "what happened" (events) and "is it correct?" (rules)
  - Analyzers are loosely coupled; add new event types without recompiling rules
  - State machine is testable; each operator type can be unit tested

- **Negative**:
  - Significant implementation effort (~80-120 hrs): proper CTM math, all operator types, edge cases
  - Risk of operator omissions or incorrect semantics on first pass; requires thorough testing against real-world PDFs
  - Event emission overhead adds ~5-10% latency to content stream processing

- **Trade-offs**:
  - Chose streaming over buffering: higher memory efficiency, slightly more complex state management
  - Chose semantic events over raw operators: rules are simpler and more readable
  - Chose recursive descent for Form XObjects over flattening: preserves structural information

### Alternatives Considered

1. **Regex parsing of content stream strings**: Fragile; doesn't handle operator variations or state dependencies
2. **Use higher-level PDF library (pdfplumber, pypdf)**: Abstracts away stream details we need for granular inspection
3. **Flatten entire PDF to single stream**: Loses structural information; difficult to map findings back to Form XObjects
4. **Parse operators on-demand (lazy)**: Adds complexity for deferred checks; streaming is simpler
5. **Use external C++ content stream parser**: Loss of Python control; harder to emit custom events

---

## ADR-003: Rule Engine and Profile Composition System

**Status:** Proposed

### Context

LintPDF must support diverse inspection scenarios:

- **Packaged profiles**: GWG guidelines (14 variants), PDF/A validation, CMYK color space enforcement
- **Tenant-specific rules**: An airline might require specific color validation (e.g., brand colors only)
- **Threshold-based rules**: "More than 50% of images must have alt text"
- **Conditional rules**: "If CMYK, check for overprint; if RGB, check for transparency"
- **Severity overrides**: A violation might be "no-fly" in one profile, "advisory" in another

A monolithic rule set is unmaintainable. We need a declarative system where rules are composable and profiles are explicitly defined.

### Decision

**Implement rules as pure Python functions; compose them into Profiles (Flight Plans) using a declarative JSON schema.**

1. **Rule Design**:
   - Each rule is a pure Python function: `rule(analyzer_output: AnalyzerOutput) -> List[Finding]`
   - Rules receive the output of a specific analyzer (e.g., `ContentStreamAnalyzer`, `ImageAnalyzer`, `ColorAnalyzer`)
   - A rule returns zero or more `Finding` objects (or `[]` if no violations)
   - Rules are stateless and deterministic; no side effects
   - Rules declare their dependencies: `@rule(analyzer=ContentStreamAnalyzer, name="text_with_transparency")`

   Example:
   ```python
   @rule(analyzer=ContentStreamAnalyzer, name="text_with_transparency")
   def check_text_with_transparency(analyzer_output: ContentStreamAnalyzerOutput) -> List[Finding]:
       findings = []
       for text_event in analyzer_output.text_rendered_events:
           if text_event.opacity < 1.0 and text_event.background_has_transparency:
               findings.append(Finding(
                   inspection_id="text_with_transparency",
                   severity="delay",
                   message=f"Text rendered with opacity {text_event.opacity} over transparent background",
                   page_num=text_event.page_num,
                   bbox=text_event.bbox,
                   details={"opacity": text_event.opacity, "font": text_event.font_name}
               ))
       return findings
   ```

2. **Finding Data Model**:
   ```python
   class Finding:
       inspection_id: str              # e.g., "text_with_transparency"
       severity: Literal["no-fly", "delay", "advisory"]
       message: str                     # Human-readable description
       page_num: int                    # 1-indexed
       bbox: Optional[BoundingBox]      # (x0, y0, x1, y1) in page coordinates
       details: Dict[str, Any]          # Machine-readable context
       affected_object_id: Optional[str] # For Form XObjects, image XObjects, etc.
   ```

3. **Rule Registry** (`RuleRegistry` class):
   - Global registry mapping rule names to functions
   - Dynamically discover and register rules from a `rules/` package
   - Support for built-in rules (GWG, PDF/A) and custom tenant rules
   - Validation: ensure all rule dependencies are satisfied

4. **Profile Schema** (JSON):
   ```json
   {
     "id": "gwg-variant-4-cmyk",
     "name": "GWG Variant 4 (CMYK Color Space)",
     "description": "Print-ready CMYK documents with overprint support",
     "rules": [
       {
         "name": "text_with_transparency",
         "enabled": true,
         "severity_override": "no-fly"
       },
       {
         "name": "images_must_have_intent",
         "enabled": true,
         "threshold": 0.95,
         "severity_override": "delay"
       },
       {
         "name": "cmyk_color_space_required",
         "enabled": true
       }
     ],
     "metadata": {
       "tenant_id": null,
       "created_by": "system",
       "version": "1.0"
     }
   }
   ```

5. **Profile Composition**:
   - Profiles select a subset of rules
   - Severity overrides: a rule's default severity can be overridden per profile
   - Thresholds: rules with configurable parameters (e.g., "at least 95% of images")
   - Inheritance: profiles can extend base profiles (e.g., `gwg-variant-4` extends `gwg-base`)

6. **GWG Complexity Support**:
   - 14 GWG variants are defined by different color spaces (RGB, CMYK), bit depths, and transparency rules
   - Profiles for each variant: `gwg-variant-1-rgb`, `gwg-variant-2-rgb-trans`, ..., `gwg-variant-14-cmyk-spot`
   - Rules are reused across variants; profiles compose them differently

7. **Tenant-Specific Rules** (Airlines Livery):
   - Tenants can define custom rules via the Dashboard (Flight Deck)
   - Custom rules are stored in PostgreSQL as JSON + Python code
   - Dynamically loaded at profile selection time
   - Validation: custom rule code is sandboxed (no `import`, `eval`, etc.)

### Rationale

- **Maintainability**: Rules are short, focused, and testable in isolation
- **Composability**: Same rule set can be used across multiple profiles
- **Extensibility**: New rules and profiles don't require code changes; can be uploaded via API
- **Clarity**: Rule intent is explicit; no hidden behavior in profile composition
- **Portability**: Profiles are JSON; can be exported, versioned, and audited
- **Debugging**: Failed rules are traceable; each Finding includes its inspection_id

### Consequences

- **Positive**:
  - Rules are unit-testable without integration infrastructure
  - Profiles are version-controlled as JSON files
  - Tenants can experiment with custom rules without risk to core engine
  - Performance: rule execution is fast (linear in number of rules, not PDF size)

- **Negative**:
  - Rule dependency graph must be tracked; can become complex
  - Tenant custom rules require careful validation to prevent malicious code
  - Profile schema versioning (future-proofing) needed as rules evolve

- **Trade-offs**:
  - Chose pure functions over class-based rules: simpler testing, less boilerplate
  - Chose JSON profiles over Python configs: more flexible for tenant customization, requires parsing layer

### Alternatives Considered

1. **Monolithic rule set in code**: Inflexible; every new rule requires code review and deployment
2. **Rule DSL (domain-specific language)**: Overkill complexity; Python functions are already Turing-complete
3. **Prolog/constraint-solving approach**: Overkill; most rules are simple checks, not complex logic
4. **Inherit rules from base profiles in code**: Profiles become code artifacts; harder to audit and version
5. **All rules enabled always**: No way to support different inspection scenarios or tenant needs

---

## ADR-004: Asynchronous API Design and Job Processing Model

**Status:** Proposed

### Context

PDF processing is latency-sensitive. A 500MB file can take 10-30 seconds to parse and inspect. Synchronous API calls would timeout. We need to:

- Accept file uploads immediately without blocking
- Return a job ID quickly
- Process in the background
- Allow clients to poll or receive webhooks
- Handle rate limiting and quota enforcement
- Track processing progress through the system

A traditional request-response model is inappropriate; we need job queue semantics.

### Decision

**Implement async processing with a Celery task queue, Redis broker, and webhook callback support. Expose three main endpoints.**

1. **API Endpoints**:

   **POST /api/v1/check-in** (File Upload and Inspection Request):
   ```
   Request:
   - Content-Type: multipart/form-data
   - Files: pdf_file (binary, 1-500MB limit)
   - Form fields:
     - profile_id (required): e.g., "gwg-variant-4-cmyk"
     - webhook_url (optional): POST callback URL when done
     - metadata (optional): JSON string of custom context (airline ID, flight number, etc.)

   Response (HTTP 202 Accepted):
   {
     "job_id": "flight-log-uuid",
     "status": "queued",
     "message": "Your preflight check has been submitted for processing",
     "polling_url": "/api/v1/flight-log/flight-log-uuid",
     "estimated_wait_seconds": 45
   }
   ```

   **GET /api/v1/flight-log/{id}** (Poll Results):
   ```
   Response:
   - status: "queued" | "taxiing" | "arrived"
   - If "queued"/"taxiing":
     {
       "job_id": "...",
       "status": "taxiing",
       "progress_percent": 45,
       "findings": null,
       "report_url": null
     }
   - If "arrived":
     {
       "job_id": "...",
       "status": "arrived",
       "findings": [...],
       "summary": {
         "total_findings": 12,
         "no_fly": 2,
         "delay": 5,
         "advisory": 5
       },
       "report_url": "https://r2-bucket.cloudflare.com/reports/...",
       "processing_time_seconds": 23,
       "completed_at": "2026-03-11T14:32:10Z"
     }
   ```

   **PUT /api/v1/livery/{tenant_id}** (Tenant Branding / Flight Plan Management):
   ```
   Request:
   {
     "logo_url": "https://cdn.airline.com/logo.png",
     "primary_color": "#0033CC",
     "secondary_color": "#FFAA00",
     "company_name": "SkyFly Airlines",
     "contact_email": "safety@skyfly.com"
   }

   Response:
   {
     "tenant_id": "airline-123",
     "livery_id": "livery-v2",
     "updated_at": "2026-03-11T14:30:00Z"
   }
   ```

2. **Authentication and Authorization**:
   - **Boarding Pass** (API Key): Header `Authorization: Bearer sk_live_XxYyZz...`
   - Keys issued per tenant (airline) in the Flight Deck dashboard
   - Rate limiting: 100 requests/minute, 1000 requests/day (configurable per tier)
   - Quota management: 10GB upload/month (Free tier), unlimited (Premium)
   - Tenant scoping: API key grants access only to that tenant's jobs, profiles, and Livery

3. **Async Processing Pipeline**:
   ```
   1. POST /check-in
      ↓
   2. FastAPI validates upload, stores file to R2, creates Job record
      ↓
   3. Enqueue Celery task: `process_pdf_inspection(job_id)`
      ↓
   4. Return 202 with job_id immediately
      ↓
   5. Celery worker picks up task from Redis queue
      ↓
   6. Worker: Load PDF, run analyzers, apply profile rules, generate findings
      ↓
   7. Worker: Generate PDF report (WeasyPrint), store to R2
      ↓
   8. Worker: Update Job record with findings, report_url, status="arrived"
      ↓
   9. If webhook_url provided, POST findings to webhook
      ↓
   10. Client polls GET /flight-log/{id} or receives webhook callback
   ```

4. **Celery Task Definition**:
   ```python
   @celery_app.task(bind=True, max_retries=3, time_limit=300)
   def process_pdf_inspection(self, job_id: str) -> dict:
       """
       Main inspection task. Handles retries and timeouts.

       Returns: {
           "job_id": str,
           "findings": List[Finding],
           "report_url": str,
           "duration_seconds": float
       }
       """
       try:
           # Load job, PDF from R2
           job = JobRepository.get(job_id)
           pdf_bytes = r2_client.get(job.pdf_key)

           # Run inspection pipeline
           findings = run_inspection_pipeline(pdf_bytes, job.profile_id, job.tenant_id)

           # Generate report
           report_bytes = generate_flight_log_report(job, findings)
           report_url = r2_client.put(report_key, report_bytes)

           # Store results
           job.findings = findings
           job.report_url = report_url
           job.status = "arrived"
           JobRepository.update(job)

           # Send webhook (if configured)
           if job.webhook_url:
               send_webhook(job.webhook_url, {"job_id": job_id, "findings": findings})

           return {"job_id": job_id, "findings": findings, "report_url": report_url}

       except PDFParseError as e:
           # Unrecoverable: mark job as failed
           job.status = "grounded"
           job.error = f"PDF parse error: {e}"
           JobRepository.update(job)
           raise
       except Exception as e:
           # Retry on transient errors
           retry_count = self.request.retries
           if retry_count < 3:
               raise self.retry(exc=e, countdown=10 * (2 ** retry_count))
           else:
               job.status = "grounded"
               job.error = f"Processing failed after 3 retries: {e}"
               JobRepository.update(job)
               raise
   ```

5. **Job Status Lifecycle**:
   - **queued**: Job created, file stored, waiting for worker
   - **taxiing**: Worker has claimed task, inspection in progress
   - **arrived**: Processing complete, findings stored, report ready
   - **grounded**: Error during processing (parse error, timeout, etc.)

6. **Webhooks ("Radio")**:
   - Optional callback URL at check-in time
   - POST to webhook when job arrives with: `{"job_id": "...", "findings": [...], "status": "arrived"}`
   - Retry strategy: exponential backoff (5s, 10s, 20s, 40s), give up after 5 attempts
   - HMAC-SHA256 signature in `X-Grounded-Signature` header for webhook verification
   - Idempotent: if webhook fires twice, client sees same job_id

7. **Rate Limiting**:
   - Per-tenant rate limit middleware on FastAPI: tracks requests in Redis
   - Limits: 100 requests/minute (per-tenant), 1000/day
   - Premium tier: 500 requests/minute, unlimited/day
   - Queued files count against rate limit to prevent abuse
   - Return HTTP 429 when exceeded

8. **Error Handling**:
   - HTTP 400: Validation error (invalid profile_id, missing file, file too large)
   - HTTP 401: Missing/invalid API key
   - HTTP 403: Tenant not authorized for this resource
   - HTTP 404: Job not found
   - HTTP 409: Duplicate file submission (within 1 hour window)
   - HTTP 429: Rate limit exceeded
   - HTTP 500: Internal server error (worker crashed)

### Rationale

- **User Experience**: Clients get immediate response; no long-lived HTTP connections
- **Scalability**: Decouples API from inspection workload; workers can scale independently
- **Resilience**: Celery retries handle transient failures; webhooks decouple from polling
- **Auditability**: Job history stored in PostgreSQL; full traceability
- **Flexibility**: Polling and webhooks both supported; clients choose based on architecture

### Consequences

- **Positive**:
  - API remains responsive even under heavy inspection load
  - Inspection latency doesn't impact API SLA
  - Clients can batch multiple check-ins and process results asynchronously
  - Webhooks enable real-time event-driven workflows

- **Negative**:
  - Infrastructure complexity: FastAPI + Celery + Redis + PostgreSQL must all run
  - Debugging distributed failures is harder than synchronous code
  - Webhook delivery can fail; clients must implement retry logic on their side
  - Eventual consistency: between job enqueue and worker pickup, 1-10s delay

- **Trade-offs**:
  - Chose Celery over: custom queue (reinventing the wheel), SQS/SNS (AWS lock-in), Temporal/Airflow (overkill for simple task flow)
  - Chose Redis broker over: RabbitMQ (simpler setup, already required for caching), PostgreSQL backend (slower, not designed for message queues)
  - Chose 202 Accepted over 200 OK: correctly represents async processing semantics

### Alternatives Considered

1. **Synchronous processing**: Request times out on large PDFs; poor UX
2. **WebSocket long-polling**: Unnecessary complexity for this use case; HTTP polling is sufficient
3. **Server-Sent Events (SSE)**: Streaming results, but adds complexity; polling is simpler
4. **AWS SQS + Lambda**: Cloud lock-in; Railway is cheaper and more flexible for our workload
5. **gRPC streaming**: Overkill; REST is sufficient and better for web clients

---

## ADR-005: White-Label Report Generation and Multi-Format Output

**Status:** Proposed

### Context

LintPDF must generate three outputs for each inspection:

1. **PDF Report** (Flight Log): White-labeled, printable, professional appearance
2. **JSON Output**: Machine-readable findings for programmatic clients
3. **XML Output**: Legacy system integration (some airlines use proprietary ESS)

The PDF must reflect each tenant's branding (Livery) without maintaining separate code branches. HTML→PDF generation is the standard approach in Python.

### Decision

**Use WeasyPrint (HTML→PDF renderer) with Jinja2 templates for PDF generation. Implement JSON and XML schemas for structured output.**

1. **PDF Report Generation Pipeline**:
   ```
   1. Fetch Job, Findings, Livery (tenant branding)
   2. Render Jinja2 HTML template with context data
   3. WeasyPrint renders HTML+CSS to PDF bytes
   4. Embed metadata (job_id, tenant, processed_at) as XMP
   5. Return PDF bytes to R2 storage
   ```

2. **Jinja2 HTML Template Structure** (`templates/flight-log.html.j2`):
   ```html
   <!DOCTYPE html>
   <html>
   <head>
       <meta charset="utf-8">
       <style>
           @page {
               size: letter;
               margin: 1in;
               @bottom-center {
                   content: "Page " counter(page) " of " counter(pages);
               }
           }
           body { font-family: Arial, sans-serif; }
           .header {
               display: flex;
               align-items: center;
               border-bottom: 3px solid {{ livery.primary_color }};
           }
           .logo { height: 60px; margin-right: 20px; }
           .company-name {
               font-size: 24px;
               color: {{ livery.primary_color }};
               font-weight: bold;
           }
           .status {
               font-size: 36px;
               padding: 10px 20px;
               border-radius: 8px;
           }
           .status.clear-to-fly {
               background: #00AA00;
               color: white;
           }
           .status.grounded {
               background: #CC0000;
               color: white;
           }
           .finding {
               margin: 10px 0;
               padding: 10px;
               border-left: 4px solid;
               page-break-inside: avoid;
           }
           .finding.no-fly { border-left-color: #CC0000; }
           .finding.delay { border-left-color: #FFAA00; }
           .finding.advisory { border-left-color: #0033CC; }
       </style>
   </head>
   <body>
       <div class="header">
           {% if livery.logo_url %}
               <img src="{{ livery.logo_url }}" class="logo" alt="Logo">
           {% endif %}
           <div>
               <div class="company-name">{{ livery.company_name }}</div>
               <div>Flight Deck Report</div>
           </div>
       </div>

       <section class="summary">
           <h1>Preflight Check Result</h1>
           <div class="status {% if summary.has_no_fly %}grounded{% else %}clear-to-fly{% endif %}">
               {% if summary.has_no_fly %}GROUNDED{% else %}CLEAR TO FLY{% endif %}
           </div>

           <table>
               <tr>
                   <td>Job ID:</td>
                   <td>{{ job_id }}</td>
               </tr>
               <tr>
                   <td>Processed At:</td>
                   <td>{{ processed_at | datetime }}</td>
               </tr>
               <tr>
                   <td>Total Findings:</td>
                   <td>{{ summary.total_findings }}</td>
               </tr>
           </table>

           <h3>Findings by Severity</h3>
           <table>
               <tr>
                   <td>🔴 No-Fly (Blockers):</td>
                   <td>{{ summary.no_fly_count }}</td>
               </tr>
               <tr>
                   <td>🟠 Delay (Warnings):</td>
                   <td>{{ summary.delay_count }}</td>
               </tr>
               <tr>
                   <td>🔵 Advisory (Info):</td>
                   <td>{{ summary.advisory_count }}</td>
               </tr>
           </table>
       </section>

       {% if findings %}
           <section class="findings">
               <h2>Detailed Findings</h2>

               {% set findings_by_page = findings | groupby('page_num') %}
               {% for page_num, page_findings in findings_by_page %}
                   <h3>Page {{ page_num }}</h3>
                   {% for finding in page_findings | sort(attribute='severity') %}
                       <div class="finding {{ finding.severity }}">
                           <strong>{{ finding.message }}</strong>
                           <p><em>{{ finding.inspection_id }}</em></p>
                           {% if finding.bbox %}
                               <p>Location: x={{ finding.bbox.x0 }}, y={{ finding.bbox.y0 }}</p>
                           {% endif %}
                           {% if finding.details %}
                               <details>
                                   <summary>Technical Details</summary>
                                   <pre>{{ finding.details | json }}</pre>
                               </details>
                           {% endif %}
                       </div>
                   {% endfor %}
               {% endfor %}
           </section>
       {% else %}
           <section class="findings">
               <h2>Detailed Findings</h2>
               <p>No findings detected. This PDF passed all inspections.</p>
           </section>
       {% endif %}

       <footer style="margin-top: 2in; border-top: 1px solid #ccc; padding-top: 10px; font-size: 10px; color: #666;">
           <p>Generated by Grounded Preflight Engine | {{ livery.contact_email }}</p>
           <p>This report is confidential and intended for {{ livery.company_name }} only.</p>
       </footer>
   </body>
   </html>
   ```

3. **Livery (Tenant Branding) Model**:
   ```python
   class Livery:
       tenant_id: str
       logo_url: Optional[str]           # HTTPS only, CDN-hosted
       primary_color: str                # Hex color #RRGGBB
       secondary_color: str              # Hex color #RRGGBB
       company_name: str                 # "SkyFly Airlines"
       contact_email: str                # safety@skyfly.com
       contact_phone: Optional[str]      # +1-800-SKYFLY
       created_at: datetime
       updated_at: datetime
   ```

4. **PDF Generation Implementation**:
   ```python
   def generate_flight_log_pdf(job: Job, findings: List[Finding],
                               livery: Livery) -> bytes:
       """Generate white-labeled Flight Log PDF report."""

       # Prepare context for template
       context = {
           "job_id": job.id,
           "processed_at": job.completed_at,
           "livery": livery,
           "findings": findings,
           "summary": {
               "total_findings": len(findings),
               "no_fly_count": sum(1 for f in findings if f.severity == "no-fly"),
               "delay_count": sum(1 for f in findings if f.severity == "delay"),
               "advisory_count": sum(1 for f in findings if f.severity == "advisory"),
               "has_no_fly": any(f.severity == "no-fly" for f in findings)
           }
       }

       # Render template
       env = Environment(loader=FileSystemLoader('templates'))
       template = env.get_template('flight-log.html.j2')
       html_string = template.render(context)

       # Generate PDF with WeasyPrint
       pdf_bytes = HTML(string=html_string).write_pdf()

       # Embed metadata
       reader = PdfReader(BytesIO(pdf_bytes))
       writer = PdfWriter()

       for page in reader.pages:
           writer.add_page(page)

       writer.add_metadata({
           '/Title': f"Flight Log {job.id}",
           '/Author': 'Grounded Preflight Engine',
           '/Subject': f"Preflight inspection for {livery.company_name}",
           '/CreationDate': datetime.now(),
           '/Producer': 'Grounded v1.0'
       })

       output = BytesIO()
       writer.write(output)
       return output.getvalue()
   ```

5. **JSON Output Schema**:
   ```json
   {
     "job_id": "flight-log-uuid",
     "status": "arrived",
     "processed_at": "2026-03-11T14:32:10Z",
     "processing_time_seconds": 23,
     "pdf_file": {
       "filename": "sample.pdf",
       "size_bytes": 4752384,
       "page_count": 42,
       "pdf_version": "1.4"
     },
     "findings": [
       {
         "inspection_id": "text_with_transparency",
         "severity": "delay",
         "message": "Text rendered with opacity 0.75 over transparent background",
         "page_num": 5,
         "bbox": {
           "x0": 100.25,
           "y0": 400.50,
           "x1": 200.75,
           "y1": 420.00
         },
         "details": {
           "opacity": 0.75,
           "font": "Helvetica-Bold",
           "color": [0, 0, 0],
           "color_space": "DeviceRGB"
         },
         "affected_object_id": "Content Stream Page 5"
       }
     ],
     "summary": {
       "total_findings": 12,
       "by_severity": {
         "no_fly": 2,
         "delay": 5,
         "advisory": 5
       },
       "by_inspection": {
         "text_with_transparency": 3,
         "images_missing_intent": 2,
         "cmyk_color_space_required": 4,
         "overprint_not_enabled": 3
       }
     },
     "profile_used": {
       "id": "gwg-variant-4-cmyk",
       "name": "GWG Variant 4 (CMYK Color Space)",
       "version": "1.0"
     },
     "tenant": {
       "id": "airline-123",
       "name": "SkyFly Airlines"
     }
   }
   ```

6. **XML Output Schema**:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <FlightLog xmlns="https://grounded.aero/schema/v1">
     <Metadata>
       <JobID>flight-log-uuid</JobID>
       <ProcessedAt>2026-03-11T14:32:10Z</ProcessedAt>
       <ProcessingTimeSeconds>23</ProcessingTimeSeconds>
       <TenantName>SkyFly Airlines</TenantName>
       <ProfileID>gwg-variant-4-cmyk</ProfileID>
     </Metadata>
     <PDFFile>
       <Filename>sample.pdf</Filename>
       <SizeBytes>4752384</SizeBytes>
       <PageCount>42</PageCount>
       <PDFVersion>1.4</PDFVersion>
     </PDFFile>
     <Findings>
       <Finding>
         <InspectionID>text_with_transparency</InspectionID>
         <Severity>delay</Severity>
         <Message>Text rendered with opacity 0.75 over transparent background</Message>
         <PageNum>5</PageNum>
         <BoundingBox>
           <X0>100.25</X0>
           <Y0>400.50</Y0>
           <X1>200.75</X1>
           <Y1>420.00</Y1>
         </BoundingBox>
         <Details>
           <Opacity>0.75</Opacity>
           <Font>Helvetica-Bold</Font>
         </Details>
       </Finding>
     </Findings>
     <Summary>
       <TotalFindings>12</TotalFindings>
       <NoFlyCount>2</NoFlyCount>
       <DelayCount>5</DelayCount>
       <AdvisoryCount>5</AdvisoryCount>
     </Summary>
   </FlightLog>
   ```

7. **Output Format Negotiation**:
   - GET `/api/v1/flight-log/{id}` returns JSON by default
   - GET `/api/v1/flight-log/{id}?format=json` explicit JSON
   - GET `/api/v1/flight-log/{id}?format=xml` returns XML
   - GET `/api/v1/flight-log/{id}/report` returns PDF (white-labeled)
   - Content-Type headers set accordingly

### Rationale

- **Flexibility**: Clients choose format based on integration requirements
- **White-labeling**: Jinja2 templates allow per-tenant customization without code branches
- **Accessibility**: PDF is human-readable, JSON/XML are machine-readable
- **Professional**: WeasyPrint renders high-quality PDFs with proper pagination and styles
- **Auditability**: XML enables archival and compliance reporting

### Consequences

- **Positive**:
  - Single template source of truth; easier to maintain than three separate report generators
  - Image URLs in templates are external (CDN), reducing PDF size
  - PDF metadata enables document management system integration
  - JSON schema is discoverable via OpenAPI/Swagger

- **Negative**:
  - WeasyPrint adds ~100MB to Docker image (though acceptable for SaaS)
  - External image URLs require network calls during PDF generation (add caching if latency becomes issue)
  - PDF pagination can vary based on content length; large finding lists may span many pages

- **Trade-offs**:
  - Chose WeasyPrint over: ReportLab (more low-level, harder to customize), headless Chrome (heavier, overkill), plain text (unprofessional)
  - Chose Jinja2 over: Mako, Cheetah (lighter alternatives, but Jinja2 is ecosystem standard)
  - Chose single template over: multiple templates per tenant (less flexibility, but simpler management)

### Alternatives Considered

1. **Puppeteer/headless Chrome for PDF**: Better CSS support, but heavier (~500MB Docker layer)
2. **ReportLab**: More control over PDF structure, but verbose API; harder to maintain templates
3. **Pre-rendered templates per tenant**: Duplication; harder to update standard report format
4. **Cloud-based PDF service (e.g., AWS Lambda Layers)**: Lock-in; not worth cost for this workload
5. **Aspose.PDF (commercial)**: Licensing cost; not necessary for our needs

---

## ADR-006: Railway Deployment Architecture and Scaling Strategy

**Status:** Proposed

### Context

LintPDF must be deployed as a multi-service application on Railway. Service dependencies:

- **API service** (FastAPI): Stateless, horizontally scalable
- **Worker service** (Celery): Long-running, scales with queue depth
- **Redis** (message broker + cache): Stateful, single instance
- **PostgreSQL** (database): Stateful, single instance with backups
- **veraPDF sidecar**: PDF/A validation, runs as subprocess in worker or separate service
- **External**: Cloudflare R2 (file storage), SendGrid (webhooks resend), Datadog (monitoring)

Deployment must handle:

- Service discovery (internal networking)
- Secrets management (API keys, database credentials)
- Health checks and auto-restart
- Horizontal scaling (API + Workers)
- Data persistence and backups
- Cost optimization

### Decision

**Deploy as a Railway multi-service application with the following architecture:**

1. **Services Overview**:

   | Service | Type | Instances | Resources | Role |
   |---------|------|-----------|-----------|------|
   | `api` | FastAPI | 1-3 (auto-scale) | 512MB RAM, 0.5 CPU | HTTP requests, job submission |
   | `worker` | Celery | 1-5 (queue-driven scale) | 1GB RAM, 1 CPU | PDF inspection, async tasks |
   | `redis` | Redis 7 | 1 (persistent) | 1GB RAM, shared CPU | Message broker, caching |
   | `postgres` | PostgreSQL 15 | 1 + backups | 2GB RAM, 1 CPU | Job records, findings, profiles |
   | `verapdf` | Sidecar (worker) | Embedded | (worker resources) | PDF/A validation subprocess |

2. **Service Configuration** (railway.toml or Railway Dashboard):

   **API Service**:
   ```toml
   [services.api]
   build.dockerfile = "Dockerfile.api"
   port = 8000
   healthcheck = "/health"

   [services.api.deploy]
   startCommand = "uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4"
   numReplicas = 2  # Start with 2, auto-scale to 3 if CPU > 70%
   restartPolicy = "always"
   timeout = 120

   [services.api.env]
   ENVIRONMENT = "production"
   REDIS_URL = "${{ services.redis.internalUrl }}"
   DATABASE_URL = "${{ services.postgres.internalUrl }}/grounded"
   LOG_LEVEL = "info"
   ```

   **Worker Service**:
   ```toml
   [services.worker]
   build.dockerfile = "Dockerfile.worker"

   [services.worker.deploy]
   startCommand = "celery -A tasks worker --loglevel=info --concurrency=2"
   numReplicas = 1  # Start with 1, scale to 5 if queue depth > 100
   restartPolicy = "always"
   timeout = 300  # 5-minute timeout for long-running tasks

   [services.worker.env]
   CELERY_BROKER_URL = "${{ services.redis.internalUrl }}"
   DATABASE_URL = "${{ services.postgres.internalUrl }}/grounded"
   R2_BUCKET_NAME = "grounded-production"
   VERAPDF_PATH = "/opt/verapdf/verapdf"
   ```

   **Redis Service**:
   ```toml
   [services.redis]
   image = "redis:7-alpine"

   [services.redis.deploy]
   numReplicas = 1
   restartPolicy = "always"

   [services.redis.env]
   REDIS_PASSWORD = "${{ env.REDIS_PASSWORD }}"
   ```

   **PostgreSQL Service**:
   ```toml
   [services.postgres]
   image = "postgres:15-alpine"

   [services.postgres.deploy]
   numReplicas = 1
   restartPolicy = "always"
   backupFrequency = "daily"
   backupRetention = "7 days"

   [services.postgres.env]
   POSTGRES_PASSWORD = "${{ env.POSTGRES_PASSWORD }}"
   POSTGRES_DB = "grounded"
   ```

3. **Internal Networking**:
   - Railway provides automatic service-to-service networking over private network
   - Services access each other via: `http://service-name:port`
   - Example: API connects to Redis via `redis://redis:6379/0`
   - No need for explicit service discovery; Railway handles DNS

4. **Secrets and Environment Variables**:
   - Stored in Railway Dashboard (Project → Settings → Variables)
   - Injected at deploy time into containers
   - Never committed to Git
   - Rotation: update in Dashboard, redeploy services

   Required secrets:
   ```
   DATABASE_URL=postgresql://user:pass@postgres:5432/grounded
   REDIS_PASSWORD=<random>
   REDIS_URL=redis://:password@redis:6379/0

   API_KEYS_SIGNING_SECRET=<random-32-char>
   JWT_SECRET=<random-32-char>

   CLOUDFLARE_ACCOUNT_ID=<from Cloudflare>
   CLOUDFLARE_API_TOKEN=<from Cloudflare>
   R2_ACCESS_KEY_ID=<from Cloudflare>
   R2_SECRET_ACCESS_KEY=<from Cloudflare>

   SENDGRID_API_KEY=<from SendGrid>
   DATADOG_API_KEY=<from Datadog>

   ENVIRONMENT=production
   LOG_LEVEL=info
   ```

5. **Horizontal Scaling**:

   **API Autoscaling**:
   ```python
   # In Railway Dashboard: Services → api → Deploy settings
   # Autoscale rule: if CPU > 70% for 60s, add 1 replica (max 3)
   # if CPU < 30% for 120s, remove 1 replica (min 1)
   ```

   **Worker Scaling** (Manual for MVP, Automated later):
   ```
   # Queue depth monitoring via Celery event stream
   # Scale logic: if queue depth > 100, spin up additional worker
   # Implementation: Celery flower dashboard (optional) or custom scaling service
   ```

6. **Dockerfiles**:

   **Dockerfile.api** (FastAPI):
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app

   RUN apt-get update && apt-get install -y \
       build-essential \
       libpq-dev \
       && rm -rf /var/lib/apt/lists/*

   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY src/ .

   EXPOSE 8000
   HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
       CMD python -c "import requests; requests.get('http://localhost:8000/health')"

   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
   ```

   **Dockerfile.worker** (Celery + veraPDF):
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app

   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       build-essential \
       libpq-dev \
       openjdk-17-jre-headless \
       curl \
       && rm -rf /var/lib/apt/lists/*

   # Install veraPDF
   RUN mkdir -p /opt/verapdf && \
       cd /opt/verapdf && \
       curl -L https://verapdf.org/downloads/verapdf-installer-1.24.jar -o installer.jar && \
       java -jar installer.jar -auto && \
       rm installer.jar

   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY src/ .

   # Health check: verify worker is connected to Redis
   HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
       CMD python -c "from tasks import celery_app; celery_app.control.inspect().ping()"

   CMD ["celery", "-A", "tasks", "worker", "--loglevel=info"]
   ```

7. **Database Migrations**:
   - Alembic for schema management
   - Run migrations before deploying new API version
   - Railway deployment hooks: pre-deploy script runs migrations
   - Rollback plan: keep N previous migration versions, can revert if needed

   ```bash
   # Deploy pre-hook (run before new API version starts)
   alembic upgrade head
   ```

8. **Monitoring and Logging**:

   **Health Checks**:
   - API: `GET /health` returns `{"status": "ok", "version": "..."}` or 503
   - Worker: Celery ping via `celery_app.control.inspect().ping()`
   - Redis: Direct connection test
   - PostgreSQL: Query system tables

   **Logging**:
   - All services log to stdout (Railway collects via container logs)
   - Structured logging: JSON format with fields: `timestamp`, `level`, `service`, `job_id`, `message`
   - Datadog agent (sidecar) ingests logs for centralized visibility
   - Log retention: 7 days in Railway, unlimited in Datadog

   **Metrics**:
   - Datadog integration: collects CPU, memory, request latency, task queue depth
   - Key metrics to monitor:
     - API response time (p50, p99)
     - Worker task duration
     - Redis memory usage
     - PostgreSQL connection pool
     - Queue depth (number of pending Celery tasks)
   - Alerts: page on-call if queue depth > 500 or worker CPU > 90% for 5 min

9. **File Storage (Cloudflare R2)**:
   - R2 bucket: `grounded-production`
   - Storage structure:
     ```
     grounded-production/
       jobs/
         <job_id>/
           original.pdf
           report.pdf
       temp/
         <upload_session_id>/
           chunk_1
           chunk_2
     ```
   - R2 configuration: CORS enabled for dashboard downloads, lifecycle policy (delete temp files after 24h)
   - Cost: ~$0.015/GB stored, $0.01/M requests (negligible for typical volume)

10. **Cost Estimation** (Monthly):

    | Component | Instance | Cost |
    |-----------|----------|------|
    | API (2 replicas × 512MB) | Railway | $20 |
    | Worker (1 replica × 1GB) | Railway | $25 |
    | Redis (1GB, persistent) | Railway | $15 |
    | PostgreSQL (2GB, backup) | Railway | $50 |
    | R2 storage (100GB baseline) | Cloudflare | $1.50 |
    | R2 requests (10M) | Cloudflare | $0.10 |
    | Datadog monitoring (logs + metrics) | Datadog | $45 |
    | **Total** | | **~$157** |

    Notes:
    - API/Worker scale to 3/5 replicas under load; +$10-$30/month
    - Free tier: 1 API replica, 0 workers (customers run own local inspection)
    - Premium tier: 2 API, 2 workers, guaranteed SLA
    - Cost per inspection: ~$0.05-$0.10 (including infrastructure + storage)

11. **Deployment Pipeline**:

    ```
    1. Developer pushes to main branch
       ↓
    2. GitHub Actions CI runs:
       - Lint (Ruff, Mypy)
       - Unit tests (pytest)
       - Build Docker images
       - Push to Docker registry
       ↓
    3. Railway monitors Docker registry
       ↓
    4. On image update, Railway:
       - Runs database migrations (pre-deploy)
       - Scales down old replicas
       - Starts new containers with new image
       - Health checks (5-min grace period)
       - Gradual traffic shift (canary deploy)
       ↓
    5. If health check fails, automatic rollback to previous image
       ↓
    6. Monitor metrics for 10 minutes; alert on-call if issues
    ```

12. **Disaster Recovery**:

    **Backup Strategy**:
    - PostgreSQL: daily backups, 7-day retention (Railway managed)
    - Manual snapshot before major schema changes
    - Recovery time objective (RTO): 1 hour (restore from backup)
    - Recovery point objective (RPO): 24 hours (daily backups)

    **Failover Procedure**:
    - Database failure: Railway auto-fails over to backup (managed service)
    - Redis failure: rebuild from dump.rdb (minimal data loss)
    - Service crash: Railway auto-restarts container
    - Cascading failure (API + Worker + DB down):
      1. Check Railway dashboard for incident status
      2. Manually trigger rollback to previous deployment
      3. If rollback fails, restore PostgreSQL from backup + rebuild Redis

### Rationale

- **Simplicity**: Railway's multi-service model eliminates need for Kubernetes knowledge
- **Scalability**: Auto-scaling API based on CPU metrics; workers scale manually (can be automated later)
- **Cost-effective**: Shared infrastructure cheaper than AWS Lambda + RDS; predictable monthly cost
- **Reliability**: Managed services (PostgreSQL, Redis) with automatic backups and failover
- **Auditability**: All deployments tracked; easy to revert to previous versions
- **Security**: Secrets managed by Railway; no credentials in code or Docker images

### Consequences

- **Positive**:
  - Low operational burden; Railway handles most DevOps tasks
  - Fast deployment cycles (minutes, not hours)
  - Clear billing model; no surprise costs
  - Excellent for SaaS growth trajectory (easy to scale horizontally)

- **Negative**:
  - Vendor lock-in (Railway-specific configuration)
  - Limited customization compared to Kubernetes (e.g., can't tune Kubelet parameters)
  - Smaller ecosystem than AWS (fewer integrations)
  - Single-region deployment; no multi-region failover out-of-box

- **Trade-offs**:
  - Chose Railway over: AWS (overcomplicated, higher cost), Heroku (expensive, limited scaling), Fly.io (good alternative, but Railway is simpler)
  - Chose managed services over: self-hosted (more control, much more operational work)
  - Chose Datadog for monitoring over: open-source stack (Prometheus + Grafana is cheaper but requires management)

### Alternatives Considered

1. **Kubernetes (EKS, GKE)**: Overkill for MVP; 6-month learning curve; operational overhead
2. **AWS (Lambda + SQS + RDS)**: Good for serverless, but higher cost; vendor lock-in to AWS
3. **Heroku**: Simple, but more expensive; limited auto-scaling; being phased out
4. **Fly.io**: Excellent alternative; similar to Railway but different pricing model
5. **Docker Compose + VPS**: Cheaper, but all operational burden on us; not suitable for SaaS
6. **Self-hosted (on-premises)**: Control, but requires infrastructure; not viable for distributed SaaS

---

## Summary and Cross-ADR Dependencies

The six ADRs form an integrated system:

```
ADR-001 (Parser)
    ↓
ADR-002 (Content Stream Interpreter)
    ↓ (emits semantic events)
ADR-003 (Rule Engine)
    ↓ (consumes events, produces findings)
ADR-004 (API Design)
    ↓ (orchestrates inspection pipeline)
ADR-005 (Report Generation)
    ↓ (formats findings for output)
ADR-006 (Deployment)
    ↓ (runs entire system)
```

**Key Integration Points**:

- **ADR-001 + ADR-002**: Parser adapter is invoked by Content Stream Interpreter to extract streams
- **ADR-002 + ADR-003**: Semantic events from interpreter are consumed by rule functions
- **ADR-003 + ADR-004**: Rule profiles are selected via API; findings are returned to client
- **ADR-004 + ADR-005**: Findings from inspection are formatted into PDF/JSON/XML reports
- **ADR-005 + ADR-006**: Report generation runs in Worker service; outputs stored on R2
- **ADR-006 + All**: Deployment architecture hosts all services; monitoring tracks system health

**Technology Stack Summary**:
- **Language**: Python 3.11
- **Web Framework**: FastAPI
- **Task Queue**: Celery + Redis
- **Database**: PostgreSQL
- **PDF Parsing**: pikepdf (QPDF)
- **Content Interpretation**: Custom state machine
- **Rule Engine**: Pure Python functions + JSON profiles
- **Report Generation**: Jinja2 + WeasyPrint
- **PDF/A Validation**: veraPDF (sidecar)
- **Hosting**: Railway
- **File Storage**: Cloudflare R2
- **Monitoring**: Datadog

These decisions establish a solid foundation for Phase 6 implementation and future scaling.
