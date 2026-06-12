from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class GlobalCliSetupAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    SKIP = "skip"


class GlobalCliSetupTargetType(StrEnum):
    DIRECTORY = "directory"
    FILE = "file"
    USER_ENVIRONMENT_VARIABLE = "user_environment_variable"


class GlobalCliLayout(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    root_path: Path
    bin_directory_path: Path
    uv_tool_directory_path: Path
    readme_file_path: Path
    noncanonical_tool_bin_directory_paths: tuple[Path, ...] = ()


class GlobalCliSetupOperation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    action: GlobalCliSetupAction
    target_type: GlobalCliSetupTargetType
    target_name: str
    target_path: Path | None = None
    environment_variable_name: str | None = None
    current_value: str | None = None
    desired_value: str | None = None
    reason: str = ""


class GlobalCliSetupPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    layout: GlobalCliLayout
    operations: tuple[GlobalCliSetupOperation, ...]
