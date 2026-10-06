from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import asyncpg

from core.domain.planning import TeamPlan
from core.domain.project import Project, ProjectGoal, ProjectStatus
from core.domain.task import TaskStatus

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    goal_text TEXT NOT NULL,
    owner_id UUID NOT NULL,
    status TEXT NOT NULL,
    requirements JSONB NOT NULL DEFAULT '[]'::jsonb,
    constraints JSONB NOT NULL DEFAULT '[]'::jsonb,
    assumptions JSONB NOT NULL DEFAULT '[]'::jsonb,
    acceptance_criteria JSONB NOT NULL DEFAULT '[]'::jsonb,
    capabilities_needed JSONB NOT NULL DEFAULT '[]'::jsonb,
    team_plan JSONB,
    execution_plan JSONB,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS work_items (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    agent_key TEXT NOT NULL,
    status TEXT NOT NULL,
    dependencies JSONB NOT NULL DEFAULT '[]'::jsonb,
    acceptance_criteria JSONB NOT NULL DEFAULT '[]'::jsonb,
    expected_artifacts JSONB NOT NULL DEFAULT '[]'::jsonb,
    required_capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
    output TEXT,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    UNIQUE(project_id, task_key)
);
CREATE TABLE IF NOT EXISTS artifacts (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    work_item_id UUID NOT NULL REFERENCES work_items(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    storage_reference TEXT NOT NULL,
    size BIGINT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    work_item_id UUID NOT NULL REFERENCES work_items(id) ON DELETE CASCADE,
    decision TEXT NOT NULL,
    summary TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    findings JSONB NOT NULL DEFAULT '[]'::jsonb,
    required_revisions JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS approval_requests (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    work_item_id UUID REFERENCES work_items(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    risk TEXT NOT NULL,
    status TEXT NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    decided_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS project_events (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_work_items_project ON work_items(project_id);
CREATE INDEX IF NOT EXISTS idx_events_project_created ON project_events(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(project_id);
"""


def now() -> datetime:
    return datetime.now(UTC)


def decode_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


class PostgresStore:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(
            self.database_url, min_size=1, max_size=10
        )
        async with self.pool.acquire() as connection:
            await connection.execute(SCHEMA_SQL)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()

    def _pool(self) -> asyncpg.Pool:
        if self.pool is None:
            raise RuntimeError("database is not connected")
        return self.pool

    async def create_project(self, project: Project) -> Project:
        await self._pool().execute(
            """
            INSERT INTO projects (
                id, name, description, goal_text, owner_id, status, requirements,
                constraints, assumptions, acceptance_criteria, capabilities_needed,
                created_at, updated_at, schema_version
            ) VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb,$9::jsonb,$10::jsonb,
                      $11::jsonb,$12,$13,$14)
            """,
            project.id,
            project.name,
            project.description,
            project.goal.text,
            project.owner_id,
            project.status.value,
            json.dumps(project.requirements),
            json.dumps(project.constraints),
            json.dumps(project.assumptions),
            json.dumps(project.acceptance_criteria),
            json.dumps(project.capabilities_needed),
            project.created_at,
            project.updated_at,
            project.schema_version,
        )
        await self.add_event(project.id, "project.created", {"name": project.name})
        return project

    async def get_project(self, project_id: UUID) -> Project | None:
        row = await self._pool().fetchrow(
            "SELECT * FROM projects WHERE id=$1", project_id
        )
        return self._project(row) if row else None

    async def list_projects(self, limit: int = 100, offset: int = 0) -> list[Project]:
        rows = await self._pool().fetch(
            "SELECT * FROM projects ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit,
            offset,
        )
        return [self._project(row) for row in rows]

    def _project(self, row: asyncpg.Record) -> Project:
        return Project(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            goal=ProjectGoal(text=row["goal_text"]),
            owner_id=row["owner_id"],
            status=ProjectStatus(row["status"]),
            requirements=decode_json(row["requirements"], []),
            constraints=decode_json(row["constraints"], []),
            assumptions=decode_json(row["assumptions"], []),
            acceptance_criteria=decode_json(row["acceptance_criteria"], []),
            capabilities_needed=decode_json(row["capabilities_needed"], []),
            team_plan=decode_json(row["team_plan"], None),
            execution_plan=decode_json(row["execution_plan"], None),
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            schema_version=row["schema_version"],
        )

    async def set_project_status(
        self, project_id: UUID, status: ProjectStatus, error: str | None = None
    ) -> None:
        await self._pool().execute(
            "UPDATE projects SET status=$2, error=$3, updated_at=$4 WHERE id=$1",
            project_id,
            status.value,
            error,
            now(),
        )
        await self.add_event(
            project_id,
            "project.status_changed",
            {"status": status.value, "error": error},
        )

    async def save_plan(self, plan: TeamPlan) -> None:
        capabilities = sorted(
            {
                capability.value
                for agent in plan.agents
                for capability in agent.capabilities
            }
        )
        await self._pool().execute(
            """
            UPDATE projects SET requirements=$2::jsonb, constraints=$3::jsonb,
              assumptions=$4::jsonb, capabilities_needed=$5::jsonb, team_plan=$6::jsonb,
              execution_plan=$7::jsonb, updated_at=$8 WHERE id=$1
            """,
            plan.project_id,
            json.dumps(plan.requirements),
            json.dumps(plan.constraints),
            json.dumps(plan.assumptions),
            json.dumps(capabilities),
            plan.model_dump_json(),
            json.dumps({"task_order": [task.key for task in plan.tasks]}),
            now(),
        )
        agent_by_key = {agent.key: agent for agent in plan.agents}
        for task in plan.tasks:
            agent = agent_by_key[task.agent_key]
            await self._pool().execute(
                """
                INSERT INTO work_items (
                    id, project_id, task_key, name, description, agent_key, status,
                    dependencies, acceptance_criteria, expected_artifacts,
                    required_capabilities, requires_approval, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9::jsonb,$10::jsonb,
                          $11::jsonb,$12,$13,$14)
                ON CONFLICT (project_id, task_key) DO UPDATE SET
                    name=EXCLUDED.name, description=EXCLUDED.description,
                    agent_key=EXCLUDED.agent_key, dependencies=EXCLUDED.dependencies,
                    acceptance_criteria=EXCLUDED.acceptance_criteria,
                    expected_artifacts=EXCLUDED.expected_artifacts,
                    required_capabilities=EXCLUDED.required_capabilities,
                    requires_approval=EXCLUDED.requires_approval, updated_at=EXCLUDED.updated_at
                """,
                uuid4(),
                plan.project_id,
                task.key,
                task.name,
                task.description,
                agent.key,
                TaskStatus.PENDING.value,
                json.dumps(task.dependencies),
                json.dumps(task.acceptance_criteria),
                json.dumps(task.expected_artifacts),
                json.dumps([item.value for item in task.required_capabilities]),
                task.requires_approval,
                now(),
                now(),
            )
        await self.add_event(
            plan.project_id, "plan.validated", {"tasks": len(plan.tasks)}
        )

    async def list_work_items(self, project_id: UUID) -> list[dict[str, Any]]:
        rows = await self._pool().fetch(
            "SELECT * FROM work_items WHERE project_id=$1 ORDER BY created_at, task_key",
            project_id,
        )
        result = []
        for row in rows:
            item = dict(row)
            for field in (
                "dependencies",
                "acceptance_criteria",
                "expected_artifacts",
                "required_capabilities",
            ):
                item[field] = decode_json(item[field], [])
            result.append(item)
        return result

    async def prepare_project_retry(self, project_id: UUID) -> None:
        await self._pool().execute(
            """
            UPDATE work_items SET status=$2, error=NULL, updated_at=$3
            WHERE project_id=$1 AND status = ANY($4::text[])
            """,
            project_id,
            TaskStatus.PENDING.value,
            now(),
            [TaskStatus.FAILED.value, TaskStatus.IN_PROGRESS.value],
        )
        await self.add_event(project_id, "project.retry_prepared", {})

    async def set_work_item_status(
        self,
        work_item_id: UUID,
        status: TaskStatus,
        output: str | None = None,
        error: str | None = None,
    ) -> None:
        row = await self._pool().fetchrow(
            """
            UPDATE work_items SET status=$2, output=COALESCE($3, output), error=$4,
              updated_at=$5 WHERE id=$1 RETURNING project_id, task_key
            """,
            work_item_id,
            status.value,
            output,
            error,
            now(),
        )
        if row:
            await self.add_event(
                row["project_id"],
                "task.status_changed",
                {"task_key": row["task_key"], "status": status.value, "error": error},
            )

    async def create_artifact(
        self,
        project_id: UUID,
        work_item_id: UUID,
        name: str,
        mime_type: str,
        content_hash: str,
        storage_reference: str,
        size: int,
    ) -> UUID:
        artifact_id = uuid4()
        await self._pool().execute(
            """
            INSERT INTO artifacts (id, project_id, work_item_id, name, mime_type,
              content_hash, storage_reference, size, status, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'reviewed',$9)
            """,
            artifact_id,
            project_id,
            work_item_id,
            name,
            mime_type,
            content_hash,
            storage_reference,
            size,
            now(),
        )
        await self.add_event(
            project_id,
            "artifact.created",
            {"artifact_id": str(artifact_id), "name": name},
        )
        return artifact_id

    async def list_artifacts(self, project_id: UUID) -> list[dict[str, Any]]:
        rows = await self._pool().fetch(
            "SELECT * FROM artifacts WHERE project_id=$1 ORDER BY created_at",
            project_id,
        )
        return [dict(row) for row in rows]

    async def get_artifact(self, artifact_id: UUID) -> dict[str, Any] | None:
        row = await self._pool().fetchrow(
            "SELECT * FROM artifacts WHERE id=$1", artifact_id
        )
        return dict(row) if row else None

    async def list_reviews(self, project_id: UUID) -> list[dict[str, Any]]:
        rows = await self._pool().fetch(
            "SELECT * FROM reviews WHERE project_id=$1 ORDER BY created_at", project_id
        )
        result = []
        for row in rows:
            item = dict(row)
            for field in ("evidence", "findings", "required_revisions"):
                item[field] = decode_json(item[field], [])
            result.append(item)
        return result

    async def save_review(
        self, project_id: UUID, work_item_id: UUID, review: dict[str, Any]
    ) -> None:
        await self._pool().execute(
            """
            INSERT INTO reviews (id, project_id, work_item_id, decision, summary,
              evidence, findings, required_revisions, created_at)
            VALUES ($1,$2,$3,$4,$5,$6::jsonb,$7::jsonb,$8::jsonb,$9)
            """,
            uuid4(),
            project_id,
            work_item_id,
            review["decision"],
            review["summary"],
            json.dumps(review.get("evidence", [])),
            json.dumps(review.get("findings", [])),
            json.dumps(review.get("required_revisions", [])),
            now(),
        )

    async def create_approval(
        self, project_id: UUID, work_item_id: UUID, action: str, risk: str
    ) -> UUID:
        approval_id = uuid4()
        await self._pool().execute(
            """
            INSERT INTO approval_requests (id, project_id, work_item_id, action, risk,
              status, created_at) VALUES ($1,$2,$3,$4,$5,'pending',$6)
            """,
            approval_id,
            project_id,
            work_item_id,
            action,
            risk,
            now(),
        )
        await self.add_event(
            project_id,
            "approval.requested",
            {"approval_id": str(approval_id), "action": action},
        )
        return approval_id

    async def decide_approval(
        self, approval_id: UUID, approved: bool, comment: str
    ) -> UUID:
        row = await self._pool().fetchrow(
            """
            UPDATE approval_requests SET status=$2, comment=$3, decided_at=$4
              WHERE id=$1 AND status='pending' RETURNING project_id, work_item_id
            """,
            approval_id,
            "approved" if approved else "rejected",
            comment,
            now(),
        )
        if not row:
            raise KeyError("approval request not found or already decided")
        if row["work_item_id"]:
            await self._pool().execute(
                "UPDATE work_items SET status=$2, updated_at=$3 WHERE id=$1",
                row["work_item_id"],
                TaskStatus.PENDING.value if approved else TaskStatus.FAILED.value,
                now(),
            )
        await self.add_event(
            row["project_id"],
            "approval.decided",
            {"approval_id": str(approval_id), "approved": approved},
        )
        return cast(UUID, row["project_id"])

    async def list_approvals(self, project_id: UUID) -> list[dict[str, Any]]:
        rows = await self._pool().fetch(
            "SELECT * FROM approval_requests WHERE project_id=$1 ORDER BY created_at",
            project_id,
        )
        return [dict(row) for row in rows]

    async def list_recoverable_projects(self) -> list[UUID]:
        rows = await self._pool().fetch(
            """
            SELECT id FROM projects WHERE status = ANY($1::text[])
            ORDER BY created_at
            """,
            [
                ProjectStatus.PLANNING.value,
                ProjectStatus.VALIDATING_PLAN.value,
                ProjectStatus.EXECUTING.value,
                ProjectStatus.REVIEWING.value,
                ProjectStatus.REPLANNING.value,
            ],
        )
        return [row["id"] for row in rows]

    async def approval_status(self, work_item_id: UUID) -> str | None:
        value = await self._pool().fetchval(
            """
            SELECT status FROM approval_requests WHERE work_item_id=$1
              ORDER BY created_at DESC LIMIT 1
            """,
            work_item_id,
        )
        return cast(str | None, value)

    async def add_event(
        self, project_id: UUID, event_type: str, payload: dict[str, Any] | None = None
    ) -> None:
        await self._pool().execute(
            """
            INSERT INTO project_events (id, project_id, event_type, payload, created_at)
            VALUES ($1,$2,$3,$4::jsonb,$5)
            """,
            uuid4(),
            project_id,
            event_type,
            json.dumps(payload or {}),
            now(),
        )

    async def list_events(
        self, project_id: UUID, after: datetime | None = None
    ) -> list[dict[str, Any]]:
        if after:
            rows = await self._pool().fetch(
                """
                SELECT * FROM project_events WHERE project_id=$1 AND created_at>$2
                ORDER BY created_at
                """,
                project_id,
                after,
            )
        else:
            rows = await self._pool().fetch(
                "SELECT * FROM project_events WHERE project_id=$1 ORDER BY created_at",
                project_id,
            )
        return [
            {**dict(row), "payload": decode_json(row["payload"], {})} for row in rows
        ]
