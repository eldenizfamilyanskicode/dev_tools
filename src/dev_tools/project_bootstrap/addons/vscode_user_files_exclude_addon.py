from __future__ import annotations

from pathlib import Path

from dev_tools.project_bootstrap.bootstrap_file_writer import BootstrapFileWriter
from dev_tools.project_bootstrap.constants import (
    POLICY_VSCODE_USER_FILES_EXCLUDE_ID,
    POLICY_VSCODE_USER_FILES_EXCLUDE_REVISION,
    VSCODE_FILES_EXCLUDE_SETTING_NAME,
    VSCODE_GLOBAL_FILES_EXCLUDE_PATTERNS,
    VSCODE_SETTINGS_FILE_NAME,
    VSCODE_USER_SETTINGS_DISPLAY_PATH,
)
from dev_tools.project_bootstrap.json_merge_service import (
    JsonMergeResult,
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
            merge_result: JsonMergeResult = self.json_merge_service.build_merge_result(
                current_content=current_content,
                managed_data=self.build_managed_settings_data(),
                overwrite_existing_values=request.force,
            )
        except ValueError:
            if settings_file_path.exists() and not request.force:
                operations.append(
                    BootstrapFileOperation(
                        relative_file_path=Path(VSCODE_SETTINGS_FILE_NAME),
                        action=BootstrapFileAction.CONFLICT,
                        content=None,
                        reason="existing JSON is not safe to merge",
                        target_file_path=settings_file_path,
                        display_path=VSCODE_USER_SETTINGS_DISPLAY_PATH,
                        policy_id=POLICY_VSCODE_USER_FILES_EXCLUDE_ID,
                        policy_revision=POLICY_VSCODE_USER_FILES_EXCLUDE_REVISION,
                        merge_strategy="json_merge",
                        conflict_paths=("$",),
                    )
                )
                return

            merge_result = JsonMergeResult(
                content=self.json_merge_service.dump_json(
                    self.build_managed_settings_data()
                ),
                applied_paths=("$",),
                preserved_paths=(),
                conflict_paths=(),
            )

        operation: BootstrapFileOperation = self.bootstrap_file_writer.build_operation(
            project_root_path=request.project_root_path,
            relative_file_path=Path(VSCODE_SETTINGS_FILE_NAME),
            content=merge_result.content,
            force=request.force,
            create_only=False,
            target_file_path=settings_file_path,
            display_path=VSCODE_USER_SETTINGS_DISPLAY_PATH,
            policy_id=POLICY_VSCODE_USER_FILES_EXCLUDE_ID,
            policy_revision=POLICY_VSCODE_USER_FILES_EXCLUDE_REVISION,
            merge_strategy="json_merge",
            applied_paths=merge_result.applied_paths,
            preserved_paths=merge_result.preserved_paths,
            conflict_paths=merge_result.conflict_paths,
            reason=self.json_merge_service.build_merge_reason(merge_result),
        )
        operations.append(operation)

    def build_managed_settings_data(self) -> JsonObject:
        files_exclude_settings: JsonObject = {}

        for file_pattern in VSCODE_GLOBAL_FILES_EXCLUDE_PATTERNS:
            files_exclude_settings[file_pattern] = True

        return {
            VSCODE_FILES_EXCLUDE_SETTING_NAME: files_exclude_settings,
        }
