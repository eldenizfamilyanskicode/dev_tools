from __future__ import annotations

import json
import os
from pathlib import Path

from dev_tools.global_cli.application_service import GlobalCliSetupService
from dev_tools.global_cli.constants import (
    GLOBAL_CLI_LAYOUT_README_CONTENT,
    UV_TOOL_BIN_ENVIRONMENT_VARIABLE_NAME,
    UV_TOOL_DIR_ENVIRONMENT_VARIABLE_NAME,
    VSCODE_FILES_EXCLUDE_SETTING_NAME,
    VSCODE_GLOBAL_FILES_EXCLUDE_PATTERNS,
    WINDOWS_USER_PATH_ENVIRONMENT_VARIABLE_NAME,
)
from dev_tools.global_cli.layout_resolver import GlobalCliLayoutResolver
from dev_tools.global_cli.vscode_settings_jsonc_editor import (
    VsCodeSettingsJsoncEditor,
)
from dev_tools.global_cli.vscode_user_settings_setup_operation_builder import (
    VsCodeUserSettingsSetupOperationBuilder,
)
from dev_tools.shared.file_system import FileSystem


class InMemoryUserEnvironmentAdapter:
    def __init__(self, variables_by_name: dict[str, str] | None = None) -> None:
        self.variables_by_name: dict[str, str] = {}
        self.notification_count: int = 0

        if variables_by_name is not None:
            self.variables_by_name.update(variables_by_name)

    def get_user_environment_variable(
        self,
        variable_name: str,
    ) -> str | None:
        return self.variables_by_name.get(variable_name)

    def set_user_environment_variable(
        self,
        variable_name: str,
        variable_value: str,
    ) -> None:
        self.variables_by_name[variable_name] = variable_value

    def notify_environment_changed(self) -> None:
        self.notification_count += 1


class FixedVsCodeUserSettingsPathResolver:
    def __init__(self, settings_file_path: Path) -> None:
        self.settings_file_path = settings_file_path

    def resolve_settings_file_path(self) -> Path:
        return self.settings_file_path


def build_global_cli_setup_service(
    global_cli_root_path: Path,
    home_directory_path: Path,
    user_environment_adapter: InMemoryUserEnvironmentAdapter,
    vscode_user_settings_file_path: Path | None = None,
) -> GlobalCliSetupService:
    resolved_vscode_user_settings_file_path: Path = (
        home_directory_path / "AppData" / "Roaming" / "Code" / "User" / "settings.json"
    )
    if vscode_user_settings_file_path is not None:
        resolved_vscode_user_settings_file_path = vscode_user_settings_file_path

    file_system: FileSystem = FileSystem()
    vscode_settings_jsonc_editor: VsCodeSettingsJsoncEditor = (
        VsCodeSettingsJsoncEditor()
    )
    vscode_user_settings_path_resolver: FixedVsCodeUserSettingsPathResolver = (
        FixedVsCodeUserSettingsPathResolver(resolved_vscode_user_settings_file_path)
    )
    vscode_user_settings_setup_operation_builder: (
        VsCodeUserSettingsSetupOperationBuilder
    ) = VsCodeUserSettingsSetupOperationBuilder(
        file_system=file_system,
        vscode_user_settings_path_resolver=vscode_user_settings_path_resolver,
        vscode_settings_jsonc_editor=vscode_settings_jsonc_editor,
    )
    return GlobalCliSetupService(
        layout_resolver=GlobalCliLayoutResolver(
            global_cli_root_path=global_cli_root_path,
            home_directory_path=home_directory_path,
        ),
        file_system=file_system,
        user_environment_adapter=user_environment_adapter,
        vscode_user_settings_setup_operation_builder=(
            vscode_user_settings_setup_operation_builder
        ),
    )


