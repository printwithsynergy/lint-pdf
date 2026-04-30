"""Statistical Process Control (SPC) analyzer for submission quality trends.

This meta-analyzer examines historical job data for a tenant to detect
quality trends using Western Electric rules on control charts. It tracks
pass/fail rates and finding counts over time to identify process shifts.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from lintpdf.ai.base import BaseAIAnalyzer, _reconstitute_ai_config
from lintpdf.ai.registry import register_ai_analyzer
from lintpdf.analyzers.finding import Finding, Severity

if TYPE_CHECKING:
    from lintpdf.plugin.protocol import AnalyzerContext

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    from scipy import stats as scipy_stats

    _HAS_SCIPY = True
except ImportError:
    scipy_stats = None
    _HAS_SCIPY = False

try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:
    np = None
    _HAS_NUMPY = False

# Minimum number of historical data points for meaningful SPC analysis
_MIN_DATA_POINTS = 20


def _apply_western_electric_rules(  # skipcq: PY-R1000
    data: list[float], mean: float, sigma: float
) -> list[dict[str, Any]]:
    """Apply Western Electric rules for control chart violation detection.

    Rules:
    1. One point beyond 3 sigma from the center line.
    2. Two out of three consecutive points beyond 2 sigma on the same side.
    3. Four out of five consecutive points beyond 1 sigma on the same side.
    4. Eight consecutive points on the same side of the center line.

    Returns a list of violation dicts with rule, index, and description.
    """
    if sigma == 0:
        return []

    violations: list[dict[str, Any]] = []

    for i, value in enumerate(data):
        z = (value - mean) / sigma

        # Rule 1: Single point beyond 3 sigma
        if abs(z) > 3.0:
            side = "above" if z > 0 else "below"
            violations.append(
                {
                    "rule": 1,
                    "index": i,
                    "value": value,
                    "z_score": round(z, 2),
                    "description": f"Point {i} is {abs(z):.1f} sigma {side} center line",
                }
            )

    # Rule 2: 2 of 3 consecutive beyond 2 sigma same side
    for i in range(2, len(data)):
        window = data[i - 2 : i + 1]
        z_scores = [(v - mean) / sigma for v in window]

        above_2s = sum(1 for z in z_scores if z > 2.0)
        below_2s = sum(1 for z in z_scores if z < -2.0)

        if above_2s >= 2:
            violations.append(
                {
                    "rule": 2,
                    "index": i,
                    "description": f"2 of 3 points (ending at {i}) beyond +2 sigma",
                }
            )
        if below_2s >= 2:
            violations.append(
                {
                    "rule": 2,
                    "index": i,
                    "description": f"2 of 3 points (ending at {i}) beyond -2 sigma",
                }
            )

    # Rule 3: 4 of 5 consecutive beyond 1 sigma same side
    for i in range(4, len(data)):
        window = data[i - 4 : i + 1]
        z_scores = [(v - mean) / sigma for v in window]

        above_1s = sum(1 for z in z_scores if z > 1.0)
        below_1s = sum(1 for z in z_scores if z < -1.0)

        if above_1s >= 4:
            violations.append(
                {
                    "rule": 3,
                    "index": i,
                    "description": f"4 of 5 points (ending at {i}) beyond +1 sigma",
                }
            )
        if below_1s >= 4:
            violations.append(
                {
                    "rule": 3,
                    "index": i,
                    "description": f"4 of 5 points (ending at {i}) beyond -1 sigma",
                }
            )

    # Rule 4: 8 consecutive on same side
    for i in range(7, len(data)):
        window = data[i - 7 : i + 1]
        deviations = [v - mean for v in window]

        if all(d > 0 for d in deviations):
            violations.append(
                {
                    "rule": 4,
                    "index": i,
                    "description": f"8 consecutive points (ending at {i}) above center",
                }
            )
        elif all(d < 0 for d in deviations):
            violations.append(
                {
                    "rule": 4,
                    "index": i,
                    "description": f"8 consecutive points (ending at {i}) below center",
                }
            )

    return violations


def _query_historical_data(tenant_id: Any) -> list[dict[str, Any]] | None:
    """Query historical job quality data for the tenant.

    Fetches completed jobs from the database and computes per-job finding
    counts to build the time series needed for SPC analysis.

    Returns None if the database is unavailable or no data exists.
    """
    try:
        from sqlalchemy import func, text

        from lintpdf.ai.types import get_db_session
        from lintpdf.api.models import Job, JobFinding, JobStatus
    except (ImportError, RuntimeError):
        logger.debug("Database not available for SPC historical query — tenant_id=%s", tenant_id)
        return None

    try:
        db = get_db_session()
    except RuntimeError:
        logger.debug("Database session not initialized — tenant_id=%s", tenant_id)
        return None

    try:
        # Subquery: per-job finding counts grouped by severity
        (
            db.query(
                JobFinding.job_id,
                func.count(JobFinding.id).label("finding_count"),
                func.sum(
                    func.cast(
                        JobFinding.severity == "error",
                        (db.bind.dialect.name != "sqlite" and text("INTEGER")) or text("INT"),
                    )
                ).label("error_count_raw"),
                func.sum(
                    func.cast(
                        JobFinding.severity == "warning",
                        (db.bind.dialect.name != "sqlite" and text("INTEGER")) or text("INT"),
                    )
                ).label("warning_count_raw"),
            )
            .group_by(JobFinding.job_id)
            .subquery()
        )

        # Simpler approach: just get completed jobs and count findings separately
        jobs = (
            db.query(Job)
            .filter(
                Job.tenant_id == str(tenant_id),
                Job.status.in_([JobStatus.COMPLETE, JobStatus.FAILED]),
            )
            .order_by(Job.created_at.desc())
            .limit(100)
            .all()
        )

        if not jobs:
            return None

        results: list[dict[str, Any]] = []
        for job in jobs:
            # Count findings per job
            counts = (
                db.query(
                    func.count(JobFinding.id).label("total"),
                    func.count(func.nullif(JobFinding.severity != "error", True)).label("errors"),
                    func.count(func.nullif(JobFinding.severity != "warning", True)).label(
                        "warnings"
                    ),
                )
                .filter(JobFinding.job_id == job.id)
                .one()
            )

            results.append(
                {
                    "job_id": str(job.id),
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "status": job.status.value if hasattr(job.status, "value") else str(job.status),
                    "finding_count": counts.total or 0,
                    "error_count": counts.errors or 0,
                    "warning_count": counts.warnings or 0,
                }
            )

        return results if results else None

    except Exception:
        logger.debug(
            "Failed to query historical data for SPC — tenant_id=%s", tenant_id, exc_info=True
        )
        return None
    finally:
        db.close()


@register_ai_analyzer
class SubmissionQualitySPCAnalyzer(BaseAIAnalyzer):
    """Analyze submission quality trends using Statistical Process Control."""

    category = "trend_analysis"
    feature_slug = "submission_quality_spc"
    tier = "cpu"
    credits_per_run = 2

    def analyze_v2(  # skipcq: PY-R1000
        self,
        ctx: AnalyzerContext,
    ) -> list[Finding]:
        # Phase 2 alpha-stream: signature migration. Uses ai_config
        # (.tenant_id). Reconstituted via _reconstitute_ai_config to
        # preserve attribute access. document + events + pdf_bytes
        # declared but never used.
        ai_config_dict = ctx.config.get("ai_config") if ctx.config else None
        ai_config = _reconstitute_ai_config(ai_config_dict)

        if not _HAS_SCIPY or not _HAS_NUMPY:
            logger.debug("scipy or numpy not installed — skipping SPC analysis")
            return []

        tenant_id = getattr(ai_config, "tenant_id", None) if ai_config else None
        if tenant_id is None:
            return []

        historical_data = _query_historical_data(tenant_id)
        if historical_data is None:
            return [
                self._make_finding(
                    inspection_id="AI_SPC_001",
                    severity=Severity.ADVISORY,
                    message=(
                        "Insufficient historical data for SPC analysis. "
                        "Trend monitoring requires at least "
                        f"{_MIN_DATA_POINTS} prior submissions."
                    ),
                    details={
                        "reason": "insufficient_data",
                        "min_required": _MIN_DATA_POINTS,
                    },
                )
            ]

        if len(historical_data) < _MIN_DATA_POINTS:
            return [
                self._make_finding(
                    inspection_id="AI_SPC_001",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Only {len(historical_data)} historical submissions "
                        f"available (need {_MIN_DATA_POINTS} for SPC). "
                        "Trend analysis will improve with more data."
                    ),
                    details={
                        "reason": "insufficient_data",
                        "data_points": len(historical_data),
                        "min_required": _MIN_DATA_POINTS,
                    },
                )
            ]

        # Extract finding counts as the quality metric
        finding_counts = [float(record.get("finding_count", 0)) for record in historical_data]
        data_array = np.array(finding_counts)
        mean = float(np.mean(data_array))
        sigma = float(np.std(data_array, ddof=1))

        if sigma == 0:
            return [
                self._make_finding(
                    inspection_id="AI_SPC_002",
                    severity=Severity.ADVISORY,
                    message="All historical submissions have identical finding counts — no variation to analyze.",
                    details={"mean": mean, "sigma": 0.0},
                )
            ]

        # Apply Western Electric rules
        violations = _apply_western_electric_rules(finding_counts, mean, sigma)

        # Compute pass rate
        pass_count = sum(1 for r in historical_data if r.get("status") in ("passed", "approved"))
        pass_rate = pass_count / len(historical_data) * 100

        findings: list[Finding] = []

        # Summary finding
        findings.append(
            self._make_finding(
                inspection_id="AI_SPC_003",
                severity=Severity.ADVISORY,
                message=(
                    f"Quality trend summary: {len(historical_data)} submissions, "
                    f"pass rate {pass_rate:.1f}%, "
                    f"mean findings {mean:.1f} (sigma={sigma:.1f}), "
                    f"{len(violations)} control chart violation(s)"
                ),
                details={
                    "submissions": len(historical_data),
                    "pass_rate_pct": round(pass_rate, 1),
                    "mean_findings": round(mean, 2),
                    "sigma": round(sigma, 2),
                    "ucl_3sigma": round(mean + 3 * sigma, 2),
                    "lcl_3sigma": round(max(0, mean - 3 * sigma), 2),
                    "violation_count": len(violations),
                },
            )
        )

        # Individual violation findings
        for violation in violations:
            findings.append(
                self._make_finding(
                    inspection_id="AI_SPC_004",
                    severity=Severity.ADVISORY,
                    message=(
                        f"Western Electric Rule {violation['rule']} violation: "
                        f"{violation['description']}"
                    ),
                    details=violation,
                )
            )

        return findings
