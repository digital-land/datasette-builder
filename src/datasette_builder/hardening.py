"""
Harden every SQLite connection Datasette opens.

The public instance lets anonymous users run ad-hoc SELECTs, so each
connection is locked down as far as SQLite allows. Everything here is applied
from Python (sqlite3_db_config / sqlite3_limit / an authorizer), so it cannot
be undone from SQL.

1. Authorizer - deny SQL functions that are unsafe for public queries:
   - fts3_tokenizer: Debian's SQLite is compiled with
     SQLITE_ENABLE_FTS3_TOKENIZER; the function leaks a memory pointer and its
     two-argument form can replace a tokenizer's function pointer (a known
     memory-corruption primitive). The authorizer is checked when each
     statement is prepared, including functions inside views, so this blocks
     the function itself whatever its arguments.
   - load_extension: Datasette already disables it; denied as a backstop.

2. Connection config (sqlite3_db_config):
   - DEFENSIVE on: no writable_schema / shadow-table corruption tricks.
   - TRUSTED_SCHEMA off: views/triggers stored in a database file can't call
     functions not marked innocuous - limits damage from a tampered dataset.
   - ENABLE_FTS3_TOKENIZER off: second layer for the fts3_tokenizer write form.
   - ENABLE_LOAD_EXTENSION off.

3. Limits (sqlite3_limit):
   - ATTACHED = 0: the connection can never attach another database file,
     even if the SELECT-only check were bypassed. (We don't use --crossdb.)
   - LENGTH: cap on any string/blob, so queries like randomblob(1e9) can't
     exhaust memory. Generous enough for large WKT geometries.
   - SQL_LENGTH: cap on the size of a submitted SQL statement.

Requires Python 3.12+ (Connection.setconfig).
"""

import sqlite3

from datasette import hookimpl

DENIED_FUNCTIONS = frozenset({"fts3_tokenizer", "load_extension"})

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
    # For SQLITE_FUNCTION, arg2 is the function name.
    if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in DENIED_FUNCTIONS:
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
