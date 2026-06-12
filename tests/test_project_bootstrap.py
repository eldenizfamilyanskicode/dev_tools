from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any, cast

from dev_tools.project_bootstrap.addons.vscode_user_files_exclude_addon import (
    VsCodeUserFilesExcludeAddon,
)
from dev_tools.project_bootstrap.application_service import ProjectBootstrapService
from dev_tools.project_bootstrap.bootstrap_file_writer import BootstrapFileWriter
from dev_tools.project_bootstrap.constants import (
    VSCODE_FILES_EXCLUDE_SETTING_NAME,
    VSCODE_GLOBAL_FILES_EXCLUDE_PATTERNS,
)
from dev_tools.project_bootstrap.json_merge_service import JsonMergeService
from dev_tools.project_bootstrap.managed_block_service import ManagedBlockService
from dev_tools.project_bootstrap.models import (
    ApplicationType,
    ProjectBootstrapRequest,
    StrictnessLevel,
    ToolName,
)
from dev_tools.project_bootstrap.template_plan_builder import TemplatePlanBuilder
from dev_tools.project_bootstrap.vscode_user_settings_path_resolver import (
    VsCodeUserSettingsPathResolver,
)
from dev_tools.shared.file_system import FileSystem
from dev_tools.templates.constants import (
    DEV_TOOLS_TEMPLATE_PACKAGE,
    GITIGNORE_MANAGED_BLOCK_TEMPLATE_FILE_NAME,
)


class FixedVsCodeUserSettingsPathResolver:
    def __init__(self, settings_file_path: Path) -> None:
        self.settings_file_path = settings_file_path

    def resolve_settings_file_path(self) -> Path:
        return self.settings_file_path


def build_project_bootstrap_service(
    vscode_user_settings_file_path: Path,
) -> ProjectBootstrapService:
    file_system: FileSystem = FileSystem()
    bootstrap_file_writer: BootstrapFileWriter = BootstrapFileWriter(file_system)
    json_merge_service: JsonMergeService = JsonMergeService()
    vscode_user_settings_path_resolver: VsCodeUserSettingsPathResolver = (
        FixedVsCodeUserSettingsPathResolver(vscode_user_settings_file_path)
    )
    vscode_user_files_exclude_addon: VsCodeUserFilesExcludeAddon = (
        VsCodeUserFilesExcludeAddon(
            json_merge_service=json_merge_service,
            bootstrap_file_writer=bootstrap_file_writer,
            vscode_user_settings_path_resolver=vscode_user_settings_path_resolver,
        )
    )
    template_plan_builder: TemplatePlanBuilder = TemplatePlanBuilder(
        managed_block_service=ManagedBlockService(),
        json_merge_service=json_merge_service,
        bootstrap_file_writer=bootstrap_file_writer,
        bootstrap_addons=(vscode_user_files_exclude_addon,),
    )
    return ProjectBootstrapService(
        template_plan_builder=template_plan_builder,
        bootstrap_file_writer=bootstrap_file_writer,
    )


def bootstrap_project(
    project_root_path: Path,
    application_type: ApplicationType = ApplicationType.FULL,
    tool_names: tuple[ToolName, ...] = (ToolName.ALL,),
    strictness_level: StrictnessLevel = StrictnessLevel.HIGH,
    force: bool = False,
    dry_run: bool = False,
    vscode_user_settings_file_path: Path | None = None,
) -> None:
    resolved_vscode_user_settings_file_path: Path = (
        project_root_path / ".test_vscode_user" / "settings.json"
    )
    if vscode_user_settings_file_path is not None:
        resolved_vscode_user_settings_file_path = vscode_user_settings_file_path

    project_bootstrap_service: ProjectBootstrapService = (
        build_project_bootstrap_service(
            resolved_vscode_user_settings_file_path,
        )
    )
    request: ProjectBootstrapRequest = ProjectBootstrapRequest(
        project_root_path=project_root_path,
        application_type=application_type,
        tool_names=tool_names,
        strictness_level=strictness_level,
        force=force,
        dry_run=dry_run,
    )
    project_bootstrap_service.bootstrap_project(request)


