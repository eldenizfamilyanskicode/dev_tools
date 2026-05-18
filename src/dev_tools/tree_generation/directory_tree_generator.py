from __future__ import annotations

from pathlib import Path

from dev_tools.typings.collections import DirectoryNames, FileExtensions, FileNames
from dev_tools.typings.strings import ProjectName


class DirectoryTreeGenerator:
    def generate_directory_tree(
        self,
        project_root: Path,
        project_name: ProjectName,
        excluded_directory_names: DirectoryNames,
        excluded_file_names: FileNames,
        excluded_extensions: FileExtensions,
    ) -> str:
        lines: list[str] = []
        lines.append(f"{project_name}/")

        self.add_directory_lines(
            current_directory=project_root,
            line_prefix="",
            lines=lines,
            excluded_directory_names=excluded_directory_names,
            excluded_file_names=excluded_file_names,
            excluded_extensions=excluded_extensions,
        )

        return "\n".join(lines)

    def add_directory_lines(
        self,
        current_directory: Path,
        line_prefix: str,
        lines: list[str],
        excluded_directory_names: DirectoryNames,
        excluded_file_names: FileNames,
        excluded_extensions: FileExtensions,
    ) -> None:
        visible_entries: list[Path] = self.get_visible_entries(
            current_directory=current_directory,
            excluded_directory_names=excluded_directory_names,
            excluded_file_names=excluded_file_names,
            excluded_extensions=excluded_extensions,
        )
        visible_entry_count: int = len(visible_entries)

        for entry_index in range(visible_entry_count):
            directory_entry: Path = visible_entries[entry_index]
            is_last_entry: bool = entry_index == visible_entry_count - 1
            entry_connector: str = "├── "
            next_line_prefix: str = line_prefix + "│   "

            if is_last_entry:
                entry_connector = "└── "
                next_line_prefix = line_prefix + "    "

            if directory_entry.is_dir():
                lines.append(f"{line_prefix}{entry_connector}{directory_entry.name}/")
                self.add_directory_lines(
                    current_directory=directory_entry,
                    line_prefix=next_line_prefix,
                    lines=lines,
                    excluded_directory_names=excluded_directory_names,
                    excluded_file_names=excluded_file_names,
                    excluded_extensions=excluded_extensions,
                )
                continue

            lines.append(f"{line_prefix}{entry_connector}{directory_entry.name}")

    def get_visible_entries(
        self,
        current_directory: Path,
        excluded_directory_names: DirectoryNames,
        excluded_file_names: FileNames,
        excluded_extensions: FileExtensions,
    ) -> list[Path]:
        directory_entries: list[Path] = []

        try:
            for directory_entry in current_directory.iterdir():
                directory_entries.append(directory_entry)
        except OSError:
            return []

        directory_entries.sort(key=self.get_path_sort_key)

        visible_entries: list[Path] = []
        for directory_entry in directory_entries:
            should_skip: bool = self.should_skip_path(
                path=directory_entry,
                excluded_directory_names=excluded_directory_names,
                excluded_file_names=excluded_file_names,
                excluded_extensions=excluded_extensions,
            )

            if should_skip:
                continue

            visible_entries.append(directory_entry)

        return visible_entries

    def get_path_sort_key(self, path: Path) -> str:
        if path.is_dir():
            return f"0_{path.name.lower()}"

        return f"1_{path.name.lower()}"

    def should_skip_path(
        self,
        path: Path,
        excluded_directory_names: DirectoryNames,
        excluded_file_names: FileNames,
        excluded_extensions: FileExtensions,
    ) -> bool:
        if path.is_dir():
            return self.name_exists(path.name, excluded_directory_names)

        if self.name_exists(path.name, excluded_file_names):
            return True

        extension: str = self.get_extension_without_dot(path)
        if extension == "":
            return False

        return self.name_exists(extension, excluded_extensions)

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
