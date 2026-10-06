from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID

class SandboxStatus(str, Enum):
    """Lifecycle states for sandbox environments"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DESTROYED = "destroyed"

class SandboxExecution(BaseModel):
    """Record of an execution in a sandbox environment"""
    id: UUID
    project_id: UUID
    work_item_id: UUID
    agent_run_id: Optional[UUID] = None
    environment_id: UUID  # ID of the sandbox environment
    command: str  # The command executed
    arguments: Optional[List[str]] = None
    working_directory: str
    timeout: int  # seconds
    status: SandboxStatus = SandboxStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    artifacts: Optional[List[UUID]] = None  # Artifact IDs produced by this execution
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SandboxEnvironment(BaseModel):
    """Definition of a sandboxed environment"""
    id: UUID
    project_id: UUID
    work_item_id: UUID
    status: SandboxStatus = SandboxStatus.PENDING
    image: str  # Container image to use
    cpu_limit: Optional[float] = None  # CPU cores
    memory_limit: Optional[int] = None  # bytes
    timeout: int = 300  # Default timeout in seconds
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)