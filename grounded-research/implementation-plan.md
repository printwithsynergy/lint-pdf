# Grounded Phase 8 Implementation Plan
## Comprehensive Engineering Playbook and Module Specifications

**Project:** Grounded — Detection-Only PDF Preflight Engine
**Date:** March 11, 2026
**Phase:** 8 (Implementation Planning)
**Timeline:** Spring 2026 (12 weeks estimated)

---

## Part 1: Module Dependency Graph and Build Sequence

### Architectural Layers

```
┌─────────────────────────────────────────────────────────────┐
│                   API Layer (FastAPI)                       │
│         APIService, TaskQueue, TenantManager, Radio          │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│              Rule Engine & Flight Plans                      │
│         RuleEngine, FlightPlanLoader, ProfileRegistry       │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│              Analysis Layer (Detection)                      │
│  FontAnalyzer, ImageAnalyzer, ColorAnalyzer, Transparency   │
│  TransparencyAnalyzer, OverprintAnalyzer, etc.              │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│          Semantic Interpretation Layer                       │
│  ContentStreamInterpreter, SemanticModel, GraphicsState     │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│           Parser Layer (Abstraction)                         │
│  ParserAdapter (interface), PikePDFAdapter (implementation) │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│              External Dependencies                           │
│  pikepdf (QPDF), veraPDF, PostgreSQL, Redis, Celery        │
└─────────────────────────────────────────────────────────────┘
```

### Build Sequence (Must-Build-Before Order)

1. **Parser Layer** (Week 1)
   - `ParserAdapter` (abstract interface)
   - `PikePDFAdapter` (pikepdf wrapper)
   - Unit tests: basic PDF structure extraction

2. **Semantic Layer** (Week 2)
   - `SemanticModel` classes (PdfDocument, PdfPage, PdfFont, etc.)
   - `GraphicsState` and state stack
   - `ContentStreamInterpreter` with operator parsing
   - Unit tests: state machine correctness

3. **Analysis Layer** (Weeks 3-4)
   - `FontAnalyzer`
   - `ImageAnalyzer` (with DPI calculation)
   - `ColorAnalyzer` (with TAC)
   - `TransparencyAnalyzer`, `OverprintAnalyzer`
   - `PDFXValidator`, `PDFAValidator`
   - Integration tests against test corpus

4. **Rule Engine** (Week 5)
   - `RuleRegistry`
   - `FlightPlanLoader` (JSON profile parsing)
   - Rule functions (20-30 built-in rules)
   - `ProfileRegistry`

5. **Output Generation** (Week 5-6)
   - `ReportGenerator` (WeasyPrint + Jinja2)
   - JSON schema generation
   - XML schema generation
   - White-label branding (Livery)

6. **API Layer** (Week 6-7)
   - `APIService` (FastAPI endpoints)
   - `TaskQueue` (Celery integration)
   - `TenantManager` (multi-tenancy)
   - `Radio` (webhook support)
   - Authentication and rate limiting

7. **Integration Testing** (Week 8-9)
   - End-to-end tests (upload → inspect → report)
   - Test corpus regression testing
   - Performance benchmarking

8. **Deployment** (Week 9-10)
   - Railway configuration
   - Docker image building
   - Database migrations
   - Health checks and monitoring

9. **Launch Preparation** (Week 10-12)
   - Documentation and tutorials
   - SDK generation
   - Public API testing
   - Marketing materials

---

## Part 2: Module Specifications (Detailed)

### Module 1: ParserAdapter (Abstract Interface)

**File:** `src/parser/adapter.py`

**Purpose:** Abstraction layer decoupling PDF parsing implementation from inspection logic

**Interface Definition:**

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class PdfStream:
    """Represents a PDF stream object"""
    dictionary: Dict[str, Any]      # /Type, /Length, /Filter, etc.
    data: bytes                      # Decompressed stream content
    is_compressed: bool
    compression_filter: Optional[str]

@dataclass
class PdfObject:
    """Represents any PDF object (dict, array, stream, etc.)"""
    object_number: int
    generation_number: int
    is_indirect: bool
    value: Any                       # Actual object content
    type: str                        # 'dict', 'array', 'stream', 'name', etc.

class ParserAdapter(ABC):
    """Abstract base class for PDF parsers"""

    @abstractmethod
    def open(self, pdf_bytes: bytes) -> 'PdfDocument':
        """Load and parse PDF from bytes

        Raises:
            PDFStructureError: If PDF is malformed
            PDFParseError: If parsing fails
        """
        pass

    @abstractmethod
    def get_page(self, document: 'PdfDocument', page_num: int) -> 'PdfPage':
        """Retrieve specific page (1-indexed)"""
        pass

    @abstractmethod
    def get_catalog(self, document: 'PdfDocument') -> Dict[str, Any]:
        """Get document catalog (root object)"""
        pass

    @abstractmethod
    def get_content_stream(self, page: 'PdfPage') -> bytes:
        """Extract and decompress page content stream"""
        pass

    @abstractmethod
    def get_resources(self, page: 'PdfPage') -> Dict[str, Any]:
        """Get page resources (fonts, images, etc.)"""
        pass

    @abstractmethod
    def resolve_reference(self, document: 'PdfDocument', ref: str) -> PdfObject:
        """Resolve indirect reference (e.g., '5 0 R')"""
        pass

    @abstractmethod
    def get_page_tree(self, document: 'PdfDocument') -> Dict[str, Any]:
        """Get page tree root (/Pages object)"""
        pass

@dataclass
class PdfDocument:
    """Represents complete PDF document"""
    version: str                     # e.g., "1.7", "2.0"
    page_count: int
    is_encrypted: bool
    info_dict: Dict[str, Any]
    trailer: Dict[str, Any]
    _parser: ParserAdapter           # Reference to parser (for lazy access)

@dataclass
class PdfPage:
    """Represents single page"""
    page_num: int                    # 1-indexed
    page_dict: Dict[str, Any]        # /Type, /Parent, /MediaBox, etc.
    media_box: tuple                 # (x0, y0, x1, y1)
    crop_box: Optional[tuple]
    bleed_box: Optional[tuple]
    trim_box: Optional[tuple]
    art_box: Optional[tuple]
    rotate: int                      # 0, 90, 180, 270
    user_unit: float                 # Default 1.0
    _parser: ParserAdapter
```

**Implementation (PikePDFAdapter):**

```python
from pikepdf import Pdf, Object as PikepdfObject
from typing import Dict, Any

class PikePDFAdapter(ParserAdapter):
    """Concrete implementation using pikepdf (QPDF)"""

    def open(self, pdf_bytes: bytes) -> PdfDocument:
        """Parse PDF using pikepdf"""
        try:
            pdf = Pdf.open(io.BytesIO(pdf_bytes))
            version = f"{pdf.pdf_version}"
            page_count = len(pdf.pages)
            is_encrypted = pdf.is_encrypted
            trailer = dict(pdf.trailer)
            info_dict = dict(pdf.metadata) if pdf.metadata else {}

            return PdfDocument(
                version=version,
                page_count=page_count,
                is_encrypted=is_encrypted,
                info_dict=info_dict,
                trailer=trailer,
                _parser=self
            )
        except Exception as e:
            raise PDFStructureError(f"Failed to open PDF: {e}")

    def get_page(self, document: PdfDocument, page_num: int) -> PdfPage:
        """Extract page object and metadata"""
        # Implementation: use pikepdf to access page by index
        # Extract MediaBox, CropBox, TrimBox, BleedBox, ArtBox, Rotate, Resources
        # Return PdfPage with resolved boxes
        pass

    def get_content_stream(self, page: PdfPage) -> bytes:
        """Extract and decompress content stream"""
        # Implementation: access /Contents entry from page dict
        # Decompress using filters (/Filter entry)
        # Return raw bytes
        pass

    # ... other methods
