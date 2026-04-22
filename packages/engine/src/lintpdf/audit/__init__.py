"""AI accuracy audit — second-pass verification of preflight findings.

Two surfaces:

* :mod:`lintpdf.audit.internal` — Claude Opus 4.7 vision pass. Dev /
  QA only; never runs in the customer request path. Used by the
  golden-PDF harness at ``scripts/audit_preflight_accuracy.py`` to
  red-team the engine against a curated corpus.
* :mod:`lintpdf.audit.customer` — Modal-hosted vision LLM
  (Qwen2-VL-7B-Instruct on A10G). Runs after ``run_preflight``
  when the tenant has ``entitlements.ai_audit_enabled``. Populates
  ``JobFinding.audit_*`` columns inline.

Both auditors return lists of :class:`AuditResult` aligned 1-to-1
with the input findings. Empty / unaudited findings carry a ``None``
status; those rows leave the DB columns NULL and the viewer shows
no chip.
"""

from __future__ import annotations

from lintpdf.audit.types import AuditResult, AuditStatus

__all__ = ["AuditResult", "AuditStatus"]
