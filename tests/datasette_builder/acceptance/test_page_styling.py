"""
Acceptance criteria: a link to the site can't change how its pages look.

The query page puts the result column names - which come from the SQL in the
link - into an inline stylesheet. Whatever those names contain, the page must
keep its own styling: exactly one escaped label rule per column, nothing more.
Runs against the deployable image, over HTTP.
"""

import re

from tests.datasette_builder.acceptance.settings import PUBLISHED_DATASET

HOSTILE_ALIAS = "x\r\n\f\"'\\{}}y"


def column_label_styles(html):
    blocks = re.findall(r"<style>(.*?)</style>", html, flags=re.DOTALL)
    return next(block for block in blocks if "td:nth-of-type" in block)


def test_column_names_from_a_link_cant_add_style_rules(client):
    response = client.get(
        f"/{PUBLISHED_DATASET}",
        params={"sql": f"select 1 as `{HOSTILE_ALIAS}`, 2 as plain"},
    )
    assert response.status_code == 200
    styles = column_label_styles(response.text)

    assert styles.count("content:") == 2
    assert "\r" not in styles
    assert "\f" not in styles
    assert styles.count("{") == styles.count("}")
    # The carriage return arrives escaped, not raw.
    assert "\\00000D" in styles
