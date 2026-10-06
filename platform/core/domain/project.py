from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProjectStatus(StrEnum):
    """Lifecycle states for projects"""

    CREATED = "created"
    CLARIFYING = "clarifying"
    PLANNING = "planning"
    VALIDATING_PLAN = "validating_plan"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    REPLANNING = "replanning"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProjectGoal(BaseModel):
    """User-provided goal for a project"""

    text: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Project(BaseModel):
    """Main project entity representing an AI execution project"""

    id: UUID
    name: str
    description: str | None = None
    goal: ProjectGoal
    status: ProjectStatus = ProjectStatus.CREATED
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    schema_version: int = 1
    owner_id: UUID
    # Additional fields that would be populated during execution
    requirements: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    capabilities_needed: list[str] = Field(default_factory=list)
    team_plan: dict[str, Any] | None = None
    execution_plan: dict[str, Any] | None = None
    error: str | None = None
