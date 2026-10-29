"""Same-origin hosted demo. CloudFront supplies the private origin header."""
from __future__ import annotations

import os
from pathlib import Path
import secrets

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse

from model.api.urban import create_app

MAX_BODY_BYTES = 3_000_000
MAX_DATASET_REQUEST_BYTES = 12 * 1024 * 1024


class OriginGuard:
    def __init__(self, app, secret: str):
        self.app, self.secret = app, secret

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        supplied = headers.get(b"x-origin-verify", b"")
        if not secrets.compare_digest(supplied, self.secret.encode("ascii")):
            return await JSONResponse({"detail": "Origin access denied."}, status_code=403)(scope, receive, send)
        import_paths = {"/api/urban/data/workspace/preview", "/api/urban/data/workspace/import",
                        "/api/urban/integration/inspect", "/api/urban/integration/validate",
                        "/api/urban/integration/imports"}
        limit = MAX_DATASET_REQUEST_BYTES if scope.get("method") == "POST" and scope.get("path") in import_paths else MAX_BODY_BYTES
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            length = -1
        if length < 0 or length > limit:
            return await JSONResponse({"detail": "Request body exceeds the hosted demo limit."}, status_code=413)(scope, receive, send)
        # Enforce the limit for chunked bodies too, before the JSON parser runs.
        chunks, count = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            count += len(message.get("body", b""))
            if count > limit:
                return await JSONResponse({"detail": "Request body exceeds the hosted demo limit."}, status_code=413)(scope, receive, send)
            chunks.append(message)
            if not message.get("more_body", False):
                break
        position = 0

        async def replay():
            nonlocal position
            if position < len(chunks):
                message = chunks[position]
                position += 1
                return message
            return await receive()

        async def private_response(message):
            if message["type"] == "http.response.start":
                headers = [(key, value) for key, value in message["headers"]
                           if key.lower() not in {b"cache-control", b"x-content-type-options"}]
                message = {**message, "headers": headers + [
                    (b"cache-control", b"no-store"), (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin")]}
            await send(message)

        await self.app(scope, replay, private_response)



class SPAFiles(StaticFiles):
    """Serve only known client routes through the SPA; missing assets stay 404."""
    routes = {'dashboard','settlements','report-issue','projects','projects/data','projects/priorities','projects/scenarios','projects/assurance','projects/reports','projects/community','data-integration','housing','services','visits','methodology'}

    async def get_response(self, path, scope):
        if scope['method'] in {'GET','HEAD'} and path.strip('/') in self.routes:
            return await super().get_response('index.html',scope)
        return await super().get_response(path,scope)


def build_app(frontend_dir: str | Path | None = None, db_path=None):
    origin_secret = os.environ.get("URBANSAARTHI_ORIGIN_SECRET", "")
    officer_key = os.environ.get("NAGARSEVA_OFFICER_KEY", "")
    if len(origin_secret) < 32 or len(officer_key) < 32:
        raise RuntimeError("Hosted deployment requires separate origin and officer secrets of at least 32 characters.")
    if origin_secret == officer_key:
        raise RuntimeError("Origin and officer secrets must be different.")
    directory = Path(frontend_dir or os.getenv("URBANSAARTHI_FRONTEND_DIR", "/app/frontend"))
    if not (directory / "index.html").is_file():
        raise RuntimeError("Build the frontend before starting the hosted app.")
    application = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    application.mount("/api", create_app(db_path))
    application.mount("/", SPAFiles(directory=directory, html=True))
    return OriginGuard(application, origin_secret)


# Uvicorn uses --factory; importing this module does not start a server.
