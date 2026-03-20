"""Tests for XmpMetadata parser."""

from __future__ import annotations

from grounded.conformance.xmp import XmpMetadata

_SAMPLE_XMP = b"""\
<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
      xmlns:dc="http://purl.org/dc/elements/1.1/"
      xmlns:xmp="http://ns.adobe.com/xap/1.0/"
      xmlns:pdf="http://ns.adobe.com/pdf/1.3/"
      xmlns:pdfxid="http://www.npes.org/pdfx/ns/id/"
      xmp:CreatorTool="Adobe InDesign 18.0"
      xmp:CreateDate="2024-01-15T10:30:00Z"
      xmp:ModifyDate="2024-01-15T11:00:00Z"
      pdf:PDFVersion="1.6"
      pdf:Trapped="False"
      pdfxid:GTS_PDFXVersion="PDF/X-4"
      pdfxid:GTS_PDFXConformance="PDF/X-4">
      <dc:title>
        <rdf:Alt>
          <rdf:li xml:lang="x-default">Test Document Title</rdf:li>
        </rdf:Alt>
      </dc:title>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>
"""


class TestXmpMetadataFromBytes:
    """Test XmpMetadata.from_bytes() parsing."""

    @staticmethod
    def test_parse_full_xmp() -> None:
        xmp = XmpMetadata.from_bytes(_SAMPLE_XMP)
        assert xmp.pdfx_version == "PDF/X-4"
        assert xmp.pdfx_conformance == "PDF/X-4"
        assert xmp.pdf_version == "1.6"
        assert xmp.creator_tool == "Adobe InDesign 18.0"
        assert xmp.create_date == "2024-01-15T10:30:00Z"
        assert xmp.modify_date == "2024-01-15T11:00:00Z"
        assert xmp.title == "Test Document Title"
        assert xmp.trapped == "False"

    @staticmethod
    def test_empty_bytes() -> None:
        xmp = XmpMetadata.from_bytes(b"")
        assert xmp.pdfx_version == ""
        assert xmp.title == ""

    @staticmethod
    def test_invalid_xml() -> None:
        xmp = XmpMetadata.from_bytes(b"<not valid xml")
        assert xmp.pdfx_version == ""

    @staticmethod
    def test_null_padded() -> None:
        padded = _SAMPLE_XMP + b"\x00" * 100
        xmp = XmpMetadata.from_bytes(padded)
        assert xmp.pdfx_version == "PDF/X-4"

    @staticmethod
    def test_minimal_xmp() -> None:
        minimal = b"""\
<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
      xmlns:pdf="http://ns.adobe.com/pdf/1.3/"
      pdf:Trapped="True"/>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>
"""
        xmp = XmpMetadata.from_bytes(minimal)
        assert xmp.trapped == "True"
        assert xmp.title == ""

    @staticmethod
    def test_raw_properties_populated() -> None:
        xmp = XmpMetadata.from_bytes(_SAMPLE_XMP)
        assert "pdf:PDFVersion" in xmp.raw_properties
        assert "xmp:CreatorTool" in xmp.raw_properties

    @staticmethod
    def test_pdfx_old_namespace() -> None:
        """Test GTS_PDFXVersion in the older pdfx namespace."""
        old_ns = b"""\
<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
      xmlns:pdfx="http://ns.adobe.com/pdfx/1.3/"
      pdfx:GTS_PDFXVersion="PDF/X-1a:2003"/>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>
"""
        xmp = XmpMetadata.from_bytes(old_ns)
        assert xmp.pdfx_version == "PDF/X-1a:2003"

    @staticmethod
    def test_frozen() -> None:
        xmp = XmpMetadata.from_bytes(_SAMPLE_XMP)
        try:
            xmp.title = "New Title"  # type: ignore[misc]
            raise AssertionError("Should not allow mutation")
        except AttributeError:
            pass
