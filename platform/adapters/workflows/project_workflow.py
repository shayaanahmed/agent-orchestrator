from __future__ import annotations

from datetime import timedelta
from typing import cast

from temporalio import workflow
from temporalio.common import RetryPolicy


@workflow.defn
class ProjectWorkflow:
    def __init__(self) -> None:
        self.resume_requested = False
        self.cancel_requested = False
        self.paused = False

    @workflow.signal
    async def pause(self) -> None:
        self.paused = True

    @workflow.signal
    async def resume(self) -> None:
        self.paused = False
        self.resume_requested = True

    @workflow.signal
    async def cancel(self) -> None:
        self.cancel_requested = True
        self.resume_requested = True

    @workflow.run
    async def run(self, project_id: str) -> str:
        while not self.cancel_requested:
            if self.paused:
                await workflow.wait_condition(
                    lambda: not self.paused or self.cancel_requested
                )
                if self.cancel_requested:
                    break
            state = cast(
                str,
                await workflow.execute_activity(
                    "run_project_until_blocked",
                    project_id,
                    start_to_close_timeout=timedelta(hours=24),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=5),
                        maximum_interval=timedelta(minutes=2),
                        maximum_attempts=5,
                    ),
                ),
            )
            if state in {"completed", "failed", "cancelled"}:
                return state
            if state == "paused":
                self.paused = True
            self.resume_requested = False
            await workflow.wait_condition(
                lambda: self.resume_requested or self.cancel_requested
            )
        return "cancelled"
