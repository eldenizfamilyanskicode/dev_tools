from __future__ import annotations

from pathlib import Path

from dev_tools.project_context.models import DevToolsContext
from dev_tools.typings.collections import (
    DirectoryNames,
    DirectorySuffixes,
    FileExtensions,
    FileNames,
    RelativePathStrings,
)


class PathMatcher:
    def should_include_file(
        self,
        file_path: Path,
        project_root: Path,
        dev_tools_context: DevToolsContext,
    ) -> bool:
        relative_path: Path = file_path.relative_to(project_root)
        relative_path_as_posix: str = relative_path.as_posix()

        if self.is_excluded_directory_path(
            relative_path=relative_path.parent,
            excluded_directory_names=dev_tools_context.exclude.directories,
            excluded_directory_suffixes=dev_tools_context.exclude.directory_suffixes,
        ):
            return False

        if self.is_explicitly_included_file(
            relative_path_as_posix=relative_path_as_posix,
            included_file_paths=dev_tools_context.include.files,
        ):
            return True

        if self.is_excluded_file_name(
            file_name=relative_path.name,
            excluded_file_names=dev_tools_context.exclude.files,
        ):
            return False

        if self.is_excluded_file_extension(
            path=relative_path,
            excluded_extensions=dev_tools_context.exclude.extensions,
        ):
            return False

        if self.is_inside_included_directory(
            relative_path_as_posix=relative_path_as_posix,
            included_directory_paths=dev_tools_context.include.directories,
        ):
            return True

        file_extension: str = self.get_extension_without_dot(file_path)
        return self.name_exists(file_extension, dev_tools_context.include.extensions)

    def is_excluded_directory_path(
        self,
        relative_path: Path,
        excluded_directory_names: DirectoryNames,
        excluded_directory_suffixes: DirectorySuffixes,
    ) -> bool:
        for path_part in relative_path.parts:
            if path_part == ".":
                continue

            if self.name_exists(path_part, excluded_directory_names):
                return True

            if self.has_excluded_directory_suffix(
                directory_name=path_part,
                excluded_directory_suffixes=excluded_directory_suffixes,
            ):
                return True

        return False

    def has_excluded_directory_suffix(
        self,
        directory_name: str,
        excluded_directory_suffixes: DirectorySuffixes,
    ) -> bool:
        normalized_directory_name: str = directory_name.lower()

        for excluded_directory_suffix in excluded_directory_suffixes:
            normalized_suffix: str = str(excluded_directory_suffix).strip().lower()

            if normalized_suffix == "":
                continue

            if not normalized_suffix.startswith("."):
                normalized_suffix = "." + normalized_suffix

            if normalized_directory_name.endswith(normalized_suffix):
                return True

        return False

    def is_excluded_file_name(
        self,
        file_name: str,
        excluded_file_names: FileNames,
    ) -> bool:
        return self.name_exists(file_name, excluded_file_names)

    def is_excluded_file_extension(
        self,
        path: Path,
        excluded_extensions: FileExtensions,
    ) -> bool:
        extension: str = self.get_extension_without_dot(path)

        if extension == "":
            return False

        return self.name_exists(extension, excluded_extensions)

    def is_explicitly_included_file(
        self,
        relative_path_as_posix: str,
        included_file_paths: RelativePathStrings,
    ) -> bool:
        normalized_relative_path: str = self.normalize_relative_path(
            relative_path_as_posix
        )

        for included_file_path in included_file_paths:
            normalized_included_file_path: str = self.normalize_relative_path(
                str(included_file_path)
            )

            if normalized_included_file_path == normalized_relative_path:
                return True

        return False

    def is_inside_included_directory(
        self,
        relative_path_as_posix: str,
        included_directory_paths: RelativePathStrings,
    ) -> bool:
        normalized_relative_path: str = self.normalize_relative_path(
            relative_path_as_posix
        )

        for included_directory_path in included_directory_paths:
            normalized_directory_path: str = self.normalize_relative_path(
                str(included_directory_path)
            )

            if normalized_directory_path == "":
                continue

            if normalized_relative_path.startswith(normalized_directory_path + "/"):
                return True

        return False

    def normalize_relative_path(self, path_as_string: str) -> str:
        normalized_path: str = path_as_string.replace("\\", "/")
        normalized_path = normalized_path.strip("/")
        return normalized_path

    def get_extension_without_dot(self, path: Path) -> str:
        suffix: str = path.suffix

        if suffix == "":
            return ""

        return suffix.removeprefix(".").lower()

    def name_exists(self, name: str, names: tuple[object, ...]) -> bool:
        normalized_name: str = name.lower()

        for candidate_name in names:
            candidate_name_as_string: str = str(candidate_name)
            if candidate_name_as_string.lower() == normalized_name:
                return True

        return False
