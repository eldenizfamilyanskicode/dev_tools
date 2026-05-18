from __future__ import annotations

from pathlib import Path

from dev_tools.include_generation.application_service import IncludeFileUpdateService
from dev_tools.project_bootstrap.application_service import ProjectBootstrapService
from dev_tools.project_bootstrap.models import (
    ApplicationType,
    ProjectBootstrapPlan,
    ProjectBootstrapRequest,
    StrictnessLevel,
    ToolName,
)
from dev_tools.project_context.project_root_resolver import ProjectRootResolver
from dev_tools.project_init.git_exclude import GitExcludeService
from dev_tools.project_init.template_writer import ProjectContextTemplateWriter
from dev_tools.shared.file_system import FileSystem


class ProjectInitService:
    def __init__(
        self,
        project_root_resolver: ProjectRootResolver,
        file_system: FileSystem,
        template_writer: ProjectContextTemplateWriter,
        git_exclude_service: GitExcludeService,
        include_file_update_service: IncludeFileUpdateService,
        project_bootstrap_service: ProjectBootstrapService,
    ) -> None:
        self.project_root_resolver = project_root_resolver
        self.file_system = file_system
        self.template_writer = template_writer
        self.git_exclude_service = git_exclude_service
        self.include_file_update_service = include_file_update_service
        self.project_bootstrap_service = project_bootstrap_service

    def initialize_project(
        self,
        requested_project_root: Path | None,
        force: bool,
        about_file_path: Path | None,
        application_type: ApplicationType = ApplicationType.FULL,
        tool_names: tuple[ToolName, ...] = (ToolName.ALL,),
        strictness_level: StrictnessLevel = StrictnessLevel.HIGH,
        dry_run: bool = False,
    ) -> Path:
        project_root: Path = self.project_root_resolver.resolve_for_init(
            requested_project_root
        )

        if dry_run:
            return project_root

        dev_tools_directory: Path = project_root / ".dev_tools"
        output_directory: Path = dev_tools_directory / "output"

        self.file_system.ensure_directory(dev_tools_directory)
        self.file_system.ensure_directory(output_directory)

        resolved_about_file_path: Path = self.template_writer.write_templates(
            project_root=project_root,
            force=force,
            about_file_path=about_file_path,
        )
        additional_ignored_paths: tuple[Path, ...]
        additional_ignored_paths = self.build_additional_ignored_paths(
            project_root=project_root,
            about_file_path=resolved_about_file_path,
        )
        self.git_exclude_service.ensure_project_context_ignored(
            project_root=project_root,
            additional_ignored_paths=additional_ignored_paths,
        )
        bootstrap_request: ProjectBootstrapRequest = ProjectBootstrapRequest(
            project_root_path=project_root,
            application_type=application_type,
            tool_names=tool_names,
            strictness_level=strictness_level,
            force=force,
            dry_run=False,
        )
        self.project_bootstrap_service.bootstrap_project(bootstrap_request)
        self.include_file_update_service.update_include_file(
            requested_project_root=project_root,
        )

        return project_root

    def render_initialization_plan(
        self,
        requested_project_root: Path | None,
        force: bool,
        application_type: ApplicationType,
        tool_names: tuple[ToolName, ...],
        strictness_level: StrictnessLevel,
    ) -> str:
        project_root: Path = self.project_root_resolver.resolve_for_init(
            requested_project_root
        )
        bootstrap_request: ProjectBootstrapRequest = ProjectBootstrapRequest(
            project_root_path=project_root,
            application_type=application_type,
            tool_names=tool_names,
            strictness_level=strictness_level,
            force=force,
            dry_run=True,
        )
        bootstrap_plan: ProjectBootstrapPlan = (
            self.project_bootstrap_service.bootstrap_project(bootstrap_request)
        )
        return self.project_bootstrap_service.render_plan(bootstrap_plan)

    def build_additional_ignored_paths(
        self,
        project_root: Path,
        about_file_path: Path,
    ) -> tuple[Path, ...]:
        try:
            relative_about_file_path: Path = about_file_path.relative_to(project_root)
        except ValueError:
            return ()

        if self.is_inside_dev_tools_directory(relative_about_file_path):
            return ()

        return (relative_about_file_path,)

    def is_inside_dev_tools_directory(self, relative_path: Path) -> bool:
        for path_part in relative_path.parts:
            if path_part == ".dev_tools":
                return True

            break

        return False
