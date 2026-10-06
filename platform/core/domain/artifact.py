from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ArtifactType(StrEnum):
    """Types of artifacts that can be produced"""

    SOURCE_CODE = "source_code"
    TEST_REPORT = "test_report"
    DOCUMENTATION = "documentation"
    IMAGE = "image"
    DATA_FILE = "data_file"
    DEPLOYMENT_MANIFEST = "deployment_manifest"
    AUDIT_EXPORT = "audit_export"
    JSON_REPORT = "json_report"
    MARKDOWN_DOCUMENT = "markdown_document"
    PATCH_FILE = "patch_file"
    SOURCE_ARCHIVE = "source_archive"


class ArtifactStatus(StrEnum):
    """Status of an artifact"""

    DRAFT = "draft"
    FINAL = "final"
    REVIEWED = "reviewed"
    REVISION_REQUIRED = "revision_required"
    REJECTED = "rejected"


class Artifact(BaseModel):
    """A generated artifact from project execution"""

    id: UUID
    project_id: UUID
    work_item_id: UUID
    producer_agent_id: UUID
    name: str
    description: str | None = None
    type: ArtifactType
    mime_type: str  # e.g., 'text/plain', 'application/json'
    size: int  # bytes
    content_hash: str  # SHA256 hash of the content
    storage_reference: str  # Reference to where artifact is stored (e.g., MinIO key)
    status: ArtifactStatus = ArtifactStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: int = 1
    parent_artifacts: list[UUID] = Field(default_factory=list)
    review_result: dict[str, Any] | None = None  # Review metadata
