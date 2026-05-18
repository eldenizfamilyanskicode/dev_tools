from __future__ import annotations

from dev_tools.project_context.models import DevToolsContext
from dev_tools.typings.collections import (
    FileExtensions,
    RelativePathStrings,
)
from dev_tools.typings.strings import FileExtension, RelativePathString


class IncludeFileTemplateRenderer:
    def render_include_file(
        self,
        dev_tools_context: DevToolsContext,
        candidate_file_paths: list[RelativePathString],
    ) -> str:
        lines: list[str] = []

        lines.append("# Relative directories from project root.")
        lines.append("# Active values include every file inside the directory.")
        self.append_relative_path_array(
            lines=lines,
            array_name="directories",
            values=dev_tools_context.include.directories,
        )
        lines.append("")

        lines.append("# Exact relative file paths from project root.")
        lines.append("# Uncomment paths you want in the exported context.")
        lines.append("# Run `dev-tools update-include-files` to refresh this catalog.")
        self.append_file_catalog_array(
            lines=lines,
            selected_file_paths=dev_tools_context.include.files,
            candidate_file_paths=candidate_file_paths,
        )
        lines.append("")

        lines.append("# Extensions without dot.")
        lines.append("# Active values include files by extension unless excluded.")
        self.append_extension_array(
            lines=lines,
            array_name="extensions",
            values=dev_tools_context.include.extensions,
        )
        lines.append("")

        return "\n".join(lines)

    def append_relative_path_array(
        self,
        lines: list[str],
        array_name: str,
        values: RelativePathStrings,
    ) -> None:
        lines.append(f"{array_name} = [")

        for value in values:
            escaped_value: str = self.escape_toml_string(str(value))
            lines.append(f'    "{escaped_value}",')

        lines.append("]")

    def append_extension_array(
        self,
        lines: list[str],
        array_name: str,
        values: FileExtensions,
    ) -> None:
        lines.append(f"{array_name} = [")

        for value in values:
            normalized_value: str = self.normalize_extension(value)
            escaped_value: str = self.escape_toml_string(normalized_value)
            lines.append(f'    "{escaped_value}",')

        lines.append("]")

    def append_file_catalog_array(
        self,
        lines: list[str],
        selected_file_paths: RelativePathStrings,
        candidate_file_paths: list[RelativePathString],
    ) -> None:
        selected_file_path_strings: set[str] = self.build_relative_path_string_set(
            selected_file_paths
        )
        candidate_file_path_strings: set[str] = self.build_candidate_path_string_set(
            candidate_file_paths
        )
        emitted_file_path_strings: set[str] = set()

        lines.append("files = [")
        escaped_value: str

        for selected_file_path in selected_file_paths:
            selected_file_path_as_string: str = str(selected_file_path)

            if selected_file_path_as_string in candidate_file_path_strings:
                continue

            escaped_value = self.escape_toml_string(selected_file_path_as_string)
            lines.append(f'    "{escaped_value}",  # selected, currently not found')
            emitted_file_path_strings.add(selected_file_path_as_string)

        for candidate_file_path in candidate_file_paths:
            candidate_file_path_as_string: str = str(candidate_file_path)

            if candidate_file_path_as_string in emitted_file_path_strings:
                continue

            escaped_value = self.escape_toml_string(candidate_file_path_as_string)

            if candidate_file_path_as_string in selected_file_path_strings:
                lines.append(f'    "{escaped_value}",')
            else:
                lines.append(f'    # "{escaped_value}",')

            emitted_file_path_strings.add(candidate_file_path_as_string)

        lines.append("]")

    def build_relative_path_string_set(
        self,
        values: RelativePathStrings,
    ) -> set[str]:
        result: set[str] = set()

        for value in values:
            result.add(str(value))

        return result

    def build_candidate_path_string_set(
        self,
        values: list[RelativePathString],
    ) -> set[str]:
        result: set[str] = set()

        for value in values:
            result.add(str(value))

        return result

    def normalize_extension(self, value: FileExtension) -> str:
        return str(value).removeprefix(".").lower()

    def escape_toml_string(self, value: str) -> str:
        escaped_value: str = value.replace("\\", "\\\\")
        escaped_value = escaped_value.replace('"', '\\"')
        return escaped_value
