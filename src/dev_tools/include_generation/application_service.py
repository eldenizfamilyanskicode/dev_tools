from __future__ import annotations

from pathlib import Path

from dev_tools.include_generation.file_catalog_generator import (
    IncludeFileCatalogGenerator,
)
from dev_tools.include_generation.include_file_template_renderer import (
    IncludeFileTemplateRenderer,
)
from dev_tools.project_context.context_loader import ProjectContextLoader
from dev_tools.project_context.models import DevToolsContext
from dev_tools.shared.file_system import FileSystem
from dev_tools.typings.strings import RelativePathString


class IncludeFileUpdateService:
    def __init__(
        self,
        context_loader: ProjectContextLoader,
        file_system: FileSystem,
        file_catalog_generator: IncludeFileCatalogGenerator,
        include_file_template_renderer: IncludeFileTemplateRenderer,
    ) -> None:
        self.context_loader = context_loader
        self.file_system = file_system
        self.file_catalog_generator = file_catalog_generator
        self.include_file_template_renderer = include_file_template_renderer

    def update_include_file(self, requested_project_root: Path | None) -> Path:
        dev_tools_context: DevToolsContext = self.context_loader.load_context(
            requested_project_root
        )
        candidate_file_paths: list[RelativePathString] = (
            self.file_catalog_generator.collect_candidate_relative_file_paths(
                dev_tools_context
            )
        )
        include_file_content: str = (
            self.include_file_template_renderer.render_include_file(
                dev_tools_context=dev_tools_context,
                candidate_file_paths=candidate_file_paths,
            )
        )
        include_file_path: Path = (
            dev_tools_context.project.root_path / ".dev_tools" / "include.toml"
        )

        self.file_system.write_text(
            file_path=include_file_path,
            content=include_file_content,
        )

        return include_file_path
