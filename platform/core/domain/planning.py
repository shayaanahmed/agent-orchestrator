from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from core.domain.agent import AgentRole, Capability
from core.domain.model import ModelClass

ROLE_MODEL_CLASSES = {
    AgentRole.PLANNER: ModelClass.PLANNER,
    AgentRole.CODER: ModelClass.CODER,
    AgentRole.REVIEWER: ModelClass.REVIEWER,
    AgentRole.RESEARCHER: ModelClass.FAST,
    AgentRole.TESTER: ModelClass.REVIEWER,
    AgentRole.DEPLOYER: ModelClass.CODER,
}


class ReviewDecision(StrEnum):
    APPROVED = "approved"
    APPROVED_WITH_WARNINGS = "approved_with_warnings"
    REVISION_REQUIRED = "revision_required"
    REJECTED = "rejected"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class PlannedAgent(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    role: AgentRole
    objective: str = Field(min_length=3, max_length=1000)
    capabilities: list[Capability] = Field(min_length=1)
    model_class: ModelClass

    @model_validator(mode="before")
    @classmethod
    def normalize_model_class(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        candidate = value.get("model_class")
        if isinstance(candidate, ModelClass):
            return value
        if isinstance(candidate, str):
            try:
                ModelClass(candidate)
                return value
            except ValueError:
                pass
        role_value = value.get("role")
        try:
            role = (
                role_value
                if isinstance(role_value, AgentRole)
                else AgentRole(role_value)
                if isinstance(role_value, str)
                else None
            )
        except ValueError:
            role = None
        if role is None:
            return value
        return {**value, "model_class": ROLE_MODEL_CLASSES[role]}


class PlannedTask(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    name: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3, max_length=5000)
    agent_key: str
    dependencies: list[str] = Field(default_factory=list)
    required_capabilities: list[Capability] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(min_length=1)
    expected_artifacts: list[str] = Field(default_factory=lambda: ["markdown_document"])
    requires_approval: bool = False


class TeamPlan(BaseModel):
    project_id: UUID
    interpreted_goal: str = Field(min_length=3)
    requirements: list[str] = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    agents: list[PlannedAgent] = Field(min_length=1, max_length=12)
    tasks: list[PlannedTask] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_references(self) -> TeamPlan:
        agent_keys = [agent.key for agent in self.agents]
        task_keys = [task.key for task in self.tasks]
        if len(agent_keys) != len(set(agent_keys)):
            raise ValueError("agent keys must be unique")
        if len(task_keys) != len(set(task_keys)):
            raise ValueError("task keys must be unique")

        known_agents = set(agent_keys)
        known_tasks = set(task_keys)
        for task in self.tasks:
            if task.agent_key not in known_agents:
                raise ValueError(
                    f"task {task.key} references unknown agent {task.agent_key}"
                )
            unknown = set(task.dependencies) - known_tasks
            if unknown:
                raise ValueError(
                    f"task {task.key} has unknown dependencies: {sorted(unknown)}"
                )
            if task.key in task.dependencies:
                raise ValueError(f"task {task.key} cannot depend on itself")
        return self


class ReviewResult(BaseModel):
    decision: ReviewDecision
    summary: str
    evidence: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    required_revisions: list[str] = Field(default_factory=list)


class DeliverableFile(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(max_length=1_000_000)
    mime_type: str = Field(default="text/plain", max_length=200)

    @field_validator("path")
    @classmethod
    def safe_relative_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts or normalized.startswith("~"):
            raise ValueError("file path must be a safe relative path")
        if not path.parts or any(part in {"", "."} for part in path.parts):
            raise ValueError("file path is invalid")
        return str(path)


class TaskDeliverable(BaseModel):
    summary: str = Field(min_length=1, max_length=20_000)
    files: list[DeliverableFile] = Field(default_factory=list, max_length=100)
    validation_commands: list[list[str]] = Field(default_factory=list, max_length=10)
    notes: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("validation_commands")
    @classmethod
    def validate_commands(cls, commands: list[list[str]]) -> list[list[str]]:
        for command in commands:
            if not command or len(command) > 30:
                raise ValueError("each validation command needs 1-30 arguments")
            if any(not arg or len(arg) > 500 for arg in command):
                raise ValueError("validation command contains an invalid argument")
        return commands
