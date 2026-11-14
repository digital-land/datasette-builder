"""Integration tests: the plugin wired into Datasette, exercised in-process."""

import sqlite3

import pytest

from datasette_builder.hardening import MAX_SQL_BYTES, MAX_VALUE_BYTES


async def test_plugin_is_loaded_from_its_entry_point(datasette):
    response = await datasette.client.get("/-/plugins.json")
    plugins = {p["name"]: p for p in response.json()}
    assert "datasette-builder" in plugins
    assert plugins["datasette-builder"]["hooks"] == ["prepare_connection"]
    assert plugins["datasette-builder"]["templates"] is True


async def test_datasette_connections_are_hardened(datasette):
    def read_settings(conn):
        return {
            "defensive": conn.getconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE),
            "trusted_schema": conn.getconfig(sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA),
            "attached": conn.getlimit(sqlite3.SQLITE_LIMIT_ATTACHED),
            "length": conn.getlimit(sqlite3.SQLITE_LIMIT_LENGTH),
            "sql_length": conn.getlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH),
        }

    settings = await datasette.get_database("testdb").execute_fn(read_settings)
    assert settings == {
        "defensive": True,
        "trusted_schema": False,
        "attached": 0,
        "length": MAX_VALUE_BYTES,
        "sql_length": MAX_SQL_BYTES,
    }


@pytest.mark.parametrize(
    "sql", ["select fts3_tokenizer('simple')", "select load_extension('x')"]
)
async def test_unsafe_functions_are_refused_over_http(query, sql):
    status, body = await query(sql)
    assert status == 400
    assert "not authorized" in body["error"]


@pytest.mark.parametrize(
    "sql, error",
    [
        ("attach database '/etc/passwd' as p", "Statement must be a SELECT"),
        ("select 1; select 2", "one statement at a time"),
    ],
)
async def test_non_select_statements_are_refused(query, sql, error):
    status, body = await query(sql)
    assert status == 400
    assert error in body["error"]


async def test_ordinary_queries_views_and_search_work(query):
    status, body = await query("select count(*) as n from entity")
    assert (status, body["rows"]) == (200, [{"n": 2}])

    status, body = await query("select name from entity_upper order by entity")
    assert (status, body["rows"]) == (
        200,
        [{"name": "HELLO WORLD"}, {"name": "OTHER TEXT"}],
    )

    status, body = await query(
        "select e.name from entity e join entity_fts f on f.rowid = e.entity"
        " where entity_fts match 'hello'"
    )
    assert (status, body["rows"]) == (200, [{"name": "hello world"}])


async def test_table_pages_use_the_custom_template(datasette):
    response = await datasette.client.get("/testdb/entity")
    assert response.status_code == 200
    assert "customised _table.html" in response.text


@pytest.mark.parametrize(
    "path", ["/", "/testdb", "/testdb/entity", "/testdb/entity.json"]
)
async def test_pages_render(datasette, path):
    response = await datasette.client.get(path)
    assert response.status_code == 200
