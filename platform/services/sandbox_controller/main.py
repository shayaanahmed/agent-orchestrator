from __future__ import annotations

import asyncio
import os
import signal
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

ARTIFACT_ROOT = Path(os.getenv("ARTIFACT_DIRECTORY", "/data/artifacts")).resolve()
TOKEN = os.getenv("SANDBOX_TOKEN", "sandbox-change-me")
MAX_OUTPUT = int(os.getenv("SANDBOX_MAX_OUTPUT_BYTES", "200000"))
ALLOWED_COMMANDS = {
    "python": {"-m", "-c"},
    "python3": {"-m", "-c"},
    "pytest": set(),
    "node": {"--check", "--test"},
    "npm": {"test", "run"},
}


class ExecutionRequest(BaseModel):
    project_id: UUID
    command: list[str] = Field(min_length=1, max_length=30)
    timeout_seconds: int = Field(default=120, ge=1, le=600)


app = FastAPI(title="Sandbox Controller", version="1.0.0")


def authorize(value: str | None) -> None:
    if value != f"Bearer {TOKEN}":
        raise HTTPException(status_code=401, detail="Invalid sandbox token")


def validate_command(command: list[str]) -> None:
    executable = Path(command[0]).name
    if executable not in ALLOWED_COMMANDS or command[0] != executable:
        raise HTTPException(status_code=400, detail="Executable is not allowed")
    if executable in {"python", "python3"} and len(command) > 1:
        if command[1] not in ALLOWED_COMMANDS[executable]:
            raise HTTPException(status_code=400, detail="Python must use -m or -c")
    if executable == "npm" and (len(command) < 2 or command[1] not in {"test", "run"}):
        raise HTTPException(status_code=400, detail="Only npm test/run is allowed")
    forbidden = {"..", "/proc", "/sys", "/etc", "/var/run", "--require"}
    if any(any(marker in argument for marker in forbidden) for argument in command[1:]):
        raise HTTPException(
            status_code=400, detail="Command contains a forbidden path or option"
        )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/execute")
async def execute(
    payload: ExecutionRequest, authorization: str | None = Header(default=None)
) -> dict[str, object]:
    authorize(authorization)
    validate_command(payload.command)
    workspace = (ARTIFACT_ROOT / str(payload.project_id) / "workspace").resolve()
    expected_parent = (ARTIFACT_ROOT / str(payload.project_id)).resolve()
    if expected_parent not in workspace.parents:
        raise HTTPException(status_code=400, detail="Invalid project workspace")
    workspace.mkdir(parents=True, exist_ok=True)
    environment = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/tmp/sandbox-home",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "CI": "true",
        "NO_COLOR": "1",
    }
    process = await asyncio.create_subprocess_exec(
        *payload.command,
        cwd=workspace,
        env=environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=payload.timeout_seconds
        )
    except TimeoutError:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = await process.communicate()
    return {
        "command": payload.command,
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "stdout": stdout[:MAX_OUTPUT].decode("utf-8", errors="replace"),
        "stderr": stderr[:MAX_OUTPUT].decode("utf-8", errors="replace"),
        "truncated": len(stdout) > MAX_OUTPUT or len(stderr) > MAX_OUTPUT,
    }
