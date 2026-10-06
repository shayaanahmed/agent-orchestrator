import unittest
from uuid import uuid4

from pydantic import ValidationError

from application.services.json_output import parse_json_object
from application.services.planning_service import validation_messages
from core.domain.agent import AgentRole, Capability
from core.domain.model import ModelClass
from core.domain.planning import PlannedAgent, PlannedTask, TeamPlan
from core.planning.validator import PlanValidationError, validate_team_plan


def valid_plan() -> TeamPlan:
    project_id = uuid4()
    return TeamPlan(
        project_id=project_id,
        interpreted_goal="Build a tested application",
        requirements=["The application must run"],
        agents=[
            PlannedAgent(
                key="coder",
                role=AgentRole.CODER,
                objective="Implement the application",
                capabilities=[Capability.CODE_GENERATION],
                model_class="coder",
            ),
            PlannedAgent(
                key="reviewer",
                role=AgentRole.REVIEWER,
                objective="Review the implementation",
                capabilities=[Capability.CODE_REVIEW, Capability.TESTING],
                model_class="reviewer",
            ),
        ],
        tasks=[
            PlannedTask(
                key="implement",
                name="Implement application",
                description="Create the complete application",
                agent_key="coder",
                required_capabilities=[Capability.CODE_GENERATION],
                acceptance_criteria=["Source code is included"],
            ),
            PlannedTask(
                key="test",
                name="Test application",
                description="Review and test the implementation",
                agent_key="reviewer",
                dependencies=["implement"],
                required_capabilities=[Capability.TESTING],
                acceptance_criteria=["Test evidence is included"],
            ),
        ],
    )


class PlanValidationTests(unittest.TestCase):
    def test_valid_plan(self) -> None:
        self.assertEqual(validate_team_plan(valid_plan()).tasks[1].key, "test")

    def test_cycle_is_rejected(self) -> None:
        plan = valid_plan()
        plan.tasks[0].dependencies = ["test"]
        with self.assertRaises(PlanValidationError):
            validate_team_plan(plan)

    def test_role_capability_escalation_is_rejected(self) -> None:
        plan = valid_plan()
        plan.agents[0].capabilities.append(Capability.DEPLOYMENT)
        with self.assertRaises(PlanValidationError):
            validate_team_plan(plan)

    def test_json_fence_is_parsed(self) -> None:
        self.assertEqual(parse_json_object('```json\n{"ok": true}\n```'), {"ok": True})

    def test_pydantic_validation_errors_become_retry_messages(self) -> None:
        with self.assertRaises(ValidationError) as caught:
            TeamPlan.model_validate({})
        messages = validation_messages(caught.exception)
        self.assertIsInstance(messages, list)
        self.assertTrue(messages)
        self.assertTrue(all(isinstance(message, str) for message in messages))

    def test_generated_model_alias_is_normalized_by_role(self) -> None:
        agent = PlannedAgent(
            key="tester",
            role=AgentRole.TESTER,
            objective="Test the application",
            capabilities=[Capability.TESTING],
            model_class="tester_v1",
        )
        self.assertEqual(agent.model_class, ModelClass.REVIEWER)


if __name__ == "__main__":
    unittest.main()
