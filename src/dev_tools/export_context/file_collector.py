from __future__ import annotations

import os
from pathlib import Path

from dev_tools.export_context.models import ExportedFile
from dev_tools.export_context.path_matcher import PathMatcher
from dev_tools.project_context.models import DevToolsContext
from dev_tools.shared.file_system import FileSystem
from dev_tools.typings.strings import EmptyFileMarker, RelativePathString


class FileCollector:
    def __init__(
        self,
        path_matcher: PathMatcher,
        file_system: FileSystem,
    ) -> None:
        self.path_matcher = path_matcher
        self.file_system = file_system

    def collect_files(self, dev_tools_context: DevToolsContext) -> list[ExportedFile]:
        project_root: Path = dev_tools_context.project.root_path
        collected_files: list[ExportedFile] = []

        for current_directory_as_string, directory_names, file_names in os.walk(
            project_root,
            topdown=True,
        ):
            current_directory: Path = Path(current_directory_as_string)
            self.prune_excluded_directories(
                current_directory=current_directory,
                project_root=project_root,
                directory_names=directory_names,
                dev_tools_context=dev_tools_context,
            )

            sorted_file_names: list[str] = []
            for file_name in file_names:
                sorted_file_names.append(file_name)

            sorted_file_names.sort()

            for file_name in sorted_file_names:
                file_path: Path = current_directory / file_name

                if not self.path_matcher.should_include_file(
                    file_path=file_path,
                    project_root=project_root,
                    dev_tools_context=dev_tools_context,
                ):
                    continue

                exported_file: ExportedFile = self.build_exported_file(
                    file_path=file_path,
                    project_root=project_root,
                    empty_file_marker=dev_tools_context.export.empty_file_marker,
                )
                collected_files.append(exported_file)

        collected_files.sort(key=self.get_exported_file_sort_key)
        return collected_files

    def prune_excluded_directories(
        self,
        current_directory: Path,
        project_root: Path,
        directory_names: list[str],
        dev_tools_context: DevToolsContext,
    ) -> None:
        filtered_directory_names: list[str] = []

        for directory_name in directory_names:
            directory_path: Path = current_directory / directory_name
            relative_directory_path: Path = directory_path.relative_to(project_root)

            if self.path_matcher.is_excluded_directory_path(
                relative_path=relative_directory_path,
                excluded_directory_names=dev_tools_context.exclude.directories,
            ):
                continue

            filtered_directory_names.append(directory_name)

        filtered_directory_names.sort()
        directory_names[:] = filtered_directory_names

    def build_exported_file(
        self,
        file_path: Path,
        project_root: Path,
        empty_file_marker: EmptyFileMarker,
    ) -> ExportedFile:
        relative_path: Path = file_path.relative_to(project_root)
        content: str = self.file_system.read_text_with_fallback(file_path)

        if content.strip() == "":
            content = str(empty_file_marker) + "\n"

        relative_path_as_string: RelativePathString = RelativePathString(
            relative_path.as_posix()
        )

        return ExportedFile(
            relative_path=relative_path,
            relative_path_as_string=relative_path_as_string,
            absolute_path=file_path,
            content=content,
        )

    def get_exported_file_sort_key(self, exported_file: ExportedFile) -> str:
        return str(exported_file.relative_path_as_string).lower()
