from __future__ import annotations

from collections.abc import Sequence
from importlib.resources import files
from pathlib import Path

from dev_tools.project_bootstrap.bootstrap_file_writer import BootstrapFileWriter
from dev_tools.project_bootstrap.constants import (
    POLICY_GITIGNORE_MANAGED_BLOCK_ID,
    POLICY_GITIGNORE_MANAGED_BLOCK_REVISION,
    POLICY_PACKAGE_JSON_ID,
    POLICY_PACKAGE_JSON_REVISION,
    POLICY_PRETTIER_CONFIG_ID,
    POLICY_PRETTIER_CONFIG_REVISION,
    POLICY_PYRIGHT_CONFIG_ID,
    POLICY_PYRIGHT_CONFIG_REVISION,
    POLICY_TSCONFIG_ID,
    POLICY_TSCONFIG_REVISION,
    POLICY_VSCODE_EXTENSIONS_ID,
    POLICY_VSCODE_EXTENSIONS_REVISION,
    POLICY_VSCODE_WORKSPACE_SETTINGS_ID,
    POLICY_VSCODE_WORKSPACE_SETTINGS_REVISION,
)
from dev_tools.project_bootstrap.json_merge_service import JsonArray, JsonObject
from dev_tools.project_bootstrap.json_operation_builder import JsonOperationBuilder
from dev_tools.project_bootstrap.managed_block_service import ManagedBlockService
from dev_tools.project_bootstrap.models import (
    ApplicationType,
    BootstrapAddon,
    BootstrapFileOperation,
    ProjectBootstrapPlan,
    ProjectBootstrapRequest,
    ToolName,
)
from dev_tools.project_bootstrap.pyproject_operation_builder import (
    PyprojectOperationBuilder,
)
from dev_tools.project_bootstrap.template_content_builder import TemplateContentBuilder
from dev_tools.templates.constants import (
    DEV_TOOLS_TEMPLATE_PACKAGE,
    GITIGNORE_MANAGED_BLOCK_TEMPLATE_FILE_NAME,
)


