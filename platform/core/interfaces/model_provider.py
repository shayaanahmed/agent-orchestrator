from __future__ import annotations

from typing import Any, Protocol

from core.domain.model import ModelRequest, ModelResponse


class ModelProvider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse: ...

    async def health_check(self) -> bool: ...

    async def get_model_info(self, model_class: str) -> dict[str, Any]: ...


class ModelGateway:
    def __init__(self, provider: ModelProvider):
        self._provider = provider

    async def generate(self, request: ModelRequest) -> ModelResponse:
        return await self._provider.generate(request)

    async def health_check(self) -> bool:
        return await self._provider.health_check()

    async def get_model_info(self, model_class: str) -> dict[str, Any]:
        return await self._provider.get_model_info(model_class)
