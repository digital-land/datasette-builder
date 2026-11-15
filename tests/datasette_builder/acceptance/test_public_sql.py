"""
Acceptance criteria for the public ad-hoc SQL surface.

An anonymous visitor can browse and run read-only SQL over every published
dataset, including the SpatiaLite databases the pipeline produces. They must
not be able to:
- read files on the server or make it fetch URLs (the security finding used
  SpatiaLite's XB_SchemaValidate for both),
- discover datasets that aren't published,
- use SpatiaLite's functions or virtual tables at all,
- corrupt SQLite's memory (fts3_tokenizer), exhaust it, or crash the service
  (SqlProc_Execute segfaulted it).

These run against the deployable image, over HTTP, as a visitor would. The
attack queries run against both a plain and a SpatiaLite dataset, since
SpatiaLite is loaded for every database.
"""

import pytest

from tests.datasette_builder.acceptance.settings import (
    PUBLISHED_DATASET,
    SPATIAL_DATASET,
    UNPUBLISHED_DATASET,
)
from tests.datasette_builder.spatial_datasets import GEOMETRY

EVERY_DATASET = pytest.mark.parametrize("db", [PUBLISHED_DATASET, SPATIAL_DATASET])

# The file read from the security finding: the schema URI makes libxml2 open
# the file, and the validation error returns the start of its contents.
XML_FILE_READ = (
    "select XB_SchemaValidate(XB_Create(CAST('<a/>' AS BLOB)),"
    " 'file:///etc/passwd') as ok, XB_GetLastValidateError() as err"
)


def run_sql(client, sql, db=PUBLISHED_DATASET, fmt="json"):
    return client.get(f"/{db}.{fmt}", params={"sql": sql, "_shape": "objects"})


# --- Visitors can use every published dataset ---------------------------------


def test_visitors_can_query_published_datasets(client):
    response = run_sql(client, "select name from entity order by entity")
    assert response.status_code == 200
    assert response.json()["rows"] == [{"name": "hello world"}, {"name": "other text"}]


def test_spatialite_datasets_are_served(client):
    # Regression: without SpatiaLite loaded, Datasette refused to start at all
    # with a database like this ("It looks like you're trying to load a
    # SpatiaLite database without first loading the SpatiaLite module").
    databases = [db["name"] for db in client.get("/-/databases.json").json()]
    assert SPATIAL_DATASET in databases

    # Geometry stays available as text.
    response = run_sql(client, "select name, geometry from entity", db=SPATIAL_DATASET)
    assert response.status_code == 200
    assert response.json()["rows"] == [{"name": "spatial entity", "geometry": GEOMETRY}]


@pytest.mark.parametrize(
    "path",
    [
        "/",
        f"/{PUBLISHED_DATASET}",
        f"/{PUBLISHED_DATASET}/entity",
        f"/{SPATIAL_DATASET}",
        f"/{SPATIAL_DATASET}/entity",
        "/digital-land",
    ],
)
def test_pages_render(client, path):
    assert client.get(path).status_code == 200


def test_table_pages_use_the_custom_template(client):
    response = client.get(f"/{PUBLISHED_DATASET}/entity")
    assert "customised _table.html" in response.text


def test_the_plugin_is_installed_in_the_image(client):
    plugins = {p["name"]: p for p in client.get("/-/plugins.json").json()}
    assert plugins["datasette-builder"]["templates"] is True


# --- Visitors can't reach the server's files or network -----------------------


@EVERY_DATASET
def test_visitors_cannot_read_server_files(client, db):
    response = run_sql(client, XML_FILE_READ, db=db)
    assert response.status_code == 400
    assert "root:" not in response.text
    assert "not authorized" in response.json()["error"]


@EVERY_DATASET
def test_visitors_cannot_read_server_files_via_csv_export(client, db):
    # Datasette's CSV export answers a failed query with 200 and an empty body
    # rather than an error status, so check that nothing comes back.
    response = run_sql(client, XML_FILE_READ, db=db, fmt="csv")
    assert "root:" not in response.text
    assert response.text.strip() == ""

    # A query that works does return rows through the same route.
    assert run_sql(client, "select 1 as a", db=db, fmt="csv").text.split() == ["a", "1"]


@EVERY_DATASET
def test_visitors_cannot_make_the_server_fetch_urls(client, db):
    # The finding fetched the container metadata service this way.
    response = run_sql(
        client,
        "select XB_SchemaValidate(XB_Create(CAST('<a/>' AS BLOB)),"
        " 'http://169.254.170.2/v2/metadata')",
        db=db,
    )
    assert response.status_code == 400
    assert "not authorized" in response.json()["error"]


def test_visitors_cannot_discover_unpublished_datasets(client):
    assert client.get(f"/{UNPUBLISHED_DATASET}.json").status_code == 404

    databases = [db["name"] for db in client.get("/-/databases.json").json()]
    assert UNPUBLISHED_DATASET not in databases

    # The path-existence oracle from the finding: an existing file gave a
    # different error ("SQLite format 3") from a missing one.
    response = run_sql(
        client,
        "select XB_SchemaValidate(XB_Create(CAST('<a/>' AS BLOB)),"
        f" '/mnt/datasets/{UNPUBLISHED_DATASET}.sqlite3')",
    )
    assert response.status_code == 400
    assert "SQLite format 3" not in response.text


# --- Visitors can't use SpatiaLite --------------------------------------------


@pytest.mark.parametrize(
    "sql",
    [
        "select AsText(geometry_geom) from entity",
        "select ST_Area(geometry_geom) from entity",
        "select spatialite_version()",
        "select Zipfile_NumSHP('/etc/passwd')",
    ],
)
def test_visitors_cannot_call_spatialite_functions(client, sql):
    # None of SpatiaLite's functions are allowed, not just the dangerous ones.
    response = run_sql(client, sql, db=SPATIAL_DATASET)
    assert response.status_code == 400
    assert "not authorized" in response.json()["error"]


@pytest.mark.parametrize("table", ["SpatialIndex", "KNN2", "ElementaryGeometries"])
def test_visitors_cannot_query_spatialite_virtual_tables(client, table):
    response = run_sql(client, f"select * from {table}", db=SPATIAL_DATASET)
    assert response.status_code == 400
    assert "prohibited" in response.json()["error"]


# --- Visitors can't damage or crash the service -------------------------------


@EVERY_DATASET
@pytest.mark.parametrize(
    "sql",
    ["select fts3_tokenizer('simple')", "select load_extension('x')"],
)
def test_visitors_cannot_use_unsafe_sqlite_functions(client, db, sql):
    response = run_sql(client, sql, db=db)
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


@EVERY_DATASET
def test_the_service_survives_the_query_that_used_to_crash_it(client, db):
    response = run_sql(
        client, "select SqlProc_Execute(SqlProc_FromText('SELECT 1;'))", db=db
    )
    assert response.status_code == 400
    assert "not authorized" in response.json()["error"]
    assert client.get("/-/versions.json").status_code == 200
