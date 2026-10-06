from __future__ import annotations

import asyncio
import hashlib
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID


@dataclass(frozen=True)
class StoredArtifact:
    storage_reference: str
    content_hash: str
    size: int


class LocalArtifactStore:
    """Volume-backed artifact store with traversal protection and hash verification."""

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, base: Path, relative: str) -> Path:
        path = (base / relative).resolve()
        if base != path and base not in path.parents:
            raise ValueError("invalid artifact path")
        return path

    def _path(self, project_id: UUID, work_item_id: UUID, filename: str) -> Path:
        base = (self.root / str(project_id) / "artifacts" / str(work_item_id)).resolve()
        return self._safe_path(base, filename)

    def workspace_path(self, project_id: UUID) -> Path:
        return (self.root / str(project_id) / "workspace").resolve()

    async def _atomic_write(self, path: Path, content: bytes) -> None:
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        await asyncio.to_thread(temporary.write_bytes, content)
        await asyncio.to_thread(os.replace, temporary, path)

    async def put(
        self, project_id: UUID, work_item_id: UUID, filename: str, content: bytes
    ) -> StoredArtifact:
        path = self._path(project_id, work_item_id, filename)
        await self._atomic_write(path, content)
        digest = hashlib.sha256(content).hexdigest()
        return StoredArtifact(
            storage_reference=str(path.relative_to(self.root)),
            content_hash=digest,
            size=len(content),
        )

    async def materialize(
        self, project_id: UUID, filename: str, content: bytes
    ) -> None:
        workspace = self.workspace_path(project_id)
        path = self._safe_path(workspace, filename)
        await self._atomic_write(path, content)

    async def workspace_snapshot(
        self, project_id: UUID, max_files: int = 200, max_bytes: int = 120_000
    ) -> dict[str, str]:
        workspace = self.workspace_path(project_id)
        if not workspace.exists():
            return {}

        def read() -> dict[str, str]:
            result: dict[str, str] = {}
            used = 0
            for path in sorted(item for item in workspace.rglob("*") if item.is_file()):
                if len(result) >= max_files or used >= max_bytes:
                    break
                data = path.read_bytes()
                remaining = max_bytes - used
                text = data[:remaining].decode("utf-8", errors="replace")
                result[str(path.relative_to(workspace))] = text
                used += len(text.encode("utf-8"))
            return result

        return await asyncio.to_thread(read)

    async def bundle(
        self, project_id: UUID, work_item_id: UUID
    ) -> StoredArtifact | None:
        workspace = self.workspace_path(project_id)
        if not workspace.exists() or not any(workspace.rglob("*")):
            return None
        destination = self._path(project_id, work_item_id, "project-workspace.zip")

        def create_zip() -> bytes:
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(f".{destination.name}.tmp")
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(
                    item for item in workspace.rglob("*") if item.is_file()
                ):
                    archive.write(path, path.relative_to(workspace))
            os.replace(temporary, destination)
            return destination.read_bytes()

        content = await asyncio.to_thread(create_zip)
        return StoredArtifact(
            storage_reference=str(destination.relative_to(self.root)),
            content_hash=hashlib.sha256(content).hexdigest(),
            size=len(content),
        )

    async def get(self, reference: str, expected_hash: str) -> bytes:
        path = (self.root / reference).resolve()
        if self.root not in path.parents:
            raise ValueError("invalid artifact reference")
        content = await asyncio.to_thread(path.read_bytes)
        digest = hashlib.sha256(content).hexdigest()
        if digest != expected_hash:
            raise ValueError("artifact hash mismatch")
        return content
