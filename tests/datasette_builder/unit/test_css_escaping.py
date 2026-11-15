"""
Unit tests for datasette_builder.css_escaping.

What these check against: a value placed inside a CSS string must never be able
to end the string or the rule around it, whatever characters it contains.
"""

import re

import pytest

from datasette_builder.css_escaping import escape_css_string

# What escaped output may contain: allowlisted characters, and backslash
# escapes of exactly six hex digits.
ESCAPED = re.compile(r"(?:[A-Za-z0-9 _-]|\\[0-9A-F]{6})*")


@pytest.mark.parametrize(
    "value", ["entity", "start_date", "Entry date", "end-date", "a1"]
)
def test_ordinary_column_names_are_unchanged(value):
    assert escape_css_string(value) == value


@pytest.mark.parametrize(
    "character, escaped",
    [
        ("\r", "\\00000D"),  # carriage return: Datasette's own filter missed this
        ("\n", "\\00000A"),
        ("\f", "\\00000C"),
        ('"', "\\000022"),
        ("'", "\\000027"),
        ("\\", "\\00005C"),
        ("{", "\\00007B"),
        ("}", "\\00007D"),
        (";", "\\00003B"),
        (":", "\\00003A"),
        ("/", "\\00002F"),
        ("<", "\\00003C"),
        (">", "\\00003E"),
        ("&", "\\000026"),
        ("é", "\\0000E9"),
        ("🗺", "\\01F5FA"),  # outside the Basic Multilingual Plane
    ],
)
def test_everything_else_is_escaped(character, escaped):
    assert escape_css_string(f"a{character}b") == f"a{escaped}b"


def test_output_can_never_end_the_css_string():
    every_character = "".join(chr(code) for code in range(1, 0x3000))
    escaped = escape_css_string(every_character)
    assert ESCAPED.fullmatch(escaped)
    for terminator in ['"', "'", "\r", "\n", "\f", "{", "}", ";", "<"]:
        assert terminator not in escaped


def test_non_strings_are_escaped_as_text():
    assert escape_css_string(1) == "1"
