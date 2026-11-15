"""
Datasette plugin for the planning data Datasette instance.

Registered through the ``datasette`` entry point in pyproject.toml, so
Datasette loads it whenever the package is installed:

- hardening.py: locks down every SQLite connection used for public queries
- read_only.py: refuses HTTP requests that could change state
- css_escaping.py: strict escaping for values the templates put inside CSS
- templates/: template overrides, which Datasette searches before its defaults
"""

from datasette_builder.css_escaping import prepare_jinja2_environment
from datasette_builder.hardening import prepare_connection
from datasette_builder.read_only import asgi_wrapper

__all__ = ["asgi_wrapper", "prepare_connection", "prepare_jinja2_environment"]
