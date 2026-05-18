from __future__ import annotations

from pathlib import Path

from dev_tools.export_context.file_chunker import FileChunker
from dev_tools.export_context.file_collector import FileCollector
from dev_tools.export_context.models import ExportedFile
from dev_tools.project_context.context_loader import ProjectContextLoader
from dev_tools.project_context.models import DevToolsContext
from dev_tools.shared.file_system import FileSystem
from dev_tools.tree_generation.directory_tree_generator import DirectoryTreeGenerator
from dev_tools.typings.integers import ChunkNumber
from dev_tools.typings.strings import RelativePathString


class ExportContextService:
    def __init__(
        self,
        context_loader: ProjectContextLoader,
        file_system: FileSystem,
        file_collector: FileCollector,
        file_chunker: FileChunker,
        directory_tree_generator: DirectoryTreeGenerator,
    ) -> None:
        self.context_loader = context_loader
        self.file_system = file_system
        self.file_collector = file_collector
        self.file_chunker = file_chunker
        self.directory_tree_generator = directory_tree_generator

    def export_context(
        self,
        requested_project_root: Path | None,
        should_include_tree: bool,
        should_include_about: bool,
    ) -> list[Path]:
        dev_tools_context: DevToolsContext = self.context_loader.load_context(
            requested_project_root
        )
        combined_context: str = self.build_combined_context(
            dev_tools_context=dev_tools_context,
            should_include_tree=should_include_tree,
            should_include_about=should_include_about,
        )

        output_directory: Path = dev_tools_context.output.directory_path
        self.file_system.ensure_directory(output_directory)

        combined_context_file_path: Path = output_directory / str(
            dev_tools_context.output.combined_context_file_name
        )
        self.file_system.write_text(
            file_path=combined_context_file_path,
            content=combined_context,
        )

        chunk_texts: list[str] = self.file_chunker.split_text_into_chunks(
            content=combined_context,
            maximum_lines_per_chunk=dev_tools_context.export.maximum_lines_per_chunk,
            separator_marker=dev_tools_context.export.file_separator,
        )

        written_files: list[Path] = []
        written_files.append(combined_context_file_path)
        self.write_chunk_files(
            output_directory=output_directory,
            chunk_texts=chunk_texts,
            dev_tools_context=dev_tools_context,
            written_files=written_files,
        )

        return written_files

    def write_chunk_files(
        self,
        output_directory: Path,
        chunk_texts: list[str],
        dev_tools_context: DevToolsContext,
        written_files: list[Path],
    ) -> None:
        for chunk_index in range(len(chunk_texts)):
            chunk_number: ChunkNumber = ChunkNumber(chunk_index + 1)
            chunk_text: str = chunk_texts[chunk_index]
            chunk_file_name: str = (
                f"{dev_tools_context.output.chunk_file_prefix}"
                f"{chunk_number}"
                f"{dev_tools_context.output.chunk_file_extension}"
            )
            chunk_file_path: Path = output_directory / chunk_file_name

            self.file_system.write_text(file_path=chunk_file_path, content=chunk_text)
            written_files.append(chunk_file_path)

    def build_combined_context(
        self,
        dev_tools_context: DevToolsContext,
        should_include_tree: bool,
        should_include_about: bool,
    ) -> str:
        sections: list[str] = []

        if should_include_about:
            self.append_about_section(
                sections=sections,
                dev_tools_context=dev_tools_context,
            )

        if should_include_tree:
            self.append_tree_section(
                sections=sections,
                dev_tools_context=dev_tools_context,
            )

        exported_files: list[ExportedFile] = self.file_collector.collect_files(
            dev_tools_context
        )

        for exported_file in exported_files:
            sections.append(
                self.format_file_section(
                    relative_file_path=exported_file.relative_path_as_string,
                    content=exported_file.content,
                )
            )
            sections.append(str(dev_tools_context.export.file_separator))

        return "\n".join(sections)

    def append_about_section(
        self,
        sections: list[str],
        dev_tools_context: DevToolsContext,
    ) -> None:
        about_file_path: Path = dev_tools_context.about.file_path

        if not about_file_path.exists():
            return

        about_content: str = self.file_system.read_text_with_fallback(about_file_path)

        if about_content.strip() == "":
            about_content = str(dev_tools_context.export.empty_file_marker) + "\n"

        relative_about_path: RelativePathString = self.get_project_relative_path_string(
            file_path=about_file_path,
            project_root=dev_tools_context.project.root_path,
        )

        sections.append(
            self.format_named_section(
                section_name=f"ABOUT CURRENT PROJECT: {relative_about_path}",
                content=about_content,
            )
        )
        sections.append(str(dev_tools_context.export.file_separator))

    def append_tree_section(
        self,
        sections: list[str],
        dev_tools_context: DevToolsContext,
    ) -> None:
        tree_content: str = self.directory_tree_generator.generate_directory_tree(
            project_root=dev_tools_context.project.root_path,
            project_name=dev_tools_context.project.name,
            excluded_directory_names=dev_tools_context.exclude.directories,
            excluded_file_names=dev_tools_context.exclude.files,
            excluded_extensions=dev_tools_context.exclude.extensions,
        )
        sections.append(tree_content)
        sections.append(str(dev_tools_context.export.file_separator))

    def format_file_section(
        self,
        relative_file_path: RelativePathString,
        content: str,
    ) -> str:
        return f'"{relative_file_path}"\n{content}'

    def format_named_section(
        self,
        section_name: str,
        content: str,
    ) -> str:
        return f'"{section_name}"\n{content}'

    def get_project_relative_path_string(
        self,
        file_path: Path,
        project_root: Path,
    ) -> RelativePathString:
        try:
            relative_path: Path = file_path.relative_to(project_root)
            return RelativePathString(relative_path.as_posix())
        except ValueError:
            return RelativePathString(file_path.as_posix())
