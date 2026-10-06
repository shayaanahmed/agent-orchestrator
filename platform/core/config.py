from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


def _models_from_env() -> dict[str, str]:
    raw = os.getenv("OLLAMA_MODEL_MAP")
    if raw:
        value = json.loads(raw)
        if not isinstance(value, dict) or not all(
            isinstance(key, str) and isinstance(item, str)
            for key, item in value.items()
        ):
            raise ValueError("OLLAMA_MODEL_MAP must be a JSON object of string aliases")
        return value
    return {
        "planner": os.getenv("OLLAMA_PLANNER_MODEL", "qwen3:8b"),
        "coder": os.getenv("OLLAMA_CODER_MODEL", "qwen2.5-coder:7b"),
        "reviewer": os.getenv("OLLAMA_REVIEWER_MODEL", "qwen3:8b"),
        "fast": os.getenv("OLLAMA_FAST_MODEL", "qwen3:4b"),
        "embedding": os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
        "vision": os.getenv("OLLAMA_VISION_MODEL", "qwen3-vl:8b"),
    }


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql://orchestrator:orchestrator@localhost:5432/orchestrator",
        )
    )
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434/v1"
        )
    )
    ollama_api_token: str = field(
        default_factory=lambda: os.getenv("OLLAMA_API_TOKEN", "ollama")
    )
    ollama_model_map: dict[str, str] = field(default_factory=_models_from_env)
    model_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("MODEL_TIMEOUT_SECONDS", "600"))
    )
    model_max_concurrency: int = field(
        default_factory=lambda: int(os.getenv("MODEL_MAX_CONCURRENCY", "2"))
    )
    artifact_directory: str = field(
        default_factory=lambda: os.getenv("ARTIFACT_DIRECTORY", "/data/artifacts")
    )
    sandbox_url: str = field(
        default_factory=lambda: os.getenv(
            "SANDBOX_URL", "http://sandbox-controller:8090"
        )
    )
    sandbox_token: str = field(
        default_factory=lambda: os.getenv("SANDBOX_TOKEN", "sandbox-change-me")
    )
    sandbox_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "120"))
    )
    auto_start_projects: bool = field(
        default_factory=lambda: (
            os.getenv("AUTO_START_PROJECTS", "true").lower() == "true"
        )
    )
    use_temporal: bool = field(
        default_factory=lambda: os.getenv("USE_TEMPORAL", "true").lower() == "true"
    )
    temporal_address: str = field(
        default_factory=lambda: os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    )
    temporal_task_queue: str = field(
        default_factory=lambda: os.getenv("TEMPORAL_TASK_QUEUE", "project-execution")
    )


settings = Settings()
