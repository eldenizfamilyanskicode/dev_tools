from __future__ import annotations

import tomllib
from pathlib import Path

from dev_tools.project_bootstrap.bootstrap_file_writer import BootstrapFileWriter
from dev_tools.project_bootstrap.constants import (
    POLICY_PYPROJECT_DEFAULTS_ID,
    POLICY_PYPROJECT_DEFAULTS_REVISION,
)
from dev_tools.project_bootstrap.models import (
    BootstrapFileAction,
    BootstrapFileOperation,
)
from dev_tools.project_bootstrap.toml_section_merge_service import (
    TomlMergeResult,
    TomlSectionMergeService,
)


class PyprojectOperationBuilder:
    def __init__(
        self,
        toml_section_merge_service: TomlSectionMergeService,
        bootstrap_file_writer: BootstrapFileWriter,
    ) -> None:
        self.toml_section_merge_service = toml_section_merge_service
        self.bootstrap_file_writer = bootstrap_file_writer

    def build_operation(
        self,
        project_root_path: Path,
        content: str,
        force: bool,
    ) -> BootstrapFileOperation:
        relative_file_path: Path = Path("pyproject.toml")
        target_file_path: Path = project_root_path / relative_file_path

        if not target_file_path.exists() or force:
            return self.build_text_operation(
                project_root_path=project_root_path,
                relative_file_path=relative_file_path,
                content=content,
                force=force,
                applied_paths=("$",),
            )

        current_content: str = target_file_path.read_text(encoding="utf-8")

        try:
            merge_result: TomlMergeResult = (
                self.toml_section_merge_service.build_merge_result(
                    current_content=current_content,
                    managed_content=content,
                )
            )
        except tomllib.TOMLDecodeError:
            return BootstrapFileOperation(
                relative_file_path=relative_file_path,
                action=BootstrapFileAction.CONFLICT,
                content=None,
                reason="existing TOML is not safe to merge",
                policy_id=POLICY_PYPROJECT_DEFAULTS_ID,
                policy_revision=POLICY_PYPROJECT_DEFAULTS_REVISION,
                merge_strategy="toml_missing_sections",
                conflict_paths=("$",),
            )

        operation_content: str = merge_result.content
        if not merge_result.applied_paths:
            operation_content = current_content

        return self.build_text_operation(
            project_root_path=project_root_path,
            relative_file_path=relative_file_path,
            content=operation_content,
            force=force,
            applied_paths=merge_result.applied_paths,
            preserved_paths=merge_result.preserved_paths,
            conflict_paths=merge_result.conflict_paths,
            reason=self.build_toml_merge_reason(merge_result),
        )

    def build_text_operation(
        self,
        project_root_path: Path,
        relative_file_path: Path,
        content: str,
        force: bool,
        applied_paths: tuple[str, ...] = (),
        preserved_paths: tuple[str, ...] = (),
        conflict_paths: tuple[str, ...] = (),
        reason: str = "",
    ) -> BootstrapFileOperation:
        return self.bootstrap_file_writer.build_operation(
            project_root_path=project_root_path,
            relative_file_path=relative_file_path,
            content=content,
            force=force,
            create_only=False,
            policy_id=POLICY_PYPROJECT_DEFAULTS_ID,
            policy_revision=POLICY_PYPROJECT_DEFAULTS_REVISION,
            merge_strategy="toml_missing_sections",
            applied_paths=applied_paths,
            preserved_paths=preserved_paths,
            conflict_paths=conflict_paths,
            reason=reason,
        )

    def build_toml_merge_reason(self, merge_result: TomlMergeResult) -> str:
        reason_parts: list[str] = []

        if merge_result.applied_paths:
            reason_parts.append(
                "missing TOML entries added: "
                f"{self.format_paths(merge_result.applied_paths)}"
            )

        if merge_result.preserved_paths:
            reason_parts.append(
                "preserved existing TOML entries: "
                f"{self.format_paths(merge_result.preserved_paths)}"
            )

        if merge_result.conflict_paths:
            reason_parts.append(
                "conflicting TOML sections: "
                f"{self.format_paths(merge_result.conflict_paths)}"
            )

        return "; ".join(reason_parts)

    def format_paths(self, paths: tuple[str, ...]) -> str:
        formatted_paths: list[str] = []

        for path in paths:
            formatted_paths.append(path)

        return ", ".join(formatted_paths)
