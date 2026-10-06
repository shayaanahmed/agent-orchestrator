"""
Test suite for domain models of the AI project execution platform.
"""

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from platform.core.domain.project import Project, ProjectGoal, ProjectStatus  
from platform.core.domain.agent import AgentSpec, AgentRole, Capability
from platform.core.domain.task import WorkItem, TaskStatus
from platform.core.domain.artifact import Artifact, ArtifactType, ArtifactStatus


def test_project_creation():
    """Test that projects can be created with valid data"""
    goal = ProjectGoal(text="Build a paper-trading application")
    
    project = Project(
        id=uuid4(),
        name="Paper Trading App",
        description="An application for paper trading stocks",
        goal=goal,
        owner_id=uuid4(),
        status=ProjectStatus.CREATED
    )
    
    assert project.id is not None
    assert project.name == "Paper Trading App"
    assert project.goal.text == "Build a paper-trading application"
    assert project.status == ProjectStatus.CREATED


def test_agent_spec_creation():
    """Test that agent specifications can be created"""
    agent = AgentSpec(
        id=uuid4(),
        role=AgentRole.PLANNER,
        objective="Plan AI projects",
        capabilities=[Capability.CODE_GENERATION, Capability.RESEARCH],
        instructions="Create structured plans for projects",
        model_class="planner",
        max_iterations=5,
        max_model_calls=20
    )
    
    assert agent.id is not None
    assert agent.role == AgentRole.PLANNER
    assert len(agent.capabilities) == 2


def test_work_item_creation():
    """Test that work items can be created"""
    work_item = WorkItem(
        id=uuid4(),
        project_id=uuid4(),
        name="Create requirements document",
        description="Document the functional requirements",
        status=TaskStatus.PENDING
    )
    
    assert work_item.id is not None
    assert work_item.name == "Create requirements document"
    assert work_item.status == TaskStatus.PENDING


def test_artifact_creation():
    """Test that artifacts can be created"""
    artifact = Artifact(
        id=uuid4(),
        project_id=uuid4(),
        work_item_id=uuid4(),
        producer_agent_id=uuid4(),
        name="Requirements Document",
        type=ArtifactType.DOCUMENTATION,
        mime_type="text/markdown",
        size=1024,
        content_hash="a1b2c3d4e5f6", 
        storage_reference="project1/requirements.md",
        status=ArtifactStatus.DRAFT
    )
    
    assert artifact.id is not None
    assert artifact.name == "Requirements Document"
    assert artifact.type == ArtifactType.DOCUMENTATION
    assert artifact.size == 1024


if __name__ == "__main__":
    pytest.main([__file__])