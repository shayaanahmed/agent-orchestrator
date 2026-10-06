from __future__ import annotations

import json

from pydantic import ValidationError

from application.services.json_output import parse_json_object
from core.domain.model import ModelClass, ModelRequest
from core.domain.planning import TeamPlan
from core.domain.project import Project
from core.interfaces.model_provider import ModelProvider
from core.planning.catalog import ROLE_CAPABILITIES
from core.planning.validator import PlanValidationError, validate_team_plan


class PlanningError(RuntimeError):
    pass


def validation_messages(
    error: ValueError | ValidationError | PlanValidationError,
) -> list[str]:
    if isinstance(error, PlanValidationError):
        return error.errors
    if isinstance(error, ValidationError):
        return [
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        ]
    return [str(error)]


class PlanningService:
    def __init__(self, model_provider: ModelProvider, max_attempts: int = 3) -> None:
        self.model_provider = model_provider
        self.max_attempts = max_attempts

    def _prompt(self, project: Project, validation_errors: list[str]) -> str:
        catalog = {
            role.value: sorted(capability.value for capability in capabilities)
            for role, capabilities in ROLE_CAPABILITIES.items()
        }
        correction = ""
        if validation_errors:
            correction = (
                "\nThe previous plan was rejected for these reasons:\n- "
                + "\n- ".join(validation_errors)
                + "\nCorrect every error."
            )
        return f"""
You are the planning component of a governed AI project execution platform.
Create the smallest competent team and an executable dependency-aware task plan.

Project ID: {project.id}
Project name: {project.name}
Goal: {project.goal.text}
Description: {project.description or "Not supplied"}
Constraints: {json.dumps(project.constraints)}

Allowed role-to-capability catalog:
{json.dumps(catalog, indent=2)}

Rules:
- Use only roles and capabilities from the catalog.
- Every task must contain measurable acceptance criteria.
- Dependencies must be acyclic and reference task keys.
- The assigned agent must possess every required capability.
- Deployment tasks must set requires_approval=true.
- Prefer 2-6 agents and 3-12 meaningful tasks.
- Do not include commentary outside the JSON object.

Return JSON matching this schema:
{json.dumps(TeamPlan.model_json_schema())}
{correction}
""".strip()

    async def create_plan(self, project: Project) -> TeamPlan:
        errors: list[str] = []
        for _ in range(self.max_attempts):
            response = await self.model_provider.generate(
                ModelRequest(
                    project_id=project.id,
                    model_class=ModelClass.PLANNER,
                    prompt=self._prompt(project, errors),
                    response_format="json_schema",
                    response_schema=TeamPlan.model_json_schema(),
                    temperature=0.2,
                    max_tokens=3000,
                )
            )
            if response.status != "success":
                raise PlanningError(response.error_message or "model request failed")
            try:
                raw = parse_json_object(response.content)
                raw["project_id"] = str(project.id)
                plan = TeamPlan.model_validate(raw)
                return validate_team_plan(plan)
            except (ValueError, ValidationError, PlanValidationError) as exc:
                errors = validation_messages(exc)
        raise PlanningError("Unable to create a valid plan: " + "; ".join(errors))
