import pytest
from datasette.app import Datasette


@pytest.fixture(scope="session")
def datasette(dataset_path):
    # Immutable, as in production. The plugin isn't passed in: Datasette loads
    # it from the installed package's entry point, exactly as production does.
    return Datasette(immutables=[str(dataset_path)])


@pytest.fixture
def query(datasette):
    async def run(sql, db="testdb"):
        response = await datasette.client.get(
            f"/{db}.json", params={"sql": sql, "_shape": "objects"}
        )
        return response.status_code, response.json()

    return run
