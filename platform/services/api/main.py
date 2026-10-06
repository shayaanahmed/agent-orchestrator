from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from adapters.artifacts.local_store import LocalArtifactStore
from adapters.database.store import PostgresStore
from adapters.sandbox.client import SandboxClient
from application.services.execution_service import ProjectExecutionService
from core.config import settings
from core.domain.agent import Capability
from core.domain.project import Project, ProjectGoal, ProjectStatus
from core.planning.catalog import ROLE_CAPABILITIES
from services.model_gateway.service import OllamaModelProvider


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    goal: str = Field(min_length=10, max_length=20_000)
    description: str | None = Field(default=None, max_length=20_000)
    constraints: list[str] = Field(default_factory=list, max_length=100)
    owner_id: UUID | None = None
    auto_start: bool | None = None


class ApprovalDecisionRequest(BaseModel):
    comment: str = Field(default="", max_length=5000)


def serialize(value: Any) -> Any:
    if isinstance(value, (UUID, datetime)):
        return str(value)
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize(item) for item in value]
    return value


def _consume_task(task: asyncio.Task[None]) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception:
        # The execution service persists the error on the project.
        pass


async def start_run(app: FastAPI, project_id: UUID) -> None:
    if settings.use_temporal:
        from temporalio.exceptions import WorkflowAlreadyStartedError

        from adapters.workflows.project_workflow import ProjectWorkflow

        try:
            await app.state.temporal.start_workflow(
                ProjectWorkflow.run,
                str(project_id),
                id=f"project-{project_id}",
                task_queue=settings.temporal_task_queue,
            )
        except WorkflowAlreadyStartedError:
            handle = app.state.temporal.get_workflow_handle(f"project-{project_id}")
            await handle.signal(ProjectWorkflow.resume)
        return
    running: dict[UUID, asyncio.Task[None]] = app.state.running
    existing = running.get(project_id)
    if existing and not existing.done():
        return
    task = asyncio.create_task(app.state.executor.run_project(project_id))
    running[project_id] = task
    task.add_done_callback(_consume_task)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    store = PostgresStore(settings.database_url)
    await store.connect()
    provider = OllamaModelProvider(
        settings.ollama_base_url,
        settings.ollama_api_token,
        settings.ollama_model_map,
        settings.model_timeout_seconds,
        settings.model_max_concurrency,
    )
    artifacts = LocalArtifactStore(settings.artifact_directory)
    sandbox = SandboxClient(
        settings.sandbox_url, settings.sandbox_token, settings.sandbox_timeout_seconds
    )
    app.state.store = store
    app.state.provider = provider
    app.state.artifacts = artifacts
    app.state.sandbox = sandbox
    app.state.executor = ProjectExecutionService(store, artifacts, provider, sandbox)
    app.state.running = {}
    app.state.temporal = None
    if settings.use_temporal:
        from temporalio.client import Client

        app.state.temporal = await Client.connect(settings.temporal_address)
    else:
        for project_id in await store.list_recoverable_projects():
            await start_run(app, project_id)
    try:
        yield
    finally:
        for task in app.state.running.values():
            if not task.done():
                task.cancel()
        await provider.close()
        await store.close()


app = FastAPI(
    title="AI Project Execution Platform",
    version="1.0.0",
    description="Durable, governed execution of projects by dynamically assembled AI teams",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
try:
    from prometheus_client import make_asgi_app

    app.mount("/metrics", make_asgi_app())
except ImportError:
    pass


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": app.title, "docs": "/docs", "health": "/system/health"}


@app.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: CreateProjectRequest, request: Request
) -> dict[str, Any]:
    project = Project(
        id=uuid4(),
        name=payload.name,
        description=payload.description,
        goal=ProjectGoal(text=payload.goal),
        owner_id=payload.owner_id or uuid4(),
        constraints=payload.constraints,
    )
    await request.app.state.store.create_project(project)
    should_start = (
        settings.auto_start_projects
        if payload.auto_start is None
        else payload.auto_start
    )
    if should_start:
        await start_run(request.app, project.id)
    return {"project": serialize(project.model_dump()), "started": should_start}


