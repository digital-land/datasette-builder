import logging
from pathlib import Path

from datasette.app import Datasette
import os

datasets = [f"{d}" for d in Path(os.getcwd()).rglob(f"*.sqlite3")]

logger = logging.getLogger("gunicorn.error")
logger.info(f"Starting server with datasets: {datasets}")

app = Datasette(
    datasets,
    config_dir=Path("."),
    sqlite_extensions=["spatialite"],
).app()