def read_json(file_path: Path) -> dict[str, Any]:
    json_content: Any = json.loads(file_path.read_text(encoding="utf-8"))
    return cast(dict[str, Any], json_content)


def test_gitignore_managed_block_is_appended_once(tmp_path: Path) -> None:
    bootstrap_project(tmp_path)
    bootstrap_project(tmp_path)

    gitignore_content: str = (tmp_path / ".gitignore").read_text(encoding="utf-8")

    assert gitignore_content.count("# >>> dev-tools managed") == 1
    assert gitignore_content.count(".venv/") == 1


def test_gitignore_managed_block_body_matches_template(tmp_path: Path) -> None:
    bootstrap_project(tmp_path)

    gitignore_content: str = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    template_content: str = (
        files(DEV_TOOLS_TEMPLATE_PACKAGE)
        .joinpath(GITIGNORE_MANAGED_BLOCK_TEMPLATE_FILE_NAME)
        .read_text(encoding="utf-8")
    )
    stripped_template_content: str = template_content.rstrip("\n")
    expected_content: str = (
        "# >>> dev-tools managed\n"
        f"{stripped_template_content}\n"
        "# <<< dev-tools managed\n"
    )

    assert gitignore_content == expected_content


def test_gitignore_managed_block_has_common_project_defaults(
    tmp_path: Path,
) -> None:
    bootstrap_project(tmp_path)

    gitignore_content: str = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    expected_gitignore_entries: tuple[str, ...] = (
        "*.py[cod]",
        ".venv-*/",
        ".nox/",
        ".pyright/",
        "node_modules/",
        ".next/",
        ".vscode/",
        ".env.*",
        "llm.env",
        "mongo.agent.env",
        "!.env.example",
        ".DS_Store",
        "Thumbs.db",
    )

    for expected_gitignore_entry in expected_gitignore_entries:
        assert expected_gitignore_entry in gitignore_content


def test_gitignore_managed_block_is_replaced_idempotently(
    tmp_path: Path,
) -> None:
    gitignore_file_path: Path = tmp_path / ".gitignore"
    gitignore_file_path.write_text(
        "custom.log\n\n# >>> dev-tools managed\nold-cache/\n# <<< dev-tools managed\n",
        encoding="utf-8",
    )

    bootstrap_project(tmp_path)
    bootstrap_project(tmp_path)
    gitignore_content: str = gitignore_file_path.read_text(encoding="utf-8")

    assert "custom.log" in gitignore_content
    assert "old-cache/" not in gitignore_content
    assert gitignore_content.count("# >>> dev-tools managed") == 1
    assert gitignore_content.count(".venv/") == 1


def test_vscode_settings_json_merge_preserves_unknown_keys(
    tmp_path: Path,
) -> None:
    settings_file_path: Path = tmp_path / ".vscode" / "settings.json"
    settings_file_path.parent.mkdir(parents=True)
    settings_file_path.write_text(
        json.dumps({"custom.keep": True}),
        encoding="utf-8",
    )

    bootstrap_project(
        tmp_path,
        application_type=ApplicationType.PYTHON,
        tool_names=(ToolName.RUFF, ToolName.PYRIGHT),
    )
    settings_data: dict[str, Any] = read_json(settings_file_path)

    assert settings_data["custom.keep"] is True
    assert settings_data["python.defaultInterpreterPath"] == (
        "${workspaceFolder}/.venv/bin/python"
    )
    assert settings_data["python.analysis.typeCheckingMode"] == "strict"


def test_vscode_extensions_json_merge_avoids_duplicates(
    tmp_path: Path,
) -> None:
    extensions_file_path: Path = tmp_path / ".vscode" / "extensions.json"
    extensions_file_path.parent.mkdir(parents=True)
    extensions_file_path.write_text(
        json.dumps({"recommendations": ["ms-python.python"]}),
        encoding="utf-8",
    )

    bootstrap_project(tmp_path)
    extensions_data: dict[str, Any] = read_json(extensions_file_path)
    recommendations: list[str] = extensions_data["recommendations"]

    assert recommendations.count("ms-python.python") == 1
    assert "charliermarsh.ruff" in recommendations
    assert "esbenp.prettier-vscode" in recommendations


