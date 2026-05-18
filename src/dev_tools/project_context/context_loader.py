from __future__ import annotations

from pathlib import Path

from dev_tools.project_context.models import (
    AboutSettings,
    DevToolsContext,
    ExcludeSettings,
    ExportSettings,
    IncludeSettings,
    OutputSettings,
    ProjectSettings,
)
from dev_tools.project_context.project_root_resolver import ProjectRootResolver
from dev_tools.shared.toml_reader import TomlData, TomlReader
from dev_tools.typings.collections import (
    DirectoryNames,
    DirectorySuffixes,
    FileExtensions,
    FileNames,
    RelativePathStrings,
)
from dev_tools.typings.integers import MaximumLinesPerChunk
from dev_tools.typings.strings import (
    ChunkFileExtension,
    ChunkFilePrefix,
    DirectoryName,
    DirectorySuffix,
    EmptyFileMarker,
    FileExtension,
    FileName,
    FileSeparator,
    ProjectName,
    RelativePathString,
)


class ProjectContextLoader:
    def __init__(
        self,
        project_root_resolver: ProjectRootResolver,
        toml_reader: TomlReader,
    ) -> None:
        self.project_root_resolver = project_root_resolver
        self.toml_reader = toml_reader

    def load_context(
        self,
        requested_project_root: Path | None = None,
    ) -> DevToolsContext:
        project_root: Path = self.project_root_resolver.resolve_existing_context(
            requested_project_root
        )
        dev_tools_directory: Path = project_root / ".dev_tools"

        context_data: TomlData = self.toml_reader.read_toml_file(
            dev_tools_directory / "context.toml"
        )
        include_data: TomlData = self.toml_reader.read_toml_file(
            dev_tools_directory / "include.toml"
        )
        exclude_data: TomlData = self.toml_reader.read_toml_file(
            dev_tools_directory / "exclude.toml"
        )

        project_settings: ProjectSettings = self.build_project_settings(
            context_data=context_data,
            fallback_project_root=project_root,
        )
        about_settings: AboutSettings = self.build_about_settings(
            context_data=context_data,
            project_root=project_settings.root_path,
        )
        output_settings: OutputSettings = self.build_output_settings(
            context_data=context_data,
            project_root=project_settings.root_path,
        )
        export_settings: ExportSettings = self.build_export_settings(context_data)
        include_settings: IncludeSettings = self.build_include_settings(include_data)
        exclude_settings: ExcludeSettings = self.build_exclude_settings(exclude_data)

        return DevToolsContext(
            project=project_settings,
            about=about_settings,
            output=output_settings,
            export=export_settings,
            include=include_settings,
            exclude=exclude_settings,
        )

    def build_project_settings(
        self,
        context_data: TomlData,
        fallback_project_root: Path,
    ) -> ProjectSettings:
        project_data: TomlData = self.get_table(context_data, "project")
        project_name_as_string: str = self.get_string(
            data=project_data,
            key="name",
            default=fallback_project_root.name,
        )
        root_path_as_string: str = self.get_string(
            data=project_data,
            key="root_path",
            default=".",
        )
        root_path: Path = self.resolve_project_relative_path(
            project_root=fallback_project_root,
            path_as_string=root_path_as_string,
        )

        return ProjectSettings(
            name=ProjectName(project_name_as_string),
            root_path=root_path,
        )

    def build_about_settings(
        self,
        context_data: TomlData,
        project_root: Path,
    ) -> AboutSettings:
        about_data: TomlData = self.get_table(context_data, "about")
        file_path_as_string: str = self.get_string(
            data=about_data,
            key="file_path",
            default=".dev_tools/about_current_project.md",
        )
        file_path: Path = self.resolve_project_relative_path(
            project_root=project_root,
            path_as_string=file_path_as_string,
        )

        return AboutSettings(file_path=file_path)

    def build_output_settings(
        self,
        context_data: TomlData,
        project_root: Path,
    ) -> OutputSettings:
        output_data: TomlData = self.get_table(context_data, "output")
        directory_as_string: str = self.get_string(
            data=output_data,
            key="directory",
            default=".dev_tools/output",
        )
        directory_path: Path = self.resolve_project_relative_path(
            project_root=project_root,
            path_as_string=directory_as_string,
        )
        combined_context_file_name: str = self.get_string(
            data=output_data,
            key="combined_context_file_name",
            default="combined_context.txt",
        )
        tree_file_name: str = self.get_string(
            data=output_data,
            key="tree_file_name",
            default="tree.txt",
        )
        chunk_file_prefix: str = self.get_string(
            data=output_data,
            key="chunk_file_prefix",
            default="context_",
        )
        chunk_file_extension: str = self.get_string(
            data=output_data,
            key="chunk_file_extension",
            default=".txt",
        )

        return OutputSettings(
            directory_path=directory_path,
            combined_context_file_name=FileName(combined_context_file_name),
            tree_file_name=FileName(tree_file_name),
            chunk_file_prefix=ChunkFilePrefix(chunk_file_prefix),
            chunk_file_extension=ChunkFileExtension(chunk_file_extension),
        )

    def build_export_settings(self, context_data: TomlData) -> ExportSettings:
        export_data: TomlData = self.get_table(context_data, "export")
        file_separator: str = self.get_string(
            data=export_data,
            key="file_separator",
            default="--- FILE SEPARATOR ---",
        )
        empty_file_marker: str = self.get_string(
            data=export_data,
            key="empty_file_marker",
            default="# File is empty",
        )
        maximum_lines_per_chunk: int = self.get_int(
            data=export_data,
            key="maximum_lines_per_chunk",
            default=2500,
        )

        return ExportSettings(
            file_separator=FileSeparator(file_separator),
            empty_file_marker=EmptyFileMarker(empty_file_marker),
            maximum_lines_per_chunk=MaximumLinesPerChunk(maximum_lines_per_chunk),
        )

    def build_include_settings(self, include_data: TomlData) -> IncludeSettings:
        return IncludeSettings(
            directories=self.get_relative_path_strings(include_data, "directories"),
            files=self.get_relative_path_strings(include_data, "files"),
            extensions=self.get_file_extensions(include_data, "extensions"),
        )

    def build_exclude_settings(self, exclude_data: TomlData) -> ExcludeSettings:
        return ExcludeSettings(
            directories=self.get_directory_names(exclude_data, "directories"),
            directory_suffixes=self.get_directory_suffixes(
                exclude_data,
                "directory_suffixes",
            ),
            files=self.get_file_names(exclude_data, "files"),
            extensions=self.get_file_extensions(exclude_data, "extensions"),
        )

    def resolve_project_relative_path(
        self,
        project_root: Path,
        path_as_string: str,
    ) -> Path:
        candidate_path: Path = Path(path_as_string)

        if candidate_path.is_absolute():
            return candidate_path.resolve()

        return (project_root / candidate_path).resolve()

    def get_table(self, data: TomlData, key: str) -> TomlData:
        value: object | None = data.get(key)

        if value is None:
            return {}

        if not isinstance(value, dict):
            raise TypeError(f"Expected TOML table `{key}` to be a table.")

        result: TomlData = {}
        for raw_key, raw_value in value.items():  # pyright: ignore[reportUnknownVariableType]
            if not isinstance(raw_key, str):
                raise TypeError(f"Expected TOML table `{key}` keys to be strings.")

            result[raw_key] = raw_value

        return result

    def get_string(self, data: TomlData, key: str, default: str) -> str:
        value: object | None = data.get(key)

        if value is None:
            return default

        if not isinstance(value, str):
            raise TypeError(f"Expected `{key}` to be string.")

        return value

    def get_int(self, data: TomlData, key: str, default: int) -> int:
        value: object | None = data.get(key)

        if value is None:
            return default

        if not isinstance(value, int):
            raise TypeError(f"Expected `{key}` to be integer.")

        return value

    def get_string_items(self, data: TomlData, key: str) -> tuple[str, ...]:
        value: object | None = data.get(key)

        if value is None:
            return ()

        if not isinstance(value, list):
            raise TypeError(f"Expected `{key}` to be list of strings.")

        result: list[str] = []
        raw_item: object
        for raw_item in value:  # pyright: ignore[reportUnknownVariableType]
            if not isinstance(raw_item, str):
                raise TypeError(f"Expected all `{key}` items to be strings.")

            result.append(raw_item)

        return tuple(result)

    def get_relative_path_strings(
        self,
        data: TomlData,
        key: str,
    ) -> RelativePathStrings:
        string_items: tuple[str, ...] = self.get_string_items(data=data, key=key)
        result: list[RelativePathString] = []

        for string_item in string_items:
            normalized_path: str = string_item.replace("\\", "/").strip("/")
            if normalized_path == "":
                continue

            result.append(RelativePathString(normalized_path))

        return tuple(result)

    def get_file_extensions(self, data: TomlData, key: str) -> FileExtensions:
        string_items: tuple[str, ...] = self.get_string_items(data=data, key=key)
        result: list[FileExtension] = []

        for string_item in string_items:
            normalized_extension: str = string_item.removeprefix(".").lower()
            if normalized_extension == "":
                continue

            result.append(FileExtension(normalized_extension))

        return tuple(result)

    def get_directory_names(self, data: TomlData, key: str) -> DirectoryNames:
        string_items: tuple[str, ...] = self.get_string_items(data=data, key=key)
        result: list[DirectoryName] = []

        for string_item in string_items:
            if string_item == "":
                continue

            result.append(DirectoryName(string_item))

        return tuple(result)

    def get_directory_suffixes(
        self,
        data: TomlData,
        key: str,
    ) -> DirectorySuffixes:
        string_items: tuple[str, ...] = self.get_string_items(data=data, key=key)
        result: list[DirectorySuffix] = []

        for string_item in string_items:
            normalized_suffix: str = string_item.strip().lower()

            if normalized_suffix == "":
                continue

            if not normalized_suffix.startswith("."):
                normalized_suffix = "." + normalized_suffix

            result.append(DirectorySuffix(normalized_suffix))

        return tuple(result)

    def get_file_names(self, data: TomlData, key: str) -> FileNames:
        string_items: tuple[str, ...] = self.get_string_items(data=data, key=key)
        result: list[FileName] = []

        for string_item in string_items:
            if string_item == "":
                continue

            result.append(FileName(string_item))

        return tuple(result)
