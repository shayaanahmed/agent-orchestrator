from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID

class AgentRole(str, Enum):
    """Supported agent roles in the platform"""
    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    RESEARCHER = "researcher"
    TESTER = "tester"
    DEPLOYER = "deployer"

class Capability(Enum):
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
    capabilities: List[Capability]
    instructions: str
    # Logical model class used by this agent (e.g., 'planner', 'coder')
    model_class: str  
    allowed_tools: Optional[List[str]] = None
    forbidden_operations: Optional[List[str]] = None
    accessible_resources: Optional[List[str]] = None
    output_schema: Optional[Dict[str, Any]] = None
    max_iterations: int = 10
    max_model_calls: int = 50
    max_tool_calls: int = 100
    execution_timeout: int = 300  # seconds
    context_budget: int = 10000  # tokens or characters
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AgentRun(BaseModel):
    """Execution record of an agent working on a specific task"""
    id: UUID
    project_id: UUID
    agent_spec_id: UUID
    work_item_id: UUID
    status: str  # TODO: Define proper status enum
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    artifacts: Optional[List[UUID]] = None  # Artifact IDs produced
    errors: Optional[List[str]] = None