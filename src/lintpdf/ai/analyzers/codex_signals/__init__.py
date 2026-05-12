"""codex_signals — Phase 3 reader of codex's AI signal contract.

Codex 1.11.0 lit up six AI signal extractors (language, logos,
symbols, barcodes, classification, spell). Phase 3 of the AI Signal
Campaign moves the lint-pdf side: instead of running our own Claude
calls for the same six kinds, the analyzers in this package READ
codex's signals from ``ctx.config["codex_payload"]`` and surface
them as findings.

Win:

- One Claude call per ``(pdf_hash, signal_kind)`` instead of N. Codex
  caches forever; the second consumer hits Redis.
- Lint stays pure detection-policy. Codex stays pure data-collection.
- Demo gets visible AI findings end-to-end with no extra cost.

Each analyzer in this package follows the same pattern: read the
matching ``detected_*`` field off the codex payload, optionally
filter on tenant config, emit one informational finding per
detection.
"""

from __future__ import annotations

from lintpdf.ai.analyzers.codex_signals import barcodes_reader  # noqa: F401
from lintpdf.ai.analyzers.codex_signals import classification_reader  # noqa: F401
from lintpdf.ai.analyzers.codex_signals import language_reader  # noqa: F401
from lintpdf.ai.analyzers.codex_signals import logos_reader  # noqa: F401
from lintpdf.ai.analyzers.codex_signals import spell_reader  # noqa: F401
from lintpdf.ai.analyzers.codex_signals import symbols_reader  # noqa: F401
