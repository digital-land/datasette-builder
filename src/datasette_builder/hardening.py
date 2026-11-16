"""
Harden every SQLite connection Datasette opens.

Why: the public instance lets anonymous visitors run ad-hoc SELECTs. A security
finding showed that SpatiaLite's XML functions let such a query read files on
the server and make it fetch internal URLs (e.g. XB_SchemaValidate with a
'file:///etc/passwd' or 'http://169.254.170.2/...' schema URI), and that
SqlProc_Execute crashed the server. SpatiaLite can't simply be removed: the
pipeline builds every dataset database with SpatiaLite metadata, whose virtual
tables Datasette can't open without it. So SpatiaLite stays loaded, and public
SQL is locked down around it as far as SQLite allows.

Everything is applied from Python (an authorizer, sqlite3_db_config and
sqlite3_limit) when Datasette opens a connection, so none of it can be undone
from SQL.

1. Function allowlist (authorizer, SQLITE_FUNCTION)
   Queries may call only the functions plain SQLite provides, recorded from a
   fresh connection with no extensions loaded, plus Datasette's own
   escape_fts. Every function an extension adds - all ~1,100 of SpatiaLite's -
   is denied without being named, so a SpatiaLite upgrade can't add a new way
   out. SQLite checks the authorizer when each statement is prepared, including
   functions used inside views, so a denied function can't be reached
   indirectly. Datasette itself needs no SpatiaLite functions to serve pages.

   Two built-in functions are denied as well:
   - fts3_tokenizer: Debian's SQLite is compiled with
     SQLITE_ENABLE_FTS3_TOKENIZER. The function leaks a memory pointer, and its
     two-argument form replaces a tokenizer's function pointer, a known
     memory-corruption primitive.
   - load_extension: Datasette already disables it after loading SpatiaLite;
     denied as a backstop.

2. Extension virtual tables (authorizer, SQLITE_READ)
   A virtual table runs its module's code whenever it's queried. SpatiaLite's
   InitSpatialMetadata creates several (SpatialIndex, ElementaryGeometries,
   and KNN or KNN2 depending on the SpatiaLite version that built the file).
   Nothing Datasette serves needs them. When a connection is hardened, its
   database schema is read and every virtual table whose module isn't one of
   SQLite's own (full-text search and rtree) is made unreadable, so tables
   from any SpatiaLite version are covered without naming them. Definitions
   that can't be parsed are treated the same way. Ordinary tables, full-text
   search tables and rtree spatial indexes stay readable. A fixed list of
   SpatiaLite's table names is denied on every connection as a backstop.

3. Connection config (sqlite3_db_config)
   - DEFENSIVE on: no writable_schema or shadow-table corruption tricks.
   - TRUSTED_SCHEMA off: views and triggers stored in a database file can't
     call functions that aren't marked innocuous, which limits what a tampered
     dataset file could do.
   - ENABLE_FTS3_TOKENIZER off: a second layer for the fts3_tokenizer write form.
   - ENABLE_LOAD_EXTENSION off: no further extensions once this hook has run.

4. Limits (sqlite3_limit)
   - ATTACHED = 0: the connection can never attach another database file, even
     if Datasette's SELECT-only check were bypassed. (We don't use --crossdb.)
   - LENGTH: cap on any single string or blob, so a query like randomblob(1e9)
     can't exhaust memory. 100 MB is ~4.5x the largest real value (the border
     dataset's geometry, ~22 MB).
   - SQL_LENGTH: cap on the size of a submitted SQL statement.

Requires Python 3.12+ (Connection.setconfig).
"""

import re
import sqlite3

from datasette import hookimpl


def _plain_sqlite_functions():
    """Names of the functions this SQLite library provides with no extensions."""
    conn = sqlite3.connect(":memory:")
    try:
        names = {
            row[0].lower()
            for row in conn.execute("select name from pragma_function_list")
        }
    finally:
        conn.close()
    if not names:
        # Fail closed: without the list, the allowlist would deny nothing useful
        # and everything else - better to stop Datasette starting.
        raise RuntimeError("Could not list SQLite's built-in functions")
    return frozenset(names)


# Built-in functions that are unsafe for public queries (see module docstring).
DENIED_BUILTIN_FUNCTIONS = frozenset({"fts3_tokenizer", "load_extension"})

# Functions Datasette registers itself and needs: escape_fts builds the
# full-text search queries behind ?_search=.
DATASETTE_FUNCTIONS = frozenset({"escape_fts"})

ALLOWED_FUNCTIONS = (
    _plain_sqlite_functions() - DENIED_BUILTIN_FUNCTIONS
) | DATASETTE_FUNCTIONS

# Virtual table modules built into SQLite. Tables using any other module are
# made unreadable (see module docstring).
CORE_VIRTUAL_TABLE_MODULES = frozenset({"fts3", "fts4", "fts5", "rtree", "rtree_i32"})

# SpatiaLite's virtual table names, denied on every connection as a backstop.
DENIED_TABLES = frozenset({"spatialindex", "knn", "knn2", "elementarygeometries"})

_VIRTUAL_TABLE_MODULE = re.compile(
    r"^\s*create\s+virtual\s+table\s+.+?\s+using\s+[\"'`\[]?(\w+)",
    re.IGNORECASE | re.DOTALL,
)

DB_CONFIG = (
    (sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True),
    (sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA, False),
    (sqlite3.SQLITE_DBCONFIG_ENABLE_FTS3_TOKENIZER, False),
    (sqlite3.SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION, False),
)

MAX_VALUE_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_SQL_BYTES = 1024 * 1024  # 1 MB

LIMITS = (
    (sqlite3.SQLITE_LIMIT_ATTACHED, 0),
    (sqlite3.SQLITE_LIMIT_LENGTH, MAX_VALUE_BYTES),
    (sqlite3.SQLITE_LIMIT_SQL_LENGTH, MAX_SQL_BYTES),
)


def virtual_table_module(create_sql):
    """The module a CREATE VIRTUAL TABLE statement uses, or None if unparseable."""
    match = _VIRTUAL_TABLE_MODULE.match(create_sql or "")
    return match.group(1).lower() if match else None


def extension_virtual_tables(conn):
    """Names of virtual tables in conn's database that don't use a core module."""
    rows = conn.execute(
        "select name, sql from sqlite_master"
        " where type = 'table' and sql like 'create virtual table%'"
    ).fetchall()
    return frozenset(
        name.lower()
        for name, create_sql in rows
        if virtual_table_module(create_sql) not in CORE_VIRTUAL_TABLE_MODULES
    )


def make_authorizer(denied_tables):
    def authorizer(action, arg1, arg2, db_name, trigger_or_view):
        # SQLITE_FUNCTION: arg2 is the function name.
        if action == sqlite3.SQLITE_FUNCTION:
            if (arg2 or "").lower() not in ALLOWED_FUNCTIONS:
                return sqlite3.SQLITE_DENY
        # SQLITE_READ: arg1 is the table name, arg2 the column.
        elif action == sqlite3.SQLITE_READ:
            if (arg1 or "").lower() in denied_tables:
                return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    return authorizer


# The authorizer with only the fixed table list, for callers without a schema.
authorizer = make_authorizer(DENIED_TABLES)


def harden(conn):
    for option, enabled in DB_CONFIG:
        conn.setconfig(option, enabled)
    for category, limit in LIMITS:
        conn.setlimit(category, limit)
    # Read the schema before the authorizer is installed.
    denied_tables = DENIED_TABLES | extension_virtual_tables(conn)
    conn.set_authorizer(make_authorizer(denied_tables))


@hookimpl
def prepare_connection(conn):
    harden(conn)
