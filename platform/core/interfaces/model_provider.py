from typing import Protocol, Dict, Any
from uuid import UUID

class ModelRequest:
    """Request to generate content using a model"""
    def __init__(
        self,
        project_id: UUID,
        agent_run_id: UUID,
        model_class: str,
        prompt: str,
        parameters: Dict[str, Any] = None,
        max_tokens: int = None,
        temperature: float = None,
        response_format: str = None
    ):
        self.project_id = project_id
        self.agent_run_id = agent_run_id
        self.model_class = model_class
        self.prompt = prompt
        self.parameters = parameters or {}
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.response_format = response_format

class ModelResponse:
    """Response from a model generation request"""
    def __init__(
        self,
        project_id: UUID,
        request_id: UUID,
        agent_run_id: UUID,
        model_class: str,
        content: str,
        usage: Dict[str, Any] = None,
        latency: float = None,
        status: str = "success",
        error_message: str = None
    ):
        self.project_id = project_id
        self.request_id = request_id
        self.agent_run_id = agent_run_id
        self.model_class = model_class
        self.content = content
        self.usage = usage or {}
        self.latency = latency
        self.status = status
        self.error_message = error_message

class ModelProvider(Protocol):
    """Protocol for model providers - abstracts different LLM interfaces"""
    
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate content using the specified model and prompt"""
        ...
    
    async def health_check(self) -> bool:
        """Check if the model provider is healthy and responsive"""
        ...
        
    async def get_model_info(self, model_class: str) -> Dict[str, Any]:
        """Get information about a specific model class"""
        ...

class ModelGateway:
    """Service that provides a unified interface for different model providers"""
    
    def __init__(self, provider: ModelProvider):
        self._provider = provider
    
    async def generate(self, request: ModelRequest) -> ModelResponse:
        return await self._provider.generate(request)
        
    async def health_check(self) -> bool:
        return await self._provider.health_check()
        
    async def get_model_info(self, model_class: str) -> Dict[str, Any]:
        return await self._provider.get_model_info(model_class)