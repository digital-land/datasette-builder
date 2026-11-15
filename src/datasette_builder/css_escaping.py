"""
Strict escaping for values Datasette's templates place inside CSS strings.

Why: the query, table and row pages build an inline stylesheet that labels
each column for narrow screens:

    .rows-and-columns td:nth-of-type(1):before { content: "<column name>"; }

On the query page the column names come from the visitor's own SQL (column
aliases). Datasette 0.65's escape_css_string filter escapes only quotes,
backslashes and line feeds, and leaves a lone carriage return as it is. A
carriage return ends a CSS string, so an alias containing one let anything
after it be read by the browser as real style rules - enough to restyle or
cover the page, load images from another site, or probe page content - from a
link to this site.

This replaces the filter with an allowlist: letters, digits, space, hyphen and
underscore pass through, and every other character becomes a six-digit CSS
escape (\\XXXXXX). Nothing a visitor supplies can end the string or the rule,
including characters nobody has thought of yet. Browsers decode the escapes,
so column labels look the same on screen.

Datasette registers its own filter and then runs the prepare_jinja2_environment
plugin hook, so this replacement is what every template uses.
"""

import re

from datasette import hookimpl

_SAFE_CHARACTER = re.compile(r"[A-Za-z0-9 _-]")


def escape_css_string(value):
    return "".join(
        character if _SAFE_CHARACTER.fullmatch(character) else f"\\{ord(character):06X}"
        for character in str(value)
    )


@hookimpl
def prepare_jinja2_environment(env, datasette):
    env.filters["escape_css_string"] = escape_css_string
