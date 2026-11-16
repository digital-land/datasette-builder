"""
Unit tests for datasette_builder.hardening, on plain sqlite3 connections.

These don't need SpatiaLite. Functions registered with create_function stand
in for an extension's functions: to SQLite's authorizer they look the same, so
if they're denied here, SpatiaLite's are denied in production. The SpatiaLite
build itself is checked in tests/datasette_builder/integration/test_spatialite.py.
"""

import sqlite3

import pytest

from datasette_builder.hardening import (
    ALLOWED_FUNCTIONS,
    DENIED_BUILTIN_FUNCTIONS,
    DENIED_TABLES,
    MAX_SQL_BYTES,
    MAX_VALUE_BYTES,
    authorizer,
    extension_virtual_tables,
    harden,
    make_authorizer,
    virtual_table_module,
)

# Names of real SpatiaLite functions from the security finding and our own
# testing, registered here as harmless stand-ins.
EXTENSION_FUNCTIONS = [
    "XB_Create",  # used to build the XML document in the file-read exploit
    "XB_SchemaValidate",  # read files / fetched URLs via its schema URI
    "XB_GetLastValidateError",  # returned the file contents in the exploit
    "SqlProc_Execute",  # runs arbitrary SQL text; crashed the server
    "Zipfile_NumSHP",  # opens a zip file at any path
    "PROJ_SetDatabasePath",  # changes process-wide state
    "AsText",  # ordinary spatial function: denied too, nothing is allowed by default
]


@pytest.fixture
def conn():
    conn = sqlite3.connect(":memory:")
    for name in EXTENSION_FUNCTIONS:
        conn.create_function(name, -1, lambda *args: "extension function ran")
    harden(conn)
    yield conn
    conn.close()


# --- The function allowlist ---------------------------------------------------


def test_allowlist_is_plain_sqlites_functions():
    # Built from a connection with no extensions, so it must contain SQLite's
    # own functions and nothing that only an extension provides.
    assert {"count", "upper", "json_extract", "substr", "length"} <= ALLOWED_FUNCTIONS
    assert not {name.lower() for name in EXTENSION_FUNCTIONS} & ALLOWED_FUNCTIONS


def test_allowlist_includes_datasettes_own_function():
    # Datasette's ?_search= builds its query with escape_fts.
    assert "escape_fts" in ALLOWED_FUNCTIONS


def test_unsafe_builtin_functions_are_not_allowed():
    assert DENIED_BUILTIN_FUNCTIONS == {"fts3_tokenizer", "load_extension"}
    assert not DENIED_BUILTIN_FUNCTIONS & ALLOWED_FUNCTIONS


@pytest.mark.parametrize("name", EXTENSION_FUNCTIONS)
def test_extension_functions_are_denied(conn, name):
    # Anything not in plain SQLite is refused when the statement is prepared,
    # so it never runs, whatever its arguments.
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        conn.execute(f"select {name}('x')")


@pytest.mark.parametrize("name", ["xb_schemavalidate", "XB_SCHEMAVALIDATE"])
def test_function_names_are_matched_case_insensitively(conn, name):
    # SQL function names are case-insensitive, so the check must be too.
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        conn.execute(f"select {name}('x')")


@pytest.mark.parametrize(
    "sql",
    [
        "select fts3_tokenizer('simple')",  # leaks a memory pointer
        "select FTS3_TOKENIZER('simple')",
        "select load_extension('x')",
    ],
)
def test_unsafe_builtin_functions_are_denied(conn, sql):
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        conn.execute(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "select (select XB_SchemaValidate('x'))",  # inside a subquery
        "select upper(XB_GetLastValidateError())",  # as an argument
        "select 1 where XB_Create('x') is not null",  # in a WHERE clause
    ],
)
def test_denied_functions_cant_be_reached_indirectly(conn, sql):
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        conn.execute(sql)


def test_denied_functions_cant_be_reached_through_a_view(conn):
    # A view stored in a dataset file can't be used to call a denied function.
    conn.execute("create temp view leak as select XB_SchemaValidate('x') as v")
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        conn.execute("select * from leak")


def test_authorizer_ignores_other_actions():
    # Only function calls are checked against the allowlist.
    assert (
        authorizer(sqlite3.SQLITE_SELECT, None, None, None, None) == sqlite3.SQLITE_OK
    )
    assert (
        authorizer(sqlite3.SQLITE_READ, "entity", "XB_Create", "main", None)
        == sqlite3.SQLITE_OK
    )


# --- SpatiaLite's virtual tables ----------------------------------------------


