from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from dev_tools.project_init.constants import (
    ABOUT_FILE_PATH_TEMPLATE_TOKEN,
    ABOUT_TEMPLATE_FILE_NAME,
    CONTEXT_TEMPLATE_FILE_NAME,
    DEFAULT_ABOUT_FILE_NAME,
    DEFAULT_PROJECT_CONTEXT_DIRECTORY_NAME,
    EXCLUDE_TEMPLATE_FILE_NAME,
    INCLUDE_TEMPLATE_FILE_NAME,
    PROJECT_NAME_TEMPLATE_TOKEN,
)
from dev_tools.shared.file_system import FileSystem
from dev_tools.templates.constants import DEV_TOOLS_TEMPLATE_PACKAGE


class ProjectContextTemplateWriter:
    def __init__(self, file_system: FileSystem) -> None:
        self.file_system = file_system

    def write_templates(
        self,
        project_root: Path,
        force: bool,
        about_file_path: Path | None,
    ) -> Path:
        resolved_about_file_path: Path = self.resolve_about_file_path(
            project_root=project_root,
            about_file_path=about_file_path,
        )
        dev_tools_directory: Path = (
            project_root / DEFAULT_PROJECT_CONTEXT_DIRECTORY_NAME
        )
        context_file_path: Path = dev_tools_directory / "context.toml"
        include_file_path: Path = dev_tools_directory / "include.toml"
        exclude_file_path: Path = dev_tools_directory / "exclude.toml"

        self.file_system.write_text_if_missing(
            file_path=context_file_path,
            content=self.build_context_template(
                project_root=project_root,
                about_file_path=resolved_about_file_path,
            ),
            force=force,
        )
        self.file_system.write_text_if_missing(
            file_path=include_file_path,
            content=self.build_include_template(),
            force=force,
        )
        self.file_system.write_text_if_missing(
            file_path=exclude_file_path,
            content=self.build_exclude_template(),
            force=force,
        )
        self.file_system.write_text_if_missing(
            file_path=resolved_about_file_path,
            content=self.build_about_template(project_root),
            force=force,
        )

        return resolved_about_file_path

    def resolve_about_file_path(
        self,
        project_root: Path,
        about_file_path: Path | None,
    ) -> Path:
        if about_file_path is None:
            return (
                project_root
                / DEFAULT_PROJECT_CONTEXT_DIRECTORY_NAME
                / DEFAULT_ABOUT_FILE_NAME
            )

        if about_file_path.is_absolute():
            return about_file_path.resolve()

        return (project_root / about_file_path).resolve()

    def build_context_template(
        self,
        project_root: Path,
        about_file_path: Path,
    ) -> str:
        about_file_path_as_string: str = self.format_context_path(
            project_root=project_root,
            file_path=about_file_path,
        )
        escaped_project_name: str = self.escape_toml_string(project_root.name)
        escaped_about_file_path: str = self.escape_toml_string(
            about_file_path_as_string
        )
        template_text: str = self.read_template(CONTEXT_TEMPLATE_FILE_NAME)
        rendered_template: str = template_text.replace(
            PROJECT_NAME_TEMPLATE_TOKEN,
            escaped_project_name,
        )

        return rendered_template.replace(
            ABOUT_FILE_PATH_TEMPLATE_TOKEN,
            escaped_about_file_path,
        )

    def build_about_template(self, project_root: Path) -> str:
        template_text: str = self.read_template(ABOUT_TEMPLATE_FILE_NAME)
        return template_text.replace(
            PROJECT_NAME_TEMPLATE_TOKEN,
            project_root.name,
        )

    def build_include_template(self) -> str:
        return self.read_template(INCLUDE_TEMPLATE_FILE_NAME)

    def build_exclude_template(self) -> str:
        return self.read_template(EXCLUDE_TEMPLATE_FILE_NAME)

    def read_template(self, template_file_name: str) -> str:
        return (
            files(DEV_TOOLS_TEMPLATE_PACKAGE)
            .joinpath(template_file_name)
            .read_text(encoding="utf-8")
        )

    def format_context_path(
        self,
        project_root: Path,
        file_path: Path,
    ) -> str:
        try:
            relative_path: Path = file_path.relative_to(project_root)
            return relative_path.as_posix()
        except ValueError:
            return file_path.as_posix()

    def escape_toml_string(self, value: str) -> str:
        escaped_value: str = value.replace("\\", "\\\\")
        escaped_value = escaped_value.replace('"', '\\"')
        return escaped_value
