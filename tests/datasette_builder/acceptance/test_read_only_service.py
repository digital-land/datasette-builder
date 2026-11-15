"""
Acceptance criteria: the public service is read-only.

Visitors can browse, query and export, but nothing can change state on their
behalf - including from another website through their browser. In particular
the site's message banner can't be set by a request, so nobody can make the
site display text of their choosing. Runs against the deployable image, over
HTTP.
"""

import pytest

from tests.datasette_builder.acceptance.settings import PUBLISHED_DATASET


@pytest.mark.parametrize(
    "headers",
    [
        {},  # no cookies, as a cross-site browser form POST arrives
        {"Origin": "https://other.example", "Referer": "https://other.example/"},
        {"Cookie": "foo=bar"},
    ],
)
def test_nobody_can_set_the_message_banner(client, headers):
    response = client.post(
        "/-/messages",
        data={"message": "test", "message_class": "INFO"},
        headers=headers,
    )
    assert response.status_code == 405
    assert "ds_messages" not in response.headers.get("set-cookie", "")


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize(
    "path", ["/-/messages", "/-/logout", f"/{PUBLISHED_DATASET}/entity"]
)
def test_requests_that_could_change_state_are_refused(client, method, path):
    response = client.request(method, path)
    assert response.status_code == 405


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_visitors_can_still_read(client, method):
    response = client.request(method, f"/{PUBLISHED_DATASET}/entity.json")
    assert response.status_code == 200


def test_cors_preflight_is_not_refused(client):
    # Browsers send OPTIONS before some cross-origin GETs; the service is
    # deliberately served with --cors.
    response = client.options(
        f"/{PUBLISHED_DATASET}.json",
        headers={
            "Origin": "https://other.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code != 405
