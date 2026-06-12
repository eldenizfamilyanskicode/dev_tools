from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict


class ApplicationType(StrEnum):
    PYTHON = "python"
    TYPESCRIPT = "ts"
    FULL = "full"


class ToolName(StrEnum):
    MYPY = "mypy"
    RUFF = "ruff"
    PYRIGHT = "pyright"
    PRETTIER = "prettier"
    ALL = "all"


class StrictnessLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProjectBootstrapRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    project_root_path: Path
    application_type: ApplicationType = ApplicationType.FULL
    tool_names: tuple[ToolName, ...] = (ToolName.ALL,)
    strictness_level: StrictnessLevel = StrictnessLevel.HIGH
    force: bool = False
    dry_run: bool = False


class TemplateRenderRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    template_directory_path: Path
    destination_directory_path: Path
    answers: dict[str, Any]
    force: bool = False


class TemplateRenderer(Protocol):
    def render_template(self, request: TemplateRenderRequest) -> None:
        raise NotImplementedError


class BootstrapFileAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    SKIP = "skip"


class BootstrapFileOperation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    relative_file_path: Path
    action: BootstrapFileAction
    content: str | None = None
    reason: str = ""
    target_file_path: Path | None = None
    display_path: str | None = None
    policy_id: str | None = None
    policy_revision: int | None = None
    merge_strategy: str = "whole_file"
    applied_paths: tuple[str, ...] = ()
    preserved_paths: tuple[str, ...] = ()
    conflict_paths: tuple[str, ...] = ()


class ProjectBootstrapPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    application_type: ApplicationType
    tool_names: tuple[ToolName, ...]
    strictness_level: StrictnessLevel
    operations: tuple[BootstrapFileOperation, ...]

    def iter_operations_for_action(
        self,
        action: BootstrapFileAction,
    ) -> tuple[BootstrapFileOperation, ...]:
        matching_operations: list[BootstrapFileOperation] = []

        for operation in self.operations:
            if operation.action == action:
                matching_operations.append(operation)

        return tuple(matching_operations)


class BootstrapAddon(Protocol):
    def add_operations(
        self,
        operations: list[BootstrapFileOperation],
        request: ProjectBootstrapRequest,
    ) -> None:
        raise NotImplementedError
