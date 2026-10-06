from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import aiohttp


class SandboxClient:
    def __init__(self, base_url: str, token: str, timeout_seconds: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds + 10)
        self.execution_timeout = timeout_seconds

    async def execute(self, project_id: UUID, command: list[str]) -> dict[str, Any]:
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(
                f"{self.base_url}/execute",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "project_id": str(project_id),
                    "command": command,
                    "timeout_seconds": self.execution_timeout,
                },
            ) as response:
                data = await response.json()
                if response.status >= 400:
                    raise RuntimeError(data.get("detail", "sandbox request failed"))
                return cast(dict[str, Any], data)

    async def health_check(self) -> bool:
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=3)
            ) as session:
                async with session.get(f"{self.base_url}/health") as response:
                    return response.status == 200
        except aiohttp.ClientError:
            return False
