from __future__ import annotations

import json
from pathlib import Path

from dev_tools.project_bootstrap.addons.vscode_user_files_exclude_addon import (
    VsCodeUserFilesExcludeAddon,
)
from dev_tools.project_bootstrap.application_service import ProjectBootstrapService
from dev_tools.project_bootstrap.bootstrap_file_writer import BootstrapFileWriter
from dev_tools.project_bootstrap.json_merge_service import JsonMergeService
from dev_tools.project_bootstrap.json_operation_builder import JsonOperationBuilder
from dev_tools.project_bootstrap.managed_block_service import ManagedBlockService
from dev_tools.project_bootstrap.models import (
    ApplicationType,
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
from dev_tools.project_bootstrap.vscode_user_settings_path_resolver import (
    VsCodeUserSettingsPathResolver,
)
from dev_tools.project_context.project_root_resolver import ProjectRootResolver
from dev_tools.project_policy.application_service import ProjectPolicyService
from dev_tools.project_policy.manifest_store import ProjectPolicyManifestStore
from dev_tools.project_policy.operation_status_resolver import (
    ProjectPolicyOperationStatusResolver,
)
from dev_tools.project_policy.project_index_store import ProjectIndexStore
from dev_tools.project_policy.report_renderer import ProjectPolicyReportRenderer
from dev_tools.shared.file_system import FileSystem


class FixedTimestampService:
    def build_current_timestamp(self) -> str:
        return "2026-06-12 19:30:00 UTC"


class FixedVsCodeUserSettingsPathResolver:
    def __init__(self, settings_file_path: Path) -> None:
        self.settings_file_path = settings_file_path

    def resolve_settings_file_path(self) -> Path:
        return self.settings_file_path


def build_project_policy_service(
    index_file_path: Path,
    vscode_user_settings_file_path: Path,
) -> ProjectPolicyService:
    file_system: FileSystem = FileSystem()
    json_merge_service: JsonMergeService = JsonMergeService()
    bootstrap_file_writer: BootstrapFileWriter = BootstrapFileWriter(file_system)
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
        json_operation_builder=JsonOperationBuilder(
            json_merge_service=json_merge_service,
            bootstrap_file_writer=bootstrap_file_writer,
        ),
        template_content_builder=TemplateContentBuilder(),
        pyproject_operation_builder=PyprojectOperationBuilder(
            toml_section_merge_service=TomlSectionMergeService(),
            bootstrap_file_writer=bootstrap_file_writer,
        ),
        bootstrap_file_writer=bootstrap_file_writer,
        bootstrap_addons=(vscode_user_files_exclude_addon,),
    )
    project_bootstrap_service: ProjectBootstrapService = ProjectBootstrapService(
        template_plan_builder=template_plan_builder,
        bootstrap_file_writer=bootstrap_file_writer,
    )
    manifest_store: ProjectPolicyManifestStore = ProjectPolicyManifestStore(file_system)
    project_index_store: ProjectIndexStore = ProjectIndexStore(
        file_system=file_system,
        manifest_store=manifest_store,
        index_file_path=index_file_path,
    )
    operation_status_resolver: ProjectPolicyOperationStatusResolver = (
        ProjectPolicyOperationStatusResolver()
    )
    report_renderer: ProjectPolicyReportRenderer = ProjectPolicyReportRenderer(
        operation_status_resolver=operation_status_resolver,
    )
    return ProjectPolicyService(
        project_root_resolver=ProjectRootResolver(),
        project_bootstrap_service=project_bootstrap_service,
        manifest_store=manifest_store,
        project_index_store=project_index_store,
        timestamp_service=FixedTimestampService(),  # type: ignore[arg-type]
        operation_status_resolver=operation_status_resolver,
        report_renderer=report_renderer,
    )


def bootstrap_and_record_project(
    project_policy_service: ProjectPolicyService,
    project_root_path: Path,
) -> None:
    context_file_path: Path = project_root_path / ".dev_tools" / "context.toml"
    context_file_path.parent.mkdir(parents=True, exist_ok=True)
    context_file_path.write_text('name = "test"\n', encoding="utf-8")
    request: ProjectBootstrapRequest = ProjectBootstrapRequest(
        project_root_path=project_root_path,
        application_type=ApplicationType.FULL,
        tool_names=(ToolName.ALL,),
        strictness_level=StrictnessLevel.HIGH,
        force=False,
        dry_run=False,
    )
    plan = project_policy_service.project_bootstrap_service.bootstrap_project(request)
    project_policy_service.record_initialized_project(request=request, plan=plan)


