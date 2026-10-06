from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class TaskStatus(StrEnum):
    """Lifecycle states for tasks"""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    REVIEWING = "reviewing"
    REVISION_REQUIRED = "revision_required"


class WorkItem(BaseModel):
    """A unit of work to be executed by an agent"""

    id: UUID
    project_id: UUID
    name: str
    description: str
    assigned_agent_id: UUID | None = None
    status: TaskStatus = TaskStatus.PENDING
    dependencies: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    expected_artifacts: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    priority: int = 0  # Higher values = higher priority
    estimated_duration: int | None = None
    actual_duration: int | None = None
    required_capabilities: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    output: str | None = None
    error: str | None = None


class WorkItemDependency(BaseModel):
    """Dependencies between work items"""

    id: UUID
    work_item_id: UUID
    depends_on_id: UUID
    created_at: datetime = Field(default_factory=utc_now)


class ExecutionPlan(BaseModel):
    """Structured plan for executing tasks in a project"""

    project_id: UUID
    work_items: list[WorkItem]
    dependencies: list[WorkItemDependency]
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
