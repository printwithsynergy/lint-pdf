"""Re-export shared API fixtures for the billing tests.

``db_session`` is defined in ``tests/api/conftest.py``; pytest only
discovers it for that directory, so the billing tests can't see it by
default. Importing the fixture symbol here makes it available under
``tests/billing/`` too.
"""

from __future__ import annotations

from tests.api.conftest import (  # noqa: F401 — re-export for pytest fixture discovery
    _disable_lifespan_services,
    _mock_celery_delay,
    _mock_clamav_clean,
    _use_in_memory_storage,
    db_session,
)
