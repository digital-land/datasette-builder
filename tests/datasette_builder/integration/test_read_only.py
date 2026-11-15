"""
Integration tests: Datasette with the plugin's read-only wrapper.

What these check against: the instance is read-only, so Datasette's
state-changing routes - for example /-/messages, which sets the message banner
a visitor sees - must not be usable, whether or not the request carries
cookies. Datasette 0.65's CSRF check is skipped for requests without cookies,
which is what a cross-site browser form POST looks like, so the refusal can't
depend on it. Reading must keep working.
"""

import pytest


@pytest.mark.parametrize(
    "headers",
    [
        {},  # no cookies: the case Datasette's CSRF check skips
        {"cookie": "foo=bar"},  # cookies but no CSRF token
        {"origin": "https://other.example"},  # from another website
    ],
)
async def test_the_message_banner_cant_be_set(datasette, headers):
    response = await datasette.client.post(
        "/-/messages",
        data={"message": "test", "message_class": "INFO"},
        headers=headers,
    )
    assert response.status_code == 405
    assert "ds_messages" not in response.headers.get("set-cookie", "")


@pytest.mark.parametrize("path", ["/-/logout", "/testdb", "/testdb/entity"])
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
async def test_state_changing_requests_are_refused(datasette, path, method):
    response = await datasette.client.request(method, path)
    assert response.status_code == 405
    assert response.headers["allow"] == "GET, HEAD, OPTIONS"


@pytest.mark.parametrize("method", ["GET", "HEAD"])
@pytest.mark.parametrize("path", ["/", "/testdb", "/testdb/entity.json"])
async def test_reading_still_works(datasette, path, method):
    response = await datasette.client.request(method, path)
    assert response.status_code == 200


async def test_sql_queries_still_work(datasette):
    # The SQL query box submits with GET.
    response = await datasette.client.get(
        "/testdb.json", params={"sql": "select 1 as a", "_shape": "array"}
    )
    assert response.status_code == 200
    assert response.json() == [{"a": 1}]