```

**Inputs:**
- PDF file bytes (1-500MB)

**Outputs:**
- PdfDocument (normalized structure)
- PdfPage objects
- Raw content stream bytes
- Decompressed stream data

**Dependencies:**
- pikepdf library
- io module

**Tests:**
- Test on veraPDF corpus (100+ files)
- Test on known malformed PDFs (Isartor)
- Test on linearized, incremental update, object stream variants
- Benchmark: 100MB PDF parses in <3 seconds

**Complexity:** M (Medium)

---

### Module 2: SemanticModel

**File:** `src/semantic/model.py`

**Purpose:** Normalized representation of PDF document structure with inheritance and validation

**Key Classes:**

```python
@dataclass
class PdfBox:
    """Page box representation with validation"""
    x0: float
    y0: float
    x1: float
    y1: float

    def __post_init__(self):
        if self.x0 >= self.x1 or self.y0 >= self.y1:
            raise InvalidBoxError("Box coordinates must satisfy x0 < x1 and y0 < y1")

    def contains_point(self, x: float, y: float) -> bool:
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1

    def area(self) -> float:
        return (self.x1 - self.x0) * (self.y1 - self.y0)

@dataclass
class PdfFont:
    """Font object with embedding and encoding information"""
    name: str                        # e.g., "Helvetica", "ABCDEF+TimesRoman"
    type: str                        # Type1, TrueType, Type0, Type3, etc.
    base_font: str
    embedded: bool
    subset: bool
    encoding: str                    # WinAnsiEncoding, Identity-H, etc.
    font_descriptor: Optional[Dict]  # FontDescriptor dict
    font_file_stream: Optional[bytes]  # Embedded font program
    to_unicode_map: Optional[str]    # ToUnicode CMap

    def is_standard_14(self) -> bool:
        """Check if font is one of PDF's standard 14 fonts"""
        standard_14 = [
            "Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic",
            "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique",
            "Courier", "Courier-Bold", "Courier-Oblique", "Courier-BoldOblique",
            "Symbol", "ZapfDingbats"
        ]
        return self.base_font in standard_14 or self.name in standard_14

@dataclass
class PdfColorSpace:
    """Color space definition"""
    type: str                        # DeviceRGB, DeviceCMYK, etc.
    components: int                  # 1 (Gray), 3 (RGB/Lab), 4 (CMYK), etc.
    icc_profile: Optional[bytes]     # ICC profile if ICCBased
    alternate_colorspace: Optional['PdfColorSpace']

@dataclass
class PdfImage:
    """Image XObject with properties"""
    name: str                        # XObject name or "inline_image_page_X"
    width: int                       # pixels
    height: int                      # pixels
    bits_per_component: int
    color_space: PdfColorSpace
    filters: List[str]               # ['/FlateDecode', '/ASCII85Decode']
    decode_params: Optional[List[Dict]]
    has_soft_mask: bool
    has_hard_mask: bool
    interpolate: bool                # /Interpolate flag
    intent: Optional[str]            # Rendering intent
    inline: bool                     # Inline image vs. XObject
    page_num: int
    bbox: Optional[PdfBox]           # Bounding box in page coordinates

@dataclass
class PdfPage:
    """Complete page representation with inheritance resolved"""
    page_num: int                    # 1-indexed
    media_box: PdfBox                # Required
    crop_box: Optional[PdfBox]       # Defaults to MediaBox
    bleed_box: Optional[PdfBox]      # Defaults to CropBox
    trim_box: Optional[PdfBox]       # Defaults to CropBox
    art_box: Optional[PdfBox]        # Defaults to CropBox
    rotate: int                      # 0, 90, 180, 270
    user_unit: float                 # Default 1.0

    fonts: Dict[str, PdfFont]        # Font name → PdfFont
    images: List[PdfImage]           # All images on page
    color_spaces: Dict[str, PdfColorSpace]  # Color space definitions

    contents_stream: bytes           # Decompressed content stream
    resources_dict: Dict             # Raw /Resources

    @property
    def effective_width(self) -> float:
        """Effective page width in points, accounting for rotation"""
        box = self.crop_box or self.media_box
        if self.rotate in [90, 270]:
            return box.y1 - box.y0
        return box.x1 - box.x0

    @property
    def effective_height(self) -> float:
        """Effective page height in points, accounting for rotation"""
        box = self.crop_box or self.media_box
        if self.rotate in [90, 270]:
            return box.x1 - box.x0
        return box.y1 - box.y0

@dataclass
class PdfDocument:
    """Document-level properties"""
    version: str
    page_count: int
    is_encrypted: bool
    metadata: Dict                   # Title, Author, Subject, etc.
    output_intent: Optional[Dict]    # Output intent dictionary
    catalog: Dict                    # Raw catalog
    pages: List[PdfPage]             # All pages with resolved properties
```

**Key Methods:**

```python
class SemanticModel:
    """Builds semantic model from parsed PDF"""

    def __init__(self, parser_adapter: ParserAdapter):
        self.parser = parser_adapter

    def build(self, document: PdfDocument) -> PdfDocument:
        """Enrich parsed PDF with semantic information"""
        # 1. Resolve all page properties (inheritance, boxes, rotation, UserUnit)
        # 2. Extract and normalize fonts (embedding status, subsetting, encoding)
        # 3. Extract and normalize images
        # 4. Extract color spaces (Device, CIE, ICC, Indexed, Separation)
        # 5. Validate box hierarchy (MediaBox ≥ CropBox ≥ BleedBox ≥ TrimBox)
        # 6. Resolve resource inheritance
        # Return enriched PdfDocument
        pass

    def resolve_inheritance(self, page: PdfPage, parent_pages: List) -> Dict:
        """Walk page tree to resolve inherited properties"""
        # Inheritance applies to: /Resources, /MediaBox, /CropBox, /Rotate
        # Walk up page tree (/Parent chain) to find values
        # Return resolved dictionary
        pass
```

**Inputs:**
- Raw PdfDocument from ParserAdapter
- PDF structure from pikepdf

**Outputs:**
- Enriched PdfDocument with all properties resolved
- PdfPage objects with fonts, images, color spaces
- Validated boxes and dimensions

**Dependencies:**
- ParserAdapter interface
- dataclasses, typing

**Tests:**
- Test box inheritance (MediaBox from parent)
- Test resource inheritance (fonts from ancestors)
- Test box validation (lly < ury, etc.)
- Test image extraction

**Complexity:** L (Large)

---

### Module 3: ContentStreamInterpreter

**File:** `src/semantic/interpreter.py`

**Purpose:** State machine for PDF operators, tracking graphics state and emitting semantic events

**Core Classes:**

```python
from dataclasses import dataclass, field
from typing import List, Callable
from enum import Enum

@dataclass
class TransformationMatrix:
    """CTM representation with matrix operations"""
    a: float
    b: float
    c: float
    d: float
    e: float
    f: float

    def multiply(self, other: 'TransformationMatrix') -> 'TransformationMatrix':
        """Matrix multiplication: self × other

        [a  b  0]   [a' b' 0]   [a*a' + b*c'  a*b' + b*d'  0]
        [c  d  0] × [c' d' 0] = [c*a' + d*c'  c*b' + d*d'  0]
        [e  f  1]   [e' f' 1]   [e*a' + f*c' + e'  e*b' + f*d' + f'  1]
        """
        return TransformationMatrix(
            a=self.a * other.a + self.b * other.c,
            b=self.a * other.b + self.b * other.d,
            c=self.c * other.a + self.d * other.c,
            d=self.c * other.b + self.d * other.d,
            e=self.e * other.a + self.f * other.c + other.e,
            f=self.e * other.b + self.f * other.d + other.f
        )

    def extract_scale(self) -> tuple:
        """Extract scale factors from transformation matrix

        Returns: (sx, sy) where sx = sqrt(a^2 + c^2), sy = sqrt(b^2 + d^2)
        """
        import math
        sx = math.sqrt(self.a**2 + self.c**2)
        sy = math.sqrt(self.b**2 + self.d**2)
        return (sx, sy)

