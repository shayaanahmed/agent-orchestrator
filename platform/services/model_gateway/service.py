import json
import asyncio
from typing import Dict, Any, Optional
from uuid import UUID
import aiohttp

from platform.core.interfaces.model_provider import ModelProvider, ModelRequest, ModelResponse
from platform.core.domain.model import ModelClass

class OllamaModelProvider(ModelProvider):
    """Implementation of ModelProvider that communicates with Ollama through the model gateway"""
    
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self._session = None
    
    async def _get_session(self):
        """Get or create an aiohttp session"""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json"
                }
            )
        return self._session
    
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate content using Ollama via the model gateway"""
        
        url = f"{self.base_url}/generate"
        
        # Map logical model class to actual model name
        model_map = {
            ModelClass.PLANNER: "llama3.2:latest",
            ModelClass.CODER: "codellama:latest", 
            ModelClass.REVIEWER: "llama3.2:latest",
            ModelClass.FAST: "phi3:latest",
            ModelClass.EMBEDDING: "nomic-embed-text:latest",
            ModelClass.VISION: "llava:latest"
        }
        
        model_name = model_map.get(request.model_class, "llama3.2:latest")
        
        # Prepare payload for Ollama API
        payload = {
            "model": model_name,
            "prompt": request.prompt,
            "stream": False
        }
        
        if request.max_tokens:
            payload["options"] = {"num_predict": request.max_tokens}
        
        if request.temperature is not None:
            if "options" not in payload:
                payload["options"] = {}
            payload["options"]["temperature"] = request.temperature
        
        session = await self._get_session()
        
        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    return ModelResponse(
                        project_id=request.project_id,
                        request_id=UUID(int=1),  # Placeholder for real UUID
                        agent_run_id=request.agent_run_id,
                        model_class=request.model_class,
                        content=result.get("response", ""),
                        status="success"
                    )
                else:
                    error_text = await response.text()
                    return ModelResponse(
                        project_id=request.project_id,
                        request_id=UUID(int=1),
                        agent_run_id=request.agent_run_id,
                        model_class=request.model_class,
                        content="",
                        status="error",
                        error_message=f"Ollama API error: {error_text}"
                    )
                    
        except Exception as e:
            return ModelResponse(
                project_id=request.project_id,
                request_id=UUID(int=1),
                agent_run_id=request.agent_run_id,
                model_class=request.model_class,
                content="",
                status="error",
                error_message=f"Request failed: {str(e)}"
            )
    
    async def health_check(self) -> bool:
        """Check if the model provider is healthy"""
        url = f"{self.base_url}/health"
        
        session = await self._get_session()
        
        try:
            async with session.get(url) as response:
                return response.status == 200
        except Exception:
            return False
    
    async def get_model_info(self, model_class: str) -> Dict[str, Any]:
        """Get information about a specific model class"""
        # In real implementation, this would query Ollama for actual model details
        return {
            "name": f"model-{model_class}",
            "status": "ready",
            "available": True,
            "description": f"Model for {model_class} tasks"
        }
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()