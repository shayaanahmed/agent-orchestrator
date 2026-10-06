from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID

class ProjectStatus(str, Enum):
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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Project(BaseModel):
    """Main project entity representing an AI execution project"""
    id: UUID
    name: str
    description: Optional[str] = None
    goal: ProjectGoal
    status: ProjectStatus = ProjectStatus.CREATED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    schema_version: int = 1
    owner_id: UUID
    # Additional fields that would be populated during execution
    requirements: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    assumptions: Optional[List[str]] = None
    acceptance_criteria: Optional[List[str]] = None
    capabilities_needed: Optional[List[str]] = None
    team_plan: Optional[Dict[str, Any]] = None
    execution_plan: Optional[Dict[str, Any]] = None