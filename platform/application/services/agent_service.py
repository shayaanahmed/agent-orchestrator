from typing import List, Optional
from uuid import UUID

from platform.core.domain.agent import AgentSpec, Capability, AgentRole
from platform.core.domain.task import WorkItem
from platform.application.services.project_service import ProjectService

class AgentService:
    """Service for managing agent specifications and assignments"""
    
    def __init__(self):
        # In a full implementation, this would be injected or come from persistence
        self._agent_catalog = self._build_agent_catalog()
    
    def _build_agent_catalog(self) -> List[AgentSpec]:
        """Build the catalog of available agents"""
        return [
            AgentSpec(
                id=UUID(int=1),
                role=AgentRole.PLANNER,
                objective="Plan and organize AI project execution",
                capabilities=[Capability.CODE_GENERATION, Capability.RESEARCH],
                instructions="Create structured plans for projects based on requirements",
                model_class="planner",
                max_iterations=5,
                max_model_calls=20
            ),
            AgentSpec(
                id=UUID(int=2),
                role=AgentRole.CODER,
                objective="Write and implement code solutions",
                capabilities=[Capability.CODE_GENERATION],
                instructions="Generate implementation code for tasks",
                model_class="coder",
                max_iterations=15,
                max_model_calls=30
            ),
            AgentSpec(
                id=UUID(int=3),
                role=AgentRole.REVIEWER,
                objective="Review and validate generated artifacts",
                capabilities=[Capability.CODE_REVIEW, Capability.TESTING],
                instructions="Examine code quality, adherence to requirements, and correctness",
                model_class="reviewer",
                max_iterations=10,
                max_model_calls=25
            )
        ]
    
    def get_available_agents(self, required_capabilities: List[Capability]) -> List[AgentSpec]:
        """Find all agents that have the necessary capabilities"""
        available = []
        
        for agent in self._agent_catalog:
            # Check if all required capabilities are contained in agent's capabilities
            agent_caps = set(agent.capabilities)
            req_caps = set(required_capabilities)
            
            if req_caps.issubset(agent_caps):
                available.append(agent)
                
        return available
    
    def get_agent_by_role(self, role: AgentRole) -> Optional[AgentSpec]:
        """Get a specific agent by role"""
        for agent in self._agent_catalog:
            if agent.role == role:
                return agent
        return None
    
    async def assign_work_to_agent(self, 
                                 work_item: WorkItem, 
                                 agent: AgentSpec) -> WorkItem:
        """Assign a work item to an agent"""
        # This would typically update state in the persistence layer
        
        # For now, just setting it in memory
        work_item.assigned_agent_id = agent.id
        work_item.status = "assigned"
        
        return work_item