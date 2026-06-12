from __future__ import annotations

from pathlib import Path

from base_pydantic_schemas._immutable_dto import ImmutableDTO

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
    EmptyFileMarker,
    FileName,
    FileSeparator,
    ProjectName,
)


class ProjectSettings(ImmutableDTO):
    name: ProjectName
    root_path: Path


class AboutSettings(ImmutableDTO):
    file_path: Path


class OutputSettings(ImmutableDTO):
    directory_path: Path
    combined_context_file_name: FileName
    tree_file_name: FileName
    chunk_file_prefix: ChunkFilePrefix
    chunk_file_extension: ChunkFileExtension


class ExportSettings(ImmutableDTO):
    file_separator: FileSeparator
    empty_file_marker: EmptyFileMarker
    maximum_lines_per_chunk: MaximumLinesPerChunk


class IncludeSettings(ImmutableDTO):
    directories: RelativePathStrings
    files: RelativePathStrings
    extensions: FileExtensions


class ExcludeSettings(ImmutableDTO):
    directories: DirectoryNames
    directory_suffixes: DirectorySuffixes
    files: FileNames
    extensions: FileExtensions


class DevToolsContext(ImmutableDTO):
    project: ProjectSettings
    about: AboutSettings
    output: OutputSettings
    export: ExportSettings
    include: IncludeSettings
    exclude: ExcludeSettings
