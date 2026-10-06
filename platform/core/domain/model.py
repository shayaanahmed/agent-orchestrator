from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ModelClass(StrEnum):
    """Logical model classes that can be used by agents"""

    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    FAST = "fast"
    EMBEDDING = "embedding"
    VISION = "vision"


class ModelRequest(BaseModel):
    """Request to generate content using a model"""

    project_id: UUID
    agent_run_id: UUID | None = None
    model_class: ModelClass
    prompt: str
    # Additional parameters for model generation
    parameters: dict[str, Any] = Field(default_factory=dict)
    max_tokens: int | None = None
    temperature: float | None = None
    response_format: str | None = None
    response_schema: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ModelResponse(BaseModel):
    """Response from a model generation request"""

    id: UUID
    project_id: UUID
    request_id: UUID
    agent_run_id: UUID | None = None
    model_class: ModelClass
    content: str  # The generated text or structured data
    usage: dict[str, Any] = Field(default_factory=dict)
    latency: float | None = None
    status: str  # e.g., "success", "error"
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
