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
            )

        current_content: str = target_file_path.read_text(encoding="utf-8")

        try:
            merged_content: str = (
                self.toml_section_merge_service.merge_missing_sections(
                    current_content=current_content,
                    managed_content=content,
                )
            )
        except tomllib.TOMLDecodeError:
            return BootstrapFileOperation(
                relative_file_path=relative_file_path,
                action=BootstrapFileAction.SKIP,
                content=None,
                reason="existing TOML is not safe to merge",
                policy_id=POLICY_PYPROJECT_DEFAULTS_ID,
                policy_revision=POLICY_PYPROJECT_DEFAULTS_REVISION,
                merge_strategy="toml_missing_sections",
            )

        return self.build_text_operation(
            project_root_path=project_root_path,
            relative_file_path=relative_file_path,
            content=merged_content,
            force=force,
        )

    def build_text_operation(
        self,
        project_root_path: Path,
        relative_file_path: Path,
        content: str,
        force: bool,
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
        )
