"""Conditional rule engine for per-check evaluation.

Evaluates conditions defined in PreflightProfile to determine whether
a finding should be included, modified, or suppressed based on
document context.

Example PreflightProfile JSON with conditions:

    {
        "checks": {
            "enabled": ["GRD_*"],
            "per_check": {
                "GRD_IMG_001": {
                    "conditions": [
                        {
                            "when": {"page": {"in": [1, -1]}},
                            "severity": "advisory"
                        },
                        {
                            "when": {"object_type": "image", "page": {"gt": 5}},
                            "params": {"min_dpi": 72}
                        }
                    ]
                }
            }
        }
    }
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CheckContext:
    """Context information for evaluating conditions against a finding.

    Populated from the Finding dataclass and document metadata.
    """

    page_num: int = 0
    total_pages: int = 0
    object_type: str = ""
    object_id: str = ""
    source: str = "engine"
    category: str = ""
    severity: str = ""
    inspection_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConditionResult:
    """Result of evaluating conditions against a finding.

    Attributes:
        include: Whether to include this finding (False = suppress).
        severity_override: Override severity, or None to keep original.
        param_overrides: Parameter overrides to apply.
    """

    include: bool = True
    severity_override: str | None = None
    param_overrides: dict[str, Any] = field(default_factory=dict)


def evaluate_conditions(
    context: CheckContext,
    conditions: list[dict[str, Any]],
) -> ConditionResult:
    """Evaluate a list of conditions against a check context.

    Conditions are evaluated in order. The FIRST matching condition wins.
    If no condition matches, the finding is included as-is.

    Args:
        context: The context to evaluate against.
        conditions: List of condition dicts from PreflightProfile.

    Returns:
        ConditionResult with include/severity/param overrides.
    """
    for condition in conditions:
        when_clause = condition.get("when", {})
        if _matches(context, when_clause):
            return ConditionResult(
                include=condition.get("include", True),
                severity_override=condition.get("severity"),
                param_overrides=condition.get("params", {}),
            )

    # No condition matched — include as-is
    return ConditionResult(include=True)


def _matches(context: CheckContext, when: dict[str, Any]) -> bool:
    """Check if a context matches a 'when' clause.

    All keys in the when clause must match (AND logic).
    Each key maps to either a literal value or an operator dict.

    Supported operators:
        eq: Equal (default if literal value given)
        ne: Not equal
        in: Value in list
        not_in: Value not in list
        gt: Greater than (numeric/page)
        lt: Less than (numeric/page)
        gte: Greater than or equal
        lte: Less than or equal
        contains: String contains
        regex: Regex match

    Special page handling:
        Negative page numbers count from the end (-1 = last page).
    """
    if not when:
        return True  # Empty when = always matches

    for key, value in when.items():
        ctx_value = _get_context_value(context, key)
        if not _matches_value(ctx_value, value, context):
            return False

    return True


def _get_context_value(context: CheckContext, key: str) -> Any:
    """Get a value from the context by key name."""
    if key == "page":
        return context.page_num
    if key == "total_pages":
        return context.total_pages
    if key == "object_type":
        return context.object_type
    if key == "object_id":
        return context.object_id
    if key == "source":
        return context.source
    if key == "category":
        return context.category
    if key == "severity":
        return context.severity
    if key == "inspection_id":
        return context.inspection_id

    # Check in details dict
    return context.details.get(key)


def _resolve_page(value: int, total_pages: int) -> int:
    """Resolve negative page numbers (-1 = last, -2 = second to last)."""
    if value < 0 and total_pages > 0:
        return total_pages + value + 1
    return value


def _matches_value(ctx_value: Any, condition: Any, context: CheckContext) -> bool:
    """Check if a context value matches a condition value or operator dict."""
    if ctx_value is None:
        return False

    # Literal value: exact match
    if not isinstance(condition, dict):
        if isinstance(condition, (int, float)) and isinstance(ctx_value, (int, float)):
            return ctx_value == condition
        return str(ctx_value) == str(condition)

    # Operator dict
    for op, op_value in condition.items():
        if op == "eq":
            if ctx_value != op_value:
                return False
        elif op == "ne":
            if ctx_value == op_value:
                return False
        elif op == "in":
            if not isinstance(op_value, list):
                return False
            # Resolve negative page numbers
            resolved = [
                _resolve_page(v, context.total_pages)
                if isinstance(v, int) and v < 0
                else v
                for v in op_value
            ]
            if ctx_value not in resolved:
                return False
        elif op == "not_in":
            if not isinstance(op_value, list):
                return False
            resolved = [
                _resolve_page(v, context.total_pages)
                if isinstance(v, int) and v < 0
                else v
                for v in op_value
            ]
            if ctx_value in resolved:
                return False
        elif op == "gt":
            resolved_val = (
                _resolve_page(op_value, context.total_pages)
                if isinstance(op_value, int) and op_value < 0
                else op_value
            )
            if not (isinstance(ctx_value, (int, float)) and ctx_value > resolved_val):
                return False
        elif op == "lt":
            resolved_val = (
                _resolve_page(op_value, context.total_pages)
                if isinstance(op_value, int) and op_value < 0
                else op_value
            )
            if not (isinstance(ctx_value, (int, float)) and ctx_value < resolved_val):
                return False
        elif op == "gte":
            resolved_val = (
                _resolve_page(op_value, context.total_pages)
                if isinstance(op_value, int) and op_value < 0
                else op_value
            )
            if not (isinstance(ctx_value, (int, float)) and ctx_value >= resolved_val):
                return False
        elif op == "lte":
            resolved_val = (
                _resolve_page(op_value, context.total_pages)
                if isinstance(op_value, int) and op_value < 0
                else op_value
            )
            if not (isinstance(ctx_value, (int, float)) and ctx_value <= resolved_val):
                return False
        elif op == "contains":
            if not isinstance(ctx_value, str) or op_value not in ctx_value:
                return False
        elif op == "regex":
            import re

            if not isinstance(ctx_value, str) or not re.search(op_value, ctx_value):
                return False

    return True
