"""
Build a DuckDB file per dataset holding views over the PySpark collections' Delta
tables, plus the datasette-parquet plugin config that serves them. startup.sh runs this
when ENABLE_DELTA is "true"; if it fails, Datasette starts with the SQLite databases only.

The views read the Parquet files in each table's current Delta snapshot, not the Delta
table itself. That keeps DuckDB's delta extension out of the running service: it reads
storage through its own code, which the plugin's lockdown of file and URL access does
not cover. Re-run this to pick up newer snapshots.
"""
import json
import os
import re
from pathlib import Path

import duckdb
from deltalake import DeltaTable

ENVIRONMENT = os.environ["ENVIRONMENT"]
DELTA_ROOT = os.environ.get("DELTA_ROOT", f"s3://{ENVIRONMENT}-parquet-datasets").rstrip("/")
DATASETS = [d.strip() for d in os.environ.get("DELTA_DATASETS", "title-boundary").split(",") if d.strip()]
OUTPUT_DIR = Path(os.environ.get("DELTA_OUTPUT_DIR", "/tmp/delta"))
# installed when the image is built - the plugin's lockdown stops DuckDB downloading them
EXTENSION_DIRECTORY = os.environ.get("DUCKDB_EXTENSION_DIRECTORY", "/app/duckdb_extensions")

TABLES = ["entity", "fact", "fact_resource", "issue"]

SETUP_SQL = ["LOAD httpfs", "LOAD aws"]
STORAGE_OPTIONS = {}
if DELTA_ROOT.startswith("s3://"):
    # read S3 with the ECS task role's credentials
    SETUP_SQL.append("CREATE SECRET (TYPE s3, PROVIDER credential_chain, REGION 'eu-west-2')")
    STORAGE_OPTIONS = {"AWS_REGION": "eu-west-2"}

SETTINGS = {
    "extension_directory": EXTENSION_DIRECTORY,
    "memory_limit": os.environ.get("DELTA_MEMORY_LIMIT", "1GiB"),
    "threads": int(os.environ.get("DELTA_THREADS", "2")),
    "temp_directory": str(OUTPUT_DIR / "spill"),
    "max_temp_directory_size": os.environ.get("DELTA_MAX_SPILL", "2GiB"),
}


def sql_string(value):
    return "'" + value.replace("'", "''") + "'"


def snapshot_files(table, dataset):
    delta_table = DeltaTable(f"{DELTA_ROOT}/{table}", storage_options=STORAGE_OPTIONS)
    return delta_table.file_uris(file_pruning_predicate=[("dataset", "=", dataset)])


def build_views(dataset):
    if not re.fullmatch(r"[a-z0-9-]+", dataset):
        raise ValueError(f"unexpected dataset name: {dataset!r}")

    path = OUTPUT_DIR / f"{dataset}.duckdb"
    path.unlink(missing_ok=True)
    conn = duckdb.connect(str(path), config={"extension_directory": EXTENSION_DIRECTORY})
    for statement in SETUP_SQL:
        conn.execute(statement)

    created = 0
    for table in TABLES:
        try:
            files = snapshot_files(table, dataset)
            if not files:
                print(f"build_delta_views: no {table} files for {dataset}")
                continue
            # hive_partitioning restores the dataset column, which Spark keeps in the path
            file_list = ", ".join(sql_string(f) for f in files)
            conn.execute(f"CREATE VIEW {table} AS SELECT * FROM read_parquet([{file_list}], hive_partitioning = true)")
            created += 1
        except Exception as error:
            print(f"build_delta_views: skipping {dataset} {table}: {error}")
    conn.close()
    return path if created else None


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    databases = {}
    for dataset in DATASETS:
        path = build_views(dataset)
        if path:
            databases[dataset] = {
                "file": str(path),
                "settings": SETTINGS,
                "setup_sql": SETUP_SQL,
                "allowed_directories": [DELTA_ROOT + "/"],
            }

    if not databases:
        raise SystemExit("build_delta_views: no Delta tables could be read")

    metadata = {"plugins": {"datasette-parquet": databases}}
    (OUTPUT_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2))
    # startup.sh skips any SQLite file with the same name, e.g. the empty title-boundary.sqlite3
    (OUTPUT_DIR / "datasets.txt").write_text("\n".join(databases) + "\n")
    print(f"build_delta_views: serving {', '.join(databases)} from {DELTA_ROOT}")


if __name__ == "__main__":
    main()
