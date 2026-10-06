from __future__ import annotations

from collections import defaultdict, deque

from core.domain.planning import PlannedAgent, PlannedTask, TeamPlan
from core.planning.catalog import ROLE_CAPABILITIES, SENSITIVE_CAPABILITIES


class PlanValidationError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def _agent_errors(agents: list[PlannedAgent]) -> list[str]:
    errors: list[str] = []
    for agent in agents:
        allowed = ROLE_CAPABILITIES.get(agent.role, set())
        unsupported = set(agent.capabilities) - allowed
        if unsupported:
            errors.append(
                f"agent {agent.key} requests capabilities not allowed for {agent.role.value}: "
                f"{sorted(item.value for item in unsupported)}"
            )

    return errors


def _task_errors(
    tasks: list[PlannedTask], agents: dict[str, PlannedAgent]
) -> list[str]:
    errors: list[str] = []
    for task in tasks:
        agent = agents[task.agent_key]
        missing = set(task.required_capabilities) - set(agent.capabilities)
        if missing:
            errors.append(
                f"task {task.key} requires capabilities absent from agent {agent.key}: "
                f"{sorted(item.value for item in missing)}"
            )
        if (
            set(task.required_capabilities) & SENSITIVE_CAPABILITIES
            and not task.requires_approval
        ):
            errors.append(f"task {task.key} requires an approval gate")
    return errors


def _contains_cycle(tasks: list[PlannedTask]) -> bool:
    graph: dict[str, list[str]] = defaultdict(list)
    indegree = {task.key: 0 for task in tasks}
    for task in tasks:
        for dependency in task.dependencies:
            graph[dependency].append(task.key)
            indegree[task.key] += 1

    queue = deque(key for key, degree in indegree.items() if degree == 0)
    visited = 0
    while queue:
        current = queue.popleft()
        visited += 1
        for child in graph[current]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    return visited != len(tasks)


def validate_team_plan(plan: TeamPlan) -> TeamPlan:
    agents = {agent.key: agent for agent in plan.agents}
    errors = _agent_errors(plan.agents) + _task_errors(plan.tasks, agents)
    if _contains_cycle(plan.tasks):
        errors.append("task dependencies contain a cycle")

    if errors:
        raise PlanValidationError(errors)
    return plan
