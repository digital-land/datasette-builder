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

2. SpatiaLite virtual tables (authorizer, SQLITE_READ)
   InitSpatialMetadata creates SpatialIndex, KNN2 and ElementaryGeometries,
   which run SpatiaLite code when queried. Nothing Datasette serves needs them,
   so reading them is denied.

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

# Virtual tables created by SpatiaLite's InitSpatialMetadata.
DENIED_TABLES = frozenset({"spatialindex", "knn2", "elementarygeometries"})

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


def authorizer(action, arg1, arg2, db_name, trigger_or_view):
    # SQLITE_FUNCTION: arg2 is the function name.
    if action == sqlite3.SQLITE_FUNCTION:
        if (arg2 or "").lower() not in ALLOWED_FUNCTIONS:
            return sqlite3.SQLITE_DENY
    # SQLITE_READ: arg1 is the table name, arg2 the column.
    elif action == sqlite3.SQLITE_READ:
        if (arg1 or "").lower() in DENIED_TABLES:
            return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def harden(conn):
    for option, enabled in DB_CONFIG:
        conn.setconfig(option, enabled)
    for category, limit in LIMITS:
        conn.setlimit(category, limit)
    conn.set_authorizer(authorizer)


@hookimpl
def prepare_connection(conn):
    harden(conn)
