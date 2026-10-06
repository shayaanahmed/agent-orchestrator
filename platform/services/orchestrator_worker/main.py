from __future__ import annotations

import asyncio
from uuid import UUID

from temporalio import activity
from temporalio.client import Client
from temporalio.worker import Worker

from adapters.artifacts.local_store import LocalArtifactStore
from adapters.database.store import PostgresStore
from adapters.sandbox.client import SandboxClient
from adapters.workflows.project_workflow import ProjectWorkflow
from application.services.execution_service import ProjectExecutionService
from core.config import settings
from services.model_gateway.service import OllamaModelProvider


class ProjectActivities:
    def __init__(self, executor: ProjectExecutionService, store: PostgresStore) -> None:
        self.executor = executor
        self.store = store

    @activity.defn(name="run_project_until_blocked")
    async def run_project_until_blocked(self, project_id: str) -> str:
        activity.heartbeat("starting")
        parsed_project_id = UUID(project_id)
        try:
            await self.executor.run_project(parsed_project_id)
        except Exception:
            # The execution service records terminal failures on the project. Returning
            # that state prevents Temporal from repeatedly moving it back to "planning"
            # while retrying the same unavailable dependency.
            project = await self.store.get_project(parsed_project_id)
            if project and project.status.value == "failed":
                activity.heartbeat("failed")
                return "failed"
            raise
        project = await self.store.get_project(parsed_project_id)
        activity.heartbeat("finished")
        return project.status.value if project else "failed"


async def main() -> None:
    store = PostgresStore(settings.database_url)
    await store.connect()
    provider = OllamaModelProvider(
        settings.ollama_base_url,
        settings.ollama_api_token,
        settings.ollama_model_map,
        settings.model_timeout_seconds,
        settings.model_max_concurrency,
    )
    sandbox = SandboxClient(
        settings.sandbox_url, settings.sandbox_token, settings.sandbox_timeout_seconds
    )
    executor = ProjectExecutionService(
        store, LocalArtifactStore(settings.artifact_directory), provider, sandbox
    )
    client = await Client.connect(settings.temporal_address)
    activities = ProjectActivities(executor, store)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[ProjectWorkflow],
        activities=[activities.run_project_until_blocked],
    )
    try:
        await worker.run()
    finally:
        await provider.close()
        await store.close()


if __name__ == "__main__":
    asyncio.run(main())
