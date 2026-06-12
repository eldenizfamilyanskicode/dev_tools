from __future__ import annotations

from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from dev_tools.project_bootstrap.application_service import ProjectBootstrapService
from dev_tools.project_bootstrap.models import (
    BootstrapFileAction,
    BootstrapFileOperation,
    ProjectBootstrapPlan,
    ProjectBootstrapRequest,
    ToolName,
)
from dev_tools.project_context.project_root_resolver import ProjectRootResolver
from dev_tools.project_policy.constants import (
    POLICY_MANIFEST_VERSION,
)
from dev_tools.project_policy.manifest_store import ProjectPolicyManifestStore
from dev_tools.project_policy.models import (
    PolicyApplicationStatus,
    ProjectPolicyIndex,
    ProjectPolicyInitSettings,
    ProjectPolicyManifest,
    ProjectPolicyProjectId,
    ProjectPolicyRecord,
    RegisteredProjectStatus,
)
from dev_tools.project_policy.project_index_store import ProjectIndexStore
from dev_tools.project_policy.timestamp_service import TimestampService


class ProjectPolicyService:
    def __init__(
        self,
        project_root_resolver: ProjectRootResolver,
        project_bootstrap_service: ProjectBootstrapService,
        manifest_store: ProjectPolicyManifestStore,
        project_index_store: ProjectIndexStore,
        timestamp_service: TimestampService,
    ) -> None:
        self.project_root_resolver = project_root_resolver
        self.project_bootstrap_service = project_bootstrap_service
        self.manifest_store = manifest_store
        self.project_index_store = project_index_store
        self.timestamp_service = timestamp_service

    def record_initialized_project(
        self,
        request: ProjectBootstrapRequest,
        plan: ProjectBootstrapPlan,
    ) -> ProjectPolicyManifest:
        timestamp: str = self.timestamp_service.build_current_timestamp()
        existing_manifest: ProjectPolicyManifest | None = self.load_manifest_if_exists(
            request.project_root_path
        )
        project_id: ProjectPolicyProjectId = ProjectPolicyProjectId()
        initialized_at: str = timestamp
        dev_tools_version_at_init: str = self.resolve_dev_tools_version()

        if existing_manifest is not None:
            project_id = existing_manifest.project_id
            initialized_at = existing_manifest.initialized_at
            dev_tools_version_at_init = existing_manifest.dev_tools_version_at_init

        manifest: ProjectPolicyManifest = ProjectPolicyManifest(
            manifest_version=POLICY_MANIFEST_VERSION,
            project_id=project_id,
            project_root_path=request.project_root_path,
            initialized_at=initialized_at,
            updated_at=timestamp,
            dev_tools_version_at_init=dev_tools_version_at_init,
            init_settings=ProjectPolicyInitSettings(
                application_type=request.application_type,
                tool_names=request.tool_names,
                strictness_level=request.strictness_level,
            ),
            policies=self.build_policy_records(
                operations=plan.operations,
                timestamp=timestamp,
            ),
        )
        self.manifest_store.write_manifest(manifest)
        self.project_index_store.upsert_manifest(
            manifest=manifest,
            timestamp=timestamp,
        )
        return manifest

    def render_registered_projects(self, refresh: bool) -> str:
        project_index: ProjectPolicyIndex = self.load_project_index(refresh=refresh)
        lines: list[str] = []
        lines.append("Registered dev-tools projects")
        lines.append("")
        lines.append(f"Index: {self.project_index_store.resolve_index_file_path()}")

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
        requested_project_root: Path | None,
        include_all_projects: bool,
    ) -> str:
        manifests: tuple[ProjectPolicyManifest, ...] = self.load_manifests(
            requested_project_root=requested_project_root,
            include_all_projects=include_all_projects,
        )
        lines: list[str] = []
        lines.append("Project policy status")

        if not manifests:
            lines.append("")
            lines.append("No active registered projects.")
            return "\n".join(lines).rstrip() + "\n"

        for manifest in manifests:
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

            for policy_record in manifest.policies:
                lines.append(
                    "  - "
                    f"{policy_record.policy_id}@{policy_record.policy_revision}: "
                    f"{policy_record.status.value}"
                )

        return "\n".join(lines).rstrip() + "\n"

    def render_update_plan(
        self,
        requested_project_root: Path | None,
        include_all_projects: bool,
    ) -> str:
        manifests: tuple[ProjectPolicyManifest, ...] = self.load_manifests(
            requested_project_root=requested_project_root,
            include_all_projects=include_all_projects,
        )
        lines: list[str] = []
        lines.append("Project policy update plan")

        if not manifests:
            lines.append("")
            lines.append("No active registered projects.")
            return "\n".join(lines).rstrip() + "\n"

        for manifest in manifests:
            plan: ProjectBootstrapPlan = self.build_bootstrap_plan(manifest)
            lines.append("")
            lines.append(str(manifest.project_root_path))
            lines.append(self.project_bootstrap_service.render_plan(plan).rstrip())

        return "\n".join(lines).rstrip() + "\n"

    def apply_policy_updates(
        self,
        requested_project_root: Path | None,
        include_all_projects: bool,
    ) -> str:
        manifests: tuple[ProjectPolicyManifest, ...] = self.load_manifests(
            requested_project_root=requested_project_root,
            include_all_projects=include_all_projects,
        )
        lines: list[str] = []
        lines.append("Applied project policy updates")

        if not manifests:
            lines.append("")
            lines.append("No active registered projects.")
            return "\n".join(lines).rstrip() + "\n"

        for manifest in manifests:
            request: ProjectBootstrapRequest = self.build_bootstrap_request(
                manifest=manifest,
                dry_run=False,
            )
            plan: ProjectBootstrapPlan = (
                self.project_bootstrap_service.bootstrap_project(request)
            )
            updated_manifest: ProjectPolicyManifest = self.record_initialized_project(
                request=request,
                plan=plan,
            )
            manifest_file_path: Path = self.manifest_store.build_manifest_file_path(
                updated_manifest.project_root_path
            )
            applied_policy_count: int = self.count_operations(
                plan,
                BootstrapFileAction.CREATE,
            ) + self.count_operations(
                plan,
                BootstrapFileAction.UPDATE,
            )
            lines.append("")
            lines.append(str(updated_manifest.project_root_path))
            lines.append(f"  manifest: {manifest_file_path}")
            lines.append(f"  applied policies: {applied_policy_count}")
            lines.append(
                "  skipped policies: "
                f"{self.count_operations(plan, BootstrapFileAction.SKIP)}"
            )

        return "\n".join(lines).rstrip() + "\n"

    def load_manifests(
        self,
        requested_project_root: Path | None,
        include_all_projects: bool,
    ) -> tuple[ProjectPolicyManifest, ...]:
        if include_all_projects:
            project_index: ProjectPolicyIndex = self.load_project_index(refresh=True)
            manifests: list[ProjectPolicyManifest] = []

            for registered_project in project_index.projects:
                if registered_project.status != RegisteredProjectStatus.ACTIVE:
                    continue

                manifests.append(
                    self.manifest_store.load_manifest(
                        registered_project.project_root_path
                    )
                )

            return tuple(manifests)

        project_root_path: Path = self.project_root_resolver.resolve_existing_context(
            requested_project_root
        )
        return (self.manifest_store.load_manifest(project_root_path),)

    def load_project_index(self, refresh: bool) -> ProjectPolicyIndex:
        if not refresh:
            return self.project_index_store.load_index()

        timestamp: str = self.timestamp_service.build_current_timestamp()
        return self.project_index_store.refresh_project_statuses(timestamp)

    def build_bootstrap_plan(
        self,
        manifest: ProjectPolicyManifest,
    ) -> ProjectBootstrapPlan:
        request: ProjectBootstrapRequest = self.build_bootstrap_request(
            manifest=manifest,
            dry_run=True,
        )
        return self.project_bootstrap_service.build_plan(request)

    def build_bootstrap_request(
        self,
        manifest: ProjectPolicyManifest,
        dry_run: bool,
    ) -> ProjectBootstrapRequest:
        return ProjectBootstrapRequest(
            project_root_path=manifest.project_root_path,
            application_type=manifest.init_settings.application_type,
            tool_names=manifest.init_settings.tool_names,
            strictness_level=manifest.init_settings.strictness_level,
            force=False,
            dry_run=dry_run,
        )

    def build_policy_records(
        self,
        operations: tuple[BootstrapFileOperation, ...],
        timestamp: str,
    ) -> tuple[ProjectPolicyRecord, ...]:
        policy_records: list[ProjectPolicyRecord] = []

        for operation in operations:
            if operation.policy_id is None or operation.policy_revision is None:
                continue

            status: PolicyApplicationStatus = self.resolve_operation_status(operation)
            applied_at: str | None = timestamp

            if status in (
                PolicyApplicationStatus.CONFLICT,
                PolicyApplicationStatus.SKIPPED_EXISTING,
            ):
                applied_at = None

            policy_records.append(
                ProjectPolicyRecord(
                    policy_id=operation.policy_id,
                    policy_revision=operation.policy_revision,
                    status=status,
                    merge_strategy=operation.merge_strategy,
                    target_files=(self.format_operation_file_path(operation),),
                    reason=operation.reason,
                    content_hash=self.build_content_hash(operation.content),
                    applied_at=applied_at,
                )
            )

        return tuple(policy_records)

    def resolve_operation_status(
        self,
        operation: BootstrapFileOperation,
    ) -> PolicyApplicationStatus:
        if operation.action in (BootstrapFileAction.CREATE, BootstrapFileAction.UPDATE):
            return PolicyApplicationStatus.APPLIED

        if operation.reason == "already up to date":
            return PolicyApplicationStatus.ALREADY_SATISFIED

        if "not safe to merge" in operation.reason:
            return PolicyApplicationStatus.CONFLICT

        return PolicyApplicationStatus.SKIPPED_EXISTING

    def build_content_hash(self, content: str | None) -> str | None:
        if content is None:
            return None

        content_digest: str = sha256(content.encode("utf-8")).hexdigest()
        return f"sha256:{content_digest}"

    def load_manifest_if_exists(
        self,
        project_root_path: Path,
    ) -> ProjectPolicyManifest | None:
        manifest_file_path: Path = self.manifest_store.build_manifest_file_path(
            project_root_path
        )

        if not manifest_file_path.exists():
            return None

        return self.manifest_store.load_manifest(project_root_path)

    def resolve_dev_tools_version(self) -> str:
        try:
            return version("dev-tools")
        except PackageNotFoundError:
            return "unknown"

    def count_operations(
        self,
        plan: ProjectBootstrapPlan,
        action: BootstrapFileAction,
    ) -> int:
        operation_count: int = 0

        for operation in plan.operations:
            if operation.action == action:
                operation_count = operation_count + 1

        return operation_count

    def format_operation_file_path(self, operation: BootstrapFileOperation) -> str:
        if operation.display_path is not None:
            return operation.display_path

        return operation.relative_file_path.as_posix()

    def format_tool_names(self, tool_names: tuple[ToolName, ...]) -> str:
        formatted_tool_names: list[str] = []

        for tool_name in tool_names:
            formatted_tool_names.append(tool_name.value)

        return ", ".join(formatted_tool_names)
