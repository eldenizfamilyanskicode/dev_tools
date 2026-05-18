from __future__ import annotations

from pathlib import Path

from dev_tools.project_bootstrap.bootstrap_file_writer import BootstrapFileWriter
from dev_tools.project_bootstrap.json_merge_service import (
    JsonArray,
    JsonMergeService,
    JsonObject,
)
from dev_tools.project_bootstrap.managed_block_service import ManagedBlockService
from dev_tools.project_bootstrap.models import (
    ApplicationType,
    BootstrapFileAction,
    BootstrapFileOperation,
    ProjectBootstrapPlan,
    ProjectBootstrapRequest,
    StrictnessLevel,
    ToolName,
)


class TemplatePlanBuilder:
    def __init__(
        self,
        managed_block_service: ManagedBlockService,
        json_merge_service: JsonMergeService,
        bootstrap_file_writer: BootstrapFileWriter,
    ) -> None:
        self.managed_block_service = managed_block_service
        self.json_merge_service = json_merge_service
        self.bootstrap_file_writer = bootstrap_file_writer

    def build_plan(self, request: ProjectBootstrapRequest) -> ProjectBootstrapPlan:
        operations: list[BootstrapFileOperation] = []
        project_root_path: Path = request.project_root_path
        expanded_tool_names: tuple[ToolName, ...] = self.expand_tool_names(
            request.tool_names
        )

        self.add_gitignore_operation(
            operations=operations,
            request=request,
        )
        self.add_vscode_settings_operation(
            operations=operations,
            request=request,
            expanded_tool_names=expanded_tool_names,
        )
        self.add_vscode_extensions_operation(
            operations=operations,
            request=request,
            expanded_tool_names=expanded_tool_names,
        )

        if self.includes_python(request.application_type):
            if self.has_tool(expanded_tool_names, ToolName.PYRIGHT):
                self.add_json_operation(
                    operations=operations,
                    project_root_path=project_root_path,
                    relative_file_path=Path("pyrightconfig.json"),
                    managed_data=self.build_pyright_config(request.strictness_level),
                    force=request.force,
                    create_only=False,
                )

            self.add_text_operation(
                operations=operations,
                project_root_path=project_root_path,
                relative_file_path=Path("pyproject.toml"),
                content=self.build_pyproject_content(
                    project_root_path=project_root_path,
                    strictness_level=request.strictness_level,
                    expanded_tool_names=expanded_tool_names,
                ),
                force=request.force,
                create_only=True,
            )

        if self.includes_typescript(request.application_type):
            self.add_text_operation(
                operations=operations,
                project_root_path=project_root_path,
                relative_file_path=Path("package.json"),
                content=self.build_package_json_content(project_root_path),
                force=request.force,
                create_only=True,
            )
            self.add_text_operation(
                operations=operations,
                project_root_path=project_root_path,
                relative_file_path=Path("tsconfig.json"),
                content=self.build_tsconfig_content(request.strictness_level),
                force=request.force,
                create_only=True,
            )

            if self.has_tool(expanded_tool_names, ToolName.PRETTIER):
                self.add_text_operation(
                    operations=operations,
                    project_root_path=project_root_path,
                    relative_file_path=Path("prettier.config.mjs"),
                    content=self.build_prettier_config_content(),
                    force=request.force,
                    create_only=True,
                )

        return ProjectBootstrapPlan(
            application_type=request.application_type,
            tool_names=request.tool_names,
            strictness_level=request.strictness_level,
            operations=tuple(operations),
        )

    def expand_tool_names(
        self,
        tool_names: tuple[ToolName, ...],
    ) -> tuple[ToolName, ...]:
        expanded_tool_names: list[ToolName] = []

        for tool_name in tool_names:
            if tool_name == ToolName.ALL:
                for candidate_tool_name in (
                    ToolName.MYPY,
                    ToolName.RUFF,
                    ToolName.PYRIGHT,
                    ToolName.PRETTIER,
                ):
                    if candidate_tool_name not in expanded_tool_names:
                        expanded_tool_names.append(candidate_tool_name)
                continue

            if tool_name not in expanded_tool_names:
                expanded_tool_names.append(tool_name)

        return tuple(expanded_tool_names)

    def includes_python(self, application_type: ApplicationType) -> bool:
        return application_type in (ApplicationType.PYTHON, ApplicationType.FULL)

    def includes_typescript(self, application_type: ApplicationType) -> bool:
        return application_type in (ApplicationType.TYPESCRIPT, ApplicationType.FULL)

    def has_tool(
        self,
        expanded_tool_names: tuple[ToolName, ...],
        tool_name: ToolName,
    ) -> bool:
        for expanded_tool_name in expanded_tool_names:
            if expanded_tool_name == tool_name:
                return True

        return False

    def add_gitignore_operation(
        self,
        operations: list[BootstrapFileOperation],
        request: ProjectBootstrapRequest,
    ) -> None:
        relative_file_path: Path = Path(".gitignore")
        target_file_path: Path = request.project_root_path / relative_file_path
        current_content: str = ""

        if target_file_path.exists():
            current_content = target_file_path.read_text(encoding="utf-8")

        updated_content: str = self.managed_block_service.merge_managed_block(
            current_content=current_content,
            begin_marker="# >>> dev-tools managed",
            end_marker="# <<< dev-tools managed",
            block_body=(
                ".venv/",
                "venv/",
                ".ruff_cache/",
                ".mypy_cache/",
                ".pytest_cache/",
                "__pycache__/",
                ".eggs/",
                "*.egg-info/",
                "*.egg",
                "node_modules/",
                "dist/",
                "build/",
                "coverage/",
            ),
        )
        self.add_text_operation(
            operations=operations,
            project_root_path=request.project_root_path,
            relative_file_path=relative_file_path,
            content=updated_content,
            force=request.force,
            create_only=False,
        )

    def add_vscode_settings_operation(
        self,
        operations: list[BootstrapFileOperation],
        request: ProjectBootstrapRequest,
        expanded_tool_names: tuple[ToolName, ...],
    ) -> None:
        managed_data: JsonObject = {}

        if self.includes_python(request.application_type):
            managed_data["python.defaultInterpreterPath"] = (
                self.choose_python_interpreter_path(request.project_root_path)
            )
            managed_data["python.terminal.activateEnvironment"] = True
            managed_data["python.analysis.typeCheckingMode"] = (
                self.map_python_type_checking_mode(request.strictness_level)
            )

            if self.has_tool(expanded_tool_names, ToolName.RUFF):
                managed_data["ruff.nativeServer"] = "on"
                managed_data["[python]"] = {
                    "editor.defaultFormatter": "charliermarsh.ruff",
                    "editor.codeActionsOnSave": {
                        "source.fixAll.ruff": "explicit",
                        "source.organizeImports.ruff": "explicit",
                    },
                }

        if self.includes_typescript(request.application_type) and self.has_tool(
            expanded_tool_names, ToolName.PRETTIER
        ):
            managed_data["editor.formatOnSave"] = True
            managed_data["[javascript]"] = {
                "editor.defaultFormatter": "esbenp.prettier-vscode"
            }
            managed_data["[typescript]"] = {
                "editor.defaultFormatter": "esbenp.prettier-vscode"
            }
            managed_data["[typescriptreact]"] = {
                "editor.defaultFormatter": "esbenp.prettier-vscode"
            }

        self.add_json_operation(
            operations=operations,
            project_root_path=request.project_root_path,
            relative_file_path=Path(".vscode/settings.json"),
            managed_data=managed_data,
            force=request.force,
            create_only=False,
        )

    def add_vscode_extensions_operation(
        self,
        operations: list[BootstrapFileOperation],
        request: ProjectBootstrapRequest,
        expanded_tool_names: tuple[ToolName, ...],
    ) -> None:
        recommendations: JsonArray = []

        if self.includes_python(request.application_type):
            recommendations.append("ms-python.python")
            recommendations.append("ms-python.vscode-pylance")

            if self.has_tool(expanded_tool_names, ToolName.RUFF):
                recommendations.append("charliermarsh.ruff")

        if self.includes_typescript(request.application_type) and self.has_tool(
            expanded_tool_names, ToolName.PRETTIER
        ):
            recommendations.append("esbenp.prettier-vscode")

        managed_data: JsonObject = {
            "recommendations": recommendations,
        }

        self.add_json_operation(
            operations=operations,
            project_root_path=request.project_root_path,
            relative_file_path=Path(".vscode/extensions.json"),
            managed_data=managed_data,
            force=request.force,
            create_only=False,
        )

    def add_json_operation(
        self,
        operations: list[BootstrapFileOperation],
        project_root_path: Path,
        relative_file_path: Path,
        managed_data: JsonObject,
        force: bool,
        create_only: bool,
    ) -> None:
        target_file_path: Path = project_root_path / relative_file_path
        current_content: str = ""

        if target_file_path.exists():
            current_content = target_file_path.read_text(encoding="utf-8")

        try:
            content: str = self.json_merge_service.merge_json_content(
                current_content=current_content,
                managed_data=managed_data,
            )
        except ValueError:
            if target_file_path.exists() and not force:
                operations.append(
                    BootstrapFileOperation(
                        relative_file_path=relative_file_path,
                        action=BootstrapFileAction.SKIP,
                        content=None,
                        reason="existing JSON is not safe to merge",
                    )
                )
                return

            content = self.json_merge_service.dump_json(managed_data)

        self.add_text_operation(
            operations=operations,
            project_root_path=project_root_path,
            relative_file_path=relative_file_path,
            content=content,
            force=force,
            create_only=create_only,
        )

    def add_text_operation(
        self,
        operations: list[BootstrapFileOperation],
        project_root_path: Path,
        relative_file_path: Path,
        content: str,
        force: bool,
        create_only: bool,
    ) -> None:
        operation: BootstrapFileOperation = self.bootstrap_file_writer.build_operation(
            project_root_path=project_root_path,
            relative_file_path=relative_file_path,
            content=content,
            force=force,
            create_only=create_only,
        )
        operations.append(operation)

    def choose_python_interpreter_path(self, project_root_path: Path) -> str:
        windows_interpreter_path: Path = (
            project_root_path / ".venv" / "Scripts" / "python.exe"
        )
        if windows_interpreter_path.exists():
            return "${workspaceFolder}/.venv/Scripts/python.exe"

        return "${workspaceFolder}/.venv/bin/python"

    def build_pyright_config(self, strictness_level: StrictnessLevel) -> JsonObject:
        return {
            "typeCheckingMode": self.map_python_type_checking_mode(strictness_level),
            "venvPath": ".",
            "venv": ".venv",
            "exclude": [
                ".venv",
                "venv",
                "node_modules",
                "**/__pycache__",
                "dist",
                "build",
                ".dev_tools",
            ],
        }

    def map_python_type_checking_mode(
        self,
        strictness_level: StrictnessLevel,
    ) -> str:
        if strictness_level == StrictnessLevel.LOW:
            return "basic"

        if strictness_level == StrictnessLevel.MEDIUM:
            return "standard"

        return "strict"

    def build_pyproject_content(
        self,
        project_root_path: Path,
        strictness_level: StrictnessLevel,
        expanded_tool_names: tuple[ToolName, ...],
    ) -> str:
        project_name: str = project_root_path.name.replace("_", "-").lower()
        development_dependencies: list[str] = []

        if self.has_tool(expanded_tool_names, ToolName.MYPY):
            development_dependencies.append('"mypy"')

        if self.has_tool(expanded_tool_names, ToolName.RUFF):
            development_dependencies.append('"ruff"')

        development_dependencies.append('"pytest"')
        dependencies_content: str = ",\n    ".join(development_dependencies)
        mypy_strict_value: str = "true"

        if strictness_level == StrictnessLevel.LOW:
            mypy_strict_value = "false"

        return f'''[project]
name = "{project_name}"
version = "0.1.0"
description = ""
readme = "README.md"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = [
    {dependencies_content},
]

[tool.uv]
package = false

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
fixable = ["ALL"]

[tool.mypy]
python_version = "3.12"
strict = {mypy_strict_value}
[[tool.mypy.overrides]]
module = [
    "app.containers.*",
    "src.containers.*",
]
[tool.pytest.ini_options]
testpaths = ["tests"]
'''

    def build_package_json_content(self, project_root_path: Path) -> str:
        data: JsonObject = {
            "name": project_root_path.name.replace("_", "-").lower(),
            "version": "0.1.0",
            "private": True,
            "type": "module",
            "scripts": {
                "typecheck": "tsc --noEmit",
                "format": "prettier --write .",
                "format:check": "prettier --check .",
            },
            "devDependencies": {
                "prettier": "^3.5.0",
                "typescript": "^5.8.0",
            },
        }

        return self.json_merge_service.dump_json(data)

    def build_tsconfig_content(self, strictness_level: StrictnessLevel) -> str:
        compiler_options: JsonObject = {
            "target": "ES2022",
            "module": "ESNext",
            "moduleResolution": "Bundler",
            "strict": strictness_level != StrictnessLevel.LOW,
            "skipLibCheck": True,
            "noEmit": True,
        }

        if strictness_level == StrictnessLevel.HIGH:
            compiler_options["noUncheckedIndexedAccess"] = True
            compiler_options["exactOptionalPropertyTypes"] = True

        data: JsonObject = {
            "compilerOptions": compiler_options,
            "include": ["src"],
        }

        return self.json_merge_service.dump_json(data)

    def build_prettier_config_content(self) -> str:
        return """export default {
  semi: true,
  singleQuote: false,
  trailingComma: "all",
  printWidth: 88,
};
"""
