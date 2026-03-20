"""XMP metadata parser — extract PDF/X and Dublin Core properties.

Parses XMP (Extensible Metadata Platform) packets embedded in PDF files.
Uses defusedxml.ElementTree for safe XML parsing (prevents XXE attacks).

XMP is stored as an XML stream in the PDF's /Metadata entry. This parser
extracts the subset of properties needed for PDF/X-4 conformance validation
and metadata analysis.

Reference: ISO 16684-1 (XMP), ISO 15930-7:2010 (PDF/X-4 metadata requirements)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import defusedxml.ElementTree as ET  # noqa: N817

# XMP namespace URIs
_NS = {
    "x": "adobe:ns:meta/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "xmp": "http://ns.adobe.com/xap/1.0/",
    "xmpMM": "http://ns.adobe.com/xap/1.0/mm/",
    "pdf": "http://ns.adobe.com/pdf/1.3/",
    "pdfx": "http://ns.adobe.com/pdfx/1.3/",
    "pdfaid": "http://www.aiim.org/pdfa/ns/id/",
    "pdfxid": "http://www.npes.org/pdfx/ns/id/",
}


@dataclass(frozen=True)
class XmpMetadata:
    """Parsed XMP metadata properties relevant to preflight.

    Attributes:
        pdfx_version: GTS_PDFXVersion (e.g., "PDF/X-4").
        pdfx_conformance: GTS_PDFXConformance level.
        pdf_version: pdf:PDFVersion from XMP.
        creator_tool: xmp:CreatorTool.
        create_date: xmp:CreateDate (ISO 8601 string).
        modify_date: xmp:ModifyDate (ISO 8601 string).
        title: dc:title (first alt value).
        trapped: pdf:Trapped (True/False/Unknown).
        raw_properties: All extracted key-value pairs for custom checks.
    """

    pdfx_version: str = ""
    pdfx_conformance: str = ""
    pdf_version: str = ""
    creator_tool: str = ""
    create_date: str = ""
    modify_date: str = ""
    title: str = ""
    trapped: str = ""
    raw_properties: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_bytes(cls, data: bytes) -> XmpMetadata:
        """Parse XMP metadata from raw bytes.

        Args:
            data: Raw XMP packet bytes (typically UTF-8 XML).

        Returns:
            Populated XmpMetadata. Missing fields default to empty strings.
            Returns empty XmpMetadata if parsing fails.
        """
        if not data:
            return cls()

        try:
            # Strip null padding and BOM
            text = data.decode("utf-8", errors="replace").strip("\x00").strip()
            root = ET.fromstring(text)
        except ET.ParseError:
            return cls()

        raw: dict[str, str] = {}

        # Find all rdf:Description elements
        rdf_ns = _NS["rdf"]
        descriptions = root.findall(f".//{{{rdf_ns}}}Description")

        for desc in descriptions:
            # Extract attributes directly on Description elements
            for attr_name, attr_value in desc.attrib.items():
                _store_property(raw, attr_name, attr_value)

            # Extract child elements
            for child in desc:
                tag = child.tag
                text_val = _extract_text(child)
                if text_val:
                    _store_property(raw, tag, text_val)

        return cls(
            pdfx_version=raw.get("pdfxid:GTS_PDFXVersion", raw.get("pdfx:GTS_PDFXVersion", "")),
            pdfx_conformance=raw.get(
                "pdfxid:GTS_PDFXConformance", raw.get("pdfx:GTS_PDFXConformance", "")
            ),
            pdf_version=raw.get("pdf:PDFVersion", ""),
            creator_tool=raw.get("xmp:CreatorTool", ""),
            create_date=raw.get("xmp:CreateDate", ""),
            modify_date=raw.get("xmp:ModifyDate", ""),
            title=raw.get("dc:title", ""),
            trapped=raw.get("pdf:Trapped", ""),
            raw_properties=raw,
        )


def _store_property(raw: dict[str, str], key: str, value: str) -> None:
    """Store a property with a simplified namespace prefix key."""
    # Convert {namespace_uri}LocalName to prefix:LocalName
    if key.startswith("{"):
        uri_end = key.index("}")
        uri = key[1:uri_end]
        local = key[uri_end + 1 :]
        prefix = _uri_to_prefix(uri)
        if prefix:
            raw[f"{prefix}:{local}"] = value
        else:
            raw[local] = value
    else:
        raw[key] = value


def _uri_to_prefix(uri: str) -> str:
    """Map namespace URI to short prefix."""
    for prefix, ns_uri in _NS.items():
        if uri == ns_uri:
            return prefix
    return ""


def _extract_text(element: ET.Element) -> str:  # skipcq: PY-R1000
    """Extract text from an XMP element, handling rdf:Alt/rdf:Seq/rdf:Bag."""
    # Direct text content
    if element.text and element.text.strip():
        return str(element.text.strip())

    rdf_ns = _NS["rdf"]

    # rdf:Alt — language alternatives (take first li)
    alt = element.find(f"{{{rdf_ns}}}Alt")
    if alt is not None:
        li = alt.find(f"{{{rdf_ns}}}li")
        if li is not None and li.text:
            return str(li.text.strip())

    # rdf:Seq — ordered list (take first li)
    seq = element.find(f"{{{rdf_ns}}}Seq")
    if seq is not None:
        li = seq.find(f"{{{rdf_ns}}}li")
        if li is not None and li.text:
            return str(li.text.strip())

    # rdf:Bag — unordered list (take first li)
    bag = element.find(f"{{{rdf_ns}}}Bag")
    if bag is not None:
        li = bag.find(f"{{{rdf_ns}}}li")
        if li is not None and li.text:
            return str(li.text.strip())

    return ""
