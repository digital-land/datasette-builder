"""
Integration tests: Datasette with SpatiaLite loaded, as in production, serving a
database built the way the pipeline builds them.

What these check against:
- Serving: the pipeline's databases need SpatiaLite loaded, or Datasette won't
  start ("It looks like you're trying to load a SpatiaLite database without
  first loading the SpatiaLite module"). They must serve normally.
- Lockdown: every SQL function SpatiaLite registers must be denied to queries.
  The security finding used XB_SchemaValidate to read files and fetch internal
  URLs, and SqlProc_Execute crashed the server; the guard test below covers
  every SpatiaLite function, so a SpatiaLite upgrade can't add an unblocked one.
- Virtual tables from extensions (SpatialIndex, KNN or KNN2 depending on the
  SpatiaLite version, ElementaryGeometries, and any others) must not be
  readable, while SQLite's own rtree spatial indexes stay readable.

They need SpatiaLite (SQLITE_EXTENSIONS) and are skipped without it; they run in
`make docker-test` and CI.
"""

import sqlite3

import pytest
from datasette.utils import check_connection

from datasette_builder.hardening import (
    ALLOWED_FUNCTIONS,
    CORE_VIRTUAL_TABLE_MODULES,
    authorizer,
    virtual_table_module,
)
from tests.datasette_builder.spatial_datasets import GEOMETRY


async def test_spatialite_databases_pass_datasettes_startup_check(spatial_datasette):
    # The check `datasette serve` runs on every database before starting; this
    # is where "without first loading the SpatiaLite module" comes from.
    await spatial_datasette.get_database("spatial").execute_fn(check_connection)


async def test_datasette_needs_no_spatialite_functions_to_serve_pages(
    spatial_datasette,
):
    # Every page is served by queries that use only plain SQLite functions;
    # if Datasette needed a SpatiaLite function, these would fail.
    for path in [
        "/",
        "/spatial",
        "/spatial/entity",
        "/spatial/entity.json",
        "/spatial/geometry_columns.json",
        "/-/databases.json",
        "/-/versions.json",
    ]:
        response = await spatial_datasette.client.get(path)
        assert response.status_code == 200, path


async def test_every_spatialite_function_is_denied(spatial_datasette):
    def registered_functions(conn):
        return {row[0] for row in conn.execute("select name from pragma_function_list")}

    names = await spatial_datasette.get_database("spatial").execute_fn(
        registered_functions
    )
    spatialite_functions = {n for n in names if n.lower() not in ALLOWED_FUNCTIONS}

    # Sanity check that SpatiaLite really is loaded (it registers ~1,100).
    assert len(spatialite_functions) > 500
    allowed = [
        name
        for name in spatialite_functions
        if authorizer(sqlite3.SQLITE_FUNCTION, None, name, None, None)
        != sqlite3.SQLITE_DENY
    ]
    assert allowed == []


@pytest.mark.parametrize(
    "sql",
    [
        # The file read from the security finding.
        "select XB_SchemaValidate(XB_Create(CAST('<a/>' AS BLOB)),"
        " 'file:///etc/passwd'), XB_GetLastValidateError()",
        # The request to the container metadata service from the finding.
        "select XB_SchemaValidate(XB_Create(CAST('<a/>' AS BLOB)),"
        " 'http://169.254.170.2/v2/metadata')",
        # Crashed the server with a segfault.
        "select SqlProc_Execute(SqlProc_FromText('SELECT 1;'))",
        # Opens a zip file at any path.
        "select Zipfile_NumSHP('/etc/passwd')",
        # Read and change process-wide PROJ state.
        "select proj_setdatabasepath(NULL)",
        "select proj_getdatabasepath()",
        # Parses image metadata supplied in the query.
        "select GeomFromExifGpsBlob(NULL)",
        # Ordinary spatial functions are denied too.
        "select AsText(geometry_geom) from entity",
        "select spatialite_version()",
    ],
)
async def test_spatialite_functions_are_refused_over_http(spatial_query, sql):
    status, body = await spatial_query(sql)
    assert status == 400
    assert "not authorized" in body["error"]


@pytest.mark.parametrize(
    "sql",
    [
        "select * from SpatialIndex",
        "select * from KNN",
        "select * from KNN2",
        "select * from ElementaryGeometries",
    ],
)
async def test_spatialite_virtual_tables_are_refused(spatial_query, sql):
    status, body = await spatial_query(sql)
    assert status == 400
    assert "prohibited" in body["error"]


async def test_every_extension_virtual_table_is_refused(spatial_query):
    # Not a fixed list: every virtual table in the database whose module isn't
    # SQLite's own must be unreadable, whatever SpatiaLite version made it.
    status, body = await spatial_query(
        "select name, sql from sqlite_master"
        " where type = 'table' and sql like 'create virtual table%'"
    )
    assert status == 200
    tables = {row["name"]: virtual_table_module(row["sql"]) for row in body["rows"]}
    extension_tables = [
        name
        for name, module in tables.items()
        if module not in CORE_VIRTUAL_TABLE_MODULES
    ]
    # Sanity check: the fixture has SpatiaLite's tables, and rtree indexes.
    assert {"SpatialIndex", "KNN", "KNN2"} <= set(extension_tables)
    assert "rtree" in tables.values()

    for name in extension_tables:
        status, body = await spatial_query(f'select * from "{name}" limit 1')
        assert status == 400, name
        assert "prohibited" in body["error"], name


async def test_rtree_spatial_indexes_stay_readable(spatial_query):
    # CreateSpatialIndex makes core SQLite rtree tables, which are fine to read.
    status, body = await spatial_query(
        "select count(*) as n from idx_entity_geometry_geom"
    )
    assert (status, body["rows"]) == (200, [{"n": 1}])


@pytest.mark.parametrize("route", ["entity.json", "entity.csv"])
async def test_spatialite_functions_are_refused_in_table_filters(
    spatial_datasette, route
):
    # SQL in a table's _where filter reaches the same connection as the query
    # box, so SpatiaLite's functions must be refused there too.
    response = await spatial_datasette.client.get(
        f"/spatial/{route}", params={"_where": "XB_Create(NULL) is null"}
    )
    assert response.status_code == 400
    assert "not authorized" in response.text


async def test_spatial_datasets_can_still_be_queried(spatial_query):
    # Geometry stays available as text in the `geometry` column.
    status, body = await spatial_query("select name, geometry from entity")
    assert status == 200
    assert body["rows"] == [{"name": "spatial entity", "geometry": GEOMETRY}]