@dataclass
class GraphicsState:
    """Complete graphics state (q/Q stack frame)"""
    # Current Transformation Matrix
    ctm: TransformationMatrix = field(default_factory=lambda: TransformationMatrix(1, 0, 0, 1, 0, 0))

    # Color
    stroking_color_space: str = "DeviceGray"
    stroking_color: List[float] = field(default_factory=lambda: [0])
    non_stroking_color_space: str = "DeviceGray"
    non_stroking_color: List[float] = field(default_factory=lambda: [0])

    # Opacity and Blending
    stroking_alpha: float = 1.0      # CA
    non_stroking_alpha: float = 1.0  # ca
    blend_mode: str = "Normal"       # BM

    # Overprint
    overprint_stroking: bool = False # OP
    overprint_non_stroking: bool = False # op
    overprint_mode: int = 0          # OPM

    # Clipping
    clipping_path: Optional['ClippingPath'] = None

    # Text
    font_name: Optional[str] = None
    font_size: float = 0.0
    text_matrix: TransformationMatrix = field(default_factory=lambda: TransformationMatrix(1, 0, 0, 1, 0, 0))

    def copy(self) -> 'GraphicsState':
        """Create deep copy for stack push (q operator)"""
        # Implementation: copy all fields, deep-copy mutable ones
        pass

class ContentStreamEvent(ABC):
    """Base class for all semantic events"""
    operator: str
    page_num: int
    operator_index: int

@dataclass
class ImagePlacedEvent(ContentStreamEvent):
    """Emitted when image XObject is invoked (Do operator)"""
    image_name: str
    bbox: tuple                      # Bounding box in page coordinates
    ctm: TransformationMatrix
    display_width_points: float
    display_height_points: float

@dataclass
class TextRenderedEvent(ContentStreamEvent):
    """Emitted when text is shown (Tj, TJ, ', " operators)"""
    bbox: tuple
    font_name: str
    font_size: float
    opacity: float                   # ca value
    color: List[float]
    color_space: str

@dataclass
class ColorChangedEvent(ContentStreamEvent):
    """Emitted when color is set (sc, scn, SC, SCN, rg, RG, k, K)"""
    fill_or_stroke: str              # "fill" or "stroke"
    color_space: str
    color_values: List[float]

@dataclass
class OpacityChangedEvent(ContentStreamEvent):
    """Emitted when opacity is set (ca, CA operators via gs)"""
    fill_or_stroke: str
    opacity: float

@dataclass
class OverprintModeChangedEvent(ContentStreamEvent):
    """Emitted when overprint settings change (OP, op, OPM)"""
    mode: int

@dataclass
class TransparencyGroupEnteredEvent(ContentStreamEvent):
    """Emitted when ExtGState with transparency is applied (gs operator)"""
    fill_opacity: float
    stroke_opacity: float
    blend_mode: str
    knockout: bool

@dataclass
class FormXObjectEnteredEvent(ContentStreamEvent):
    """Emitted when Form XObject is invoked (Do)"""
    form_name: str
    matrix: TransformationMatrix
    nesting_depth: int

@dataclass
class PathPaintingEvent(ContentStreamEvent):
    """Emitted for path rendering (S, s, f, F, f*, B, B*, b, b*, n)"""
    operator: str
    bbox: Optional[tuple]
    fill: bool
    stroke: bool

@dataclass
class ClippingPathSetEvent(ContentStreamEvent):
    """Emitted when clipping path is set (W, W*)"""
    bbox: tuple
    even_odd_rule: bool

class ContentStreamInterpreter:
    """State machine interpreter for PDF content streams"""

    def __init__(self, page: PdfPage, resources: Dict):
        self.page = page
        self.resources = resources
        self.state_stack: List[GraphicsState] = [GraphicsState()]
        self.events: List[ContentStreamEvent] = []
        self.current_path: List[tuple] = []
        self.nesting_depth = 0

    def interpret(self) -> List[ContentStreamEvent]:
        """Parse and interpret content stream

        Returns: List of semantic events
        """
        # 1. Tokenize content stream bytes
        # 2. For each token sequence (operator + operands):
        #    a. Validate operand count
        #    b. Update graphics state
        #    c. Emit semantic event
        # 3. Validate state stack balance (q/Q matching)
        # 4. Return events
        pass

    def handle_q(self):
        """Save graphics state (q operator)"""
        current = self.state_stack[-1]
        self.state_stack.append(current.copy())

    def handle_Q(self):
        """Restore graphics state (Q operator)"""
        if len(self.state_stack) > 1:
            self.state_stack.pop()
        # Else: error - Q without matching q

    def handle_cm(self, a: float, b: float, c: float, d: float, e: float, f: float):
        """Modify CTM by concatenating transformation (cm operator)"""
        new_matrix = TransformationMatrix(a, b, c, d, e, f)
        current_ctm = self.state_stack[-1].ctm
        self.state_stack[-1].ctm = current_ctm.multiply(new_matrix)

    def handle_Do(self, xobject_name: str):
        """Invoke XObject (Do operator)"""
        # Look up XObject in /Resources
        # If Image: emit ImagePlacedEvent with current CTM
        # If Form: emit FormXObjectEnteredEvent, recursively interpret Form's stream
        pass

    def handle_Tf(self, font_name: str, font_size: float):
        """Set font and size (Tf operator)"""
        self.state_stack[-1].font_name = font_name
        self.state_stack[-1].font_size = font_size

    def handle_sc_colorspace_color(self, color_space: str, color_values: List[float]):
        """Set non-stroking color (sc, scn, rg, RG, k, K)"""
        self.state_stack[-1].non_stroking_color_space = color_space
        self.state_stack[-1].non_stroking_color = color_values
        self.events.append(ColorChangedEvent(
            operator="sc",
            page_num=self.page.page_num,
            operator_index=len(self.events),
            fill_or_stroke="fill",
            color_space=color_space,
            color_values=color_values
        ))

    def handle_BI_ID_EI(self, inline_image_dict: Dict):
        """Parse inline image (BI/ID/EI operators)"""
        # 1. Read /W, /H, /BPC from inline image dictionary
        # 2. Calculate expected data bytes
        # 3. Skip ID whitespace, read data, verify EI
        # 4. Emit ImagePlacedEvent
        pass

    # ... handlers for all critical operators
```

**Key Algorithms:**

#### Algorithm 1: Content Stream Tokenizer

PDF content streams use postfix notation: operands appear before operators. The tokenizer must handle all PDF token types per ISO 32000-2 §7.2.

**Token types:** integer, real, boolean, string (literal `(...)` and hex `<...>`), name (`/Name`), array (`[...]`), dictionary (`<< ... >>`), operator (keyword).

**Tokenizer state machine:**

```python
def tokenize(stream_bytes: bytes) -> List[Token]:
    """Tokenize PDF content stream into operand/operator pairs.

    PDF uses postfix notation: operands accumulate on a stack,
    then the operator consumes them.

    Yields (operator_name, operands_list) tuples.
    """
    tokens = []
    operand_stack = []
    i = 0

    while i < len(stream_bytes):
        byte = stream_bytes[i]

        # Skip whitespace (0x00, 0x09, 0x0A, 0x0D, 0x20)
        if byte in WHITESPACE:
            i += 1
            continue

        # Skip comments (% through end of line)
        if byte == 0x25:  # '%'
            while i < len(stream_bytes) and stream_bytes[i] not in (0x0A, 0x0D):
                i += 1
            continue

        # Literal string: (...)
        if byte == 0x28:  # '('
            value, i = read_literal_string(stream_bytes, i)
            operand_stack.append(Token('string', value))
            continue

        # Hex string: <...>
        if byte == 0x3C:  # '<'
            if i + 1 < len(stream_bytes) and stream_bytes[i + 1] == 0x3C:
                # Dictionary start <<
                operand_stack.append(Token('dict_start', '<<'))
                i += 2
                continue
            value, i = read_hex_string(stream_bytes, i)
            operand_stack.append(Token('hex_string', value))
            continue

        # Dictionary end >>
        if byte == 0x3E and i + 1 < len(stream_bytes) and stream_bytes[i + 1] == 0x3E:
            operand_stack.append(Token('dict_end', '>>'))
            i += 2
            continue

        # Array start/end
        if byte == 0x5B:  # '['
            operand_stack.append(Token('array_start', '['))
            i += 1
            continue
        if byte == 0x5D:  # ']'
            operand_stack.append(Token('array_end', ']'))
            i += 1
            continue

        # Name object: /Name
        if byte == 0x2F:  # '/'
            name, i = read_name(stream_bytes, i)
            operand_stack.append(Token('name', name))
            continue

        # Number (integer or real)
        if byte in NUMERIC_START:  # 0-9, +, -, .
            number, i = read_number(stream_bytes, i)
            operand_stack.append(Token('number', number))
            continue

        # Keyword (operator or boolean/null)
        if byte in ALPHA:
            keyword, i = read_keyword(stream_bytes, i)
            if keyword in ('true', 'false'):
                operand_stack.append(Token('boolean', keyword == 'true'))
            elif keyword == 'null':
                operand_stack.append(Token('null', None))
            elif keyword == 'BI':
                # Special: inline image — delegate to inline image parser
                inline_dict, image_data, i = parse_inline_image(stream_bytes, i)
                yield ('BI_ID_EI', operand_stack + [inline_dict, image_data])
                operand_stack = []
            else:
                # This is an operator — consume operand stack
                yield (keyword, operand_stack)
                operand_stack = []
            continue

        # Unknown byte — skip with warning
        i += 1
