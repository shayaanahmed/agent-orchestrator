from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from uuid import uuid4

import aiohttp

from core.domain.model import ModelClass, ModelRequest, ModelResponse
from core.interfaces.model_provider import ModelProvider


class ModelProviderError(RuntimeError):
    pass


class OllamaModelProvider(ModelProvider):
    """OpenAI-compatible client for an Ollama server or its authenticated proxy."""

    def __init__(
        self,
        base_url: str,
        api_token: str = "ollama",
        model_map: dict[str, str] | None = None,
        timeout_seconds: int = 600,
        max_concurrency: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token or "ollama"
        self.model_map = model_map or {
            ModelClass.PLANNER.value: "qwen3:8b",
            ModelClass.CODER.value: "qwen2.5-coder:7b",
            ModelClass.REVIEWER.value: "qwen3:8b",
            ModelClass.FAST.value: "qwen3:4b",
            ModelClass.EMBEDDING.value: "nomic-embed-text",
            ModelClass.VISION.value: "qwen3-vl:8b",
        }
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._session: aiohttp.ClientSession | None = None
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                },
            )
        return self._session

    def _model_name(self, model_class: ModelClass | str) -> str:
        key = model_class.value if isinstance(model_class, ModelClass) else model_class
        try:
            return self.model_map[key]
        except KeyError as exc:
            raise ModelProviderError(
                f"No model configured for logical class '{key}'"
            ) from exc

    async def generate(self, request: ModelRequest) -> ModelResponse:
        started = time.monotonic()
        payload: dict[str, Any] = {
            "model": self._model_name(request.model_class),
            "messages": [{"role": "user", "content": request.prompt}],
            "stream": False,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.response_format == "json_schema":
            payload["response_format"] = {"type": "json_object"}
            # Qwen reasoning models can spend most of their output budget on hidden
            # chain-of-thought. Structured orchestration calls need direct JSON.
            payload["think"] = False

        session = await self._get_session()
        try:
            async with self._semaphore:
                async with session.post(
                    f"{self.base_url}/chat/completions", json=payload
                ) as response:
                    body = await response.text()
                    if response.status >= 400:
                        raise ModelProviderError(
                            f"Ollama returned HTTP {response.status}: {body[:1000]}"
                        )
                    data = json.loads(body)
            content = data["choices"][0]["message"]["content"]
            return ModelResponse(
                id=uuid4(),
                project_id=request.project_id,
                request_id=uuid4(),
                agent_run_id=request.agent_run_id,
                model_class=request.model_class,
                content=content,
                usage=data.get("usage", {}),
                latency=time.monotonic() - started,
                status="success",
            )
        except (TimeoutError, aiohttp.ClientError, KeyError, ValueError) as exc:
            return ModelResponse(
                id=uuid4(),
                project_id=request.project_id,
                request_id=uuid4(),
                agent_run_id=request.agent_run_id,
                model_class=request.model_class,
                content="",
                latency=time.monotonic() - started,
                status="error",
                error_message=str(exc),
            )
        except ModelProviderError as exc:
            return ModelResponse(
                id=uuid4(),
                project_id=request.project_id,
                request_id=uuid4(),
                agent_run_id=request.agent_run_id,
                model_class=request.model_class,
                content="",
                latency=time.monotonic() - started,
                status="error",
                error_message=str(exc),
            )

    async def health_check(self) -> bool:
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.base_url}/models", timeout=aiohttp.ClientTimeout(total=8)
            ) as response:
                return response.status == 200
        except (TimeoutError, aiohttp.ClientError):
            return False

    async def get_model_info(self, model_class: str) -> dict[str, Any]:
        model = self._model_name(model_class)
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.base_url}/models", timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                data = await response.json()
            available = any(item.get("id") == model for item in data.get("data", []))
            return {"logical_name": model_class, "model": model, "available": available}
        except (TimeoutError, aiohttp.ClientError, ValueError):
            return {"logical_name": model_class, "model": model, "available": False}

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self) -> OllamaModelProvider:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()
