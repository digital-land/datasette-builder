"""
Refuse every HTTP request that could change state.

Why: this is a public, read-only instance. Browsing, the SQL query box, search,
exports and health checks all use GET, and nothing legitimately sends POST,
PUT, PATCH or DELETE. Datasette still has state-changing routes, though: debug
tools such as /-/messages (which sets the message banner shown to the
visitor), /-/logout, and whatever future versions add.

Datasette 0.65's CSRF protection (asgi-csrf) skips its token check when a
request has no cookies at all. A cross-site form POST from a browser is exactly
that, because Datasette's cookies are SameSite=Lax and the browser withholds
them, so another website could make a visitor's browser use those routes.

Refusing unsafe methods outright removes that whole class of problem, without
relying on the CSRF library. Datasette applies asgi_wrapper outside its own
CSRF handling and routing, so a refused request never reaches any route.
(Datasette 1.0 replaces asgi-csrf with header-based cross-origin checks; this
stays correct after an upgrade.)

GET, HEAD and OPTIONS are allowed. OPTIONS is kept for browsers' CORS preflight
requests, since the instance is served with --cors.
"""

from datasette import hookimpl

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def refuse_unsafe_methods(app):
    async def read_only_app(scope, receive, send):
        # Only HTTP requests have a method; lifespan events pass straight through.
        if scope["type"] == "http" and scope["method"].upper() not in SAFE_METHODS:
            await send(
                {
                    "type": "http.response.start",
                    "status": 405,
                    "headers": [
                        (b"allow", ", ".join(sorted(SAFE_METHODS)).encode()),
                        (b"content-type", b"text/plain; charset=utf-8"),
                    ],
                }
            )
            await send(
                {"type": "http.response.body", "body": b"405: Method Not Allowed"}
            )
            return
        await app(scope, receive, send)

    return read_only_app


@hookimpl
def asgi_wrapper(datasette):
    return refuse_unsafe_methods
