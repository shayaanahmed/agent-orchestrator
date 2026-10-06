from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID

class ModelClass(str, Enum):
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
    agent_run_id: Optional[UUID] = None
    model_class: ModelClass
    prompt: str
    # Additional parameters for model generation
    parameters: Optional[Dict[str, Any]] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    response_format: Optional[str] = None  # e.g., "json_schema"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ModelResponse(BaseModel):
    """Response from a model generation request"""
    id: UUID
    project_id: UUID
    request_id: UUID
    agent_run_id: Optional[UUID] = None
    model_class: ModelClass
    content: str  # The generated text or structured data
    usage: Optional[Dict[str, Any]] = None  # Token usage details
    latency: Optional[float] = None  # seconds
    status: str  # e.g., "success", "error"
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)