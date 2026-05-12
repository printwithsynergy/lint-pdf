"""Bundled alembic configuration + migrations.

Shipped inside the lintpdf wheel so the runtime can `lintpdf migrate` without
needing the upstream repo on disk. The CLI in `lintpdf.cli` resolves
`alembic.ini` and `alembic/` via `importlib.resources.files(__name__)`.
"""
