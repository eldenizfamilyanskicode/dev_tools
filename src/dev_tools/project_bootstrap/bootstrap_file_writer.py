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
        target_file_path: Path | None = None,
        display_path: str | None = None,
        policy_id: str | None = None,
        policy_revision: int | None = None,
        merge_strategy: str = "whole_file",
        applied_paths: tuple[str, ...] = (),
        preserved_paths: tuple[str, ...] = (),
        conflict_paths: tuple[str, ...] = (),
        reason: str = "",
    ) -> BootstrapFileOperation:
        resolved_target_file_path: Path = project_root_path / relative_file_path

        if target_file_path is not None:
            if not target_file_path.is_absolute():
                raise ValueError("Bootstrap target file path must be absolute.")

            resolved_target_file_path = target_file_path

        if conflict_paths and resolved_target_file_path.exists() and not force:
            operation_reason: str = reason
            if operation_reason == "":
                operation_reason = "conflicting existing values require --force"

            return BootstrapFileOperation(
                relative_file_path=relative_file_path,
                action=BootstrapFileAction.CONFLICT,
                content=None,
                reason=operation_reason,
                target_file_path=target_file_path,
                display_path=display_path,
                policy_id=policy_id,
                policy_revision=policy_revision,
                merge_strategy=merge_strategy,
                preserved_paths=preserved_paths,
                conflict_paths=conflict_paths,
            )

        if not resolved_target_file_path.exists():
            return BootstrapFileOperation(
                relative_file_path=relative_file_path,
                action=BootstrapFileAction.CREATE,
                content=content,
                target_file_path=target_file_path,
                display_path=display_path,
                policy_id=policy_id,
                policy_revision=policy_revision,
                merge_strategy=merge_strategy,
                applied_paths=applied_paths,
                preserved_paths=preserved_paths,
                conflict_paths=conflict_paths,
                reason=reason,
            )

        current_content: str = resolved_target_file_path.read_text(encoding="utf-8")
        if current_content == content:
            already_satisfied_reason: str = reason
            if already_satisfied_reason == "":
                already_satisfied_reason = "already up to date"

            return BootstrapFileOperation(
                relative_file_path=relative_file_path,
                action=BootstrapFileAction.SKIP,
                content=content,
                reason=already_satisfied_reason,
                target_file_path=target_file_path,
                display_path=display_path,
                policy_id=policy_id,
                policy_revision=policy_revision,
                merge_strategy=merge_strategy,
                applied_paths=applied_paths,
                preserved_paths=preserved_paths,
                conflict_paths=conflict_paths,
            )

        if create_only and not force:
            return BootstrapFileOperation(
                relative_file_path=relative_file_path,
                action=BootstrapFileAction.SKIP,
                content=None,
                reason="exists",
                target_file_path=target_file_path,
                display_path=display_path,
                policy_id=policy_id,
                policy_revision=policy_revision,
                merge_strategy=merge_strategy,
                applied_paths=applied_paths,
                preserved_paths=preserved_paths,
                conflict_paths=conflict_paths,
            )

        return BootstrapFileOperation(
            relative_file_path=relative_file_path,
            action=BootstrapFileAction.UPDATE,
            content=content,
            target_file_path=target_file_path,
            display_path=display_path,
            policy_id=policy_id,
            policy_revision=policy_revision,
            merge_strategy=merge_strategy,
            applied_paths=applied_paths,
            preserved_paths=preserved_paths,
            conflict_paths=conflict_paths,
            reason=reason,
        )

    def apply_plan(self, project_root_path: Path, plan: ProjectBootstrapPlan) -> None:
        for operation in plan.operations:
            if operation.action in (
                BootstrapFileAction.SKIP,
                BootstrapFileAction.CONFLICT,
            ):
                continue

            if operation.content is None:
                raise ValueError(
                    f"Cannot write bootstrap operation without content: "
                    f"{operation.relative_file_path}"
                )

            target_file_path: Path = project_root_path / operation.relative_file_path
            if operation.target_file_path is not None:
                target_file_path = operation.target_file_path

            self.file_system.write_text(
                file_path=target_file_path,
                content=operation.content,
            )
