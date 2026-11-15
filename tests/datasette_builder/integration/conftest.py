import pytest
from datasette.app import Datasette


@pytest.fixture(scope="session")
def datasette(dataset_path):
    # Immutable, as in production. The plugin isn't passed in: Datasette loads
    # it from the installed package's entry point, exactly as production does.
    return Datasette(immutables=[str(dataset_path)])


@pytest.fixture(scope="session")
def spatial_datasette(spatial_dataset_path, spatialite_extension):
    # As production: SpatiaLite loaded on every connection, then the plugin's
    # prepare_connection hook locks the connection down.
    return Datasette(
        immutables=[str(spatial_dataset_path)],
        sqlite_extensions=[spatialite_extension],
    )


@pytest.fixture
def query(datasette):
    async def run(sql, db="testdb"):
        response = await datasette.client.get(
            f"/{db}.json", params={"sql": sql, "_shape": "objects"}
        )
        return response.status_code, response.json()

    return run


@pytest.fixture
def spatial_query(spatial_datasette):
    async def run(sql):
        response = await spatial_datasette.client.get(
            "/spatial.json", params={"sql": sql, "_shape": "objects"}
        )
        return response.status_code, response.json()

    return run
