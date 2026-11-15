"""
Runs the deployable image with fixture datasets, using testcontainers.

The image is built beforehand (`make image`) and named by DATASETTE_IMAGE, so
these tests exercise exactly what would ship: the installed plugin, SpatiaLite,
the entrypoint script and the Debian SQLite build. Datasets are copied into the
container rather than mounted, so this works the same from the host and from
inside a container (`make docker-test`).
"""

import base64
import inspect
import json
import textwrap
import time

import docker
import httpx
import pytest
from testcontainers.core.container import DockerContainer

from tests.datasette_builder import spatial_datasets
from tests.datasette_builder.acceptance.settings import (
    CORE_DATABASES,
    DATASETS_DIR,
    IMAGE,
    PUBLISHED_DATASET,
    SPATIAL_DATASET,
    UNPUBLISHED_DATASET,
)
from tests.datasette_builder.datasets import create_dataset, inspect_entry

STARTUP_TIMEOUT_SECONDS = 60


@pytest.fixture(scope="session")
def image():
    try:
        docker.from_env().images.get(IMAGE)
    except docker.errors.ImageNotFound:
        pytest.fail(f"Image {IMAGE!r} not found. Build it with `make image`.")
    return IMAGE


@pytest.fixture(scope="session")
def dataset_files(tmp_path_factory, image):
    directory = tmp_path_factory.mktemp("acceptance-datasets")
    plain = [*CORE_DATABASES, PUBLISHED_DATASET, UNPUBLISHED_DATASET]
    files = {name: create_dataset(directory / f"{name}.sqlite3") for name in plain}

    files[SPATIAL_DATASET] = directory / f"{SPATIAL_DATASET}.sqlite3"
    _build_spatial_dataset_in_image(image, files[SPATIAL_DATASET])

    inspect_file = directory / "inspect-data-all.json"
    published = [PUBLISHED_DATASET, SPATIAL_DATASET]
    inspect_file.write_text(json.dumps({n: inspect_entry(files[n]) for n in published}))
    return [*files.values(), inspect_file]


@pytest.fixture(scope="session")
def datasette_url(image, dataset_files):
    container = DockerContainer(image).with_exposed_ports(5000)
    for path in dataset_files:
        container = container.with_copy_into_container(
            path, f"{DATASETS_DIR}/{path.name}"
        )

    with container:
        host = container.get_container_host_ip()
        url = f"http://{host}:{container.get_exposed_port(5000)}"
        _wait_until_serving(url, container)
        yield url


@pytest.fixture
def client(datasette_url):
    with httpx.Client(base_url=datasette_url, timeout=30) as client:
        yield client


def _build_spatial_dataset_in_image(image, path):
    """
    Build the SpatiaLite dataset inside the image, which has SpatiaLite even
    when the machine running the tests doesn't. Runs spatial_datasets' source
    with the image's Python and returns the file base64-encoded on stdout.
    """
    script = inspect.getsource(spatial_datasets) + textwrap.dedent(
        """
        import base64, sys
        create_spatial_dataset("/tmp/spatial.sqlite3")
        with open("/tmp/spatial.sqlite3", "rb") as f:
            sys.stdout.write(base64.b64encode(f.read()).decode())
        """
    )
    output = docker.from_env().containers.run(
        image, entrypoint=["python", "-c", script], remove=True, stderr=False
    )
    path.write_bytes(base64.b64decode(output))


def _wait_until_serving(url, container):
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{url}/-/versions.json", timeout=2).status_code == 200:
                return
        except httpx.TransportError:
            pass
        time.sleep(0.5)
    # Datasette refusing to start (for example the SpatiaLite error) ends up
    # here, with its output attached.
    stdout, stderr = container.get_logs()
    pytest.fail(
        f"Datasette did not start within {STARTUP_TIMEOUT_SECONDS}s.\n"
        f"{stdout.decode()}\n{stderr.decode()}"
    )
