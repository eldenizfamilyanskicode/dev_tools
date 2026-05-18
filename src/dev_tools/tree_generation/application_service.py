from __future__ import annotations

from pathlib import Path

from dev_tools.project_context.context_loader import ProjectContextLoader
from dev_tools.project_context.models import DevToolsContext
from dev_tools.shared.file_system import FileSystem
from dev_tools.tree_generation.directory_tree_generator import (
    DirectoryTreeGenerator,
)


class TreeGenerationService:
    def __init__(
        self,
        context_loader: ProjectContextLoader,
        file_system: FileSystem,
        directory_tree_generator: DirectoryTreeGenerator,
    ) -> None:
        self.context_loader = context_loader
        self.file_system = file_system
        self.directory_tree_generator = directory_tree_generator

    def generate_tree(
        self,
        requested_project_root: Path | None,
        should_write: bool,
    ) -> str:
        dev_tools_context: DevToolsContext = self.context_loader.load_context(
            requested_project_root
        )
        tree_content: str = self.directory_tree_generator.generate_directory_tree(
            project_root=dev_tools_context.project.root_path,
            project_name=dev_tools_context.project.name,
            excluded_directory_names=dev_tools_context.exclude.directories,
            excluded_file_names=dev_tools_context.exclude.files,
            excluded_extensions=dev_tools_context.exclude.extensions,
        )

        if should_write:
            output_file_path: Path = dev_tools_context.output.directory_path / str(
                dev_tools_context.output.tree_file_name
            )
            self.file_system.write_text(
                file_path=output_file_path,
                content=tree_content,
            )

        return tree_content