```

**Critical parsing helpers:**
- `read_literal_string`: Handle nested parentheses `(text (nested) more)` and escape sequences `\n \r \t \\ \( \) \ddd`
- `read_hex_string`: Handle `<48656C6C6F>`, ignore whitespace within hex
- `read_name`: Handle `#XX` hex escapes in name objects (e.g., `/Foo#20Bar`)
- `read_number`: Parse integers and reals, handle `+`, `-`, `.` prefixes

**pikepdf shortcut:** For MVP, use `pikepdf.parse_content_stream()` which returns a list of `(operands, operator)` tuples. This avoids writing a custom tokenizer entirely. The custom tokenizer is needed only if pikepdf doesn't handle a specific edge case.

```python
# MVP approach using pikepdf
import pikepdf

def tokenize_with_pikepdf(page: pikepdf.Page) -> List[Tuple[List, str]]:
    """Use pikepdf's built-in content stream parser."""
    instructions = pikepdf.parse_content_stream(page)
    # Returns List[Tuple[operands, operator]] where:
    #   operands = list of pikepdf objects (Name, String, Array, etc.)
    #   operator = pikepdf.Operator (has .operator attribute as bytes)
    return [(list(operands), str(op)) for operands, op in instructions]
```

---

#### Algorithm 2: Operator Priority Matrix

Operators categorized by implementation priority for LintPDF's detection use case:

**CRITICAL (Must implement for MVP — 18 operators):**

| Operator | Category | Purpose for Preflight |
|----------|----------|----------------------|
| `q` | Graphics state | Push state stack — required for CTM tracking |
| `Q` | Graphics state | Pop state stack |
| `cm` | Graphics state | Modify CTM — required for DPI calculation |
| `gs` | Graphics state | Set ExtGState (opacity, blend mode, overprint) |
| `Do` | XObject | Invoke image or Form XObject — triggers image/form analysis |
| `Tf` | Text | Set font — required for font detection |
| `Tj` | Text | Show string — triggers text analysis |
| `TJ` | Text | Show array of strings — triggers text analysis |
| `BT` | Text | Begin text object |
| `ET` | Text | End text object |
| `Tm` | Text | Set text matrix — affects effective font size |
| `sc`/`scn` | Color | Set non-stroking color |
| `SC`/`SCN` | Color | Set stroking color |
| `cs`/`CS` | Color | Set color space (non-stroking/stroking) |
| `rg`/`RG` | Color | Set RGB color (non-stroking/stroking) |
| `k`/`K` | Color | Set CMYK color (non-stroking/stroking) |
| `g`/`G` | Color | Set gray color (non-stroking/stroking) |
| `BI`/`ID`/`EI` | Inline image | Inline image — triggers image analysis |

**IMPORTANT (Implement for accuracy — 14 operators):**

| Operator | Category | Purpose |
|----------|----------|---------|
| `W`/`W*` | Clipping | Set clipping path (affects visibility detection for GWG D0030) |
| `m`/`l`/`c`/`v`/`y`/`h`/`re` | Path construction | Build paths — needed for path bounding box |
| `S`/`s`/`f`/`F`/`f*`/`B`/`B*`/`b`/`b*`/`n` | Path painting | Paint paths — triggers overprint/color analysis |
| `Td`/`TD` | Text positioning | Move text position |
| `T*` | Text positioning | Move to next line |
| `'`/`"` | Text showing | Show string with line advance |

**DEFERRABLE (Skip for MVP — ~60 operators):**

| Category | Operators | Why Deferrable |
|----------|-----------|---------------|
| Line style | `w`, `J`, `j`, `M`, `d`, `i` | Line width (`w`) needed for GWG R0010 thin line check — promote to IMPORTANT if implementing GWG |
| Rendering intent | `ri` | Rarely affects preflight detection |
| Flatness | `i` | No preflight relevance |
| Color rendering | `RI` | Minimal detection impact |
| Marked content | `BMC`, `BDC`, `EMC`, `MP`, `DP` | Relevant for PDF/UA only (defer to Phase 2) |
| Compatibility | `BX`, `EX` | Error recovery sections — log and skip |
| Type 3 font | `d0`, `d1` | Rare, defer |
| Shading | `sh` | Gradient fills — minimal preflight impact |

---

#### Algorithm 3: Inline Image Parsing (BI/ID/EI)

Inline images are notoriously difficult because the `EI` end marker can appear inside image data. The parsing approach:

```python
def parse_inline_image(stream_bytes: bytes, pos: int) -> Tuple[dict, bytes, int]:
    """Parse inline image starting after BI keyword.

    Structure: BI <key value pairs> ID <image data> EI
    Challenge: EI can appear inside image data bytes.

    Strategy: Calculate expected data length from image parameters,
    then verify EI marker at that position.
    """
    # 1. Parse image dictionary (key-value pairs until ID keyword)
    img_dict = {}
    while pos < len(stream_bytes):
        # Skip whitespace
        pos = skip_whitespace(stream_bytes, pos)

        # Check for ID keyword (marks start of data)
        if stream_bytes[pos:pos+2] == b'ID':
            pos += 2
            # ID must be followed by single whitespace byte
            if stream_bytes[pos] in WHITESPACE:
                pos += 1
            break

        # Read key (abbreviated name, e.g., /W, /H, /BPC, /CS, /F)
        key, pos = read_inline_image_key(stream_bytes, pos)
        # Read value
        value, pos = read_inline_image_value(stream_bytes, pos)
        img_dict[key] = value

    # 2. Calculate expected data length
    width = img_dict.get('W', img_dict.get('Width', 0))
    height = img_dict.get('H', img_dict.get('Height', 0))
    bpc = img_dict.get('BPC', img_dict.get('BitsPerComponent', 8))
    cs = img_dict.get('CS', img_dict.get('ColorSpace', 'DeviceGray'))
    components = COLOR_SPACE_COMPONENTS.get(cs, 1)
    is_mask = img_dict.get('IM', img_dict.get('ImageMask', False))
    filters = img_dict.get('F', img_dict.get('Filter', None))

    if is_mask:
        bpc = 1
        components = 1

    if filters is None:
        # Uncompressed: exact byte count calculable
        bits_per_row = width * components * bpc
        bytes_per_row = (bits_per_row + 7) // 8  # Ceiling division
        expected_length = bytes_per_row * height
        data = stream_bytes[pos:pos + expected_length]
        pos += expected_length
    else:
        # Compressed: scan for EI preceded by whitespace
        # Use heuristic: find b'\x20EI' or b'\x0AEI' or b'\x0DEI'
        # then verify the byte after EI is whitespace or EOF
        data_start = pos
        while pos < len(stream_bytes) - 2:
            if (stream_bytes[pos] in WHITESPACE and
                stream_bytes[pos+1:pos+3] == b'EI' and
                (pos + 3 >= len(stream_bytes) or
                 stream_bytes[pos+3] in WHITESPACE)):
                data = stream_bytes[data_start:pos]
                pos += 3  # Skip whitespace + EI
                break
            pos += 1

    # 3. Verify EI marker
    pos = skip_whitespace(stream_bytes, pos)

    return img_dict, data, pos

# Inline image abbreviation mappings
INLINE_ABBREV = {
    'BPC': 'BitsPerComponent', 'CS': 'ColorSpace',
    'D': 'Decode', 'DP': 'DecodeParms', 'F': 'Filter',
    'H': 'Height', 'IM': 'ImageMask', 'I': 'Interpolate',
    'W': 'Width',
    'G': 'DeviceGray', 'RGB': 'DeviceRGB',
    'CMYK': 'DeviceCMYK', 'I': 'Indexed',
    'AHx': 'ASCIIHexDecode', 'A85': 'ASCII85Decode',
    'LZW': 'LZWDecode', 'Fl': 'FlateDecode',
    'RL': 'RunLengthDecode', 'CCF': 'CCITTFaxDecode',
    'DCT': 'DCTDecode',
}

COLOR_SPACE_COMPONENTS = {
    'DeviceGray': 1, 'G': 1, 'DeviceRGB': 3, 'RGB': 3,
    'DeviceCMYK': 4, 'CMYK': 4, 'Indexed': 1, 'I': 1,
}
```

