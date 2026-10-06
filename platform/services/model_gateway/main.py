from __future__ import annotations

import os

import aiohttp
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import Response

app = FastAPI(title="Model Gateway", version="1.0.0")
UPSTREAM = os.getenv(
    "UPSTREAM_OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1"
).rstrip("/")
UPSTREAM_TOKEN = os.getenv("UPSTREAM_OLLAMA_API_TOKEN", "ollama")
GATEWAY_TOKEN = os.getenv("MODEL_GATEWAY_TOKEN", "local-gateway")
CONNECT_TIMEOUT_SECONDS = int(os.getenv("MODEL_CONNECT_TIMEOUT_SECONDS", "10"))
TIMEOUT = aiohttp.ClientTimeout(
    total=int(os.getenv("MODEL_TIMEOUT_SECONDS", "600")),
    connect=CONNECT_TIMEOUT_SECONDS,
    sock_connect=CONNECT_TIMEOUT_SECONDS,
)
try:
    from prometheus_client import make_asgi_app

    app.mount("/metrics", make_asgi_app())
except ImportError:
    pass


def authorize(authorization: str | None) -> None:
    if authorization != f"Bearer {GATEWAY_TOKEN}":
        raise HTTPException(status_code=401, detail="Invalid model gateway token")


async def proxy(request: Request, path: str, authorization: str | None) -> Response:
    authorize(authorization)
    body = await request.body()
    headers = {
        "Authorization": f"Bearer {UPSTREAM_TOKEN}",
        "Content-Type": request.headers.get("content-type", "application/json"),
    }
    async with aiohttp.ClientSession(timeout=TIMEOUT, headers=headers) as session:
        try:
            async with session.request(
                request.method, f"{UPSTREAM}/{path}", data=body or None
            ) as upstream:
                content_type = upstream.headers.get("content-type", "application/json")
                data = await upstream.read()
                return Response(
                    data, status_code=upstream.status, media_type=content_type
                )
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Ollama upstream is unavailable. Check the configured address, "
                    "ensure Ollama is running, and allow connections from the Docker host."
                ),
            ) from exc


@app.api_route("/v1/{path:path}", methods=["GET", "POST"])
async def v1_proxy(
    path: str, request: Request, authorization: str | None = Header(default=None)
) -> Response:
    return await proxy(request, path, authorization)


@app.get("/health")
async def health() -> dict[str, object]:
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5)
        ) as session:
            async with session.get(
                f"{UPSTREAM}/models",
                headers={"Authorization": f"Bearer {UPSTREAM_TOKEN}"},
            ) as response:
                return {
                    "status": "healthy" if response.status == 200 else "degraded",
                    "upstream": response.status,
                }
    except (aiohttp.ClientError, TimeoutError):
        return {"status": "degraded", "upstream": False}
