from typing import List, Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import (
    Column, String, Text, DateTime, Uuid, Enum, JSON, Integer, Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum as PyEnum

# Using SQLAlchemy 2.x declarative base
Base = declarative_base()

class ProjectStatus(PyEnum):
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

class ArtifactType(PyEnum):
    SOURCE_CODE = "source_code"
    TEST_REPORT = "test_report"
    DOCUMENTATION = "documentation"
    IMAGE = "image"
    DATA_FILE = "data_file"
    DEPLOYMENT_MANIFEST = "deployment_manifest"
    AUDIT_EXPORT = "audit_export"
    JSON_REPORT = "json_report"
    MARKDOWN_DOCUMENT = "markdown_document"
    PATCH_FILE = "patch_file"
    SOURCE_ARCHIVE = "source_archive"

class ArtifactStatus(PyEnum):
    DRAFT = "draft"
    FINAL = "final"
    REVIEWED = "reviewed"
    REVISION_REQUIRED = "revision_required"
    REJECTED = "rejected"

class AgentRole(PyEnum):
    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    RESEARCHER = "researcher"
    TESTER = "tester"
    DEPLOYER = "deployer"

class Capability(PyEnum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review" 
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    SECURITY_ANALYSIS = "security_analysis"
    DEPLOYMENT = "deployment"

class TaskStatus(PyEnum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_FOR_APPROVAL = "waiting_for_approval"

class ProjectModel(Base):
    __tablename__ = 'projects'
    
    id: UUID = Column(Uuid, primary_key=True, default=uuid4)
    name: str = Column(String(255), nullable=False)
    description: Optional[str] = Column(Text)
    goal_text: str = Column(Text, nullable=False)
    status: ProjectStatus = Column(Enum(ProjectStatus), nullable=False)
    owner_id: UUID = Column(Uuid, nullable=False)
    
    # Project metadata
    requirements: Optional[List[str]] = Column(JSON)
    constraints: Optional[List[str]] = Column(JSON)
    assumptions: Optional[List[str]] = Column(JSON)
    acceptance_criteria: Optional[List[str]] = Column(JSON)
    capabilities_needed: Optional[List[str]] = Column(JSON)
    team_plan: Optional[dict] = Column(JSON)
    execution_plan: Optional[dict] = Column(JSON)
    
    created_at: datetime = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    schema_version: int = Column(Integer, nullable=False, default=1)

class AgentSpecModel(Base):
    __tablename__ = 'agent_specs'
    
    id: UUID = Column(Uuid, primary_key=True, default=uuid4)
    role: AgentRole = Column(Enum(AgentRole), nullable=False)
    objective: str = Column(Text, nullable=False)
    capabilities: List[Capability] = Column(JSON, nullable=False)  # This would likely be a JSON array
    instructions: str = Column(Text, nullable=False)
    
    # Model and execution parameters
    model_class: str = Column(String(100), nullable=False)
    allowed_tools: Optional[List[str]] = Column(JSON)
    forbidden_operations: Optional[List[str]] = Column(JSON)
    accessible_resources: Optional[List[str]] = Column(JSON)
    output_schema: Optional[dict] = Column(JSON)
    
    # Execution limits
    max_iterations: int = Column(Integer, nullable=False, default=10)
    max_model_calls: int = Column(Integer, nullable=False, default=50)
    max_tool_calls: int = Column(Integer, nullable=False, default=100)
    execution_timeout: int = Column(Integer, nullable=False, default=300)  # seconds
    context_budget: int = Column(Integer, nullable=False, default=10000)  # tokens or characters
    
    created_at: datetime = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class WorkItemModel(Base):
    __tablename__ = 'work_items'
    
    id: UUID = Column(Uuid, primary_key=True, default=uuid4)
    project_id: UUID = Column(Uuid, nullable=False)
    name: str = Column(String(255), nullable=False)
    description: str = Column(Text, nullable=False)
    assigned_agent_id: Optional[UUID] = Column(Uuid)
    status: TaskStatus = Column(Enum(TaskStatus), nullable=False)
    
    # Dependencies
    dependencies: List[UUID] = Column(JSON, default=[])
    
    created_at: datetime = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Task details
    expected_artifacts: Optional[List[str]] = Column(JSON)
    acceptance_criteria: Optional[List[str]] = Column(JSON)
    priority: int = Column(Integer, nullable=False, default=0)
    estimated_duration: Optional[int] = Column(Integer)  # seconds
    actual_duration: Optional[int] = Column(Integer)  # seconds

class ArtifactModel(Base):
    __tablename__ = 'artifacts'
    
    id: UUID = Column(Uuid, primary_key=True, default=uuid4)
    project_id: UUID = Column(Uuid, nullable=False)
    work_item_id: UUID = Column(Uuid, nullable=False)
    producer_agent_id: UUID = Column(Uuid, nullable=False)
    name: str = Column(String(255), nullable=False)
    description: Optional[str] = Column(Text)
    type: ArtifactType = Column(Enum(ArtifactType), nullable=False)
    mime_type: str = Column(String(100), nullable=False)
    size: int = Column(Integer, nullable=False)
    content_hash: str = Column(String(64), nullable=False)
    storage_reference: str = Column(Text, nullable=False)  # MinIO object key
    status: ArtifactStatus = Column(Enum(ArtifactStatus), nullable=False)
    
    created_at: datetime = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    schema_version: int = Column(Integer, nullable=False, default=1)
    parent_artifacts: List[UUID] = Column(JSON, default=[])
    review_result: Optional[dict] = Column(JSON)

# Additional support tables
class ProjectEvent(Base):
    __tablename__ = 'project_events'
    
    id: UUID = Column(Uuid, primary_key=True, default=uuid4)
    project_id: UUID = Column(Uuid, nullable=False)
    event_type: str = Column(String(100), nullable=False)  # e.g., "project_started", "task_completed"
    payload: Optional[dict] = Column(JSON)
    timestamp: datetime = Column(DateTime, nullable=False, default=datetime.utcnow)

class ModelRequestModel(Base):
    __tablename__ = 'model_requests'
    
    id: UUID = Column(Uuid, primary_key=True, default=uuid4)
    project_id: UUID = Column(Uuid, nullable=False)
    agent_run_id: Optional[UUID] = Column(Uuid)
    model_class: str = Column(String(100), nullable=False)
    prompt: str = Column(Text, nullable=False)
    parameters: Optional[dict] = Column(JSON)
    max_tokens: Optional[int] = Column(Integer)
    temperature: Optional[float] = Column(Integer)
    response_format: Optional[str] = Column(String(50))
    created_at: datetime = Column(DateTime, nullable=False, default=datetime.utcnow)

class SandboxExecution(Base):
    __tablename__ = 'sandbox_executions'
    
    id: UUID = Column(Uuid, primary_key=True, default=uuid4)
    project_id: UUID = Column(Uuid, nullable=False)
    work_item_id: UUID = Column(Uuid, nullable=False)
    agent_run_id: Optional[UUID] = Column(Uuid)
    environment_id: UUID = Column(Uuid, nullable=False)
    command: str = Column(Text, nullable=False)
    arguments: Optional[List[str]] = Column(JSON)
    working_directory: str = Column(String(255), nullable=False)
    timeout: int = Column(Integer, nullable=False)  # seconds
    status: TaskStatus = Column(Enum(TaskStatus), nullable=False)
    started_at: Optional[datetime] = Column(DateTime)
    completed_at: Optional[datetime] = Column(DateTime)
    exit_code: Optional[int] = Column(Integer)
    stdout: Optional[str] = Column(Text)
    stderr: Optional[str] = Column(Text)
    artifacts: List[UUID] = Column(JSON, default=[])
    created_at: datetime = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

# TODO: Add other tables such as approvals, reviews, user tables, etc.