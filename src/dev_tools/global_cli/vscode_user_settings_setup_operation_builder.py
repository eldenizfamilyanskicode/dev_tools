from __future__ import annotations

from pathlib import Path

from dev_tools.global_cli.constants import (
    VSCODE_GLOBAL_FILES_EXCLUDE_PATTERNS,
    VSCODE_USER_SETTINGS_DISPLAY_PATH,
)
from dev_tools.global_cli.exceptions import GlobalCliSetupError
from dev_tools.global_cli.models import (
    GlobalCliSetupAction,
    GlobalCliSetupOperation,
    GlobalCliSetupTargetType,
)
from dev_tools.global_cli.vscode_settings_jsonc_editor import (
    VsCodeSettingsJsoncEditor,
)
from dev_tools.global_cli.vscode_user_settings_path_resolver import (
    VsCodeUserSettingsPathResolver,
)
from dev_tools.shared.file_system import FileSystem


class VsCodeUserSettingsSetupOperationBuilder:
    def __init__(
        self,
        file_system: FileSystem,
        vscode_user_settings_path_resolver: VsCodeUserSettingsPathResolver,
        vscode_settings_jsonc_editor: VsCodeSettingsJsoncEditor,
    ) -> None:
        self.file_system = file_system
        self.vscode_user_settings_path_resolver = vscode_user_settings_path_resolver
        self.vscode_settings_jsonc_editor = vscode_settings_jsonc_editor

    def build_operation(self) -> GlobalCliSetupOperation:
        settings_file_path: Path
        settings_file_path = (
            self.vscode_user_settings_path_resolver.resolve_settings_file_path()
        )
        if settings_file_path.exists() and not settings_file_path.is_file():
            return GlobalCliSetupOperation(
                action=GlobalCliSetupAction.CONFLICT,
                target_type=GlobalCliSetupTargetType.FILE,
                target_name=VSCODE_USER_SETTINGS_DISPLAY_PATH,
                target_path=settings_file_path,
                reason=(
                    "Expected VS Code user settings path to be a file, "
                    "but found a directory."
                ),
            )

        current_content: str = ""
        if settings_file_path.exists():
            current_content = self.file_system.read_text(settings_file_path)

        try:
            desired_content: str = (
                self.vscode_settings_jsonc_editor.merge_files_exclude_patterns(
                    current_content=current_content,
                    file_patterns=VSCODE_GLOBAL_FILES_EXCLUDE_PATTERNS,
                )
            )
        except GlobalCliSetupError as error:
            return GlobalCliSetupOperation(
                action=GlobalCliSetupAction.CONFLICT,
                target_type=GlobalCliSetupTargetType.FILE,
                target_name=VSCODE_USER_SETTINGS_DISPLAY_PATH,
                target_path=settings_file_path,
                reason=str(error),
            )

        action: GlobalCliSetupAction = GlobalCliSetupAction.UPDATE
        reason: str = "VS Code files.exclude is missing Python cache patterns."

        if not settings_file_path.exists():
            action = GlobalCliSetupAction.CREATE
            reason = "VS Code user settings file is missing."
        elif current_content == desired_content:
            action = GlobalCliSetupAction.SKIP
            reason = "VS Code files.exclude already hides Python cache patterns."

        return GlobalCliSetupOperation(
            action=action,
            target_type=GlobalCliSetupTargetType.FILE,
            target_name=VSCODE_USER_SETTINGS_DISPLAY_PATH,
            target_path=settings_file_path,
            content=desired_content,
            reason=reason,
        )
