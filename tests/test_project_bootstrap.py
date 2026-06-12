from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any, cast

from dev_tools.project_bootstrap.application_service import ProjectBootstrapService
from dev_tools.project_bootstrap.bootstrap_file_writer import BootstrapFileWriter
from dev_tools.project_bootstrap.json_merge_service import JsonMergeService
from dev_tools.project_bootstrap.json_operation_builder import JsonOperationBuilder
from dev_tools.project_bootstrap.managed_block_service import ManagedBlockService
from dev_tools.project_bootstrap.models import (
    ApplicationType,
    BootstrapFileAction,
    BootstrapFileOperation,
    ProjectBootstrapRequest,
    StrictnessLevel,
    ToolName,
)
from dev_tools.project_bootstrap.pyproject_operation_builder import (
    PyprojectOperationBuilder,
)
from dev_tools.project_bootstrap.template_content_builder import TemplateContentBuilder
from dev_tools.project_bootstrap.template_plan_builder import TemplatePlanBuilder
from dev_tools.project_bootstrap.toml_section_merge_service import (
    TomlSectionMergeService,
)
from dev_tools.project_bootstrap.toml_section_parser import TomlSectionParser
from dev_tools.shared.file_system import FileSystem
from dev_tools.templates.constants import (
    DEV_TOOLS_TEMPLATE_PACKAGE,
    GITIGNORE_MANAGED_BLOCK_TEMPLATE_FILE_NAME,
)


