"""
Regression tests for the public ad-hoc SQL surface.

Background: anonymous SQL could read host files and make the server fetch
internal URLs through SpatiaLite's XB_* functions, and crash it through
SqlProc_*. SpatiaLite was removed and plugins/harden_sqlite_connections.py
locks down every connection. Run these in the built image too
(`make test-image`) so they exercise Debian's SQLite build.
"""

import sqlite3

import pytest

from harden_sqlite_connections import MAX_SQL_BYTES, MAX_VALUE_BYTES


async def test_hardening_plugin_is_loaded(datasette):
    response = await datasette.client.get("/-/plugins.json")
    names = [p["name"] for p in response.json()]
    assert "harden_sqlite_connections.py" in names


@pytest.mark.parametrize(
    "sql",
    [
        "select fts3_tokenizer('simple')",
        "select FTS3_TOKENIZER('simple')",
        "select (select fts3_tokenizer('simple'))",
        "select load_extension('x')",
    ],
)
async def test_unsafe_functions_are_denied(query, sql):
    status, body = await query(sql)
    assert status == 400
    assert "not authorized" in body["error"]


async def test_spatialite_unsafe_functions_are_not_registered(query):
    # The original finding: XB_SchemaValidate(..., 'file:///etc/passwd').
    status, body = await query(
        "select XB_SchemaValidate(XB_Create(CAST('<a/>' AS BLOB)),"
        "'file:///etc/passwd')"
    )
    assert status == 400
    assert "no such function" in body["error"]

    status, body = await query(
        "select name from pragma_function_list"
        " where name like 'xb\\_%' escape '\\'"
        " or name like 'sqlproc\\_%' escape '\\'"
        " or name like 'storedproc\\_%' escape '\\'"
        " or name like 'zipfile\\_%' escape '\\'"
        " or name in ('readfile', 'writefile', 'proj_setdatabasepath')"
    )
    assert status == 200
    assert body["rows"] == []


@pytest.mark.parametrize(
    "sql, error",
    [
        ("attach database '/etc/passwd' as p", "Statement must be a SELECT"),
        ("select 1; select 2", "one statement at a time"),
    ],
)
async def test_non_select_statements_rejected(query, sql, error):
    status, body = await query(sql)
    assert status == 400
    assert error in body["error"]


async def test_connection_config_is_hardened(datasette):
    def read_settings(conn):
        return {
            "defensive": conn.getconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE),
            "trusted_schema": conn.getconfig(sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA),
            "fts3_tokenizer": conn.getconfig(
                sqlite3.SQLITE_DBCONFIG_ENABLE_FTS3_TOKENIZER
            ),
            "load_extension": conn.getconfig(
                sqlite3.SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION
            ),
            "attached": conn.getlimit(sqlite3.SQLITE_LIMIT_ATTACHED),
            "length": conn.getlimit(sqlite3.SQLITE_LIMIT_LENGTH),
            "sql_length": conn.getlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH),
        }

    settings = await datasette.get_database("testdb").execute_fn(read_settings)
    assert settings == {
        "defensive": True,
        "trusted_schema": False,
        "fts3_tokenizer": False,
        "load_extension": False,
        "attached": 0,
        "length": MAX_VALUE_BYTES,
        "sql_length": MAX_SQL_BYTES,
    }


async def test_attach_impossible_even_below_datasette(datasette):
    # Datasette's SELECT-only check is the first line of defence; the
    # connection itself must also refuse to attach anything.
    def try_attach(conn):
        try:
            conn.execute("attach database ':memory:' as extra")
        except sqlite3.OperationalError as e:
            return str(e)
        return None

    error = await datasette.get_database("testdb").execute_fn(try_attach)
    assert error is not None and "too many attached databases" in error


async def test_oversized_values_rejected(query):
    status, body = await query(
        f"select length(randomblob({MAX_VALUE_BYTES + 1})) as n"
    )
    assert status == 400
    assert "too big" in body["error"]


async def test_large_values_within_limit_allowed(query):
    status, body = await query("select length(randomblob(5000000)) as n")
    assert status == 200
    assert body["rows"] == [{"n": 5000000}]


async def test_ordinary_queries_still_work(query):
    status, body = await query("select count(*) as n from docs")
    assert (status, body["rows"]) == (200, [{"n": 2}])

    status, body = await query("select json_extract('{\"a\": 2}', '$.a') as v")
    assert (status, body["rows"]) == (200, [{"v": 2}])


async def test_views_work_with_untrusted_schema(query):
    status, body = await query("select body from upper_docs order by id")
    assert status == 200
    assert body["rows"] == [{"body": "HELLO WORLD"}, {"body": "OTHER TEXT"}]


async def test_full_text_search_still_works(query):
    status, body = await query(
        "select d.body from docs d join docs_fts f on f.rowid = d.id"
        " where docs_fts match 'hello'"
    )
    assert status == 200
    assert body["rows"] == [{"body": "hello world"}]


@pytest.mark.parametrize("path", ["/", "/testdb", "/testdb/docs", "/testdb/docs.json"])
async def test_pages_render(datasette, path):
    response = await datasette.client.get(path)
    assert response.status_code == 200
