"""
Unit tests for datasette_builder.read_only.

The instance is read-only, so any request that could change state is refused
before it reaches Datasette. These call the wrapper directly with a stand-in
app, recording whether the request got through.
"""

import pytest

from datasette_builder.read_only import SAFE_METHODS, refuse_unsafe_methods


class StandInApp:
    def __init__(self):
        self.called = False

    async def __call__(self, scope, receive, send):
        self.called = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})


async def call(method, scope_type="http"):
    app = StandInApp()
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {"type": scope_type, "method": method, "path": "/", "headers": []}
    await refuse_unsafe_methods(app)(scope, receive, send)
    return app, sent


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "post"])
async def test_methods_that_could_change_state_are_refused(method):
    app, sent = await call(method)
    # Refused before the request reaches Datasette.
    assert app.called is False
    assert sent[0]["status"] == 405
    assert (b"allow", b"GET, HEAD, OPTIONS") in sent[0]["headers"]


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
async def test_safe_methods_reach_datasette(method):
    app, sent = await call(method)
    assert app.called is True
    assert sent[0]["status"] == 200


def test_safe_methods_are_only_read_methods():
    # OPTIONS is allowed for CORS preflight requests; nothing else.
    assert SAFE_METHODS == {"GET", "HEAD", "OPTIONS"}


async def test_non_http_events_pass_through():
    # Lifespan events (server startup/shutdown) have no method.
    app = StandInApp()

    async def receive():
        return {"type": "lifespan.startup"}

    async def send(message):
        pass

    await refuse_unsafe_methods(app)({"type": "lifespan"}, receive, send)
    assert app.called is True