**pikepdf shortcut:** pikepdf's `parse_content_stream()` handles inline images automatically, returning them as `PdfInlineImage` objects with `.iimage` attribute containing the dictionary and data. For MVP, rely on pikepdf and only implement custom parsing if edge cases arise.

---

#### Algorithm 4: Form XObject Recursion with Cycle Detection

```python
def interpret_form_xobject(self, form_name: str, form_stream: PdfStream,
                           form_resources: Dict, form_matrix: TransformationMatrix,
                           visited: Set[str] = None):
    """Recursively interpret Form XObject content stream.

    Args:
        form_name: Resource name (e.g., '/Fm0')
        form_stream: Form XObject stream object
        form_resources: Form's own /Resources dict (falls back to page resources)
        form_matrix: Form's /Matrix entry (default identity)
        visited: Set of form object IDs for cycle detection
    """
    MAX_NESTING_DEPTH = 32

    if visited is None:
        visited = set()

    # Cycle detection: use object ID (obj_num, gen_num)
    form_id = f"{form_stream.object_number}_{form_stream.generation_number}"
    if form_id in visited:
        self.warnings.append(f"Circular Form XObject reference: {form_name}")
        return
    if self.nesting_depth >= MAX_NESTING_DEPTH:
        self.warnings.append(f"Max Form XObject nesting depth ({MAX_NESTING_DEPTH}) exceeded")
        return

    visited.add(form_id)
    self.nesting_depth += 1

    # Save and modify graphics state
    self.handle_q()  # Push state

    # Apply Form's Matrix to current CTM
    current_ctm = self.state_stack[-1].ctm
    self.state_stack[-1].ctm = current_ctm.multiply(form_matrix)

    # Emit event
    self.events.append(FormXObjectEnteredEvent(
        operator='Do', page_num=self.page.page_num,
        operator_index=len(self.events),
        form_name=form_name, matrix=form_matrix,
        nesting_depth=self.nesting_depth
    ))

    # Merge resources (form resources override page resources)
    merged_resources = {**self.resources, **form_resources}

    # Interpret form's content stream with merged resources
    saved_resources = self.resources
    self.resources = merged_resources
    self._interpret_stream(form_stream.data)
    self.resources = saved_resources

    # Restore state
    self.handle_Q()  # Pop state

    self.nesting_depth -= 1
    visited.discard(form_id)
```

---

#### Algorithm 5: Resource Inheritance Resolution

Page tree nodes can define Resources that are inherited by child pages. The algorithm walks from leaf page up to root, collecting inherited properties.

```python
INHERITABLE_PROPERTIES = {'Resources', 'MediaBox', 'CropBox', 'Rotate'}

def resolve_page_properties(page_dict: Dict, page_tree: Dict) -> Dict:
    """Resolve inherited properties by walking page tree ancestors.

    Per ISO 32000-2 §7.7.3.4: Resources, MediaBox, CropBox, and Rotate
    are inheritable. A page's effective value is the nearest ancestor's
    value, or the page's own value if defined.

    Pages override ancestors. MediaBox is required (must exist somewhere
    in the chain). Other properties have defaults if absent entirely.
    """
    resolved = dict(page_dict)  # Start with page's own properties
    current = page_dict

    while '/Parent' in current:
        parent = resolve_reference(current['/Parent'])

        for prop in INHERITABLE_PROPERTIES:
            key = f'/{prop}'
            if key not in resolved and key in parent:
                resolved[key] = parent[key]

        current = parent

    # Validate: MediaBox must be present after inheritance
    if '/MediaBox' not in resolved:
        raise InvalidPageError("No MediaBox found in page or ancestors")

    # Defaults for optional properties
    if '/CropBox' not in resolved:
        resolved['/CropBox'] = resolved['/MediaBox']  # CropBox defaults to MediaBox
    if '/Rotate' not in resolved:
        resolved['/Rotate'] = 0

    return resolved
```

---

**Inputs:**
- Page object with content stream bytes
- Resources dictionary (for font/image lookups)

**Outputs:**
- List of semantic events (ImagePlaced, TextRendered, ColorChanged, etc.)
- Validation warnings for state imbalances

**Dependencies:**
- SemanticModel classes
- pikepdf (for MVP tokenization via `parse_content_stream()`)
- dataclasses, typing

**Tests:**
- Test CTM matrix multiplication correctness (known matrices)
- Test state stack balance (q/Q pairing, unmatched Q recovery)
- Test inline image data size calculation (uncompressed and compressed)
- Test Form XObject recursion depth limit (32 levels)
- Test Form XObject cycle detection (circular references)
- Test operator dispatch for all 18 CRITICAL operators
- Test resource inheritance (3-level page tree, property at each level)
- Validate against 100+ test PDFs from veraPDF corpus
- Benchmark: 500-page PDF processes in < 10 seconds

**Complexity:** XL (Extra Large) — This is the most complex module

---

### Module 4: ImageAnalyzer

**File:** `src/analyzers/image.py`

**Purpose:** Detect and validate images with primary focus on effective DPI calculation

**Key Algorithm - Effective DPI Calculation:**

