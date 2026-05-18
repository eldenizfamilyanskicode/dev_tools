from __future__ import annotations

import os
from pathlib import Path

from dev_tools.export_context.path_matcher import PathMatcher
from dev_tools.project_context.models import DevToolsContext
from dev_tools.typings.strings import RelativePathString


class IncludeFileCatalogGenerator:
    def __init__(self, path_matcher: PathMatcher) -> None:
        self.path_matcher = path_matcher

    def collect_candidate_relative_file_paths(
        self,
        dev_tools_context: DevToolsContext,
    ) -> list[RelativePathString]:
        project_root: Path = dev_tools_context.project.root_path
        candidate_file_paths: list[RelativePathString] = []

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
                should_skip_file: bool = self.should_skip_file(
                    file_path=file_path,
                    project_root=project_root,
                    dev_tools_context=dev_tools_context,
                )

                if should_skip_file:
                    continue

                relative_file_path: Path = file_path.relative_to(project_root)
                relative_file_path_as_string: RelativePathString = RelativePathString(
                    relative_file_path.as_posix()
                )
                candidate_file_paths.append(relative_file_path_as_string)

        candidate_file_paths.sort(key=self.get_relative_path_sort_key)
        return candidate_file_paths

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
            is_excluded: bool = self.path_matcher.is_excluded_directory_path(
                relative_path=relative_directory_path,
                excluded_directory_names=dev_tools_context.exclude.directories,
            )

            if is_excluded:
                continue

            filtered_directory_names.append(directory_name)

        filtered_directory_names.sort()
        directory_names[:] = filtered_directory_names

    def should_skip_file(
        self,
        file_path: Path,
        project_root: Path,
        dev_tools_context: DevToolsContext,
    ) -> bool:
        relative_path: Path = file_path.relative_to(project_root)

        is_excluded_file_name: bool = self.path_matcher.is_excluded_file_name(
            file_name=relative_path.name,
            excluded_file_names=dev_tools_context.exclude.files,
        )
        if is_excluded_file_name:
            return True

        is_excluded_file_extension: bool = self.path_matcher.is_excluded_file_extension(
            path=relative_path,
            excluded_extensions=dev_tools_context.exclude.extensions,
        )
        if is_excluded_file_extension:
            return True

        is_excluded_directory_path: bool = self.path_matcher.is_excluded_directory_path(
            relative_path=relative_path.parent,
            excluded_directory_names=dev_tools_context.exclude.directories,
        )
        return is_excluded_directory_path

    def get_relative_path_sort_key(self, relative_path: RelativePathString) -> str:
        return str(relative_path).lower()
