import unittest
from uuid import uuid4

from core.domain.agent import AgentRole, AgentSpec, Capability
from core.domain.artifact import Artifact, ArtifactType
from core.domain.project import Project, ProjectGoal, ProjectStatus
from core.domain.task import TaskStatus, WorkItem


class DomainModelTests(unittest.TestCase):
    def test_project_creation(self) -> None:
        project = Project(
            id=uuid4(),
            name="Paper Trading App",
            description="An application for paper trading stocks",
            goal=ProjectGoal(text="Build a paper-trading application"),
            owner_id=uuid4(),
        )
        self.assertEqual(project.status, ProjectStatus.CREATED)
        self.assertEqual(project.requirements, [])

    def test_agent_spec_creation(self) -> None:
        agent = AgentSpec(
            id=uuid4(),
            role=AgentRole.CODER,
            objective="Implement project deliverables",
            capabilities=[Capability.CODE_GENERATION],
            instructions="Produce complete code",
            model_class="coder",
        )
        self.assertEqual(agent.role, AgentRole.CODER)
        self.assertIn(Capability.CODE_GENERATION, agent.capabilities)

    def test_work_item_uses_independent_default_lists(self) -> None:
        first = WorkItem(
            id=uuid4(), project_id=uuid4(), name="One", description="First task"
        )
        second = WorkItem(
            id=uuid4(), project_id=uuid4(), name="Two", description="Second task"
        )
        first.dependencies.append(uuid4())
        self.assertEqual(second.dependencies, [])
        self.assertEqual(first.status, TaskStatus.PENDING)

    def test_artifact_creation(self) -> None:
        artifact = Artifact(
            id=uuid4(),
            project_id=uuid4(),
            work_item_id=uuid4(),
            producer_agent_id=uuid4(),
            name="Requirements",
            type=ArtifactType.DOCUMENTATION,
            mime_type="text/markdown",
            size=12,
            content_hash="a" * 64,
            storage_reference="project/requirements.md",
        )
        self.assertEqual(artifact.size, 12)


if __name__ == "__main__":
    unittest.main()
