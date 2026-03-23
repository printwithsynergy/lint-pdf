"""Tests for the Pantone reference enrichment script."""

import json
import tempfile
from pathlib import Path

import pytest

# Import from the scripts directory
import sys

sys.path.insert(0, str(Path(__file__).parent / "../../scripts"))
from enrich_pantone_reference import (
    cross_reference,
    delta_e_76,
    normalize_pantone_name,
    parse_csv,
    main,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CSV_CONTENT = """\
Library|Pantone_Name|Hex|R|G|B|C|M|Y|K|L|a|b|Hex_Source|RGB_Source|CMYK_Source|Lab_Source
Pantone Formula Guide Coated|PANTONE 100 C|#F5F6F2|245|246|242|0.0|0.0|51.0|0.0|97.0|-8.0|65.0|COMPUTED|COMPUTED|COMPUTED|PANTONE_PUBLISHED
Pantone Formula Guide Uncoated|PANTONE 100 U|#F7F5E7|247|245|231|0.0|1.0|25.0|0.0|98.0|-6.0|39.0|COMPUTED|COMPUTED|COMPUTED|PANTONE_PUBLISHED
Pantone Formula Guide Coated|PANTONE 999 C|#AA0000|170|0|0|0.0|90.0|80.0|10.0|40.0|60.0|50.0|COMPUTED|COMPUTED|COMPUTED|PANTONE_PUBLISHED
Pantone Color Bridge Coated|PANTONE 100 CP|#F0E080|240|224|128|0.0|5.0|50.0|4.0|89.0|-6.0|55.0|COMPUTED|COMPUTED|COMPUTED|PANTONE_PUBLISHED
FHI Cotton TCX|PANTONE 19-4052 TCX|#1A3A6B|26|58|107|80.0|50.0|0.0|40.0|28.0|6.0|-33.0|COMPUTED|COMPUTED|COMPUTED|PANTONE_PUBLISHED
"""


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "test_pantone.csv"
    csv_path.write_text(SAMPLE_CSV_CONTENT, encoding="utf-8")
    return csv_path


@pytest.fixture
def sample_existing() -> dict:
    return {
        "PANTONE 100 C": {
            "lab": [97.26, -7.41, 37.67],
            "cmyk_bridge": [0, 0, 51, 0],
        },
        "PANTONE 100 U": {
            "lab": [98.85, -6.09, 30.98],
            "cmyk_bridge": [0, 1, 25, 0],
        },
    }


@pytest.fixture
def existing_json(tmp_path: Path, sample_existing: dict) -> Path:
    json_path = tmp_path / "pantone_reference.json"
    json_path.write_text(
        json.dumps({"_meta": {"count": 2}, "colors": sample_existing}),
        encoding="utf-8",
    )
    return json_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_basic(self):
        assert normalize_pantone_name("PANTONE 485 C") == "PANTONE 485 C"

    def test_case(self):
        assert normalize_pantone_name("pantone 485 c") == "PANTONE 485 C"

    def test_extra_spaces(self):
        assert normalize_pantone_name("PANTONE  485   C") == "PANTONE 485 C"

    def test_strip(self):
        assert normalize_pantone_name("  PANTONE 485 C  ") == "PANTONE 485 C"


class TestDeltaE:
    def test_identical(self):
        assert delta_e_76((50.0, 0.0, 0.0), (50.0, 0.0, 0.0)) == 0.0

    def test_known_distance(self):
        # Simple L-only difference
        de = delta_e_76((50.0, 0.0, 0.0), (60.0, 0.0, 0.0))
        assert abs(de - 10.0) < 0.01


class TestParseCSV:
    def test_parse_rows(self, sample_csv: Path):
        rows = parse_csv(sample_csv)
        assert len(rows) == 5

    def test_row_structure(self, sample_csv: Path):
        rows = parse_csv(sample_csv)
        row = rows[0]
        assert row["library"] == "Pantone Formula Guide Coated"
        assert row["name"] == "PANTONE 100 C"
        assert len(row["lab"]) == 3
        assert len(row["cmyk"]) == 4
        assert row["lab_source"] == "PANTONE_PUBLISHED"


class TestCrossReference:
    def test_matched_colors(self, sample_csv: Path, sample_existing: dict):
        csv_rows = parse_csv(sample_csv)
        result = cross_reference(sample_existing, csv_rows)
        report = result["report"]
        assert report["matched_count"] == 2  # PANTONE 100 C and U

    def test_preserves_existing_with_upgrade(self, sample_csv: Path, sample_existing: dict):
        csv_rows = parse_csv(sample_csv)
        result = cross_reference(sample_existing, csv_rows, upgrade_threshold=2.0)
        enriched = result["enriched_colors"]

        # PANTONE 100 C should exist
        c100 = enriched.get("PANTONE 100 C")
        assert c100 is not None
        # Lab should be upgraded since ΔE between existing and CSV is large
        assert c100["lab_source"] in ("PANTONE_PUBLISHED", "community_measured")

    def test_new_formula_guide_added(self, sample_csv: Path, sample_existing: dict):
        csv_rows = parse_csv(sample_csv)
        result = cross_reference(sample_existing, csv_rows)
        enriched = result["enriched_colors"]

        # PANTONE 999 C is new (not in existing)
        c999 = enriched.get("PANTONE 999 C")
        assert c999 is not None
        assert c999["lab"] == [40.0, 60.0, 50.0]
        assert c999["lab_source"] == "PANTONE_PUBLISHED"
        assert c999["library"] == "Pantone Formula Guide Coated"

    def test_color_bridge_cmyk_preferred(self, sample_csv: Path, sample_existing: dict):
        csv_rows = parse_csv(sample_csv)
        result = cross_reference(sample_existing, csv_rows)
        enriched = result["enriched_colors"]

        # PANTONE 100 C should use Color Bridge CMYK (from 100 CP)
        c100 = enriched.get("PANTONE 100 C")
        assert c100 is not None
        assert c100["cmyk_source"] == "color_bridge"
        assert c100["cmyk_bridge"] == [0.0, 5.0, 50.0, 4.0]

    def test_tcx_color_added(self, sample_csv: Path, sample_existing: dict):
        csv_rows = parse_csv(sample_csv)
        result = cross_reference(sample_existing, csv_rows)
        enriched = result["enriched_colors"]

        tcx = enriched.get("PANTONE 19-4052 TCX")
        assert tcx is not None
        assert tcx["library"] == "FHI Cotton TCX"
        assert tcx["lab_source"] == "PANTONE_PUBLISHED"

    def test_report_contains_delta_e_stats(self, sample_csv: Path, sample_existing: dict):
        csv_rows = parse_csv(sample_csv)
        result = cross_reference(sample_existing, csv_rows)
        report = result["report"]
        assert "delta_e_stats" in report
        assert report["delta_e_stats"]["count"] == 2


class TestMainCLI:
    def test_dry_run(self, sample_csv: Path, existing_json: Path):
        exit_code = main([
            "--csv", str(sample_csv),
            "--existing", str(existing_json),
            "--dry-run",
        ])
        assert exit_code == 0

    def test_output_write(self, sample_csv: Path, existing_json: Path, tmp_path: Path):
        output_path = tmp_path / "enriched.json"
        exit_code = main([
            "--csv", str(sample_csv),
            "--existing", str(existing_json),
            "--output", str(output_path),
        ])
        assert exit_code == 0
        assert output_path.exists()

        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert "_meta" in data
        assert "colors" in data
        assert data["_meta"]["count"] > 2