```python
import math
from dataclasses import dataclass

@dataclass
class ImageDPIResult:
    """Result of DPI calculation for single image"""
    page_num: int
    image_name: str
    width_pixels: int
    height_pixels: int

    # CTM components
    ctm_a: float
    ctm_b: float
    ctm_c: float
    ctm_d: float
    ctm_e: float
    ctm_f: float

    # Calculated display dimensions
    display_width_points: float
    display_height_points: float
    display_width_inches: float
    display_height_inches: float

    # Calculated DPI
    dpi_x: float
    dpi_y: float
    dpi_effective: float  # max(dpi_x, dpi_y)

    # Color space and compression
    color_space: str
    bits_per_component: int
    filters: List[str]

    # Status
    is_valid: bool
    issues: List[str]  # Low DPI, excessive resolution, etc.

class ImageAnalyzer:
    """Analyze all images on PDF pages"""

    def __init__(self, semantic_model: PdfDocument):
        self.document = semantic_model
        self.dpi_threshold_print = 150  # Configurable per profile
        self.dpi_threshold_web = 72

    def analyze_images(self) -> Dict[int, List[ImageDPIResult]]:
        """Analyze all images across all pages

        Returns: {page_num: [ImageDPIResult, ...]}
        """
        results = {}
        for page in self.document.pages:
            page_results = self.analyze_page_images(page)
            if page_results:
                results[page.page_num] = page_results
        return results

    def calculate_effective_dpi(self, image: PdfImage, ctm: TransformationMatrix) -> ImageDPIResult:
        """Calculate effective DPI for image given its CTM

        Algorithm:
        1. Extract image dimensions in pixels
        2. Extract CTM components [a, b, c, d, e, f]
        3. Calculate display size in points:
           - display_width = sqrt(a² + b²)
           - display_height = sqrt(c² + d²)
        4. Convert to inches (72 points/inch):
           - display_width_in = display_width / 72
           - display_height_in = display_height / 72
        5. Calculate DPI:
           - dpi_x = width_pixels / display_width_in
           - dpi_y = height_pixels / display_height_in
           - dpi_effective = max(dpi_x, dpi_y)
        """
        # Extract image dimensions
        width_px = image.width
        height_px = image.height

        # Extract CTM components
        a, b, c, d, e, f = ctm.a, ctm.b, ctm.c, ctm.d, ctm.e, ctm.f

        # Calculate display dimensions in points
        display_width_pts = math.sqrt(a**2 + b**2)
        display_height_pts = math.sqrt(c**2 + d**2)

        # Handle degenerate cases
        if display_width_pts == 0 or display_height_pts == 0:
            return ImageDPIResult(
                page_num=image.page_num,
                image_name=image.name,
                width_pixels=width_px,
                height_pixels=height_px,
                ctm_a=a, ctm_b=b, ctm_c=c, ctm_d=d, ctm_e=e, ctm_f=f,
                display_width_points=display_width_pts,
                display_height_points=display_height_pts,
                display_width_inches=0,
                display_height_inches=0,
                dpi_x=float('inf'),
                dpi_y=float('inf'),
                dpi_effective=float('inf'),
                color_space=image.color_space.type,
                bits_per_component=image.bits_per_component,
                filters=image.filters,
                is_valid=False,
                issues=["Degenerate transformation matrix (zero scale)"]
            )

        # Convert to inches (72 points/inch)
        display_width_in = display_width_pts / 72.0
        display_height_in = display_height_pts / 72.0

        # Calculate DPI
        dpi_x = width_px / display_width_in
        dpi_y = height_px / display_height_in
        dpi_effective = max(dpi_x, dpi_y)  # Conservative (worst-case)

        # Determine validity
        is_valid = dpi_effective >= self.dpi_threshold_print
        issues = []
        if dpi_effective < self.dpi_threshold_web:
            issues.append(f"Very low resolution ({dpi_effective:.1f} DPI)")
        elif dpi_effective < self.dpi_threshold_print:
            issues.append(f"Low resolution ({dpi_effective:.1f} DPI, recommended minimum {self.dpi_threshold_print} DPI)")

        if dpi_effective > 600:
            issues.append(f"Excessive resolution ({dpi_effective:.1f} DPI, consider downsampling)")

        return ImageDPIResult(
            page_num=image.page_num,
            image_name=image.name,
            width_pixels=width_px,
            height_pixels=height_px,
            ctm_a=a, ctm_b=b, ctm_c=c, ctm_d=d, ctm_e=e, ctm_f=f,
            display_width_points=display_width_pts,
            display_height_points=display_height_pts,
            display_width_inches=display_width_in,
            display_height_inches=display_height_in,
            dpi_x=dpi_x,
            dpi_y=dpi_y,
            dpi_effective=dpi_effective,
            color_space=image.color_space.type,
            bits_per_component=image.bits_per_component,
            filters=image.filters,
            is_valid=is_valid,
            issues=issues
        )

    def analyze_page_images(self, page: PdfPage) -> List[ImageDPIResult]:
        """Analyze all images on single page"""
        # From ContentStreamInterpreter events, extract all ImagePlaced events
        # For each event, look up image object and calculate DPI with event's CTM
        # Return list of ImageDPIResult
        pass

    def check_color_space_match(self, image: PdfImage, document_workflow: str) -> Optional[Finding]:
        """Validate image color space matches document workflow

        document_workflow: "RGB" | "CMYK" | "CMYK_with_spots"
        """
        # If workflow is CMYK and image is RGB → Warning
        # If workflow is RGB and image is CMYK → Warning
        # If image is Indexed → Check palette base color space
        pass

    def check_compression_efficiency(self, image: PdfImage) -> Optional[Finding]:
        """Validate image uses efficient compression"""
        # Flag ASCII85/ASCIIHex (no actual compression)
        # Flag missing compression on large images
        # Recommend FlateDecode for non-lossy
        pass
```

**Checks Generated:**
- GRD_IMG_001: Low resolution (< 150 DPI for print)
- GRD_IMG_002: Excessive resolution (> 600 DPI)
- GRD_IMG_003: Color space mismatch (RGB in CMYK workflow)
- GRD_IMG_004: Compression efficiency warning
- GRD_IMG_005: Inline image detected (informational)

**Inputs:**
- SemanticModel (pages with images)
- ContentStreamInterpreteroutput (image placement events with CTM)

**Outputs:**
- List of ImageDPIResult objects
- List of Finding objects (violations)

**Dependencies:**
- SemanticModel classes
- math module

**Tests:**
- Test DPI calculation with known matrices (scale, rotation, skew)
- Test nested Form XObject CTM multiplication
- Test against GWG test corpus (260 images at known DPIs)
- Benchmark: 1000 images analyzed in <1 second

**Complexity:** L (Large)

---

### Module 5: FontAnalyzer

**File:** `src/analyzers/font.py`

**Purpose:** Detect font issues (embedding, subsetting, encoding, metrics)

**10-Point Check List:**

1. **Font not embedded** (GRD_FONT_001)
   - Check FontDescriptor → FontFile/FontFile2/FontFile3
   - Exclude Standard 14 fonts
   - Exclude Type3 fonts (inline)

2. **Font subset detection** (GRD_FONT_002)
   - Check for 6-char uppercase prefix + "+"
   - Report if subsetting required full fonts

3. **Corrupt font program** (GRD_FONT_003)
   - Attempt to parse embedded font
   - Validate required tables/sections

4. **Missing glyph widths** (GRD_FONT_004)
   - Extract used glyph codes from content
   - Verify width entries exist

5. **Type3 fonts present** (GRD_FONT_005)
   - Flag as potential compatibility issue
   - Note: not allowed in PDF/A-1

6. **Font substitution risk** (GRD_FONT_006)
   - Standard 14 → Substitution risk (Helvetica→Arial)
   - MMType1 → Legacy unsupported

7. **CID font encoding issues** (GRD_FONT_007)
   - Type0 fonts: verify CIDSystemInfo consistency
   - Verify ToUnicode CMap present
   - Verify CIDToGIDMap (for Type2)

8. **Font metrics inconsistency** (GRD_FONT_008)
   - PDF widths vs. embedded font widths
   - Tolerance: 1/1000 unit

9. **Invalid encoding/ToUnicode** (GRD_FONT_009)
   - Check Differences array glyph names
   - Validate ToUnicode ranges
   - Check for invalid Unicode values

10. **Font licensing/embedding flags** (GRD_FONT_010)
    - Check fsType in font (may restrict embedding)
    - Informational only

