import os

import pytest

from tests.datasette_builder.datasets import create_dataset
from tests.datasette_builder.spatial_datasets import create_spatial_dataset

# The SpatiaLite extension to load, as in production. Set in the Docker image
# (so `make docker-test` has it) and in CI; usually unset on a laptop.
SPATIALITE = os.environ.get("SQLITE_EXTENSIONS")


@pytest.fixture(scope="session")
def dataset_path(tmp_path_factory):
    """A plain SQLite dataset: entity table, full-text index and a view."""
    return create_dataset(tmp_path_factory.mktemp("datasets") / "testdb.sqlite3")


@pytest.fixture(scope="session")
def spatialite_extension():
    # Skip only when SpatiaLite isn't configured at all. If it is configured but
    # won't load, the fixtures below fail loudly instead, so CI can't silently
    # skip the SpatiaLite tests.
    if not SPATIALITE:
        pytest.skip(
            "SpatiaLite not configured: set SQLITE_EXTENSIONS=mod_spatialite "
            "(already set in the Docker image and CI; run `make docker-test`)"
        )
    return SPATIALITE


@pytest.fixture(scope="session")
def spatial_dataset_path(tmp_path_factory, spatialite_extension):
    """A dataset built the way the pipeline builds them, with SpatiaLite metadata."""
    directory = tmp_path_factory.mktemp("spatial-datasets")
    return create_spatial_dataset(directory / "spatial.sqlite3", spatialite_extension)