def test_setup_creates_layout_readme_and_user_environment(tmp_path: Path) -> None:
    global_cli_root_path: Path = tmp_path / "repositories" / "global_cli"
    user_environment_adapter: InMemoryUserEnvironmentAdapter = (
        InMemoryUserEnvironmentAdapter()
    )
    service: GlobalCliSetupService = build_global_cli_setup_service(
        global_cli_root_path=global_cli_root_path,
        home_directory_path=tmp_path,
        user_environment_adapter=user_environment_adapter,
    )

    result_text: str = service.setup_global_cli()

    assert global_cli_root_path.is_dir()
    assert (global_cli_root_path / "bin").is_dir()
    assert (global_cli_root_path / "uv_tools").is_dir()
    assert (global_cli_root_path / "README.md").read_text(encoding="utf-8") == (
        GLOBAL_CLI_LAYOUT_README_CONTENT
    )
    vscode_settings_file_path: Path = (
        tmp_path / "AppData" / "Roaming" / "Code" / "User" / "settings.json"
    )
    settings_document: dict[str, object] = json.loads(
        vscode_settings_file_path.read_text(encoding="utf-8")
    )
    files_exclude_settings: object = settings_document[
        VSCODE_FILES_EXCLUDE_SETTING_NAME
    ]
    assert isinstance(files_exclude_settings, dict)
    for file_pattern in VSCODE_GLOBAL_FILES_EXCLUDE_PATTERNS:
        assert files_exclude_settings[file_pattern] is True

    assert user_environment_adapter.variables_by_name[
        UV_TOOL_BIN_ENVIRONMENT_VARIABLE_NAME
    ] == str(global_cli_root_path / "bin")
    assert user_environment_adapter.variables_by_name[
        UV_TOOL_DIR_ENVIRONMENT_VARIABLE_NAME
    ] == str(global_cli_root_path / "uv_tools")
    user_path_entries: list[str] = user_environment_adapter.variables_by_name[
        WINDOWS_USER_PATH_ENVIRONMENT_VARIABLE_NAME
    ].split(os.pathsep)
    assert str(global_cli_root_path / "bin") in user_path_entries
    assert user_environment_adapter.notification_count == 1
    assert "Global CLI setup result" in result_text


def test_setup_is_idempotent(tmp_path: Path) -> None:
    global_cli_root_path: Path = tmp_path / "repositories" / "global_cli"
    user_environment_adapter: InMemoryUserEnvironmentAdapter = (
        InMemoryUserEnvironmentAdapter()
    )
    service: GlobalCliSetupService = build_global_cli_setup_service(
        global_cli_root_path=global_cli_root_path,
        home_directory_path=tmp_path,
        user_environment_adapter=user_environment_adapter,
    )

    service.setup_global_cli()
    second_result_text: str = service.setup_global_cli()

    path_entries: list[str] = user_environment_adapter.variables_by_name[
        WINDOWS_USER_PATH_ENVIRONMENT_VARIABLE_NAME
    ].split(os.pathsep)
    assert path_entries.count(str(global_cli_root_path / "bin")) == 1
    assert user_environment_adapter.notification_count == 1
    assert "Already configured" in second_result_text


def test_setup_preserves_existing_global_cli_readme(tmp_path: Path) -> None:
    global_cli_root_path: Path = tmp_path / "repositories" / "global_cli"
    readme_file_path: Path = global_cli_root_path / "README.md"
    readme_file_path.parent.mkdir(parents=True)
    readme_file_path.write_text("custom readme\n", encoding="utf-8")
    user_environment_adapter: InMemoryUserEnvironmentAdapter = (
        InMemoryUserEnvironmentAdapter()
    )
    service: GlobalCliSetupService = build_global_cli_setup_service(
        global_cli_root_path=global_cli_root_path,
        home_directory_path=tmp_path,
        user_environment_adapter=user_environment_adapter,
    )

    service.setup_global_cli()

    assert readme_file_path.read_text(encoding="utf-8") == "custom readme\n"


def test_setup_merges_vscode_jsonc_files_exclude(tmp_path: Path) -> None:
    global_cli_root_path: Path = tmp_path / "repositories" / "global_cli"
    vscode_user_settings_file_path: Path = tmp_path / "Code" / "User" / "settings.json"
    vscode_user_settings_file_path.parent.mkdir(parents=True)
    vscode_user_settings_file_path.write_text(
        (
            "{\n"
            '  "editor.unicodeHighlight.allowedCharacters": {\n'
            '    "с": true,\n'
            "  },\n"
            "  // keep this comment\n"
            f'  "{VSCODE_FILES_EXCLUDE_SETTING_NAME}": {{\n'
            '    "**/.git": false,\n'
            '    "**/__pycache__": false,\n'
            "  },\n"
            "}\n"
        ),
        encoding="utf-8",
    )
    user_environment_adapter: InMemoryUserEnvironmentAdapter = (
        InMemoryUserEnvironmentAdapter()
    )
    service: GlobalCliSetupService = build_global_cli_setup_service(
        global_cli_root_path=global_cli_root_path,
        home_directory_path=tmp_path,
        user_environment_adapter=user_environment_adapter,
        vscode_user_settings_file_path=vscode_user_settings_file_path,
    )

    service.setup_global_cli()
    first_content: str = vscode_user_settings_file_path.read_text(encoding="utf-8")
    service.setup_global_cli()
    second_content: str = vscode_user_settings_file_path.read_text(encoding="utf-8")

    assert first_content == second_content
    assert "// keep this comment" in first_content
    assert '"**/.git": false' in first_content
    for file_pattern in VSCODE_GLOBAL_FILES_EXCLUDE_PATTERNS:
        assert f'"{file_pattern}": true' in first_content


