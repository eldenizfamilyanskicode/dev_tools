from __future__ import annotations

from pathlib import Path
from typing import Any

from dev_tools.project_bootstrap.application_service import ProjectBootstrapService
from dev_tools.project_bootstrap.bootstrap_file_writer import BootstrapFileWriter
from dev_tools.project_bootstrap.json_merge_service import JsonMergeService
from dev_tools.project_bootstrap.json_operation_builder import JsonOperationBuilder
from dev_tools.project_bootstrap.managed_block_service import ManagedBlockService
from dev_tools.project_bootstrap.models import (
    ApplicationType,
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
from dev_tools.project_context.project_root_resolver import ProjectRootResolver
from dev_tools.project_init.application_service import ProjectInitService
from dev_tools.project_init.git_exclude import GitExcludeService
from dev_tools.project_init.template_writer import ProjectContextTemplateWriter
from dev_tools.shared.file_system import FileSystem


class RecordingIncludeFileUpdateService:
    def __init__(self) -> None:
        self.requested_project_root: Path | None = None

    def update_include_file(self, requested_project_root: Path | None) -> Path:
        self.requested_project_root = requested_project_root
        return requested_project_root / ".dev_tools" / "include.toml"  # type: ignore[operator]


class RecordingProjectBootstrapService:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    def bootstrap_project(self, request: Any) -> Any:
        self.requests.append(request)
        return type("RecordedPlan", (), {"operations": ()})()

    def render_plan(self, plan: Any) -> str:
        return ""


class RecordingProjectPolicyService:
    def __init__(self) -> None:
        self.requests: list[Any] = []
        self.plans: list[Any] = []

    def record_initialized_project(self, request: Any, plan: Any) -> None:
        self.requests.append(request)
        self.plans.append(plan)


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


def test_old_dev_tools_init_behavior_still_works(tmp_path: Path) -> None:
    git_info_directory: Path = tmp_path / ".git" / "info"
    git_info_directory.mkdir(parents=True)
    (git_info_directory / "exclude").write_text("", encoding="utf-8")
    file_system: FileSystem = FileSystem()
    include_file_update_service: RecordingIncludeFileUpdateService = (
        RecordingIncludeFileUpdateService()
    )
    project_bootstrap_service: RecordingProjectBootstrapService = (
        RecordingProjectBootstrapService()
    )
    project_policy_service: RecordingProjectPolicyService = (
        RecordingProjectPolicyService()
    )
    project_init_service: ProjectInitService = ProjectInitService(
        project_root_resolver=ProjectRootResolver(),
        file_system=file_system,
        template_writer=ProjectContextTemplateWriter(file_system),
        git_exclude_service=GitExcludeService(file_system),
        include_file_update_service=include_file_update_service,  # type: ignore[arg-type]
        project_bootstrap_service=project_bootstrap_service,  # type: ignore[arg-type]
        project_policy_service=project_policy_service,  # type: ignore[arg-type]
    )

    initialized_project_root: Path = project_init_service.initialize_project(
        requested_project_root=tmp_path,
        force=False,
        about_file_path=None,
    )

    assert initialized_project_root == tmp_path
    assert (tmp_path / ".dev_tools" / "context.toml").exists()
    assert (tmp_path / ".dev_tools" / "include.toml").exists()
    assert (tmp_path / ".dev_tools" / "exclude.toml").exists()
    assert (tmp_path / ".dev_tools" / "about_current_project.md").exists()
    assert (tmp_path / ".dev_tools" / "output").is_dir()
    assert include_file_update_service.requested_project_root == tmp_path
    assert len(project_bootstrap_service.requests) == 1
    assert len(project_policy_service.requests) == 1
    assert project_bootstrap_service.requests[0].manage_pyproject is True
    assert project_bootstrap_service.requests[0].manage_package_json is True
    assert ".dev_tools/" in (git_info_directory / "exclude").read_text(encoding="utf-8")


def test_project_context_template_writer_renders_resource_templates(
    tmp_path: Path,
) -> None:
    file_system: FileSystem = FileSystem()
    template_writer: ProjectContextTemplateWriter = ProjectContextTemplateWriter(
        file_system
    )
    custom_about_file_path: Path = Path("docs/about_current_project.md")

    resolved_about_file_path: Path = template_writer.write_templates(
        project_root=tmp_path,
        force=False,
        about_file_path=custom_about_file_path,
    )

    dev_tools_directory: Path = tmp_path / ".dev_tools"
    context_content: str = (dev_tools_directory / "context.toml").read_text(
        encoding="utf-8"
    )
    include_content: str = (dev_tools_directory / "include.toml").read_text(
        encoding="utf-8"
    )
    exclude_content: str = (dev_tools_directory / "exclude.toml").read_text(
        encoding="utf-8"
    )
    about_content: str = resolved_about_file_path.read_text(encoding="utf-8")

    assert resolved_about_file_path == (tmp_path / custom_about_file_path).resolve()
    assert f'name = "{tmp_path.name}"' in context_content
    assert 'file_path = "docs/about_current_project.md"' in context_content
    assert about_content.startswith(f"# About current project: {tmp_path.name}")
    assert "directories = []" in include_content
    assert '"node_modules",' in exclude_content


def test_initialization_dry_run_plans_pyproject_not_pyrightconfig(
    tmp_path: Path,
) -> None:
    (tmp_path / ".git").mkdir()
    file_system: FileSystem = FileSystem()
    project_init_service: ProjectInitService = ProjectInitService(
        project_root_resolver=ProjectRootResolver(),
        file_system=file_system,
        template_writer=ProjectContextTemplateWriter(file_system),
        git_exclude_service=GitExcludeService(file_system),
        include_file_update_service=RecordingIncludeFileUpdateService(),  # type: ignore[arg-type]
        project_bootstrap_service=build_project_bootstrap_service(),
        project_policy_service=RecordingProjectPolicyService(),  # type: ignore[arg-type]
    )

    result_text: str = project_init_service.render_initialization_plan(
        requested_project_root=tmp_path,
        force=False,
        application_type=ApplicationType.PYTHON,
        tool_names=(ToolName.RUFF, ToolName.PYRIGHT),
        strictness_level=StrictnessLevel.HIGH,
    )

    assert "pyproject.toml" in result_text
    assert "pyrightconfig.json" not in result_text
    assert not (tmp_path / "pyproject.toml").exists()
    assert not (tmp_path / "pyrightconfig.json").exists()
