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
            missing_section_names: tuple[str, ...] = (
                self.toml_section_merge_service.collect_missing_section_names(
                    current_content=current_content,
                    managed_content=content,
                )
            )
            merged_content: str = (
                self.toml_section_merge_service.merge_missing_sections(
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

        return self.build_text_operation(
            project_root_path=project_root_path,
            relative_file_path=relative_file_path,
            content=merged_content,
            force=force,
            applied_paths=missing_section_names,
            reason=self.build_toml_merge_reason(missing_section_names),
        )

    def build_text_operation(
        self,
        project_root_path: Path,
        relative_file_path: Path,
        content: str,
        force: bool,
        applied_paths: tuple[str, ...] = (),
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
            conflict_paths=conflict_paths,
            reason=reason,
        )

    def build_toml_merge_reason(self, missing_section_names: tuple[str, ...]) -> str:
        if not missing_section_names:
            return ""

        formatted_section_names: list[str] = []
        for section_name in missing_section_names:
            formatted_section_names.append(section_name)

        return "missing sections added: " + ", ".join(formatted_section_names)
