"""Unit tests for datasette_builder.hardening on plain sqlite3 connections."""

import sqlite3

import pytest

from datasette_builder.hardening import (
    MAX_SQL_BYTES,
    MAX_VALUE_BYTES,
    authorizer,
    harden,
)


@pytest.fixture
def conn():
    conn = sqlite3.connect(":memory:")
    harden(conn)
    yield conn
    conn.close()


@pytest.mark.parametrize("name", ["fts3_tokenizer", "FTS3_TOKENIZER", "load_extension"])
def test_authorizer_denies_unsafe_functions(name):
    assert (
        authorizer(sqlite3.SQLITE_FUNCTION, None, name, None, None)
        == sqlite3.SQLITE_DENY
    )


@pytest.mark.parametrize(
    "action, arg2",
    [
        (sqlite3.SQLITE_FUNCTION, "upper"),
        (sqlite3.SQLITE_FUNCTION, "json_extract"),
        (sqlite3.SQLITE_FUNCTION, None),
        # Non-function actions are never denied, even if arg2 matches a name.
        (sqlite3.SQLITE_READ, "fts3_tokenizer"),
        (sqlite3.SQLITE_SELECT, None),
    ],
)
def test_authorizer_allows_everything_else(action, arg2):
    assert authorizer(action, None, arg2, None, None) == sqlite3.SQLITE_OK


@pytest.mark.parametrize(
    "sql",
    [
        "select fts3_tokenizer('simple')",
        "select FTS3_TOKENIZER('simple')",
        "select (select fts3_tokenizer('simple'))",
        "select load_extension('x')",
    ],
)
def test_unsafe_functions_fail_to_prepare(conn, sql):
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        conn.execute(sql)


def test_unsafe_functions_denied_inside_views(conn):
    conn.execute("create temp view leak as select fts3_tokenizer('simple') as p")
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        conn.execute("select * from leak")


def test_connection_config(conn):
    assert conn.getconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE) is True
    assert conn.getconfig(sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA) is False
    assert conn.getconfig(sqlite3.SQLITE_DBCONFIG_ENABLE_FTS3_TOKENIZER) is False
    assert conn.getconfig(sqlite3.SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION) is False


def test_connection_limits(conn):
    assert conn.getlimit(sqlite3.SQLITE_LIMIT_ATTACHED) == 0
    assert conn.getlimit(sqlite3.SQLITE_LIMIT_LENGTH) == MAX_VALUE_BYTES
    assert conn.getlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH) == MAX_SQL_BYTES


def test_attach_is_impossible(conn):
    with pytest.raises(sqlite3.OperationalError, match="too many attached databases"):
        conn.execute("attach database ':memory:' as extra")


def test_values_over_the_limit_are_rejected(conn):
    with pytest.raises(sqlite3.DataError, match="too big"):
        conn.execute(f"select randomblob({MAX_VALUE_BYTES + 1})").fetchone()


def test_large_values_within_the_limit_are_allowed(conn):
    assert conn.execute("select length(randomblob(5000000))").fetchone() == (5000000,)


def test_sql_over_the_limit_is_rejected(conn):
    sql = "select '" + "x" * MAX_SQL_BYTES + "'"
    # Python's sqlite3 enforces the connection's SQL length limit before SQLite does.
    with pytest.raises(sqlite3.DataError, match="query string is too large"):
        conn.execute(sql)


def test_ordinary_sql_still_works(conn):
    conn.executescript(
        """
        create table t (name text);
        insert into t values ('a'), ('b');
        create view t_upper as select upper(name) as name from t;
        """
    )
    assert conn.execute("select name from t_upper order by name").fetchall() == [
        ("A",),
        ("B",),
    ]
    assert conn.execute("""select json_extract('{"a": 2}', '$.a')""").fetchone() == (2,)
