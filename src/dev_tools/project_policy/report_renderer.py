from __future__ import annotations

from pathlib import Path

from base_pydantic_schemas import ImmutableDTO

from dev_tools.project_bootstrap.models import (
    BootstrapFileAction,
    BootstrapFileOperation,
    ProjectBootstrapPlan,
    ToolName,
)
from dev_tools.project_policy.models import (
    PolicyApplicationStatus,
    ProjectPolicyIndex,
    ProjectPolicyManifest,
    ProjectPolicyRecord,
    RegisteredProjectStatus,
)
from dev_tools.project_policy.operation_status_resolver import (
    ProjectPolicyOperationStatusResolver,
)


class ProjectPolicyPlanEntry(ImmutableDTO):
    manifest: ProjectPolicyManifest
    plan: ProjectBootstrapPlan


class ProjectPolicyApplyResult(ImmutableDTO):
    manifest: ProjectPolicyManifest
    manifest_file_path: Path
    plan: ProjectBootstrapPlan


class ProjectPolicyReportRenderer:
    def __init__(
        self,
        operation_status_resolver: ProjectPolicyOperationStatusResolver,
    ) -> None:
        self.operation_status_resolver = operation_status_resolver

    def render_registered_projects(
        self,
        project_index: ProjectPolicyIndex,
        index_file_path: Path,
    ) -> str:
        lines: list[str] = []
        lines.append("Registered dev-tools projects")
        lines.append("")
        lines.append(f"Index: {index_file_path}")

        if not project_index.projects:
            lines.append("No projects registered.")
            return "\n".join(lines).rstrip() + "\n"

        for registered_project in project_index.projects:
            lines.append(
                "- "
                f"{registered_project.status.value}: "
                f"{registered_project.project_root_path}"
            )
            lines.append(f"  project_id: {registered_project.project_id}")
            lines.append(f"  manifest: {registered_project.manifest_file_path}")
            lines.append(f"  last_seen_at: {registered_project.last_seen_at}")

        return "\n".join(lines).rstrip() + "\n"

    def render_policy_status(
        self,
        plan_entries: tuple[ProjectPolicyPlanEntry, ...],
        project_index: ProjectPolicyIndex | None,
    ) -> str:
        lines: list[str] = []
        lines.append("Project policy status")

        if not plan_entries:
            lines.append("")
            lines.append("No active registered projects.")
            self.append_skipped_registered_projects(lines, project_index)
            return "\n".join(lines).rstrip() + "\n"

        for plan_entry in plan_entries:
            manifest: ProjectPolicyManifest = plan_entry.manifest
            lines.append("")
            lines.append(str(manifest.project_root_path))
            lines.append(f"  project_id: {manifest.project_id}")
            lines.append(f"  initialized_at: {manifest.initialized_at}")
            lines.append(f"  updated_at: {manifest.updated_at}")
            lines.append(
                f"  dev_tools_version_at_init: {manifest.dev_tools_version_at_init}"
            )
            lines.append(
                "  init: "
                f"{manifest.init_settings.application_type.value}, "
                f"{self.format_tool_names(manifest.init_settings.tool_names)}, "
                f"{manifest.init_settings.strictness_level.value}"
            )
            current_policy_revisions: dict[str, int] = (
                self.build_current_policy_revisions(plan_entry.plan)
            )

            for policy_record in manifest.policies:
                revision_state: str = self.resolve_policy_record_revision_state(
                    policy_record=policy_record,
                    current_policy_revisions=current_policy_revisions,
                )
                lines.append(
                    "  - "
                    f"{policy_record.policy_id}@{policy_record.policy_revision}: "
                    f"{policy_record.status.value}; {revision_state}"
                )
                self.append_path_detail(
                    lines=lines,
                    title="applied",
                    paths=policy_record.applied_paths,
                )
                self.append_path_detail(
                    lines=lines,
                    title="preserved",
                    paths=policy_record.preserved_paths,
                )
                self.append_path_detail(
                    lines=lines,
                    title="conflicts",
                    paths=policy_record.conflict_paths,
                )
                if policy_record.reason:
                    lines.append(f"    reason: {policy_record.reason}")

        self.append_skipped_registered_projects(lines, project_index)
        return "\n".join(lines).rstrip() + "\n"

    def render_update_plan(
        self,
        plan_entries: tuple[ProjectPolicyPlanEntry, ...],
        project_index: ProjectPolicyIndex | None,
    ) -> str:
        lines: list[str] = []
        lines.append("Project policy update plan")

        if not plan_entries:
            lines.append("")
            lines.append("No active registered projects.")
            self.append_skipped_registered_projects(lines, project_index)
            return "\n".join(lines).rstrip() + "\n"

        for plan_entry in plan_entries:
            manifest: ProjectPolicyManifest = plan_entry.manifest
            lines.append("")
            lines.append(str(manifest.project_root_path))
            lines.append(
                "  init: "
                f"{manifest.init_settings.application_type.value}, "
                f"{self.format_tool_names(manifest.init_settings.tool_names)}, "
                f"{manifest.init_settings.strictness_level.value}"
            )
            self.append_policy_plan_lines(
                lines=lines,
                manifest=manifest,
                plan=plan_entry.plan,
            )

        self.append_skipped_registered_projects(lines, project_index)
        return "\n".join(lines).rstrip() + "\n"

    def render_apply_results(
        self,
        apply_results: tuple[ProjectPolicyApplyResult, ...],
        project_index: ProjectPolicyIndex | None,
    ) -> str:
        lines: list[str] = []
        lines.append("Applied project policy updates")

        if not apply_results:
            lines.append("")
            lines.append("No active registered projects.")
            self.append_skipped_registered_projects(lines, project_index)
            return "\n".join(lines).rstrip() + "\n"

        for apply_result in apply_results:
            applied_policy_count: int = (
                self.operation_status_resolver.count_applied_operations(
                    apply_result.plan
                )
            )
            conflict_policy_count: int = (
                self.operation_status_resolver.count_conflict_operations(
                    apply_result.plan
                )
            )
            skipped_policy_count: int = (
                self.operation_status_resolver.count_skipped_operations(
                    apply_result.plan
                )
            )
            lines.append("")
            lines.append(str(apply_result.manifest.project_root_path))
            lines.append(f"  manifest: {apply_result.manifest_file_path}")
            lines.append(f"  applied policies: {applied_policy_count}")
            lines.append(f"  conflict policies: {conflict_policy_count}")
            lines.append(f"  skipped policies: {skipped_policy_count}")
            self.append_policy_plan_lines(
                lines=lines,
                manifest=apply_result.manifest,
                plan=apply_result.plan,
            )

        self.append_skipped_registered_projects(lines, project_index)
        return "\n".join(lines).rstrip() + "\n"

    def append_policy_plan_lines(
        self,
        lines: list[str],
        manifest: ProjectPolicyManifest,
        plan: ProjectBootstrapPlan,
    ) -> None:
        policy_records_by_id: dict[str, ProjectPolicyRecord] = {}

        for policy_record in manifest.policies:
            policy_records_by_id[policy_record.policy_id] = policy_record

        for operation in plan.operations:
            if operation.policy_id is None or operation.policy_revision is None:
                continue

            operation_status: PolicyApplicationStatus = (
                self.operation_status_resolver.resolve_operation_status(operation)
            )
            revision_state: str = self.resolve_revision_state(
                policy_records_by_id=policy_records_by_id,
                operation=operation,
            )
            operation_display_path: str = self.format_operation_file_path(operation)
            lines.append(
                "  - "
                f"{operation.policy_id}@{operation.policy_revision} "
                f"[{revision_state}]"
            )
            lines.append(
                "    action: "
                f"{operation.action.value}; status: {operation_status.value}; "
                f"target: {operation_display_path}; "
                f"merge: {operation.merge_strategy}"
            )

            self.append_path_detail(
                lines=lines,
                title="applied",
                paths=operation.applied_paths,
            )
            self.append_path_detail(
                lines=lines,
                title="preserved",
                paths=operation.preserved_paths,
            )
            self.append_path_detail(
                lines=lines,
                title="conflicts",
                paths=operation.conflict_paths,
            )

            if operation.reason:
                lines.append(f"    reason: {operation.reason}")

    def append_path_detail(
        self,
        lines: list[str],
        title: str,
        paths: tuple[str, ...],
    ) -> None:
        if not paths:
            return

        lines.append(f"    {title}: {self.format_string_items(paths)}")

    def append_skipped_registered_projects(
        self,
        lines: list[str],
        project_index: ProjectPolicyIndex | None,
    ) -> None:
        if project_index is None:
            return

        has_skipped_projects: bool = False

        for registered_project in project_index.projects:
            if registered_project.status == RegisteredProjectStatus.ACTIVE:
                continue

            if not has_skipped_projects:
                lines.append("")
                lines.append("Skipped registered projects:")
                has_skipped_projects = True

            lines.append(
                "  - "
                f"{registered_project.status.value}: "
                f"{registered_project.project_root_path}"
            )
            lines.append(f"    manifest: {registered_project.manifest_file_path}")

    def resolve_revision_state(
        self,
        policy_records_by_id: dict[str, ProjectPolicyRecord],
        operation: BootstrapFileOperation,
    ) -> str:
        if operation.policy_id is None or operation.policy_revision is None:
            return "unknown"

        existing_policy_record: ProjectPolicyRecord | None = policy_records_by_id.get(
            operation.policy_id
        )

        if existing_policy_record is None:
            return "new"

        if existing_policy_record.policy_revision < operation.policy_revision:
            return f"outdated from {existing_policy_record.policy_revision}"

        if existing_policy_record.policy_revision > operation.policy_revision:
            return f"ahead at {existing_policy_record.policy_revision}"

        if operation.action == BootstrapFileAction.CONFLICT:
            return "conflict"

        if operation.action == BootstrapFileAction.SKIP:
            operation_status: PolicyApplicationStatus = (
                self.operation_status_resolver.resolve_operation_status(operation)
            )
            if operation_status == PolicyApplicationStatus.SKIPPED_EXISTING:
                return "skipped"

            return "current"

        return "drift"

    def build_current_policy_revisions(
        self,
        plan: ProjectBootstrapPlan,
    ) -> dict[str, int]:
        current_policy_revisions: dict[str, int] = {}

        for operation in plan.operations:
            if operation.policy_id is None or operation.policy_revision is None:
                continue

            current_policy_revisions[operation.policy_id] = operation.policy_revision

        return current_policy_revisions

    def resolve_policy_record_revision_state(
        self,
        policy_record: ProjectPolicyRecord,
        current_policy_revisions: dict[str, int],
    ) -> str:
        current_policy_revision: int | None = current_policy_revisions.get(
            policy_record.policy_id
        )

        if current_policy_revision is None:
            return "not in current policy set"

        if policy_record.policy_revision < current_policy_revision:
            return f"outdated; latest revision {current_policy_revision}"

        if policy_record.policy_revision > current_policy_revision:
            return f"ahead of latest revision {current_policy_revision}"

        return "latest revision"

    def format_operation_file_path(self, operation: BootstrapFileOperation) -> str:
        if operation.display_path is not None:
            return operation.display_path

        return operation.relative_file_path.as_posix()

    def format_string_items(self, values: tuple[str, ...]) -> str:
        formatted_values: list[str] = []

        for value in values:
            formatted_values.append(value)

        return ", ".join(formatted_values)

    def format_tool_names(self, tool_names: tuple[ToolName, ...]) -> str:
        formatted_tool_names: list[str] = []

        for tool_name in tool_names:
            formatted_tool_names.append(tool_name.value)

        return ", ".join(formatted_tool_names)
