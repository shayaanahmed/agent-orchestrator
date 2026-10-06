from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class AgentRole(StrEnum):
    """Supported agent roles in the platform"""

    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    RESEARCHER = "researcher"
    TESTER = "tester"
    DEPLOYER = "deployer"


class Capability(StrEnum):
    """Available capabilities that agents can possess"""

    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    SECURITY_ANALYSIS = "security_analysis"
    DEPLOYMENT = "deployment"


class AgentSpec(BaseModel):
    """Specification for an AI agent that can work on projects"""

    id: UUID
    role: AgentRole
    objective: str
    capabilities: list[Capability]
    instructions: str
    # Logical model class used by this agent (e.g., 'planner', 'coder')
    model_class: str
    allowed_tools: list[str] = Field(default_factory=list)
    forbidden_operations: list[str] = Field(default_factory=list)
    accessible_resources: list[str] = Field(default_factory=list)
    output_schema: dict[str, Any] | None = None
    max_iterations: int = Field(default=10, ge=1, le=100)
    max_model_calls: int = Field(default=50, ge=1, le=500)
    max_tool_calls: int = Field(default=100, ge=0, le=1000)
    execution_timeout: int = Field(default=300, ge=1, le=86400)
    context_budget: int = Field(default=10000, ge=256, le=1_000_000)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AgentRun(BaseModel):
    """Execution record of an agent working on a specific task"""

    id: UUID
    project_id: UUID
    agent_spec_id: UUID
    work_item_id: UUID
    status: str  # TODO: Define proper status enum
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    artifacts: list[UUID] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
