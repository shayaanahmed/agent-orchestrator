from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID, uuid4

from adapters.artifacts.local_store import LocalArtifactStore
from adapters.database.store import PostgresStore
from adapters.sandbox.client import SandboxClient
from application.services.json_output import parse_json_object
from application.services.planning_service import PlanningService
from core.domain.agent import Capability
from core.domain.model import ModelClass, ModelRequest
from core.domain.planning import (
    DeliverableFile,
    PlannedAgent,
    PlannedTask,
    ReviewDecision,
    ReviewResult,
    TaskDeliverable,
    TeamPlan,
)
from core.domain.project import ProjectStatus
from core.domain.task import TaskStatus
from core.interfaces.model_provider import ModelProvider


class ProjectExecutionService:
    def __init__(
        self,
        store: PostgresStore,
        artifacts: LocalArtifactStore,
        model_provider: ModelProvider,
        sandbox: SandboxClient,
        max_parallel_tasks: int = 4,
    ) -> None:
        self.store = store
        self.artifacts = artifacts
        self.model_provider = model_provider
        self.sandbox = sandbox
        self.planner = PlanningService(model_provider)
        self.max_parallel_tasks = max_parallel_tasks

    async def run_project(self, project_id: UUID) -> None:
        project = await self.store.get_project(project_id)
        if not project:
            raise KeyError(f"project {project_id} not found")
        try:
            if project.status == ProjectStatus.FAILED:
                await self.store.prepare_project_retry(project_id)
            if not project.team_plan:
                await self.store.set_project_status(project_id, ProjectStatus.PLANNING)
                plan = await self.planner.create_plan(project)
                await self.store.set_project_status(
                    project_id, ProjectStatus.VALIDATING_PLAN
                )
                await self.store.save_plan(plan)
            else:
                plan = TeamPlan.model_validate(project.team_plan)
            await self.store.set_project_status(project_id, ProjectStatus.EXECUTING)
            completed = await self._execute_plan(plan)
            if not completed:
                current = await self.store.get_project(project_id)
                if current and current.status != ProjectStatus.AWAITING_APPROVAL:
                    await self.store.set_project_status(
                        project_id,
                        ProjectStatus.FAILED,
                        "One or more tasks failed review or execution",
                    )
                return
            await self.store.set_project_status(project_id, ProjectStatus.REVIEWING)
            failed = [
                item
                for item in await self.store.list_work_items(project_id)
                if item["status"] != TaskStatus.COMPLETED.value
            ]
            if failed:
                raise RuntimeError(f"{len(failed)} tasks did not complete")
            await self._create_project_bundle(project_id)
            await self.store.set_project_status(project_id, ProjectStatus.COMPLETED)
            await self.store.add_event(project_id, "project.completed", {})
        except Exception as exc:
            await self.store.set_project_status(
                project_id, ProjectStatus.FAILED, str(exc)
            )
            raise

    async def _execute_plan(self, plan: TeamPlan) -> bool:
        task_specs = {task.key: task for task in plan.tasks}
        agent_specs = {agent.key: agent for agent in plan.agents}
        semaphore = asyncio.Semaphore(self.max_parallel_tasks)

        while True:
            rows = await self.store.list_work_items(plan.project_id)
            states = {row["task_key"]: row["status"] for row in rows}
            if all(state == TaskStatus.COMPLETED.value for state in states.values()):
                return True
            if any(state == TaskStatus.FAILED.value for state in states.values()):
                return False

            runnable = [
                row
                for row in rows
                if row["status"]
                in {
                    TaskStatus.PENDING.value,
                    TaskStatus.ASSIGNED.value,
                    TaskStatus.IN_PROGRESS.value,
                }
                and all(
                    states.get(dependency) == TaskStatus.COMPLETED.value
                    for dependency in row["dependencies"]
                )
            ]
            if not runnable:
                waiting = [
                    row
                    for row in rows
                    if row["status"] == TaskStatus.WAITING_FOR_APPROVAL.value
                ]
                if waiting:
                    await self.store.set_project_status(
                        plan.project_id, ProjectStatus.AWAITING_APPROVAL
                    )
                    return False
                raise RuntimeError("task graph is blocked and has no runnable tasks")

            async def guarded(row: dict[str, Any]) -> None:
                async with semaphore:
                    spec = task_specs[row["task_key"]]
                    await self._execute_task(
                        plan, row, spec, agent_specs[spec.agent_key]
                    )

            await asyncio.gather(*(guarded(row) for row in runnable))

    async def _execute_task(
        self,
        plan: TeamPlan,
        row: dict[str, Any],
        task: PlannedTask,
        agent: PlannedAgent,
    ) -> None:
        if not await self._approval_allows(plan, row, task):
            return

        await self.store.set_work_item_status(row["id"], TaskStatus.IN_PROGRESS)
        workspace = await self.artifacts.workspace_snapshot(
            plan.project_id, max_bytes=60_000
        )
        all_rows = await self.store.list_work_items(plan.project_id)
        dependency_outputs = {
            item["task_key"]: item["output"]
            for item in all_rows
            if item["task_key"] in task.dependencies
        }
        prompt = f"""
You are the {agent.role.value} on project: {plan.interpreted_goal}
Objective: {agent.objective}
Task: {task.name}
Task description: {task.description}
Acceptance criteria: {json.dumps(task.acceptance_criteria)}
Dependency outputs: {json.dumps(dependency_outputs)}
Current project workspace files: {json.dumps(workspace)}

Produce the actual deliverable, not a tutorial or a proposal. Return only JSON matching
this schema: {json.dumps(TaskDeliverable.model_json_schema())}

For implementation work, return complete file contents in files. Paths are relative to
the project root. Modify an existing file by returning its full replacement content.
Use validation_commands to request relevant checks. Commands are argv arrays and may
only use python/python3 (-m or -c), pytest, node (--check or --test), or npm (test/run).
Do not install packages, access the network, use absolute paths, or include secrets.
For non-file work, put the concrete result in summary and optionally a Markdown file.
Explicitly satisfy every acceptance criterion.
""".strip()
        deliverable: TaskDeliverable | None = None
        review: ReviewResult | None = None
        validation: list[dict[str, Any]] = []
        attempt_prompt = prompt
        for attempt in range(2):
            try:
                deliverable = await self._generate_deliverable(
                    plan,
                    agent,
                    attempt_prompt,
                    temperature=0.2 if attempt == 0 else 0.1,
                )
            except RuntimeError as exc:
                await self.store.set_work_item_status(
                    row["id"], TaskStatus.FAILED, error=str(exc)
                )
                return
            for file in deliverable.files:
                await self.artifacts.materialize(
                    plan.project_id, file.path, file.content.encode("utf-8")
                )
            validation = await self._validate_deliverable(
                plan.project_id, task, deliverable
            )
            review = await self._review(plan, task, deliverable, validation)
            await self.store.save_review(
                plan.project_id, row["id"], review.model_dump(mode="json")
            )
            if review.decision in {
                ReviewDecision.APPROVED,
                ReviewDecision.APPROVED_WITH_WARNINGS,
            }:
                break
            if attempt == 0:
                feedback = review.required_revisions or review.findings
                attempt_prompt = (
                    prompt
                    + "\n\nYour previous deliverable failed independent review. Correct all "
                    + "of these issues and return the entire corrected JSON deliverable:\n- "
                    + "\n- ".join(feedback)
                    + f"\nValidation results: {json.dumps(validation)}"
                )

        if (
            deliverable is None
            or review is None
            or review.decision
            not in {
                ReviewDecision.APPROVED,
                ReviewDecision.APPROVED_WITH_WARNINGS,
            }
        ):
            await self.store.set_work_item_status(
                row["id"],
                TaskStatus.FAILED,
                error=review.summary if review else "No valid deliverable was produced",
            )
            return

        files = deliverable.files
        if not files:
            files = [
                DeliverableFile(
                    path=f"reports/{task.key}.md",
                    content=deliverable.summary,
                    mime_type="text/markdown",
                )
            ]
            await self.artifacts.materialize(
                plan.project_id, files[0].path, files[0].content.encode("utf-8")
            )
        for file in files:
            stored = await self.artifacts.put(
                plan.project_id, row["id"], file.path, file.content.encode("utf-8")
            )
            await self.store.create_artifact(
                plan.project_id,
                row["id"],
                file.path,
                file.mime_type,
                stored.content_hash,
                stored.storage_reference,
                stored.size,
            )
        await self.store.set_work_item_status(
            row["id"],
            TaskStatus.COMPLETED,
            output=json.dumps(
                {
                    "summary": deliverable.summary,
                    "files": [file.path for file in files],
                    "validation": validation,
                }
            ),
        )

    async def _approval_allows(
        self, plan: TeamPlan, row: dict[str, Any], task: PlannedTask
    ) -> bool:
        if not row["requires_approval"]:
            return True
        approval = await self.store.approval_status(row["id"])
        if approval is None:
            await self.store.create_approval(
                plan.project_id,
                row["id"],
                task.name,
                "This task uses a capability that requires explicit human approval.",
            )
            await self.store.set_work_item_status(
                row["id"], TaskStatus.WAITING_FOR_APPROVAL
            )
            return False
        if approval == "rejected":
            await self.store.set_work_item_status(
                row["id"], TaskStatus.FAILED, error="Human rejected this action"
            )
            return False
        return approval == "approved"

    async def _generate_deliverable(
        self, plan: TeamPlan, agent: PlannedAgent, prompt: str, temperature: float
    ) -> TaskDeliverable:
        parsing_error = ""
        for _ in range(2):
            response = await self.model_provider.generate(
                ModelRequest(
                    project_id=plan.project_id,
                    agent_run_id=uuid4(),
                    model_class=agent.model_class,
                    prompt=prompt + parsing_error,
                    response_format="json_schema",
                    response_schema=TaskDeliverable.model_json_schema(),
                    max_tokens=12_000,
                    temperature=temperature,
                )
            )
            if response.status != "success":
                raise RuntimeError(response.error_message or "model generation failed")
            try:
                return TaskDeliverable.model_validate(
                    parse_json_object(response.content)
                )
            except ValueError as exc:
                parsing_error = (
                    "\n\nYour response was invalid: "
                    + str(exc)
                    + ". Return only a valid JSON object matching the schema."
                )
        raise RuntimeError("model repeatedly returned an invalid task deliverable")

    async def _validate(
        self, project_id: UUID, deliverable: TaskDeliverable
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for command in deliverable.validation_commands:
            try:
                result = await self.sandbox.execute(project_id, command)
            except Exception as exc:
                result = {
                    "command": command,
                    "exit_code": None,
                    "timed_out": False,
                    "stdout": "",
                    "stderr": f"Sandbox error: {exc}",
                }
            results.append(result)
        return results

    async def _validate_deliverable(
        self, project_id: UUID, task: PlannedTask, deliverable: TaskDeliverable
    ) -> list[dict[str, Any]]:
        if not set(task.required_capabilities) & {
            Capability.CODE_GENERATION,
            Capability.TESTING,
        }:
            deliverable.validation_commands = []
        return await self._validate(project_id, deliverable)

    async def _review(
        self,
        plan: TeamPlan,
        task: PlannedTask,
        deliverable: TaskDeliverable,
        validation: list[dict[str, Any]],
    ) -> ReviewResult:
        prompt = f"""
Independently review this task deliverable.
Project goal: {plan.interpreted_goal}
Task: {task.name}
Acceptance criteria: {json.dumps(task.acceptance_criteria)}
Deliverable: {deliverable.model_dump_json()}
Sandbox validation results: {json.dumps(validation)}

Return only a JSON object with these fields:
- decision: approved, approved_with_warnings, revision_required, rejected, or human_review_required
- summary: string
- evidence: string array
- findings: string array
- required_revisions: string array
Do not approve unless every acceptance criterion is addressed by concrete evidence.
If a validation command failed or timed out, require revision.
Judge only this task's stated scope and acceptance criteria. Do not demand application
code or tests from research, planning, review, or documentation tasks. An empty
validation result is expected when the task does not generate or test code.
""".strip()
        response = await self.model_provider.generate(
            ModelRequest(
                project_id=plan.project_id,
                agent_run_id=uuid4(),
                model_class=ModelClass.REVIEWER,
                prompt=prompt,
                response_format="json_schema",
                response_schema=ReviewResult.model_json_schema(),
                max_tokens=2000,
                temperature=0.0,
            )
        )
        if response.status != "success":
            return ReviewResult(
                decision=ReviewDecision.REJECTED,
                summary=response.error_message or "review model failed",
                findings=[response.error_message or "review model failed"],
                required_revisions=["Run review again when the model is available"],
            )
        try:
            return ReviewResult.model_validate(parse_json_object(response.content))
        except ValueError as exc:
            return ReviewResult(
                decision=ReviewDecision.REJECTED,
                summary="Reviewer returned invalid structured output",
                findings=[str(exc)],
                required_revisions=["Repeat independent review"],
            )

    async def _create_project_bundle(self, project_id: UUID) -> None:
        existing = await self.store.list_artifacts(project_id)
        if any(item["name"] == "project-workspace.zip" for item in existing):
            return
        work_items = await self.store.list_work_items(project_id)
        if not work_items:
            return
        stored = await self.artifacts.bundle(project_id, work_items[-1]["id"])
        if stored:
            await self.store.create_artifact(
                project_id,
                work_items[-1]["id"],
                "project-workspace.zip",
                "application/zip",
                stored.content_hash,
                stored.storage_reference,
                stored.size,
            )
