import os
import sqlite3
from pathlib import Path

import pytest
from datasette.app import Datasette

PLUGINS_DIR = Path(__file__).resolve().parents[2] / "plugins"


@pytest.fixture(scope="session")
def db_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("datasets") / "testdb.sqlite3"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        create table docs (id integer primary key, body text);
        insert into docs (body) values ('hello world'), ('other text');
        create virtual table docs_fts using fts4(body, content='docs');
        insert into docs_fts (docs_fts) values ('rebuild');
        create view upper_docs as select id, upper(body) as body from docs;
        """
    )
    conn.commit()
    conn.close()
    return path


@pytest.fixture(scope="session")
def datasette(db_path):
    # Mirror production: immutable databases, plugins loaded from ./plugins,
    # plus any extensions the image is configured with.
    extensions = [e for e in os.environ.get("SQLITE_EXTENSIONS", "").split(":") if e]
    return Datasette(
        immutables=[str(db_path)],
        plugins_dir=str(PLUGINS_DIR),
        sqlite_extensions=extensions or None,
    )


@pytest.fixture
def query(datasette):
    async def run(sql, db="testdb"):
        response = await datasette.client.get(
            f"/{db}.json", params={"sql": sql, "_shape": "objects"}
        )
        return response.status_code, response.json()

    return run
