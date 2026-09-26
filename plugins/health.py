from datasette import hookimpl
from datasette.utils.asgi import Response


@hookimpl
def register_routes():
    async def health_check(request):
        return Response.text("ok", status=200)

    return [
        (r"^/health$", health_check),
    ]
