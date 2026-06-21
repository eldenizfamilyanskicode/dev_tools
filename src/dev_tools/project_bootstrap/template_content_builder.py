from __future__ import annotations

from pathlib import Path

from dev_tools.project_bootstrap.json_merge_service import JsonObject
from dev_tools.project_bootstrap.models import StrictnessLevel, ToolName


class TemplateContentBuilder:
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

    def build_package_json_data(self, project_root_path: Path) -> JsonObject:
        return {
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
                "playwright-chromium": "^1.61.0",
                "prettier": "^3.5.0",
                "typescript": "^5.8.0",
            },
        }

    def build_tsconfig_data(self, strictness_level: StrictnessLevel) -> JsonObject:
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

        return {
            "compilerOptions": compiler_options,
            "include": ["src"],
        }

    def build_prettier_config_content(self) -> str:
        return """export default {
  semi: true,
  singleQuote: false,
  trailingComma: "all",
  printWidth: 88,
};
"""

    def has_tool(
        self,
        expanded_tool_names: tuple[ToolName, ...],
        tool_name: ToolName,
    ) -> bool:
        for expanded_tool_name in expanded_tool_names:
            if expanded_tool_name == tool_name:
                return True

        return False
