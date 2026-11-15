"""
Integration tests: column names in the pages' inline stylesheet.

What these check against: the query page labels each result column in an
inline stylesheet, using column names that come from the visitor's own SQL.
Whatever an alias contains, the stylesheet must keep exactly one rule per
column, with the name escaped inside it.
"""

import re

from datasette_builder.css_escaping import escape_css_string

# Characters that end a CSS string or rule, plus quotes and a backslash.
HOSTILE_ALIAS = "x\r\n\f\"'\\{}}y"


def column_label_styles(html):
    """The inline style block that holds the column labels."""
    blocks = re.findall(r"<style>(.*?)</style>", html, flags=re.DOTALL)
    return next(block for block in blocks if "td:nth-of-type" in block)


async def test_the_plugins_filter_is_the_one_templates_use(datasette):
    # Datasette runs prepare_jinja2_environment at startup, before it serves
    # any request (`datasette serve` does this before accepting connections).
    await datasette.invoke_startup()
    assert datasette.jinja_env.filters["escape_css_string"] is escape_css_string


async def test_query_page_escapes_column_names_in_its_stylesheet(datasette):
    response = await datasette.client.get(
        "/testdb", params={"sql": f"select 1 as `{HOSTILE_ALIAS}`, 2 as plain"}
    )
    assert response.status_code == 200
    styles = column_label_styles(response.text)

    # One rule per column, each with its name escaped.
    assert styles.count("content:") == 2
    assert f'content: "{escape_css_string(HOSTILE_ALIAS)}"' in styles
    assert 'content: "plain"' in styles
    # Nothing in the stylesheet came through raw.
    assert "\r" not in styles
    assert "\f" not in styles
    assert styles.count("{") == styles.count("}")


async def test_table_page_labels_are_unchanged_for_ordinary_names(datasette):
    response = await datasette.client.get("/testdb/entity")
    styles = column_label_styles(response.text)
    assert 'content: "name"' in styles