def test_setup_reports_conflict_for_invalid_vscode_jsonc(tmp_path: Path) -> None:
    global_cli_root_path: Path = tmp_path / "repositories" / "global_cli"
    vscode_user_settings_file_path: Path = tmp_path / "Code" / "User" / "settings.json"
    vscode_user_settings_file_path.parent.mkdir(parents=True)
    vscode_user_settings_file_path.write_text("{", encoding="utf-8")
    user_environment_adapter: InMemoryUserEnvironmentAdapter = (
        InMemoryUserEnvironmentAdapter()
    )
    service: GlobalCliSetupService = build_global_cli_setup_service(
        global_cli_root_path=global_cli_root_path,
        home_directory_path=tmp_path,
        user_environment_adapter=user_environment_adapter,
        vscode_user_settings_file_path=vscode_user_settings_file_path,
    )

    result_text: str = service.setup_global_cli()

    assert "Conflict: file VS Code user settings" in result_text
    assert vscode_user_settings_file_path.read_text(encoding="utf-8") == "{"


def test_setup_removes_non_executable_canonical_layout_paths_from_user_path(
    tmp_path: Path,
) -> None:
    global_cli_root_path: Path = tmp_path / "repositories" / "global_cli"
    other_bin_directory_path: Path = tmp_path / "other_bin"
    initial_user_path: str = os.pathsep.join(
        (
            str(global_cli_root_path / "bin"),
            str(global_cli_root_path),
            str(global_cli_root_path / "uv_tools"),
            str(tmp_path / ".local" / "bin"),
            str(global_cli_root_path / "bin"),
            str(other_bin_directory_path),
        )
    )
    user_environment_adapter: InMemoryUserEnvironmentAdapter = (
        InMemoryUserEnvironmentAdapter(
            {
                WINDOWS_USER_PATH_ENVIRONMENT_VARIABLE_NAME: initial_user_path,
            }
        )
    )
    service: GlobalCliSetupService = build_global_cli_setup_service(
        global_cli_root_path=global_cli_root_path,
        home_directory_path=tmp_path,
        user_environment_adapter=user_environment_adapter,
    )

    service.setup_global_cli()

    path_entries: list[str] = user_environment_adapter.variables_by_name[
        WINDOWS_USER_PATH_ENVIRONMENT_VARIABLE_NAME
    ].split(os.pathsep)
    assert path_entries.count(str(global_cli_root_path / "bin")) == 1
    assert str(global_cli_root_path) not in path_entries
    assert str(global_cli_root_path / "uv_tools") not in path_entries
    assert str(tmp_path / ".local" / "bin") not in path_entries
    assert str(other_bin_directory_path) in path_entries


def test_dry_run_does_not_mutate_files_or_environment(tmp_path: Path) -> None:
    global_cli_root_path: Path = tmp_path / "repositories" / "global_cli"
    user_environment_adapter: InMemoryUserEnvironmentAdapter = (
        InMemoryUserEnvironmentAdapter()
    )
    service: GlobalCliSetupService = build_global_cli_setup_service(
        global_cli_root_path=global_cli_root_path,
        home_directory_path=tmp_path,
        user_environment_adapter=user_environment_adapter,
    )

    result_text: str = service.setup_global_cli(dry_run=True)

    assert not global_cli_root_path.exists()
    assert not (
        tmp_path / "AppData" / "Roaming" / "Code" / "User" / "settings.json"
    ).exists()
    assert user_environment_adapter.variables_by_name == {}
    assert user_environment_adapter.notification_count == 0
    assert "Global CLI setup plan" in result_text
    assert "Will create" in result_text
