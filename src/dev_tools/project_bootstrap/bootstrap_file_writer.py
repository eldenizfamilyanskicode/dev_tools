from __future__ import annotations

from pathlib import Path

from dev_tools.project_bootstrap.models import (
    BootstrapFileAction,
    BootstrapFileOperation,
    ProjectBootstrapPlan,
)
from dev_tools.shared.file_system import FileSystem


class BootstrapFileWriter:
    def __init__(self, file_system: FileSystem) -> None:
        self.file_system = file_system

    def build_operation(
        self,
        project_root_path: Path,
        relative_file_path: Path,
        content: str,
        force: bool,
        create_only: bool = False,
    ) -> BootstrapFileOperation:
        target_file_path: Path = project_root_path / relative_file_path

        if not target_file_path.exists():
            return BootstrapFileOperation(
                relative_file_path=relative_file_path,
                action=BootstrapFileAction.CREATE,
                content=content,
            )

        current_content: str = target_file_path.read_text(encoding="utf-8")
        if current_content == content:
            return BootstrapFileOperation(
                relative_file_path=relative_file_path,
                action=BootstrapFileAction.SKIP,
                content=None,
                reason="already up to date",
            )

        if create_only and not force:
            return BootstrapFileOperation(
                relative_file_path=relative_file_path,
                action=BootstrapFileAction.SKIP,
                content=None,
                reason="exists",
            )

        return BootstrapFileOperation(
            relative_file_path=relative_file_path,
            action=BootstrapFileAction.UPDATE,
            content=content,
        )

    def apply_plan(self, project_root_path: Path, plan: ProjectBootstrapPlan) -> None:
        for operation in plan.operations:
            if operation.action == BootstrapFileAction.SKIP:
                continue

            if operation.content is None:
                raise ValueError(
                    f"Cannot write bootstrap operation without content: "
                    f"{operation.relative_file_path}"
                )

            target_file_path: Path = project_root_path / operation.relative_file_path
            self.file_system.write_text(
                file_path=target_file_path,
                content=operation.content,
            )

