import pytest

from tests.datasette_builder.datasets import create_dataset


@pytest.fixture(scope="session")
def dataset_path(tmp_path_factory):
    return create_dataset(tmp_path_factory.mktemp("datasets") / "testdb.sqlite3")