```python
class FontAnalyzer:
    """Analyze fonts for embedding, encoding, and metrics issues"""

    def analyze_fonts(self, semantic_model: PdfDocument) -> Dict[str, List[Finding]]:
        """Analyze all fonts across document

        Returns: {font_name: [Finding, ...]}
        """
        findings_by_font = {}
        all_fonts = self.extract_all_fonts(semantic_model)

        for font_name, font in all_fonts.items():
            findings = []

            # Check 1: Font embedding
            if not self.is_font_embedded(font):
                findings.append(Finding(
                    inspection_id="GRD_FONT_001",
                    severity="error" if font.type != "Type3" else "info",
                    message=f"Font '{font_name}' is not embedded",
                    details={"font_name": font_name, "type": font.type}
                ))

            # Check 2: Subsetting
            if font.subset:
                findings.append(Finding(
                    inspection_id="GRD_FONT_002",
                    severity="warning",
                    message=f"Font '{font_name}' is subsetted; full embedding may be required",
                    details={"original_name": font.name[7:]}  # Strip XXXXXX+ prefix
                ))

            # Check 3-10: Additional checks...

            findings_by_font[font_name] = findings

        return findings_by_font

    def is_font_embedded(self, font: PdfFont) -> bool:
        """Determine if font is embedded

        Algorithm:
        1. If Type3: return True (always inline)
        2. If Standard 14: return False (never embedded)
        3. If no FontDescriptor: return False
        4. If FontDescriptor has FontFile/FontFile2/FontFile3: return True
        5. Else: return False
        """
        if font.type == "Type3":
            return True

        if font.is_standard_14():
            return False

        if font.font_descriptor is None:
            return False

        has_fontfile = (
            font.font_descriptor.get('FontFile') is not None or
            font.font_descriptor.get('FontFile2') is not None or
            font.font_descriptor.get('FontFile3') is not None
        )

        return has_fontfile

    def detect_subsetting(self, font_name: str) -> bool:
        """Detect if font is subsetted using 6-char prefix rule"""
        if len(font_name) < 8:
            return False

        if font_name[6] != '+':
            return False

        prefix = font_name[:6]
        return all(c.isupper() and c.isalpha() for c in prefix)

    def check_to_unicode(self, font: PdfFont) -> Optional[Finding]:
        """Validate ToUnicode CMap for Type0 fonts"""
        if font.type != "Type0":
            return None

        if font.to_unicode_map is None:
            return Finding(
                inspection_id="GRD_FONT_004",
                severity="error",
                message=f"Type0 font '{font.name}' missing ToUnicode CMap",
                details={"font_type": "Type0"}
            )

        return None
```

**Inputs:**
- SemanticModel (fonts from pages and resources)

**Outputs:**
- List of Finding objects (violations)

**Dependencies:**
- SemanticModel classes
- Font file parsers (fontTools library optional)

**Tests:**
- Test subsetting detection (6-char prefix rule)
- Test embedding detection for all font types
- Test Standard 14 font handling
- Test Type0 ToUnicode validation

**Complexity:** M (Medium)

---

### Module 6: ColorAnalyzer

**File:** `src/analyzers/color.py`

**Purpose:** Detect color space issues, spot colors, TAC violations

**Key Features:**

```python
class ColorAnalyzer:
    """Analyze color spaces and detect color-related violations"""

    def analyze_colors(self, semantic_model: PdfDocument, workflow_intent: str) -> List[Finding]:
        """Analyze all colors in document

        workflow_intent: "RGB" | "CMYK" | "CMYK_with_spots"
        """
        findings = []

        # Extract all unique color spaces from page content
        for page in semantic_model.pages:
            # 1. From content stream color change events
            # 2. From image color spaces
            # 3. From annotation colors

            # Check each color space
            for color_space in page.color_spaces.values():
                # RGB in CMYK workflow
                if workflow_intent.startswith("CMYK") and color_space.type == "DeviceRGB":
                    findings.append(Finding(
                        inspection_id="GRD_COLOR_001",
                        severity="warning",
                        page_num=page.page_num,
                        message="RGB color space found in CMYK workflow (requires conversion)",
                        details={"color_space": color_space.type}
                    ))

                # CMYK in RGB workflow
                if workflow_intent == "RGB" and color_space.type == "DeviceCMYK":
                    findings.append(Finding(
                        inspection_id="GRD_COLOR_002",
                        severity="warning",
                        page_num=page.page_num,
                        message="CMYK color space found in RGB workflow",
                        details={"color_space": color_space.type}
                    ))

                # ICC profile validation
                if color_space.type == "ICCBased" and color_space.icc_profile:
                    if not self.validate_icc_profile(color_space.icc_profile):
                        findings.append(Finding(
                            inspection_id="GRD_COLOR_003",
                            severity="warning",
                            page_num=page.page_num,
                            message="ICC profile is corrupt or invalid",
                            details={}
                        ))

        # TAC (Total Ink Coverage) Calculation
        tac_issues = self.calculate_tac(semantic_model)
        findings.extend(tac_issues)

        # Spot color detection
        spot_color_findings = self.detect_spot_colors(semantic_model)
        findings.extend(spot_color_findings)

        return findings

    def calculate_tac(self, semantic_model: PdfDocument) -> List[Finding]:
        """Calculate Total Ink Coverage (TAC) for all pages

        TAC = sum of all CMYK color components at any point on page
        Typical limits: 240% (conservative) to 320% (liberal)

        For each page:
        1. Extract all objects with CMYK colors or images
        2. Calculate cumulative ink coverage
        3. Flag if exceeds threshold
        """
        findings = []
        tac_threshold = 320  # Default conservative limit

        for page in semantic_model.page:
            # Extract CMYK colors from content stream events
            # Calculate cumulative TAC
            # If TAC > threshold, report
            pass

        return findings

    def detect_spot_colors(self, semantic_model: PdfDocument) -> List[Finding]:
        """Detect and report spot colors (Separation, DeviceN)"""
        findings = []

        for page in semantic_model.pages:
            for color_space in page.color_spaces.values():
                if color_space.type == "Separation":
                    # Extract spot color name and alternate CMYK
                    findings.append(Finding(
                        inspection_id="GRD_COLOR_SPT_001",
                        severity="info",
                        page_num=page.page_num,
                        message=f"Spot color detected: {color_space.name}",
                        details={"color_space": "Separation"}
                    ))

                elif color_space.type == "DeviceN":
                    findings.append(Finding(
                        inspection_id="GRD_COLOR_SPT_002",
                        severity="info",
                        page_num=page.page_num,
                        message=f"Multiple spot colors detected (DeviceN)",
                        details={"color_space": "DeviceN"}
                    ))

        return findings

    def validate_icc_profile(self, profile_bytes: bytes) -> bool:
        """Validate ICC profile structure"""
        # Check magic number, required tags, color space
        pass
```

**Checks Generated:**
- GRD_COLOR_001: RGB in CMYK workflow
- GRD_COLOR_002: CMYK in RGB workflow
- GRD_COLOR_003: Invalid ICC profile
- GRD_COLOR_SPT_001: Spot color detected
- GRD_COLOR_SPT_002: Multiple spot colors (DeviceN)
- GRD_COLOR_TAC_001: Total ink coverage exceeds threshold

**Inputs:**
- SemanticModel (color spaces, images)
- ContentStreamInterpreter output (color change events)
- Workflow intent (from profile)

**Outputs:**
- List of Finding objects

**Dependencies:**
- SemanticModel classes
- ICC profile parser (optional)

**Complexity:** M (Medium)

---

### Module 7-12: Additional Analyzers (Brief Specs)

Due to length constraints, following analyzers are specified briefly:

#### Module 7: TransparencyAnalyzer (GRD_TRANS_*)
- Detects opacity values (ca, CA < 1.0)
- Detects blend modes (BM != Normal)
- Detects soft masks (SMask)
- Validates PDF/X transparency compliance
- Inputs: ContentStreamInterpreter events, page dictionary
- Outputs: Transparency findings

#### Module 8: OverprintAnalyzer (GRD_OVERPRT_*)
- Detects overprint settings (OP, op, OPM)
- Flags white/light text with overprint (dangerous)
- Validates overprint + transparency interactions
- Inputs: ContentStreamInterpreter events, graphics state
- Outputs: Overprint findings

#### Module 9: PDFXValidator (GRD_COMP_PDF_X_*)
- PDF/X-1a, X-3, X-4 compliance checking
- Checks: CMYK-only, fonts embedded, output intent, no transparency (X-1a)
- Implements all 20+ PDF/X requirements from standard
- Inputs: SemanticModel, analyzer results
- Outputs: Compliance findings

#### Module 10: PDFAValidator (GRD_COMP_PDF_A_*)
- PDF/A-1, A-2, A-3 compliance
- Delegates complex checks to veraPDF integration
- Checks: fonts embedded, ToUnicode required, no transparency (A-1), XMP metadata
- Inputs: SemanticModel, veraPDF results
- Outputs: Compliance findings

#### Module 11: AccessibilityAnalyzer (GRD_ACCESS_*)
- PDF/UA accessibility compliance
- Checks: tagged structure, alt text on images, logical reading order
- Inputs: SemanticModel, content analysis
- Outputs: Accessibility findings

#### Module 12: RuleEngine & Report Generation

