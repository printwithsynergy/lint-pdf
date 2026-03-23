"""SPC (Statistical Process Control) trend analysis engine.

Computes control chart metrics from job finding history and detects
out-of-control conditions using Western Electric rules.

Metrics tracked:
- Findings per job (total, by severity, by category)
- Color Quality Score trend
- Processing time trend
- Page count trend
- DPI distribution
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SpcDataPoint:
    """A single data point for SPC analysis."""

    job_id: str = ""
    timestamp: str = ""
    value: float = 0.0
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class ControlLimits:
    """Control chart limits."""

    ucl: float = 0.0  # Upper Control Limit (mean + 3*sigma)
    lcl: float = 0.0  # Lower Control Limit (mean - 3*sigma)
    mean: float = 0.0
    sigma: float = 0.0
    uwl: float = 0.0  # Upper Warning Limit (mean + 2*sigma)
    lwl: float = 0.0  # Lower Warning Limit (mean - 2*sigma)


@dataclass
class SpcAlert:
    """An SPC alert for an out-of-control condition."""

    rule: str = ""  # e.g., "western_electric_1", "nelson_2"
    metric: str = ""
    description: str = ""
    severity: str = "advisory"
    data_points: list[SpcDataPoint] = field(default_factory=list)


@dataclass
class SpcResult:
    """Result of SPC analysis for a metric."""

    metric: str = ""
    data_points: list[SpcDataPoint] = field(default_factory=list)
    limits: ControlLimits = field(default_factory=ControlLimits)
    alerts: list[SpcAlert] = field(default_factory=list)
    in_control: bool = True


class SpcEngine:
    """Statistical Process Control engine using Western Electric rules.

    Analyzes sequences of data points to compute control chart limits
    and detect out-of-control conditions.

    Western Electric rules implemented:
        1. Single point beyond 3-sigma (UCL/LCL)
        2. Two of three consecutive points beyond 2-sigma (same side)
        3. Four of five consecutive points beyond 1-sigma (same side)
        4. Eight consecutive points on same side of center line
    """

    def compute_limits(self, data_points: list[SpcDataPoint]) -> ControlLimits:
        """Calculate control limits from data points.

        Computes the mean and standard deviation of the values, then
        derives UCL, LCL, UWL, and LWL at 3-sigma and 2-sigma
        respectively.

        Args:
            data_points: Sequence of data points to analyze.

        Returns:
            ControlLimits with computed mean, sigma, and limit values.
        """
        if not data_points:
            return ControlLimits()

        values = [dp.value for dp in data_points]
        n = len(values)
        mean = sum(values) / n

        if n < 2:
            return ControlLimits(
                ucl=mean,
                lcl=mean,
                mean=mean,
                sigma=0.0,
                uwl=mean,
                lwl=mean,
            )

        variance = sum((v - mean) ** 2 for v in values) / (n - 1)
        sigma = variance**0.5

        return ControlLimits(
            ucl=mean + 3 * sigma,
            lcl=mean - 3 * sigma,
            mean=mean,
            sigma=sigma,
            uwl=mean + 2 * sigma,
            lwl=mean - 2 * sigma,
        )

    def detect_alerts(
        self,
        data_points: list[SpcDataPoint],
        limits: ControlLimits,
        metric: str,
    ) -> list[SpcAlert]:
        """Apply Western Electric rules to detect out-of-control conditions.

        Args:
            data_points: Sequence of data points to check.
            limits: Pre-computed control limits.
            metric: Name of the metric being analyzed.

        Returns:
            List of SpcAlert objects for each detected violation.
        """
        alerts: list[SpcAlert] = []

        if not data_points or limits.sigma == 0.0:
            return alerts

        alerts.extend(self._rule_1_beyond_3_sigma(data_points, limits, metric))
        alerts.extend(self._rule_2_two_of_three_beyond_2_sigma(data_points, limits, metric))
        alerts.extend(self._rule_3_four_of_five_beyond_1_sigma(data_points, limits, metric))
        alerts.extend(self._rule_4_eight_consecutive_same_side(data_points, limits, metric))

        return alerts

    def analyze(
        self,
        data_points: list[SpcDataPoint],
        metric: str,
    ) -> SpcResult:
        """Perform full SPC analysis on a sequence of data points.

        Computes control limits, applies Western Electric rules, and
        returns a comprehensive result.

        Args:
            data_points: Sequence of data points to analyze.
            metric: Name of the metric being analyzed.

        Returns:
            SpcResult with limits, alerts, and in-control status.
        """
        limits = self.compute_limits(data_points)
        alerts = self.detect_alerts(data_points, limits, metric)

        return SpcResult(
            metric=metric,
            data_points=list(data_points),
            limits=limits,
            alerts=alerts,
            in_control=len(alerts) == 0,
        )

    # ------------------------------------------------------------------
    # Western Electric Rule 1 — Single point beyond 3-sigma
    # ------------------------------------------------------------------

    @staticmethod
    def _rule_1_beyond_3_sigma(
        data_points: list[SpcDataPoint],
        limits: ControlLimits,
        metric: str,
    ) -> list[SpcAlert]:
        """Detect single points beyond UCL or LCL (3-sigma)."""
        alerts: list[SpcAlert] = []

        for dp in data_points:
            if dp.value > limits.ucl or dp.value < limits.lcl:
                side = "above UCL" if dp.value > limits.ucl else "below LCL"
                alerts.append(
                    SpcAlert(
                        rule="western_electric_1",
                        metric=metric,
                        description=(
                            f"Point {side} (value={dp.value:.4f}, "
                            f"UCL={limits.ucl:.4f}, LCL={limits.lcl:.4f})"
                        ),
                        severity="warning",
                        data_points=[dp],
                    )
                )

        return alerts

    # ------------------------------------------------------------------
    # Western Electric Rule 2 — Two of three beyond 2-sigma (same side)
    # ------------------------------------------------------------------

    @staticmethod
    def _rule_2_two_of_three_beyond_2_sigma(
        data_points: list[SpcDataPoint],
        limits: ControlLimits,
        metric: str,
    ) -> list[SpcAlert]:
        """Detect two of three consecutive points beyond 2-sigma on the same side."""
        alerts: list[SpcAlert] = []

        if len(data_points) < 3:
            return alerts

        for i in range(len(data_points) - 2):
            window = data_points[i : i + 3]
            values = [dp.value for dp in window]

            # Check upper side
            above_uwl = sum(1 for v in values if v > limits.uwl)
            if above_uwl >= 2:
                alerts.append(
                    SpcAlert(
                        rule="western_electric_2",
                        metric=metric,
                        description=(
                            f"Two of three consecutive points above UWL (2-sigma={limits.uwl:.4f})"
                        ),
                        severity="warning",
                        data_points=list(window),
                    )
                )

            # Check lower side
            below_lwl = sum(1 for v in values if v < limits.lwl)
            if below_lwl >= 2:
                alerts.append(
                    SpcAlert(
                        rule="western_electric_2",
                        metric=metric,
                        description=(
                            f"Two of three consecutive points below LWL (2-sigma={limits.lwl:.4f})"
                        ),
                        severity="warning",
                        data_points=list(window),
                    )
                )

        return alerts

    # ------------------------------------------------------------------
    # Western Electric Rule 3 — Four of five beyond 1-sigma (same side)
    # ------------------------------------------------------------------

    @staticmethod
    def _rule_3_four_of_five_beyond_1_sigma(
        data_points: list[SpcDataPoint],
        limits: ControlLimits,
        metric: str,
    ) -> list[SpcAlert]:
        """Detect four of five consecutive points beyond 1-sigma on the same side."""
        alerts: list[SpcAlert] = []

        if len(data_points) < 5:
            return alerts

        one_sigma_upper = limits.mean + limits.sigma
        one_sigma_lower = limits.mean - limits.sigma

        for i in range(len(data_points) - 4):
            window = data_points[i : i + 5]
            values = [dp.value for dp in window]

            # Check upper side
            above_1s = sum(1 for v in values if v > one_sigma_upper)
            if above_1s >= 4:
                alerts.append(
                    SpcAlert(
                        rule="western_electric_3",
                        metric=metric,
                        description=(
                            f"Four of five consecutive points above 1-sigma ({one_sigma_upper:.4f})"
                        ),
                        severity="advisory",
                        data_points=list(window),
                    )
                )

            # Check lower side
            below_1s = sum(1 for v in values if v < one_sigma_lower)
            if below_1s >= 4:
                alerts.append(
                    SpcAlert(
                        rule="western_electric_3",
                        metric=metric,
                        description=(
                            f"Four of five consecutive points below 1-sigma ({one_sigma_lower:.4f})"
                        ),
                        severity="advisory",
                        data_points=list(window),
                    )
                )

        return alerts

    # ------------------------------------------------------------------
    # Western Electric Rule 4 — Eight consecutive on same side of center
    # ------------------------------------------------------------------

    @staticmethod
    def _rule_4_eight_consecutive_same_side(
        data_points: list[SpcDataPoint],
        limits: ControlLimits,
        metric: str,
    ) -> list[SpcAlert]:
        """Detect eight consecutive points on the same side of the center line."""
        alerts: list[SpcAlert] = []

        if len(data_points) < 8:
            return alerts

        for i in range(len(data_points) - 7):
            window = data_points[i : i + 8]
            values = [dp.value for dp in window]

            all_above = all(v > limits.mean for v in values)
            all_below = all(v < limits.mean for v in values)

            if all_above:
                alerts.append(
                    SpcAlert(
                        rule="western_electric_4",
                        metric=metric,
                        description=(
                            f"Eight consecutive points above center line (mean={limits.mean:.4f})"
                        ),
                        severity="advisory",
                        data_points=list(window),
                    )
                )
            elif all_below:
                alerts.append(
                    SpcAlert(
                        rule="western_electric_4",
                        metric=metric,
                        description=(
                            f"Eight consecutive points below center line (mean={limits.mean:.4f})"
                        ),
                        severity="advisory",
                        data_points=list(window),
                    )
                )

        return alerts
