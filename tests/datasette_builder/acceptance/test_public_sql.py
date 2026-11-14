"""
Acceptance criteria for the public ad-hoc SQL surface.

An anonymous visitor can run read-only SQL over published datasets, but must
not be able to read files on the server, make the server fetch URLs, discover
datasets that aren't published, corrupt SQLite's memory or crash the service.
These run against the deployable image, over HTTP, as a visitor would.
"""

import pytest

from tests.datasette_builder.acceptance.settings import (
    PUBLISHED_DATASET,
    UNPUBLISHED_DATASET,
)

XML_FILE_READ = (
    "select XB_SchemaValidate(XB_Create(CAST('<a/>' AS BLOB)),"
    " 'file:///etc/passwd') as ok, XB_GetLastValidateError() as err"
)


def run_sql(client, sql, db=PUBLISHED_DATASET, fmt="json"):
    return client.get(f"/{db}.{fmt}", params={"sql": sql, "_shape": "objects"})


def test_visitors_can_query_published_datasets(client):
    response = run_sql(client, "select name from entity order by entity")
    assert response.status_code == 200
    assert response.json()["rows"] == [{"name": "hello world"}, {"name": "other text"}]


def test_visitors_cannot_read_server_files(client):
    response = run_sql(client, XML_FILE_READ)
    assert response.status_code == 400
    assert "root:" not in response.text
    assert "no such function" in response.json()["error"]


def test_visitors_cannot_read_server_files_via_csv_export(client):
    # Datasette's CSV export answers a failed query with 200 and an empty body
    # rather than an error status, so check that nothing comes back.
    response = run_sql(client, XML_FILE_READ, fmt="csv")
    assert "root:" not in response.text
    assert response.text.strip() == ""

    # A query that works does return rows through the same route.
    assert run_sql(client, "select 1 as a", fmt="csv").text.split() == ["a", "1"]


def test_visitors_cannot_make_the_server_fetch_urls(client):
    response = run_sql(
        client,
        "select XB_SchemaValidate(XB_Create(CAST('<a/>' AS BLOB)),"
        " 'http://169.254.170.2/v2/metadata')",
    )
    assert response.status_code == 400
    assert "no such function" in response.json()["error"]


def test_visitors_cannot_discover_unpublished_datasets(client):
    assert client.get(f"/{UNPUBLISHED_DATASET}.json").status_code == 404

    databases = [db["name"] for db in client.get("/-/databases.json").json()]
    assert UNPUBLISHED_DATASET not in databases

    # The path-existence oracle from the original finding.
    response = run_sql(
        client,
        "select XB_SchemaValidate(XB_Create(CAST('<a/>' AS BLOB)),"
        f" '/mnt/datasets/{UNPUBLISHED_DATASET}.sqlite3')",
    )
    assert response.status_code == 400
    assert "SQLite format 3" not in response.text


@pytest.mark.parametrize(
    "sql",
    ["select fts3_tokenizer('simple')", "select load_extension('x')"],
)
def test_visitors_cannot_use_unsafe_sqlite_functions(client, sql):
    response = run_sql(client, sql)
    assert response.status_code == 400
    assert "not authorized" in response.json()["error"]


@pytest.mark.parametrize(
    "sql",
    [
        "attach database '/etc/passwd' as p",
        "select 1; attach database '/etc/passwd' as p",
    ],
)
def test_visitors_cannot_run_statements_other_than_select(client, sql):
    assert run_sql(client, sql).status_code == 400


def test_visitors_cannot_exhaust_memory_with_huge_values(client):
    response = run_sql(client, "select length(randomblob(200000000)) as n")
    assert response.status_code == 400
    assert "too big" in response.json()["error"]


def test_the_service_survives_the_query_that_used_to_crash_it(client):
    response = run_sql(client, "select SqlProc_Execute(SqlProc_FromText('SELECT 1;'))")
    assert response.status_code == 400
    assert "no such function" in response.json()["error"]
    assert client.get("/-/versions.json").status_code == 200


def test_the_plugin_is_installed_in_the_image(client):
    plugins = {p["name"]: p for p in client.get("/-/plugins.json").json()}
    assert plugins["datasette-builder"]["templates"] is True


@pytest.mark.parametrize(
    "path",
    ["/", f"/{PUBLISHED_DATASET}", f"/{PUBLISHED_DATASET}/entity", "/digital-land"],
)
def test_pages_render(client, path):
    assert client.get(path).status_code == 200


def test_table_pages_use_the_custom_template(client):
    response = client.get(f"/{PUBLISHED_DATASET}/entity")
    assert "customised _table.html" in response.text
