from __future__ import annotations

from dev_tools.project_bootstrap.bootstrap_file_writer import BootstrapFileWriter
from dev_tools.project_bootstrap.models import (
    BootstrapFileAction,
    BootstrapFileOperation,
    ProjectBootstrapPlan,
    ProjectBootstrapRequest,
    ToolName,
)
from dev_tools.project_bootstrap.template_plan_builder import TemplatePlanBuilder


class ProjectBootstrapService:
    def __init__(
        self,
        template_plan_builder: TemplatePlanBuilder,
        bootstrap_file_writer: BootstrapFileWriter,
    ) -> None:
        self.template_plan_builder = template_plan_builder
        self.bootstrap_file_writer = bootstrap_file_writer

    def build_plan(self, request: ProjectBootstrapRequest) -> ProjectBootstrapPlan:
        return self.template_plan_builder.build_plan(request)

    def bootstrap_project(
        self,
        request: ProjectBootstrapRequest,
    ) -> ProjectBootstrapPlan:
        plan: ProjectBootstrapPlan = self.build_plan(request)

        if not request.dry_run:
            self.bootstrap_file_writer.apply_plan(
                project_root_path=request.project_root_path,
                plan=plan,
            )

        return plan

    def render_plan(self, plan: ProjectBootstrapPlan) -> str:
        lines: list[str] = []
        lines.append("Project bootstrap plan")
        lines.append("")
        lines.append(f"Application type: {plan.application_type.value}")
        lines.append(f"Toolset: {self.format_tool_names(plan.tool_names)}")
        lines.append(f"Strictness: {plan.strictness_level.value}")
        lines.append("")
        self.append_operation_group(
            lines=lines,
            title="Will create:",
            operations=plan.iter_operations_for_action(BootstrapFileAction.CREATE),
        )
        self.append_operation_group(
            lines=lines,
            title="Will update:",
            operations=plan.iter_operations_for_action(BootstrapFileAction.UPDATE),
        )
        self.append_operation_group(
            lines=lines,
            title="Will skip existing:",
            operations=plan.iter_operations_for_action(BootstrapFileAction.SKIP),
        )
        return "\n".join(lines).rstrip() + "\n"

    def append_operation_group(
        self,
        lines: list[str],
        title: str,
        operations: tuple[BootstrapFileOperation, ...],
    ) -> None:
        if not operations:
            return

        lines.append(title)
        for operation in operations:
            lines.append(f"  {operation.relative_file_path.as_posix()}")

        lines.append("")

    def format_tool_names(self, tool_names: tuple[ToolName, ...]) -> str:
        formatted_tool_names: list[str] = []

        for tool_name in tool_names:
            formatted_tool_names.append(tool_name.value)

        return ", ".join(formatted_tool_names)