@app.get("/projects")
async def list_projects(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    projects = await request.app.state.store.list_projects(limit, offset)
    return {"items": [serialize(item.model_dump()) for item in projects]}


async def require_project(request: Request, project_id: UUID) -> Project:
    project = await request.app.state.store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return cast(Project, project)


@app.get("/projects/{project_id}")
async def get_project(project_id: UUID, request: Request) -> dict[str, Any]:
    project = await require_project(request, project_id)
    return {
        "project": serialize(project.model_dump()),
        "tasks": serialize(await request.app.state.store.list_work_items(project_id)),
        "artifacts": serialize(
            await request.app.state.store.list_artifacts(project_id)
        ),
        "reviews": serialize(await request.app.state.store.list_reviews(project_id)),
        "approvals": serialize(
            await request.app.state.store.list_approvals(project_id)
        ),
    }


@app.get("/artifacts/{artifact_id}/download")
async def download_artifact(artifact_id: UUID, request: Request) -> Response:
    artifact = await request.app.state.store.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    try:
        content = await request.app.state.artifacts.get(
            artifact["storage_reference"], artifact["content_hash"]
        )
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    safe_name = str(artifact["name"]).replace('"', "").split("/")[-1]
    return Response(
        content,
        media_type=artifact["mime_type"],
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@app.post("/projects/{project_id}/start", status_code=status.HTTP_202_ACCEPTED)
async def start_project(project_id: UUID, request: Request) -> dict[str, str]:
    project = await require_project(request, project_id)
    if project.status in {ProjectStatus.COMPLETED, ProjectStatus.CANCELLED}:
        raise HTTPException(
            status_code=409, detail=f"Project is {project.status.value}"
        )
    await start_run(request.app, project_id)
    return {"project_id": str(project_id), "status": "accepted"}


@app.post("/projects/{project_id}/pause")
async def pause_project(project_id: UUID, request: Request) -> dict[str, str]:
    await require_project(request, project_id)
    if settings.use_temporal:
        from adapters.workflows.project_workflow import ProjectWorkflow

        handle = request.app.state.temporal.get_workflow_handle(f"project-{project_id}")
        await handle.signal(ProjectWorkflow.pause)
    else:
        running = request.app.state.running.get(project_id)
        if running and not running.done():
            running.cancel()
    await request.app.state.store.set_project_status(project_id, ProjectStatus.PAUSED)
    return {"status": "paused"}


@app.post("/projects/{project_id}/resume", status_code=status.HTTP_202_ACCEPTED)
async def resume_project(project_id: UUID, request: Request) -> dict[str, str]:
    await require_project(request, project_id)
    await start_run(request.app, project_id)
    return {"status": "accepted"}


@app.post("/projects/{project_id}/cancel")
async def cancel_project(project_id: UUID, request: Request) -> dict[str, str]:
    await require_project(request, project_id)
    if settings.use_temporal:
        from adapters.workflows.project_workflow import ProjectWorkflow

        handle = request.app.state.temporal.get_workflow_handle(f"project-{project_id}")
        await handle.signal(ProjectWorkflow.cancel)
    else:
        running = request.app.state.running.get(project_id)
        if running and not running.done():
            running.cancel()
    await request.app.state.store.set_project_status(
        project_id, ProjectStatus.CANCELLED
    )
    return {"status": "cancelled"}


@app.post("/approvals/{approval_id}/approve", status_code=status.HTTP_202_ACCEPTED)
async def approve(
    approval_id: UUID, payload: ApprovalDecisionRequest, request: Request
) -> dict[str, str]:
    try:
        project_id = await request.app.state.store.decide_approval(
            approval_id, True, payload.comment
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await start_run(request.app, project_id)
    return {"status": "approved", "project_id": str(project_id)}


@app.post("/approvals/{approval_id}/reject")
async def reject(
    approval_id: UUID, payload: ApprovalDecisionRequest, request: Request
) -> dict[str, str]:
    try:
        project_id = await request.app.state.store.decide_approval(
            approval_id, False, payload.comment
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await start_run(request.app, project_id)
    return {"status": "rejected", "project_id": str(project_id)}


@app.get("/projects/{project_id}/events")
async def project_events(project_id: UUID, request: Request) -> dict[str, Any]:
    await require_project(request, project_id)
    return {"items": serialize(await request.app.state.store.list_events(project_id))}


@app.get("/projects/{project_id}/events/stream")
async def stream_project_events(
    project_id: UUID, request: Request
) -> StreamingResponse:
    await require_project(request, project_id)

    async def stream() -> AsyncIterator[str]:
        cursor = datetime.fromtimestamp(0, tz=UTC)
        while not await request.is_disconnected():
            events = await request.app.state.store.list_events(project_id, cursor)
            for event in events:
                cursor = max(cursor, event["created_at"])
                yield f"data: {json.dumps(serialize(event))}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/capabilities")
async def list_capabilities() -> dict[str, list[str]]:
    return {"capabilities": [item.value for item in Capability]}


@app.get("/role-templates")
async def list_role_templates() -> dict[str, Any]:
    return {
        "roles": [
            {
                "role": role.value,
                "capabilities": sorted(capability.value for capability in capabilities),
            }
            for role, capabilities in ROLE_CAPABILITIES.items()
        ]
    }


@app.get("/models")
async def list_models(request: Request) -> dict[str, Any]:
    results = []
    for logical_name in settings.ollama_model_map:
        results.append(await request.app.state.provider.get_model_info(logical_name))
    return {"models": results}


@app.get("/system/health")
async def system_health(request: Request) -> dict[str, Any]:
    database_ok = False
    if request.app.state.store.pool:
        database_ok = bool(await request.app.state.store.pool.fetchval("SELECT 1"))
    ollama_ok = await request.app.state.provider.health_check()
    sandbox_ok = await request.app.state.sandbox.health_check()
    healthy = database_ok and ollama_ok and sandbox_ok
    return {
        "status": "healthy" if healthy else "degraded",
        "database": database_ok,
        "ollama": ollama_ok,
        "sandbox": sandbox_ok,
    }


@app.get("/system/readiness")
async def readiness(request: Request) -> dict[str, bool]:
    database_ok = bool(
        request.app.state.store.pool
        and await request.app.state.store.pool.fetchval("SELECT 1")
    )
    if not database_ok:
        raise HTTPException(status_code=503, detail="Database is unavailable")
    return {"ready": True}
