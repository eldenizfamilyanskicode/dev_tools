from __future__ import annotations

import json

from dev_tools.global_cli.constants import VSCODE_FILES_EXCLUDE_SETTING_NAME
from dev_tools.global_cli.exceptions import GlobalCliSetupError
from dev_tools.global_cli.jsonc_object_scanner import (
    JsoncObjectMember,
    JsoncObjectScanner,
    JsoncObjectSpan,
)


class VsCodeSettingsJsoncEditor:
    def __init__(self, jsonc_object_scanner: JsoncObjectScanner | None = None) -> None:
        self.jsonc_object_scanner = jsonc_object_scanner or JsoncObjectScanner()

    def merge_files_exclude_patterns(
        self,
        current_content: str,
        file_patterns: tuple[str, ...],
    ) -> str:
        if current_content.strip() == "":
            return self.build_new_settings_document(file_patterns)

        root_span: JsoncObjectSpan = self.jsonc_object_scanner.find_root_object_span(
            current_content
        )
        root_members: tuple[JsoncObjectMember, ...]
        root_members = self.jsonc_object_scanner.parse_object_members(
            content=current_content,
            object_span=root_span,
        )
        files_exclude_member: JsoncObjectMember | None
        files_exclude_member = self.jsonc_object_scanner.find_member(
            members=root_members,
            key=VSCODE_FILES_EXCLUDE_SETTING_NAME,
        )

        if files_exclude_member is None:
            return self.add_files_exclude_member(
                current_content=current_content,
                root_span=root_span,
                root_members=root_members,
                file_patterns=file_patterns,
            )

        return self.replace_files_exclude_member(
            current_content=current_content,
            files_exclude_member=files_exclude_member,
            file_patterns=file_patterns,
        )

    def build_new_settings_document(self, file_patterns: tuple[str, ...]) -> str:
        files_exclude_content: str = self.build_files_exclude_object_content(
            current_content="",
            existing_members=(),
            member_indent="    ",
            closing_indent="  ",
            file_patterns=file_patterns,
        )
        return (
            "{\n"
            f'  "{VSCODE_FILES_EXCLUDE_SETTING_NAME}": '
            f"{files_exclude_content}\n"
            "}\n"
        )

    def add_files_exclude_member(
        self,
        current_content: str,
        root_span: JsoncObjectSpan,
        root_members: tuple[JsoncObjectMember, ...],
        file_patterns: tuple[str, ...],
    ) -> str:
        root_closing_indent: str = self.jsonc_object_scanner.resolve_line_indent(
            content=current_content,
            index=root_span.close_brace_index,
        )
        member_indent: str = f"{root_closing_indent}  "
        if root_members:
            member_indent = self.jsonc_object_scanner.resolve_line_indent(
                content=current_content,
                index=root_members[0].key_start_index,
            )

        files_exclude_content: str = self.build_files_exclude_object_content(
            current_content=current_content,
            existing_members=(),
            member_indent=f"{member_indent}  ",
            closing_indent=member_indent,
            file_patterns=file_patterns,
        )
        member_content: str = (
            f'{member_indent}"{VSCODE_FILES_EXCLUDE_SETTING_NAME}": '
            f"{files_exclude_content}"
        )

        if not root_members:
            return (
                current_content[: root_span.open_brace_index + 1]
                + "\n"
                + member_content
                + "\n"
                + root_closing_indent
                + current_content[root_span.close_brace_index :]
            )

        last_member: JsoncObjectMember = root_members[-1]
        separator_content: str = ""
        if last_member.comma_index is None:
            separator_content = ","

        return (
            current_content[: last_member.value_end_index]
            + separator_content
            + current_content[last_member.value_end_index : root_span.close_brace_index]
            + "\n"
            + member_content
            + current_content[root_span.close_brace_index :]
        )

    def replace_files_exclude_member(
        self,
        current_content: str,
        files_exclude_member: JsoncObjectMember,
        file_patterns: tuple[str, ...],
    ) -> str:
        value_start_index: int = self.jsonc_object_scanner.skip_whitespace_and_comments(
            content=current_content,
            start_index=files_exclude_member.value_start_index,
        )
        if (
            value_start_index >= len(current_content)
            or current_content[value_start_index] != "{"
        ):
            raise GlobalCliSetupError(
                "Expected files.exclude to be an object in VS Code user settings."
            )

        files_exclude_span: JsoncObjectSpan = JsoncObjectSpan(
            open_brace_index=value_start_index,
            close_brace_index=self.jsonc_object_scanner.find_matching_closing_brace(
                content=current_content,
                open_brace_index=value_start_index,
            ),
        )
        existing_members: tuple[JsoncObjectMember, ...]
        existing_members = self.jsonc_object_scanner.parse_object_members(
            content=current_content,
            object_span=files_exclude_span,
        )
        closing_indent: str = self.jsonc_object_scanner.resolve_line_indent(
            content=current_content,
            index=files_exclude_span.close_brace_index,
        )
        member_indent: str = f"{closing_indent}  "
        if existing_members:
            member_indent = self.jsonc_object_scanner.resolve_line_indent(
                content=current_content,
                index=existing_members[0].key_start_index,
            )

        files_exclude_content: str = self.build_files_exclude_object_content(
            current_content=current_content,
            existing_members=existing_members,
            member_indent=member_indent,
            closing_indent=closing_indent,
            file_patterns=file_patterns,
        )

        return (
            current_content[: files_exclude_span.open_brace_index]
            + files_exclude_content
            + current_content[files_exclude_span.close_brace_index + 1 :]
        )

    def build_files_exclude_object_content(
        self,
        current_content: str,
        existing_members: tuple[JsoncObjectMember, ...],
        member_indent: str,
        closing_indent: str,
        file_patterns: tuple[str, ...],
    ) -> str:
        managed_patterns: set[str] = set(file_patterns)
        ordered_keys: list[str] = []
        existing_values_by_key: dict[str, str] = {}

        for existing_member in existing_members:
            ordered_keys.append(existing_member.key)
            existing_value: str = current_content[
                existing_member.value_start_index : existing_member.value_end_index
            ].strip()
            existing_values_by_key[existing_member.key] = existing_value

        for file_pattern in file_patterns:
            if file_pattern not in existing_values_by_key:
                ordered_keys.append(file_pattern)

        lines: list[str] = ["{"]
        for key_index, key in enumerate(ordered_keys):
            entry_value: str = existing_values_by_key.get(key, "true")
            if key in managed_patterns:
                entry_value = "true"

            entry_suffix: str = ","
            if key_index == len(ordered_keys) - 1:
                entry_suffix = ""

            lines.append(
                f"{member_indent}{json.dumps(key)}: {entry_value}{entry_suffix}"
            )

        lines.append(f"{closing_indent}}}")
        return "\n".join(lines)