RuleEngine: Apply profile rules, aggregate findings by severity

ReportGenerator:
- JSON output (structured findings)
- XML output (legacy integration)
- PDF output (white-labeled Flight Log with Jinja2 + WeasyPrint)
- HTML email templates

---

## Part 3: Check Implementation Priority (MVP to Phase 3)

### MVP Phase (Weeks 1-8): Must-Have for Launch

**Font Checks (5 checks)**
- GRD_FONT_001: Font not embedded
- GRD_FONT_002: Font subset detection
- GRD_FONT_004: Type0 missing ToUnicode
- GRD_FONT_003: Corrupt font program (basic check)
- GRD_FONT_006: Font substitution risk (Standard 14)

**Image Checks (3 checks)**
- GRD_IMG_001: Low image DPI (< 150 print, < 72 web)
- GRD_IMG_003: Color space mismatch (RGB in CMYK)
- GRD_IMG_005: Inline image detection

**Color Checks (2 checks)**
- GRD_COLOR_001: RGB in CMYK workflow
- GRD_COLOR_SPT_001: Spot color detection (informational)

**Page/Structure Checks (3 checks)**
- GRD_BOX_001: MediaBox validation
- GRD_BOX_002: TrimBox/BleedBox missing
- GRD_STRUCT_001: Form fields detected

**Compliance Checks (4 checks)**
- GRD_COMP_PDF_X_001: Output intent missing
- GRD_COMP_PDF_X_002: CMYK color space validation (PDF/X)
- GRD_COMP_PDF_A_001: Font embedding (PDF/A)
- GRD_COMP_PDF_A_002: ToUnicode requirement (PDF/A)

**Rationale:** These 17 checks cover 80% of real-world print workflow issues. Font embedding, image DPI, and color validation are the top-3 requested features from competitive analysis.

---

### Phase 2 (Weeks 9-12): Growth Features

**Additional Font Checks (3)**
- GRD_FONT_005: Type3 fonts present
- GRD_FONT_008: Font metrics inconsistency
- GRD_FONT_009: Invalid encoding/ToUnicode

**Additional Image Checks (4)**
- GRD_IMG_002: Excessive resolution (> 600 DPI)
- GRD_IMG_004: Compression efficiency
- GRD_IMG_006: OPI reference detected
- GRD_IMG_007: Inline image problems

**Transparency/Overprint (4)**
- GRD_TRANS_001: Transparent object detected
- GRD_TRANS_PDF_X_001: Transparency in PDF/X-1a
- GRD_OVERPRT_001: White text overprint
- GRD_OVERPRT_002: Overprint mode validation

**Additional Color (3)**
- GRD_COLOR_002: CMYK in RGB workflow
- GRD_COLOR_003: Invalid ICC profile
- GRD_COLOR_TAC_001: Total ink coverage

**All PDF/X Variants (6)**
- GRD_COMP_PDF_X_003-006: X-1a, X-3, X-4 specific checks

**All PDF/A Variants (4)**
- GRD_COMP_PDF_A_003-006: A-1, A-2, A-3 specific checks

**Rationale:** Phase 2 adds comprehensive PDF/X-4 and PDF/A-2 support (most common in enterprise). Transparency and overprint checks enable print-safe validation.

---

### Phase 3 (Future): Differentiation Features

**Advanced Checks**
- GWG profile compliance (14 variants, each with specific rules)
- Barcode detection (computer vision)
- Advanced color profile analysis
- Digital signature validation
- Automated repair suggestions
- Custom tenant rules (JavaScript-based)

---

## Part 4: Risk Register with Mitigations

| Risk ID | Risk Description | Likelihood | Impact | Mitigation |
|---------|------------------|-----------|--------|-----------|
| R1 | CTM matrix multiplication errors | HIGH | CRITICAL | Unit tests with known matrices (identity, 90° rotation, scale); validate against 260 GWG files |
| R2 | Content stream operator omissions | MEDIUM | CRITICAL | Operator-by-operator testing; fallback to lenient parsing; test against 2000+ files |
| R3 | Malformed PDF handling | MEDIUM | HIGH | pikepdf error recovery; graceful degradation strategy; detailed error reporting |
| R4 | Performance on 100MB+ files | MEDIUM | HIGH | Streaming architecture; Celery worker benchmarking; profiling-guided optimization |
| R5 | veraPDF integration complexity | MEDIUM | MEDIUM | Wrap as subprocess; graceful fallback; document integration points |
| R6 | Whitespace/encoding edge cases | MEDIUM | MEDIUM | Comprehensive testing; multiple parsing strategies; detailed logging |
| R7 | Tenant custom rule code injection | LOW | CRITICAL | Sandbox custom rules; whitelist-only allowed functions; no eval/import |
| R8 | API rate limiting / DDoS | LOW | MEDIUM | Redis-based rate limiting; API key quotas; Cloudflare protection |
| R9 | Database scalability | LOW | MEDIUM | PostgreSQL indexing on job_id, tenant_id; archive old jobs; read replicas if needed |
| R10 | Worker queue backup | LOW | MEDIUM | Redis persistence; Celery result backend; dead letter queue for failed tasks |

---

## Part 5: MVP Definition

### What's Included in MVP (Launch at Week 8)

**Checks (17 total):**
- All 5 font checks
- All 3 image core checks
- All 2 color core checks
- All 3 page structure checks
- All 4 basic compliance checks

**Output Formats:**
- JSON (programmatic)
- PDF white-label report (Flight Log)

**API Endpoints:**
- POST /check-in (file upload)
- GET /flight-log/{id} (polling)
- No webhooks (Phase 2)

**Flight Plans:**
- Generic "All Checks" profile
- PDF/X-4 Basic profile
- PDF/A-2b Basic profile

**Authentication:**
- API key (Bearer token)
- Rate limiting: 100 req/min, 1GB/month

**Infrastructure:**
- 1 API instance, 1 Worker
- PostgreSQL + Redis
- Cloudflare R2 file storage
- Railway deployment

### What's Deferred to Phase 2+

- Webhooks (Radio)
- All PDF/X variants (14 GWG profiles)
- All PDF/A variants (A-1, A-3)
- Transparency and overprint checking
- TAC calculation
- Custom tenant rules
- XML output
- Barcode detection
- Accessibility (PDF/UA)

---

## Part 6: Pricing Tier Feature Mapping

| Feature | Free | Starter ($49) | Growth ($149) | Scale ($399) | Enterprise |
|---------|------|------------------|-------------|------------|-----------|
| **Checks** | 10 | 17 | 25 | All 40+ | All + custom |
| **Files/Month** | 50 | 500 | 5,000 | 25,000 | Custom |
| **Output Formats** | JSON | JSON, PDF | JSON, PDF, XML | All | All |
| **Flight Plans** | 2 (Generic, PDF/X-4) | 5 | 14 (GWG) | All | All + custom |
| **Webhooks (Radio)** | ✗ | ✗ | ✓ | ✓ | ✓ |
| **White-Label (Livery)** | ✗ | ✗ | ✗ | ✓ | ✓ |
| **API Rate Limit** | 100 req/min | 500 req/min | Unlimited | Unlimited | Custom SLA |
| **Storage** | 1GB | 10GB | 100GB | 1TB | Custom |
| **Support** | Docs | Email | Priority | Dedicated | Dedicated |

---

## Conclusion

This comprehensive implementation plan provides detailed specifications for all modules needed to build Grounded. The module dependency graph ensures correct build order, while the risk register identifies and mitigates technical challenges. The MVP definition focuses resources on 17 critical checks that address 80% of real-world use cases, enabling launch on schedule while deferring less critical features to Phase 2.

**Timeline:** 12 weeks (Spring 2026)
**Team Size:** 4 engineers (1 tech lead + 3 engineers) + 1 QA
**Critical Path:** Parser → Semantic Model → ContentStreamInterpreter → ImageAnalyzer (DPI calculation)

---

**Document Version:** 1.0 (Phase 8 Implementation Plan)
**Status:** Ready for Implementation
**Next Step:** Begin Phase 8 development in Sprint 1