def test_record_initialized_project_writes_manifest_and_index(tmp_path: Path) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )

    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )

    manifest_content: str = (
        project_root_path / ".dev_tools" / "policy_manifest.toml"
    ).read_text(encoding="utf-8")
    index_content: str = (tmp_path / "index" / "project_index.toml").read_text(
        encoding="utf-8"
    )

    assert "gitignore.managed_block.common_local_artifacts" in manifest_content
    assert "pyproject.uv_python_tooling_defaults" in manifest_content
    assert f'project_root = "{project_root_path.as_posix()}"' in index_content
    assert 'status = "active"' in index_content


def test_manifest_records_preserved_policy_paths(tmp_path: Path) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    package_file_path: Path = project_root_path / "package.json"
    package_file_path.write_text(
        json.dumps(
            {
                "name": "custom-package",
                "version": "9.9.9",
                "devDependencies": {
                    "typescript": "5.0.0",
                },
            }
        ),
        encoding="utf-8",
    )
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )

    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )

    manifest_content: str = (
        project_root_path / ".dev_tools" / "policy_manifest.toml"
    ).read_text(encoding="utf-8")

    assert 'status = "applied_with_skips"' in manifest_content
    assert 'preserved_paths = ["name", "version", "devDependencies.typescript"]' in (
        manifest_content
    )


def test_manifest_records_json_conflict_paths(tmp_path: Path) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    package_file_path: Path = project_root_path / "package.json"
    package_file_path.write_text(
        json.dumps(
            {
                "scripts": "custom-script-shape",
            }
        ),
        encoding="utf-8",
    )
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )

    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )

    manifest_content: str = (
        project_root_path / ".dev_tools" / "policy_manifest.toml"
    ).read_text(encoding="utf-8")

    assert 'status = "conflict"' in manifest_content
    assert 'conflict_paths = ["scripts"]' in manifest_content


def test_policy_plan_shows_revision_action_and_merge_details(tmp_path: Path) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    package_file_path: Path = project_root_path / "package.json"
    package_file_path.write_text(
        json.dumps(
            {
                "name": "custom-package",
                "version": "9.9.9",
            }
        ),
        encoding="utf-8",
    )
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )
    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )

    result_text: str = project_policy_service.render_update_plan(
        requested_project_root=project_root_path,
        include_all_projects=False,
    )

    assert "package_json.typescript_tooling_defaults@1 [current]" in result_text
    assert "action: skip; status: skipped_existing" in result_text
    assert "target: package.json; merge: json_merge" in result_text
    assert "preserved: name, version" in result_text


def test_apply_policy_updates_uses_global_index(tmp_path: Path) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )
    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )
    pyproject_file_path: Path = project_root_path / "pyproject.toml"
    pyproject_file_path.write_text('[project]\nname = "custom"\n', encoding="utf-8")

    result_text: str = project_policy_service.apply_policy_updates(
        requested_project_root=None,
        include_all_projects=True,
    )

    pyproject_content: str = pyproject_file_path.read_text(encoding="utf-8")

    assert "Applied project policy updates" in result_text
    assert "[tool.uv]" in pyproject_content
    assert "[tool.ruff]" in pyproject_content
    assert pyproject_content.count("[project]") == 1


def test_projects_doctor_marks_invalid_manifest(tmp_path: Path) -> None:
    project_root_path: Path = tmp_path / "sample_project"
    project_root_path.mkdir()
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )
    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=project_root_path,
    )
    manifest_file_path: Path = project_root_path / ".dev_tools" / "policy_manifest.toml"
    manifest_file_path.write_text("manifest_version = ", encoding="utf-8")

    result_text: str = project_policy_service.render_registered_projects(refresh=True)

    assert "invalid_manifest" in result_text
    assert str(project_root_path) in result_text


def test_apply_all_skips_invalid_manifest_projects(tmp_path: Path) -> None:
    active_project_root_path: Path = tmp_path / "active_project"
    invalid_project_root_path: Path = tmp_path / "invalid_project"
    active_project_root_path.mkdir()
    invalid_project_root_path.mkdir()
    project_policy_service: ProjectPolicyService = build_project_policy_service(
        index_file_path=tmp_path / "index" / "project_index.toml",
        vscode_user_settings_file_path=tmp_path / "vscode" / "settings.json",
    )
    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=active_project_root_path,
    )
    bootstrap_and_record_project(
        project_policy_service=project_policy_service,
        project_root_path=invalid_project_root_path,
    )
    invalid_manifest_file_path: Path = (
        invalid_project_root_path / ".dev_tools" / "policy_manifest.toml"
    )
    invalid_manifest_file_path.write_text("manifest_version = ", encoding="utf-8")

    result_text: str = project_policy_service.apply_policy_updates(
        requested_project_root=None,
        include_all_projects=True,
    )

    assert str(active_project_root_path) in result_text
    assert "Skipped registered projects:" in result_text
    assert "invalid_manifest" in result_text
    assert str(invalid_project_root_path) in result_text
