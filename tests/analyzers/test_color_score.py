"""Tests for Color Quality Score."""

from siftpdf.analyzers.finding import Finding, Severity
from siftpdf.color_score import compute_color_quality_score


class TestColorQualityScore:
    def test_perfect_score_no_findings(self):
        result = compute_color_quality_score([])
        assert result.score == 100.0
        assert result.grade == "Excellent"

    def test_deduction_for_missing_output_intent(self):
        findings = [
            Finding(
                inspection_id="LPDF_COLOR_006",
                severity=Severity.ERROR,
                message="No Output Intent defined",
            )
        ]
        result = compute_color_quality_score(findings)
        # Critical floor of 25 applies for missing output intent
        assert result.score <= 25.0

    def test_critical_floor_for_corrupt_icc(self):
        findings = [
            Finding(
                inspection_id="LPDF_ICC_003",
                severity=Severity.ERROR,
                message="Corrupt ICC profile",
            )
        ]
        result = compute_color_quality_score(findings)
        assert result.score <= 30.0
        assert result.critical_floor == 30.0

    def test_critical_floor_rgb_in_cmyk(self):
        findings = [
            Finding(
                inspection_id="LPDF_COLOR_013",
                severity=Severity.ERROR,
                message="RGB in CMYK workflow",
            )
        ]
        result = compute_color_quality_score(findings)
        assert result.score <= 20.0

    def test_grade_thresholds(self):
        from siftpdf.color_score import _get_grade

        assert _get_grade(95) == "Excellent"
        assert _get_grade(80) == "Good"
        assert _get_grade(60) == "Fair"
        assert _get_grade(30) == "Poor"
        assert _get_grade(10) == "Critical"

    def test_non_color_findings_ignored(self):
        findings = [
            Finding(
                inspection_id="LPDF_IMG_001",
                severity=Severity.ERROR,
                message="Image DPI too low",
            )
        ]
        result = compute_color_quality_score(findings)
        assert result.score == 100.0

    def test_breakdown_has_categories(self):
        result = compute_color_quality_score([])
        assert "color_spaces" in result.breakdown
        assert "ink_coverage" in result.breakdown
        assert "profiles" in result.breakdown
        assert "spot_colors" in result.breakdown
        assert "overprint" in result.breakdown