class TemplatePlanBuilder:
    def __init__(
        self,
        managed_block_service: ManagedBlockService,
        json_operation_builder: JsonOperationBuilder,
        template_content_builder: TemplateContentBuilder,
        pyproject_operation_builder: PyprojectOperationBuilder,
        bootstrap_file_writer: BootstrapFileWriter,
        bootstrap_addons: Sequence[BootstrapAddon] | None = None,
    ) -> None:
        self.managed_block_service = managed_block_service
        self.json_operation_builder = json_operation_builder
        self.template_content_builder = template_content_builder
        self.pyproject_operation_builder = pyproject_operation_builder
        self.bootstrap_file_writer = bootstrap_file_writer
        self.bootstrap_addons = tuple(bootstrap_addons or ())

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
        for bootstrap_addon in self.bootstrap_addons:
            bootstrap_addon.add_operations(
                operations=operations,
                request=request,
            )

        if self.includes_python(request.application_type):
            if self.has_tool(expanded_tool_names, ToolName.PYRIGHT):
                self.add_json_operation(
                    operations=operations,
                    project_root_path=project_root_path,
                    relative_file_path=Path("pyrightconfig.json"),
                    managed_data=self.template_content_builder.build_pyright_config(
                        request.strictness_level
                    ),
                    force=request.force,
                    create_only=False,
                    policy_id=POLICY_PYRIGHT_CONFIG_ID,
                    policy_revision=POLICY_PYRIGHT_CONFIG_REVISION,
                    merge_strategy="json_merge",
                )

            if request.manage_pyproject:
                operations.append(
                    self.pyproject_operation_builder.build_operation(
                        project_root_path=project_root_path,
                        content=self.template_content_builder.build_pyproject_content(
                            project_root_path=project_root_path,
                            strictness_level=request.strictness_level,
                            expanded_tool_names=expanded_tool_names,
                        ),
                        force=request.force,
                    )
                )

        if self.includes_typescript(request.application_type):
            if request.manage_package_json:
                self.add_json_operation(
                    operations=operations,
                    project_root_path=project_root_path,
                    relative_file_path=Path("package.json"),
                    managed_data=self.template_content_builder.build_package_json_data(
                        project_root_path
                    ),
                    force=request.force,
                    create_only=False,
                    policy_id=POLICY_PACKAGE_JSON_ID,
                    policy_revision=POLICY_PACKAGE_JSON_REVISION,
                    merge_strategy="json_merge",
                )
            self.add_json_operation(
                operations=operations,
                project_root_path=project_root_path,
                relative_file_path=Path("tsconfig.json"),
                managed_data=self.template_content_builder.build_tsconfig_data(
                    request.strictness_level
                ),
                force=request.force,
                create_only=False,
                policy_id=POLICY_TSCONFIG_ID,
                policy_revision=POLICY_TSCONFIG_REVISION,
                merge_strategy="json_merge",
            )

            if self.has_tool(expanded_tool_names, ToolName.PRETTIER):
                self.add_text_operation(
                    operations=operations,
                    project_root_path=project_root_path,
                    relative_file_path=Path("prettier.config.mjs"),
                    content=self.template_content_builder.build_prettier_config_content(),
                    force=request.force,
                    create_only=True,
                    policy_id=POLICY_PRETTIER_CONFIG_ID,
                    policy_revision=POLICY_PRETTIER_CONFIG_REVISION,
                    merge_strategy="create_only_text",
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
            block_body=self.read_gitignore_managed_block_template(),
        )
        self.add_text_operation(
            operations=operations,
            project_root_path=request.project_root_path,
            relative_file_path=relative_file_path,
            content=updated_content,
            force=request.force,
            create_only=False,
            policy_id=POLICY_GITIGNORE_MANAGED_BLOCK_ID,
            policy_revision=POLICY_GITIGNORE_MANAGED_BLOCK_REVISION,
            merge_strategy="managed_block",
        )

    def read_gitignore_managed_block_template(self) -> tuple[str, ...]:
        template_content: str = (
            files(DEV_TOOLS_TEMPLATE_PACKAGE)
            .joinpath(GITIGNORE_MANAGED_BLOCK_TEMPLATE_FILE_NAME)
            .read_text(encoding="utf-8")
        )
        return tuple(template_content.splitlines())

    def add_vscode_settings_operation(
        self,
        operations: list[BootstrapFileOperation],
        request: ProjectBootstrapRequest,
        expanded_tool_names: tuple[ToolName, ...],
    ) -> None:
        managed_data: JsonObject = {}

        if self.includes_python(request.application_type):
            managed_data["python.defaultInterpreterPath"] = (
                self.template_content_builder.choose_python_interpreter_path(
                    request.project_root_path
                )
            )
            managed_data["python.terminal.activateEnvironment"] = True
            managed_data["python.analysis.typeCheckingMode"] = (
                self.template_content_builder.map_python_type_checking_mode(
                    request.strictness_level
                )
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
            policy_id=POLICY_VSCODE_WORKSPACE_SETTINGS_ID,
            policy_revision=POLICY_VSCODE_WORKSPACE_SETTINGS_REVISION,
            merge_strategy="json_merge",
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
            policy_id=POLICY_VSCODE_EXTENSIONS_ID,
            policy_revision=POLICY_VSCODE_EXTENSIONS_REVISION,
            merge_strategy="json_merge",
        )

    def add_json_operation(
        self,
        operations: list[BootstrapFileOperation],
        project_root_path: Path,
        relative_file_path: Path,
        managed_data: JsonObject,
        force: bool,
        create_only: bool,
        policy_id: str | None = None,
        policy_revision: int | None = None,
        merge_strategy: str = "json_merge",
    ) -> None:
        operation: BootstrapFileOperation = self.json_operation_builder.build_operation(
            project_root_path=project_root_path,
            relative_file_path=relative_file_path,
            managed_data=managed_data,
            force=force,
            create_only=create_only,
            policy_id=policy_id,
            policy_revision=policy_revision,
            merge_strategy=merge_strategy,
        )
        operations.append(operation)

    def add_text_operation(
        self,
        operations: list[BootstrapFileOperation],
        project_root_path: Path,
        relative_file_path: Path,
        content: str,
        force: bool,
        create_only: bool,
        policy_id: str | None = None,
        policy_revision: int | None = None,
        merge_strategy: str = "whole_file",
    ) -> None:
        operation: BootstrapFileOperation = self.bootstrap_file_writer.build_operation(
            project_root_path=project_root_path,
            relative_file_path=relative_file_path,
            content=content,
            force=force,
            create_only=create_only,
            policy_id=policy_id,
            policy_revision=policy_revision,
            merge_strategy=merge_strategy,
        )
        operations.append(operation)
