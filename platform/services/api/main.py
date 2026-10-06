from fastapi import FastAPI, HTTPException, Depends
from uuid import UUID
import asyncio

from platform.core.domain.project import Project, ProjectGoal
from platform.core.domain.agent import AgentSpec
from platform.application.services.project_service import ProjectService
from platform.application.services.agent_service import AgentService
from platform.adapters.database.project_repository import ProjectRepository
from platform.services.model_gateway.service import OllamaModelProvider

app = FastAPI(
    title="AI Project Execution Platform",
    version="1.0.0",
    description="Platform that transforms human objectives into verified project deliverables through a dynamically assembled team of AI agents"
)

# Initialize services - in production, these would be injected via DI
async def get_model_provider():
    # This would normally come from dependency injection
    return OllamaModelProvider(
        base_url="https://llm.internal.example/v1",
        api_token="<secret>"
    )

@app.get("/")
async def root():
    return {"message": "AI Project Execution Platform API"}

@app.post("/projects")
async def create_project(goal_text: str, name: str, description: str = None):
    """Create a new project with an objective"""
    # In practice, this would be handled through domain services
    try:
        project = Project(
            id=UUID(int=1),  # This would be generated properly in real implementation
            name=name,
            description=description,
            goal=ProjectGoal(text=goal_text),
            owner_id=UUID(int=2),
            status="created"
        )
        return {"project_id": str(project.id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}")
async def get_project(project_id: UUID):
    """Get project details"""
    # In practice, this would fetch from database
    return {
        "project_id": str(project_id),
        "name": "Sample Project",
        "status": "created"
    }

@app.post("/projects/{project_id}/clarify")
async def clarify_requirements(project_id: UUID, user_input: str):
    """Clarify project requirements with the user"""
    model_provider = await get_model_provider()
    project_service = ProjectService(model_provider)
    
    try:
        requirements = await project_service.clarify_requirements(project_id, user_input)
        return {"requirements": requirements}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/capabilities")
async def list_capabilities():
    """List available agent capabilities"""
    # In a full implementation, this would query the capability catalog
    return {
        "capabilities": ["code_generation", "code_review", "testing", "documentation", "research", "security_analysis", "deployment"]
    }

@app.get("/role-templates")
async def list_role_templates():
    """List available agent role templates"""
    # In a full implementation, this would query the agent catalog
    return {
        "roles": ["planner", "coder", "reviewer", "researcher", "tester", "deployer"]
    }

@app.get("/models")
async def list_models():
    """List available logical model classes"""
    return {
        "models": ["planner", "coder", "reviewer", "fast", "embedding", "vision"]
    }

@app.get("/system/health")
async def system_health():
    """Check system health status"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)