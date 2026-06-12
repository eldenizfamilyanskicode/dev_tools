from __future__ import annotations

import tomllib
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from pydantic import ValidationError

from dev_tools.project_bootstrap.application_service import ProjectBootstrapService
from dev_tools.project_bootstrap.models import (
    BootstrapFileOperation,
    ProjectBootstrapPlan,
    ProjectBootstrapRequest,
)
from dev_tools.project_context.project_root_resolver import ProjectRootResolver
from dev_tools.project_policy.constants import POLICY_MANIFEST_VERSION
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
from dev_tools.project_policy.operation_status_resolver import (
    ProjectPolicyOperationStatusResolver,
)
from dev_tools.project_policy.project_index_store import ProjectIndexStore
from dev_tools.project_policy.report_renderer import (
    ProjectPolicyApplyResult,
    ProjectPolicyPlanEntry,
    ProjectPolicyReportRenderer,
)
from dev_tools.project_policy.timestamp_service import TimestampService


class ProjectPolicyService:
    def __init__(
        self,
        project_root_resolver: ProjectRootResolver,
        project_bootstrap_service: ProjectBootstrapService,
        manifest_store: ProjectPolicyManifestStore,
        project_index_store: ProjectIndexStore,
        timestamp_service: TimestampService,
        operation_status_resolver: ProjectPolicyOperationStatusResolver,
        report_renderer: ProjectPolicyReportRenderer,
    ) -> None:
        self.project_root_resolver = project_root_resolver
        self.project_bootstrap_service = project_bootstrap_service
        self.manifest_store = manifest_store
        self.project_index_store = project_index_store
        self.timestamp_service = timestamp_service
        self.operation_status_resolver = operation_status_resolver
        self.report_renderer = report_renderer

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
        return self.report_renderer.render_registered_projects(
            project_index=project_index,
            index_file_path=self.project_index_store.resolve_index_file_path(),
        )

    def render_policy_status(
        self,
        requested_project_root: Path | None,
        include_all_projects: bool,
    ) -> str:
        manifests: tuple[ProjectPolicyManifest, ...] = self.load_manifests(
            requested_project_root=requested_project_root,
            include_all_projects=include_all_projects,
        )
        plan_entries: tuple[ProjectPolicyPlanEntry, ...] = self.build_plan_entries(
            manifests
        )
        return self.report_renderer.render_policy_status(
            plan_entries=plan_entries,
            project_index=self.load_project_index_for_report(include_all_projects),
        )

    def render_update_plan(
        self,
        requested_project_root: Path | None,
        include_all_projects: bool,
        force: bool = False,
    ) -> str:
        manifests: tuple[ProjectPolicyManifest, ...] = self.load_manifests(
            requested_project_root=requested_project_root,
            include_all_projects=include_all_projects,
        )
        plan_entries: tuple[ProjectPolicyPlanEntry, ...] = self.build_plan_entries(
            manifests=manifests,
            force=force,
        )
        return self.report_renderer.render_update_plan(
            plan_entries=plan_entries,
            project_index=self.load_project_index_for_report(include_all_projects),
        )

    def apply_policy_updates(
        self,
        requested_project_root: Path | None,
        include_all_projects: bool,
        force: bool = False,
    ) -> str:
        manifests: tuple[ProjectPolicyManifest, ...] = self.load_manifests(
            requested_project_root=requested_project_root,
            include_all_projects=include_all_projects,
        )
        apply_results: list[ProjectPolicyApplyResult] = []

        for manifest in manifests:
            request: ProjectBootstrapRequest = self.build_bootstrap_request(
                manifest=manifest,
                dry_run=False,
                force=force,
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
            apply_results.append(
                ProjectPolicyApplyResult(
                    manifest=updated_manifest,
                    manifest_file_path=manifest_file_path,
                    plan=plan,
                )
            )

        return self.report_renderer.render_apply_results(
            apply_results=tuple(apply_results),
            project_index=self.load_project_index_for_report(include_all_projects),
        )

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

                try:
                    manifests.append(
                        self.manifest_store.load_manifest(
                            registered_project.project_root_path
                        )
                    )
                except (
                    FileNotFoundError,
                    NotADirectoryError,
                    tomllib.TOMLDecodeError,
                    TypeError,
                    ValueError,
                    ValidationError,
                ):
                    continue

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

    def load_project_index_for_report(
        self,
        include_all_projects: bool,
    ) -> ProjectPolicyIndex | None:
        if not include_all_projects:
            return None

        return self.load_project_index(refresh=False)

    def build_plan_entries(
        self,
        manifests: tuple[ProjectPolicyManifest, ...],
        force: bool = False,
    ) -> tuple[ProjectPolicyPlanEntry, ...]:
        plan_entries: list[ProjectPolicyPlanEntry] = []

        for manifest in manifests:
            plan_entries.append(
                ProjectPolicyPlanEntry(
                    manifest=manifest,
                    plan=self.build_bootstrap_plan(
                        manifest=manifest,
                        force=force,
                    ),
                )
            )

        return tuple(plan_entries)

    def build_bootstrap_plan(
        self,
        manifest: ProjectPolicyManifest,
        force: bool = False,
    ) -> ProjectBootstrapPlan:
        request: ProjectBootstrapRequest = self.build_bootstrap_request(
            manifest=manifest,
            dry_run=True,
            force=force,
        )
        return self.project_bootstrap_service.build_plan(request)

    def build_bootstrap_request(
        self,
        manifest: ProjectPolicyManifest,
        dry_run: bool,
        force: bool = False,
    ) -> ProjectBootstrapRequest:
        return ProjectBootstrapRequest(
            project_root_path=manifest.project_root_path,
            application_type=manifest.init_settings.application_type,
            tool_names=manifest.init_settings.tool_names,
            strictness_level=manifest.init_settings.strictness_level,
            force=force,
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

            status: PolicyApplicationStatus = (
                self.operation_status_resolver.resolve_operation_status(operation)
            )
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
                    applied_paths=operation.applied_paths,
                    preserved_paths=operation.preserved_paths,
                    conflict_paths=operation.conflict_paths,
                    content_hash=self.build_content_hash(operation.content),
                    applied_at=applied_at,
                )
            )

        return tuple(policy_records)

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

    def format_operation_file_path(self, operation: BootstrapFileOperation) -> str:
        if operation.display_path is not None:
            return operation.display_path

        return operation.relative_file_path.as_posix()
