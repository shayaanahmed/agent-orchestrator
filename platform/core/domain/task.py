from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID

class TaskStatus(str, Enum):
    """Lifecycle states for tasks"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_FOR_APPROVAL = "waiting_for_approval"

class WorkItem(BaseModel):
    """A unit of work to be executed by an agent"""
    id: UUID
    project_id: UUID
    name: str
    description: str
    assigned_agent_id: Optional[UUID] = None
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expected_artifacts: Optional[List[str]] = None  # MIME types or artifact types
    acceptance_criteria: Optional[List[str]] = None
    priority: int = 0  # Higher values = higher priority
    estimated_duration: Optional[int] = None  # seconds
    actual_duration: Optional[int] = None  # seconds

class WorkItemDependency(BaseModel):
    """Dependencies between work items"""
    id: UUID
    work_item_id: UUID
    depends_on_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ExecutionPlan(BaseModel):
    """Structured plan for executing tasks in a project"""
    project_id: UUID
    work_items: List[WorkItem]
    dependencies: List[WorkItemDependency]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)