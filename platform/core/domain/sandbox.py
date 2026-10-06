from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class SandboxStatus(StrEnum):
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
    agent_run_id: UUID | None = None
    environment_id: UUID  # ID of the sandbox environment
    command: str  # The command executed
    arguments: list[str] | None = None
    working_directory: str
    timeout: int  # seconds
    status: SandboxStatus = SandboxStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    artifacts: list[UUID] | None = None  # Artifact IDs produced by this execution
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SandboxEnvironment(BaseModel):
    """Definition of a sandboxed environment"""

    id: UUID
    project_id: UUID
    work_item_id: UUID
    status: SandboxStatus = SandboxStatus.PENDING
    image: str  # Container image to use
    cpu_limit: float | None = None  # CPU cores
    memory_limit: int | None = None  # bytes
    timeout: int = 300  # Default timeout in seconds
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
