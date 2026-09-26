import os
from http.client import HTTPConnection, HTTPSConnection
from urllib.parse import urlparse

from smoke_canary import main


def test_smoke_canary_main():
    os.environ["BASE_URL"] = os.environ.get(
        "SMOKE_TEST_BASE_URL", "https://datasette.planning.data.gov.uk"
    )
    main()


def test_health_endpoint():
    base_url = os.environ.get("SMOKE_TEST_BASE_URL", "https://datasette.planning.data.gov.uk")
    health_url = urlparse(f"{base_url}/health")
    connection_cls = HTTPSConnection if health_url.scheme == "https" else HTTPConnection
    connection = connection_cls(health_url.netloc)
    connection.request("GET", health_url.path)
    response = connection.getresponse()
    assert response.status == 200