def test_vscode_user_settings_global_files_exclude_is_created(
    tmp_path: Path,
) -> None:
    vscode_user_settings_file_path: Path = tmp_path / "vscode-user" / "settings.json"

    bootstrap_project(
        tmp_path,
        vscode_user_settings_file_path=vscode_user_settings_file_path,
    )

    settings_data: dict[str, Any] = read_json(vscode_user_settings_file_path)
    files_exclude_settings: dict[str, bool] = settings_data[
        VSCODE_FILES_EXCLUDE_SETTING_NAME
    ]

    for file_pattern in VSCODE_GLOBAL_FILES_EXCLUDE_PATTERNS:
        assert files_exclude_settings[file_pattern] is True


def test_vscode_user_settings_global_files_exclude_preserves_existing_settings(
    tmp_path: Path,
) -> None:
    vscode_user_settings_file_path: Path = tmp_path / "vscode-user" / "settings.json"
    vscode_user_settings_file_path.parent.mkdir(parents=True)
    vscode_user_settings_file_path.write_text(
        json.dumps(
            {
                "editor.fontSize": 14,
                VSCODE_FILES_EXCLUDE_SETTING_NAME: {
                    "**/custom-cache": False,
                },
            }
        ),
        encoding="utf-8",
    )

    bootstrap_project(
        tmp_path,
        vscode_user_settings_file_path=vscode_user_settings_file_path,
    )
    bootstrap_project(
        tmp_path,
        vscode_user_settings_file_path=vscode_user_settings_file_path,
    )

    settings_data: dict[str, Any] = read_json(vscode_user_settings_file_path)
    files_exclude_settings: dict[str, bool] = settings_data[
        VSCODE_FILES_EXCLUDE_SETTING_NAME
    ]

    assert settings_data["editor.fontSize"] == 14
    assert files_exclude_settings["**/custom-cache"] is False

    for file_pattern in VSCODE_GLOBAL_FILES_EXCLUDE_PATTERNS:
        assert files_exclude_settings[file_pattern] is True


def test_vscode_user_settings_invalid_json_is_not_overwritten(
    tmp_path: Path,
) -> None:
    vscode_user_settings_file_path: Path = tmp_path / "vscode-user" / "settings.json"
    vscode_user_settings_file_path.parent.mkdir(parents=True)
    vscode_user_settings_file_path.write_text("{", encoding="utf-8")

    bootstrap_project(
        tmp_path,
        vscode_user_settings_file_path=vscode_user_settings_file_path,
    )

    assert vscode_user_settings_file_path.read_text(encoding="utf-8") == "{"


def test_existing_pyproject_is_skipped_by_default(tmp_path: Path) -> None:
    pyproject_file_path: Path = tmp_path / "pyproject.toml"
    pyproject_file_path.write_text('[project]\nname = "custom"\n', encoding="utf-8")

    bootstrap_project(tmp_path)

    assert pyproject_file_path.read_text(encoding="utf-8") == (
        '[project]\nname = "custom"\n'
    )


def test_force_overwrites_force_managed_files(tmp_path: Path) -> None:
    pyproject_file_path: Path = tmp_path / "pyproject.toml"
    pyproject_file_path.write_text('[project]\nname = "custom"\n', encoding="utf-8")

    bootstrap_project(tmp_path, force=True)

    pyproject_content: str = pyproject_file_path.read_text(encoding="utf-8")
    assert 'name = "custom"' not in pyproject_content
    assert "[tool.ruff]" in pyproject_content


def test_dry_run_does_not_write_files(tmp_path: Path) -> None:
    vscode_user_settings_file_path: Path = tmp_path / "vscode-user" / "settings.json"

    bootstrap_project(
        tmp_path,
        dry_run=True,
        vscode_user_settings_file_path=vscode_user_settings_file_path,
    )

    assert not (tmp_path / ".gitignore").exists()
    assert not (tmp_path / ".vscode" / "settings.json").exists()
    assert not vscode_user_settings_file_path.exists()
