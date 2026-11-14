"""
Runs the deployable image with fixture datasets, using testcontainers.

The image is built beforehand (`make image`) and named by DATASETTE_IMAGE, so
these tests exercise exactly what would ship. Datasets are copied into the
container rather than mounted, so this works the same from the host and from
inside a container (`make docker-test`).
"""

import json
import time

import docker
import httpx
import pytest
from testcontainers.core.container import DockerContainer

from tests.datasette_builder.acceptance.settings import (
    CORE_DATABASES,
    DATASETS_DIR,
    IMAGE,
    PUBLISHED_DATASET,
    UNPUBLISHED_DATASET,
)
from tests.datasette_builder.datasets import create_dataset, inspect_entry

STARTUP_TIMEOUT_SECONDS = 60


@pytest.fixture(scope="session")
def dataset_files(tmp_path_factory):
    directory = tmp_path_factory.mktemp("acceptance-datasets")
    names = [*CORE_DATABASES, PUBLISHED_DATASET, UNPUBLISHED_DATASET]
    files = {name: create_dataset(directory / f"{name}.sqlite3") for name in names}

    inspect = {PUBLISHED_DATASET: inspect_entry(files[PUBLISHED_DATASET])}
    inspect_file = directory / "inspect-data-all.json"
    inspect_file.write_text(json.dumps(inspect))
    return [*files.values(), inspect_file]


@pytest.fixture(scope="session")
def datasette_url(dataset_files):
    try:
        docker.from_env().images.get(IMAGE)
    except docker.errors.ImageNotFound:
        pytest.fail(f"Image {IMAGE!r} not found. Build it with `make image`.")

    container = DockerContainer(IMAGE).with_exposed_ports(5000)
    for path in dataset_files:
        container = container.with_copy_into_container(
            path, f"{DATASETS_DIR}/{path.name}"
        )

    with container:
        url = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(5000)}"
        _wait_until_serving(url, container)
        yield url


@pytest.fixture
def client(datasette_url):
    with httpx.Client(base_url=datasette_url, timeout=30) as client:
        yield client


def _wait_until_serving(url, container):
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{url}/-/versions.json", timeout=2).status_code == 200:
                return
        except httpx.TransportError:
            pass
        time.sleep(0.5)
    stdout, stderr = container.get_logs()
    pytest.fail(
        f"Datasette did not start within {STARTUP_TIMEOUT_SECONDS}s.\n"
        f"{stdout.decode()}\n{stderr.decode()}"
    )
