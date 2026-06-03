from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any, cast

from dev_tools.project_bootstrap.application_service import ProjectBootstrapService
from dev_tools.project_bootstrap.bootstrap_file_writer import BootstrapFileWriter
from dev_tools.project_bootstrap.json_merge_service import JsonMergeService
from dev_tools.project_bootstrap.managed_block_service import ManagedBlockService
from dev_tools.project_bootstrap.models import (
    ApplicationType,
    ProjectBootstrapRequest,
    StrictnessLevel,
    ToolName,
)
from dev_tools.project_bootstrap.template_plan_builder import TemplatePlanBuilder
from dev_tools.shared.file_system import FileSystem
from dev_tools.templates.constants import (
    DEV_TOOLS_TEMPLATE_PACKAGE,
    GITIGNORE_MANAGED_BLOCK_TEMPLATE_FILE_NAME,
)


def build_project_bootstrap_service() -> ProjectBootstrapService:
    file_system: FileSystem = FileSystem()
    bootstrap_file_writer: BootstrapFileWriter = BootstrapFileWriter(file_system)
    template_plan_builder: TemplatePlanBuilder = TemplatePlanBuilder(
        managed_block_service=ManagedBlockService(),
        json_merge_service=JsonMergeService(),
        bootstrap_file_writer=bootstrap_file_writer,
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
) -> None:
    project_bootstrap_service: ProjectBootstrapService = (
        build_project_bootstrap_service()
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
    bootstrap_project(tmp_path, dry_run=True)

    assert not (tmp_path / ".gitignore").exists()
    assert not (tmp_path / ".vscode" / "settings.json").exists()
