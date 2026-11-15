"""
Datasette plugin for the planning data Datasette instance.

Registered through the ``datasette`` entry point in pyproject.toml, so
Datasette loads it whenever the package is installed:

- hooks: SQLite connection hardening (see hardening.py)
- templates/: template overrides, which Datasette searches before its defaults
"""

from datasette_builder.hardening import prepare_connection

__all__ = ["prepare_connection"]
