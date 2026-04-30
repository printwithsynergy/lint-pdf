"""Wave V V-05 — per-document/per-finding/per-operator decision audit.

Importing this package registers the :class:`Decision` ORM model with
``Base.metadata`` so ``create_all`` (test harness) sees the table.
"""

from siftpdf.decisions.models import Decision

__all__ = ["Decision"]