@pytest.mark.parametrize(
    "table", ["SpatialIndex", "KNN", "KNN2", "ElementaryGeometries"]
)
def test_spatialite_virtual_table_names_are_always_denied(table):
    # The fixed backstop list: these run SpatiaLite code when queried and
    # nothing we serve needs them. KNN and KNN2 come from different SpatiaLite
    # versions. (The integration tests query real ones.)
    assert table.lower() in DENIED_TABLES
    assert (
        authorizer(sqlite3.SQLITE_READ, table, "rowid", "main", None)
        == sqlite3.SQLITE_DENY
    )


@pytest.mark.parametrize(
    "create_sql, module",
    [
        ("CREATE VIRTUAL TABLE KNN USING VirtualKNN()", "virtualknn"),
        ("create virtual table x using fts5(name)", "fts5"),
        ('CREATE VIRTUAL TABLE "idx_entity_geom" USING rtree(pkid, xmin)', "rtree"),
        ('CREATE VIRTUAL TABLE t USING "Quoted"(a)', "quoted"),
        ("CREATE VIRTUAL TABLE\n  t\n  USING\n  fts4(a)", "fts4"),
        ("not a virtual table", None),
        (None, None),
    ],
)
def test_virtual_table_module_is_read_from_the_definition(create_sql, module):
    assert virtual_table_module(create_sql) == module


class StandInSchema:
    """A connection whose sqlite_master holds the given virtual tables."""

    def __init__(self, rows):
        self.rows = rows

    def execute(self, sql):
        return self

    def fetchall(self):
        return self.rows


def test_virtual_tables_from_extensions_are_found():
    schema = StandInSchema(
        [
            ("KNN", "CREATE VIRTUAL TABLE KNN USING VirtualKNN()"),
            ("Future", "CREATE VIRTUAL TABLE Future USING VirtualSomethingNew()"),
            ("Broken", "CREATE VIRTUAL TABLE Broken"),  # unparseable: denied
            ("entity_fts", "CREATE VIRTUAL TABLE entity_fts USING fts5(name)"),
            ("idx_geom", "CREATE VIRTUAL TABLE idx_geom USING rtree(pkid, x1, x2)"),
        ]
    )
    assert extension_virtual_tables(schema) == {"knn", "future", "broken"}


def test_sqlites_own_virtual_tables_stay_readable():
    # Full-text search and rtree spatial indexes are core SQLite and are used
    # by the published datasets, so they must not be caught by the denial.
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        create virtual table docs using fts5(body);
        insert into docs values ('hello world');
        create virtual table idx using rtree(id, minx, maxx);
        insert into idx values (1, 0, 1);
        """
    )
    harden(conn)
    assert conn.execute("select body from docs where docs match 'hello'").fetchall()
    assert conn.execute("select id from idx").fetchall() == [(1,)]
    conn.close()


def test_denied_tables_apply_per_connection():
    denied = make_authorizer(DENIED_TABLES | {"future"})
    assert (
        denied(sqlite3.SQLITE_READ, "Future", "x", "main", None) == sqlite3.SQLITE_DENY
    )
    assert denied(sqlite3.SQLITE_READ, "entity", "x", "main", None) == sqlite3.SQLITE_OK


def test_other_tables_can_be_read(conn):
    conn.execute("create table entity (name text)")
    conn.execute("insert into entity values ('a')")
    assert conn.execute("select name from entity").fetchall() == [("a",)]


# --- Connection config and limits ---------------------------------------------


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
    # Even below Datasette's SELECT-only check, no other file can be attached.
    with pytest.raises(sqlite3.OperationalError, match="too many attached databases"):
        conn.execute("attach database ':memory:' as extra")


def test_values_over_the_limit_are_rejected(conn):
    with pytest.raises(sqlite3.DataError, match="too big"):
        conn.execute(f"select randomblob({MAX_VALUE_BYTES + 1})").fetchone()


def test_large_values_within_the_limit_are_allowed(conn):
    # Large geometries must still work.
    assert conn.execute("select length(randomblob(5000000))").fetchone() == (5000000,)


def test_sql_over_the_limit_is_rejected(conn):
    sql = "select '" + "x" * MAX_SQL_BYTES + "'"
    # Python's sqlite3 enforces the connection's SQL length limit before SQLite does.
    with pytest.raises(sqlite3.DataError, match="query string is too large"):
        conn.execute(sql)


# --- What must keep working ---------------------------------------------------


def test_ordinary_sql_still_works(conn):
    conn.executescript(
        """
        create table t (name text);
        insert into t values ('a'), ('b');
        create view t_upper as select upper(name) as name from t;
        """
    )
    rows = conn.execute("select name from t_upper order by name").fetchall()
    assert rows == [("A",), ("B",)]
    assert conn.execute("""select json_extract('{"a": 2}', '$.a')""").fetchone() == (2,)
    assert conn.execute("select count(*), max(name) from t").fetchone() == (2, "b")
