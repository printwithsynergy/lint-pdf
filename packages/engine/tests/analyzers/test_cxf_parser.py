"""Tests for CxF/X-4 spectral data parser."""

from lintpdf.analyzers.cxf_parser import CxfData, CxfSpotColor, parse_cxf_xml


_VALID_CXF_XML = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<CxF xmlns="http://colorexchange.org/CxF/v3" Version="3.0">
  <FileInformation>
    <Standard>CxF/X-4</Standard>
  </FileInformation>
  <ObjectCollection>
    <Object Name="PANTONE 485 C">
      <ColorValues>
        <ColorCIELab>
          <L>51.42</L>
          <A>64.27</A>
          <B>52.93</B>
        </ColorCIELab>
        <ReflectanceSpectrum StartWL="380" EndWL="730" Interval="10">
          0.05 0.05 0.05 0.04 0.04 0.04 0.04 0.04 0.04 0.04
          0.04 0.04 0.05 0.05 0.06 0.06 0.07 0.08 0.09 0.12
          0.15 0.20 0.28 0.38 0.48 0.56 0.62 0.65 0.67 0.68
          0.69 0.69 0.70 0.70 0.70 0.70
        </ReflectanceSpectrum>
      </ColorValues>
    </Object>
    <Object Name="PANTONE Reflex Blue C">
      <ColorValues>
        <ColorCIELab>
          <L>21.75</L>
          <A>16.93</A>
          <B>-56.28</B>
        </ColorCIELab>
      </ColorValues>
    </Object>
  </ObjectCollection>
</CxF>
"""

_MALFORMED_XML = b"<CxF><broken"

_NO_NAMESPACE_CXF = b"""\
<?xml version="1.0"?>
<CxF Version="3.0">
  <Object Name="TestSpot">
    <ColorValues>
      <ColorCIELab>
        <L>55.0</L>
        <A>10.0</A>
        <B>-20.0</B>
      </ColorCIELab>
    </ColorValues>
  </Object>
</CxF>
"""


class TestCxfParser:
    def test_parse_valid_cxf(self):
        result = parse_cxf_xml(_VALID_CXF_XML)
        assert result.valid
        assert len(result.spot_colors) == 2
        assert "CxF" in result.file_standard

    def test_parse_spot_color_lab(self):
        result = parse_cxf_xml(_VALID_CXF_XML)
        pantone_485 = next(
            (sc for sc in result.spot_colors if "485" in sc.name),
            None,
        )
        assert pantone_485 is not None
        assert pantone_485.lab is not None
        assert abs(pantone_485.lab[0] - 51.42) < 0.1
        assert abs(pantone_485.lab[1] - 64.27) < 0.1

    def test_parse_spectral_data(self):
        result = parse_cxf_xml(_VALID_CXF_XML)
        pantone_485 = next(
            (sc for sc in result.spot_colors if "485" in sc.name),
            None,
        )
        assert pantone_485 is not None
        assert pantone_485.spectral_data is not None
        assert len(pantone_485.spectral_data) == 36
        assert pantone_485.wavelength_start == 380
        assert pantone_485.wavelength_end == 730

    def test_parse_reflex_blue_lab_only(self):
        result = parse_cxf_xml(_VALID_CXF_XML)
        reflex = next(
            (sc for sc in result.spot_colors if "Reflex" in sc.name),
            None,
        )
        assert reflex is not None
        assert reflex.lab is not None
        assert reflex.spectral_data is None  # No spectral for this one

    def test_malformed_xml(self):
        result = parse_cxf_xml(_MALFORMED_XML)
        assert result.valid is False
        assert len(result.errors) >= 1

    def test_no_namespace_cxf(self):
        result = parse_cxf_xml(_NO_NAMESPACE_CXF)
        assert len(result.spot_colors) >= 1
        assert result.spot_colors[0].name == "TestSpot"
        assert result.spot_colors[0].lab is not None

    def test_empty_xml(self):
        result = parse_cxf_xml(b"<?xml version='1.0'?><CxF/>")
        assert result.valid  # Valid XML, just no objects
        assert len(result.spot_colors) == 0


class TestCxfSpotColor:
    def test_dataclass_defaults(self):
        sc = CxfSpotColor(name="Test")
        assert sc.lab is None
        assert sc.spectral_data is None
        assert sc.wavelength_start == 380
        assert sc.wavelength_end == 730
        assert sc.wavelength_interval == 10
