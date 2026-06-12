from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from base_typed_id import BaseTypedId
from pydantic import BaseModel, ConfigDict

from dev_tools.project_bootstrap.models import (
    ApplicationType,
    StrictnessLevel,
    ToolName,
)


class ProjectPolicyProjectId(BaseTypedId):
    pass


class PolicyApplicationStatus(StrEnum):
    APPLIED = "applied"
    APPLIED_WITH_SKIPS = "applied_with_skips"
    ALREADY_SATISFIED = "already_satisfied"
    SKIPPED_EXISTING = "skipped_existing"
    CONFLICT = "conflict"


class RegisteredProjectStatus(StrEnum):
    ACTIVE = "active"
    MISSING = "missing"
    INVALID_MANIFEST = "invalid_manifest"


class ProjectPolicyInitSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    application_type: ApplicationType
    tool_names: tuple[ToolName, ...]
    strictness_level: StrictnessLevel


class ProjectPolicyRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_id: str
    policy_revision: int
    status: PolicyApplicationStatus
    merge_strategy: str
    target_files: tuple[str, ...]
    reason: str = ""
    applied_paths: tuple[str, ...] = ()
    preserved_paths: tuple[str, ...] = ()
    conflict_paths: tuple[str, ...] = ()
    content_hash: str | None = None
    applied_at: str | None = None


class ProjectPolicyManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_version: int
    project_id: ProjectPolicyProjectId
    project_root_path: Path
    initialized_at: str
    updated_at: str
    dev_tools_version_at_init: str
    init_settings: ProjectPolicyInitSettings
    policies: tuple[ProjectPolicyRecord, ...]


class RegisteredProject(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: ProjectPolicyProjectId
    project_root_path: Path
    manifest_file_path: Path
    last_seen_at: str
    status: RegisteredProjectStatus


class ProjectPolicyIndex(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    index_version: int
    projects: tuple[RegisteredProject, ...]
