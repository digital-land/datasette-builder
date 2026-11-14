"""Small SQLite datasets shaped like the published planning data databases."""

import sqlite3
from pathlib import Path


def create_dataset(path: Path) -> Path:
    """Create a dataset database with an entity table, a full-text index and a view."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        create table entity (entity integer primary key, name text, geometry text);
        insert into entity (name, geometry)
            values ('hello world', 'POINT (0 0)'), ('other text', 'POINT (1 1)');
        create virtual table entity_fts using fts4(name, content='entity');
        insert into entity_fts (entity_fts) values ('rebuild');
        create view entity_upper as select entity, upper(name) as name from entity;
        """
    )
    conn.commit()
    conn.close()
    return path


def inspect_entry(path: Path) -> dict:
    """The entry Datasette's --inspect-file expects for one database."""
    return {
        "hash": path.stem,
        "size": path.stat().st_size,
        "file": path.name,
        "tables": {},
    }