def build_project_bootstrap_service() -> ProjectBootstrapService:
    file_system: FileSystem = FileSystem()
    bootstrap_file_writer: BootstrapFileWriter = BootstrapFileWriter(file_system)
    json_merge_service: JsonMergeService = JsonMergeService()
    template_plan_builder: TemplatePlanBuilder = TemplatePlanBuilder(
        managed_block_service=ManagedBlockService(),
        json_operation_builder=JsonOperationBuilder(
            json_merge_service=json_merge_service,
            bootstrap_file_writer=bootstrap_file_writer,
        ),
        template_content_builder=TemplateContentBuilder(),
        pyproject_operation_builder=PyprojectOperationBuilder(
            toml_section_merge_service=TomlSectionMergeService(
                toml_section_parser=TomlSectionParser(),
            ),
            bootstrap_file_writer=bootstrap_file_writer,
        ),
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


def build_bootstrap_plan(
    project_root_path: Path,
    application_type: ApplicationType = ApplicationType.FULL,
    tool_names: tuple[ToolName, ...] = (ToolName.ALL,),
    strictness_level: StrictnessLevel = StrictnessLevel.HIGH,
    force: bool = False,
) -> tuple[BootstrapFileOperation, ...]:
    project_bootstrap_service: ProjectBootstrapService = (
        build_project_bootstrap_service()
    )
    request: ProjectBootstrapRequest = ProjectBootstrapRequest(
        project_root_path=project_root_path,
        application_type=application_type,
        tool_names=tool_names,
        strictness_level=strictness_level,
        force=force,
        dry_run=True,
    )
    return project_bootstrap_service.build_plan(request).operations


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


def test_package_json_merge_preserves_existing_project_values(
    tmp_path: Path,
) -> None:
    package_file_path: Path = tmp_path / "package.json"
    package_file_path.write_text(
        json.dumps(
            {
                "name": "custom-package",
                "version": "9.9.9",
                "scripts": {
                    "typecheck": "custom-typecheck",
                },
                "devDependencies": {
                    "typescript": "5.0.0",
                },
            }
        ),
        encoding="utf-8",
    )

    bootstrap_project(
        tmp_path,
        application_type=ApplicationType.TYPESCRIPT,
        tool_names=(ToolName.PRETTIER,),
    )
    package_document: dict[str, Any] = read_json(package_file_path)
    package_scripts: dict[str, str] = package_document["scripts"]
    package_development_dependencies: dict[str, str] = package_document[
        "devDependencies"
    ]

    assert package_document["name"] == "custom-package"
    assert package_document["version"] == "9.9.9"
    assert package_scripts["typecheck"] == "custom-typecheck"
    assert package_scripts["format"] == "prettier --write ."
    assert package_development_dependencies["typescript"] == "5.0.0"
    assert package_development_dependencies["prettier"] == "^3.5.0"


def test_package_json_force_overwrites_managed_values(tmp_path: Path) -> None:
    package_file_path: Path = tmp_path / "package.json"
    package_file_path.write_text(
        json.dumps(
            {
                "name": "custom-package",
                "version": "9.9.9",
                "scripts": {
                    "typecheck": "custom-typecheck",
                },
                "devDependencies": {
                    "typescript": "5.0.0",
                },
            }
        ),
        encoding="utf-8",
    )

    bootstrap_project(
        tmp_path,
        application_type=ApplicationType.TYPESCRIPT,
        tool_names=(ToolName.PRETTIER,),
        force=True,
    )
    package_document: dict[str, Any] = read_json(package_file_path)
    package_scripts: dict[str, str] = package_document["scripts"]
    package_development_dependencies: dict[str, str] = package_document[
        "devDependencies"
    ]

    assert package_document["name"] == tmp_path.name.replace("_", "-").lower()
    assert package_document["version"] == "0.1.0"
    assert package_scripts["typecheck"] == "tsc --noEmit"
    assert package_development_dependencies["typescript"] == "^5.8.0"


def test_package_json_preserved_only_merge_does_not_rewrite_file(
    tmp_path: Path,
) -> None:
    package_file_path: Path = tmp_path / "package.json"
    initial_content: str = json.dumps(
        {
            "name": "custom-package",
            "version": "9.9.9",
            "private": True,
            "type": "module",
            "scripts": {
                "typecheck": "custom-typecheck",
                "format": "prettier --write .",
                "format:check": "prettier --check .",
            },
            "devDependencies": {
                "prettier": "^3.5.0",
                "typescript": "5.0.0",
            },
        },
        separators=(",", ":"),
    )
    package_file_path.write_text(initial_content, encoding="utf-8")

    bootstrap_project(
        tmp_path,
        application_type=ApplicationType.TYPESCRIPT,
        tool_names=(ToolName.PRETTIER,),
    )

    assert package_file_path.read_text(encoding="utf-8") == initial_content


def test_tsconfig_merge_preserves_existing_compiler_options(tmp_path: Path) -> None:
    tsconfig_file_path: Path = tmp_path / "tsconfig.json"
    tsconfig_file_path.write_text(
        json.dumps(
            {
                "compilerOptions": {
                    "strict": False,
                    "module": "CommonJS",
                },
                "include": ["app"],
            }
        ),
        encoding="utf-8",
    )

    bootstrap_project(
        tmp_path,
        application_type=ApplicationType.TYPESCRIPT,
        tool_names=(ToolName.PRETTIER,),
    )
    tsconfig_document: dict[str, Any] = read_json(tsconfig_file_path)
    compiler_options: dict[str, Any] = tsconfig_document["compilerOptions"]
    include_paths: list[str] = tsconfig_document["include"]

    assert compiler_options["strict"] is False
    assert compiler_options["module"] == "CommonJS"
    assert compiler_options["noEmit"] is True
    assert compiler_options["skipLibCheck"] is True
    assert include_paths == ["app", "src"]


def test_existing_pyproject_receives_missing_managed_sections(tmp_path: Path) -> None:
    pyproject_file_path: Path = tmp_path / "pyproject.toml"
    pyproject_file_path.write_text('[project]\nname = "custom"\n', encoding="utf-8")

    bootstrap_project(tmp_path)

    pyproject_content: str = pyproject_file_path.read_text(encoding="utf-8")

    assert '[project]\nname = "custom"\n' in pyproject_content
    assert pyproject_content.count("[project]") == 1
    assert 'version = "0.1.0"' in pyproject_content
    assert "[tool.uv]" in pyproject_content
    assert "[tool.ruff]" in pyproject_content


def test_existing_pyproject_receives_missing_managed_options(tmp_path: Path) -> None:
    pyproject_file_path: Path = tmp_path / "pyproject.toml"
    pyproject_file_path.write_text(
        "[tool.ruff]\nline-length = 100\n",
        encoding="utf-8",
    )

    bootstrap_project(tmp_path)

    pyproject_content: str = pyproject_file_path.read_text(encoding="utf-8")

    assert pyproject_content.count("[tool.ruff]") == 1
    assert "line-length = 100" in pyproject_content
    assert 'target-version = "py312"' in pyproject_content


def test_existing_pyproject_reports_preserved_managed_sections(
    tmp_path: Path,
) -> None:
    pyproject_file_path: Path = tmp_path / "pyproject.toml"
    pyproject_file_path.write_text(
        '[project]\nname = "custom"\n\n[tool.ruff]\nline-length = 100\n',
        encoding="utf-8",
    )

    operations: tuple[BootstrapFileOperation, ...] = build_bootstrap_plan(tmp_path)
    pyproject_operation: BootstrapFileOperation | None = None

    for operation in operations:
        if operation.relative_file_path == Path("pyproject.toml"):
            pyproject_operation = operation
            break

    assert pyproject_operation is not None
    assert pyproject_operation.action == BootstrapFileAction.UPDATE
    assert "[project].name" in pyproject_operation.preserved_paths
    assert "[tool.ruff].line-length" in pyproject_operation.preserved_paths
    assert "[project].version" in pyproject_operation.applied_paths
    assert "[tool.ruff].target-version" in pyproject_operation.applied_paths
    assert "[tool.uv]" in pyproject_operation.applied_paths


def test_invalid_pyproject_is_not_overwritten_by_default(tmp_path: Path) -> None:
    pyproject_file_path: Path = tmp_path / "pyproject.toml"
    pyproject_file_path.write_text("[project", encoding="utf-8")

    bootstrap_project(tmp_path)

    assert pyproject_file_path.read_text(encoding="utf-8") == "[project"


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
