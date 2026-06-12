from __future__ import annotations

from pathlib import Path

from dev_tools.project_bootstrap.bootstrap_file_writer import BootstrapFileWriter
from dev_tools.project_bootstrap.constants import (
    VSCODE_FILES_EXCLUDE_SETTING_NAME,
    VSCODE_GLOBAL_FILES_EXCLUDE_PATTERNS,
    VSCODE_SETTINGS_FILE_NAME,
    VSCODE_USER_SETTINGS_DISPLAY_PATH,
)
from dev_tools.project_bootstrap.json_merge_service import (
    JsonMergeService,
    JsonObject,
)
from dev_tools.project_bootstrap.models import (
    BootstrapFileAction,
    BootstrapFileOperation,
    ProjectBootstrapRequest,
)
from dev_tools.project_bootstrap.vscode_user_settings_path_resolver import (
    VsCodeUserSettingsPathResolver,
)


class VsCodeUserFilesExcludeAddon:
    def __init__(
        self,
        json_merge_service: JsonMergeService,
        bootstrap_file_writer: BootstrapFileWriter,
        vscode_user_settings_path_resolver: VsCodeUserSettingsPathResolver,
    ) -> None:
        self.json_merge_service = json_merge_service
        self.bootstrap_file_writer = bootstrap_file_writer
        self.vscode_user_settings_path_resolver = vscode_user_settings_path_resolver

    def add_operations(
        self,
        operations: list[BootstrapFileOperation],
        request: ProjectBootstrapRequest,
    ) -> None:
        settings_file_path: Path
        settings_file_path = (
            self.vscode_user_settings_path_resolver.resolve_settings_file_path()
        )
        current_content: str = ""

        if settings_file_path.exists():
            current_content = settings_file_path.read_text(encoding="utf-8")

        try:
            content: str = self.json_merge_service.merge_json_content(
                current_content=current_content,
                managed_data=self.build_managed_settings_data(),
            )
        except ValueError:
            operations.append(
                BootstrapFileOperation(
                    relative_file_path=Path(VSCODE_SETTINGS_FILE_NAME),
                    action=BootstrapFileAction.SKIP,
                    content=None,
                    reason="existing JSON is not safe to merge",
                    target_file_path=settings_file_path,
                    display_path=VSCODE_USER_SETTINGS_DISPLAY_PATH,
                )
            )
            return

        operation: BootstrapFileOperation = self.bootstrap_file_writer.build_operation(
            project_root_path=request.project_root_path,
            relative_file_path=Path(VSCODE_SETTINGS_FILE_NAME),
            content=content,
            force=False,
            create_only=False,
            target_file_path=settings_file_path,
            display_path=VSCODE_USER_SETTINGS_DISPLAY_PATH,
        )
        operations.append(operation)

    def build_managed_settings_data(self) -> JsonObject:
        files_exclude_settings: JsonObject = {}

        for file_pattern in VSCODE_GLOBAL_FILES_EXCLUDE_PATTERNS:
            files_exclude_settings[file_pattern] = True

        return {
            VSCODE_FILES_EXCLUDE_SETTING_NAME: files_exclude_settings,
        }
