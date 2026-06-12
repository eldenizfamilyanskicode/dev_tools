from __future__ import annotations

import json
from dataclasses import dataclass

from dev_tools.global_cli.exceptions import GlobalCliSetupError


@dataclass(frozen=True)
class JsoncObjectSpan:
    open_brace_index: int
    close_brace_index: int


@dataclass(frozen=True)
class JsoncObjectMember:
    key: str
    key_start_index: int
    key_end_index: int
    value_start_index: int
    value_end_index: int
    comma_index: int | None


class JsoncObjectScanner:
    def find_root_object_span(self, content: str) -> JsoncObjectSpan:
        open_brace_index: int = self.skip_whitespace_and_comments(
            content=content,
            start_index=0,
        )
        if open_brace_index >= len(content) or content[open_brace_index] != "{":
            raise GlobalCliSetupError(
                "Expected VS Code user settings to start with a JSONC object."
            )

        close_brace_index: int = self.find_matching_closing_brace(
            content=content,
            open_brace_index=open_brace_index,
        )
        trailing_index: int = self.skip_whitespace_and_comments(
            content=content,
            start_index=close_brace_index + 1,
        )
        if trailing_index != len(content):
            raise GlobalCliSetupError(
                "Expected no content after VS Code user settings root object."
            )

        return JsoncObjectSpan(
            open_brace_index=open_brace_index,
            close_brace_index=close_brace_index,
        )

    def parse_object_members(
        self,
        content: str,
        object_span: JsoncObjectSpan,
    ) -> tuple[JsoncObjectMember, ...]:
        members: list[JsoncObjectMember] = []
        cursor_index: int = object_span.open_brace_index + 1

        while cursor_index < object_span.close_brace_index:
            cursor_index = self.skip_whitespace_and_comments(
                content=content,
                start_index=cursor_index,
            )
            if cursor_index >= object_span.close_brace_index:
                break

            if content[cursor_index] == ",":
                cursor_index += 1
                continue

            if content[cursor_index] != '"':
                raise GlobalCliSetupError(
                    "Expected object member name in VS Code user settings JSONC."
                )

            key_start_index: int = cursor_index
            key_end_index: int = self.skip_string(
                content=content,
                start_index=key_start_index,
            )
            key: str = self.parse_string_token(
                content=content,
                start_index=key_start_index,
                end_index=key_end_index,
            )
            cursor_index = self.skip_whitespace_and_comments(
                content=content,
                start_index=key_end_index,
            )
            if (
                cursor_index >= object_span.close_brace_index
                or content[cursor_index] != ":"
            ):
                raise GlobalCliSetupError(
                    f"Expected ':' after VS Code user settings key: {key}"
                )

            value_start_index: int = self.skip_whitespace_and_comments(
                content=content,
                start_index=cursor_index + 1,
            )
            value_boundary_index: int = self.find_value_boundary(
                content=content,
                start_index=value_start_index,
                object_close_index=object_span.close_brace_index,
            )
            value_end_index: int = self.trim_trailing_whitespace(
                content=content,
                start_index=value_start_index,
                end_index=value_boundary_index,
            )
            separator_index: int = self.skip_whitespace_and_comments(
                content=content,
                start_index=value_boundary_index,
            )
            comma_index: int | None = None
            if (
                separator_index < object_span.close_brace_index
                and content[separator_index] == ","
            ):
                comma_index = separator_index
                cursor_index = separator_index + 1
            else:
                cursor_index = separator_index

            members.append(
                JsoncObjectMember(
                    key=key,
                    key_start_index=key_start_index,
                    key_end_index=key_end_index,
                    value_start_index=value_start_index,
                    value_end_index=value_end_index,
                    comma_index=comma_index,
                )
            )

        return tuple(members)

    def parse_string_token(
        self,
        content: str,
        start_index: int,
        end_index: int,
    ) -> str:
        try:
            parsed_value: object = json.loads(content[start_index:end_index])
        except json.JSONDecodeError as error:
            raise GlobalCliSetupError(
                "Expected a valid JSON string token in VS Code user settings."
            ) from error

        if not isinstance(parsed_value, str):
            raise GlobalCliSetupError(
                "Expected a string object key in VS Code user settings."
            )

        return parsed_value

    def find_member(
        self,
        members: tuple[JsoncObjectMember, ...],
        key: str,
    ) -> JsoncObjectMember | None:
        for member in members:
            if member.key == key:
                return member

        return None

    def find_matching_closing_brace(
        self,
        content: str,
        open_brace_index: int,
    ) -> int:
        cursor_index: int = open_brace_index
        brace_depth: int = 0

        while cursor_index < len(content):
            character: str = content[cursor_index]
            if character == '"':
                cursor_index = self.skip_string(
                    content=content,
                    start_index=cursor_index,
                )
                continue

            if self.starts_comment(content=content, index=cursor_index):
                cursor_index = self.skip_comment(
                    content=content,
                    start_index=cursor_index,
                )
                continue

            if character == "{":
                brace_depth += 1
            elif character == "}":
                brace_depth -= 1
                if brace_depth == 0:
                    return cursor_index

            cursor_index += 1

        raise GlobalCliSetupError("VS Code user settings JSONC object is not closed.")

    def find_value_boundary(
        self,
        content: str,
        start_index: int,
        object_close_index: int,
    ) -> int:
        cursor_index: int = start_index
        brace_depth: int = 0
        bracket_depth: int = 0

        while cursor_index < object_close_index:
            character: str = content[cursor_index]
            if character == '"':
                cursor_index = self.skip_string(
                    content=content,
                    start_index=cursor_index,
                )
                continue

            if self.starts_comment(content=content, index=cursor_index):
                cursor_index = self.skip_comment(
                    content=content,
                    start_index=cursor_index,
                )
                continue

            if character == "{":
                brace_depth += 1
            elif character == "}":
                if brace_depth == 0 and bracket_depth == 0:
                    return cursor_index

                brace_depth -= 1
            elif character == "[":
                bracket_depth += 1
            elif character == "]":
                bracket_depth -= 1
            elif character == "," and brace_depth == 0 and bracket_depth == 0:
                return cursor_index

            cursor_index += 1

        return object_close_index

    def skip_whitespace_and_comments(self, content: str, start_index: int) -> int:
        cursor_index: int = start_index

        while cursor_index < len(content):
            character: str = content[cursor_index]
            if character.isspace():
                cursor_index += 1
                continue

            if self.starts_comment(content=content, index=cursor_index):
                cursor_index = self.skip_comment(
                    content=content,
                    start_index=cursor_index,
                )
                continue

            break

        return cursor_index

    def starts_comment(self, content: str, index: int) -> bool:
        return (
            index + 1 < len(content)
            and content[index] == "/"
            and content[index + 1] in ("/", "*")
        )

    def skip_comment(self, content: str, start_index: int) -> int:
        if start_index + 1 >= len(content) or content[start_index] != "/":
            return start_index

        next_character: str = content[start_index + 1]
        if next_character == "/":
            line_end_index: int = content.find("\n", start_index + 2)
            if line_end_index == -1:
                return len(content)

            return line_end_index + 1

        if next_character == "*":
            comment_end_index: int = content.find("*/", start_index + 2)
            if comment_end_index == -1:
                raise GlobalCliSetupError(
                    "VS Code user settings JSONC block comment is not closed."
                )

            return comment_end_index + 2

        return start_index

    def skip_string(self, content: str, start_index: int) -> int:
        cursor_index: int = start_index + 1

        while cursor_index < len(content):
            character: str = content[cursor_index]
            if character == "\\":
                cursor_index += 2
                continue

            if character == '"':
                return cursor_index + 1

            cursor_index += 1

        raise GlobalCliSetupError(
            "VS Code user settings JSONC string token is not closed."
        )

    def trim_trailing_whitespace(
        self,
        content: str,
        start_index: int,
        end_index: int,
    ) -> int:
        cursor_index: int = end_index

        while cursor_index > start_index and content[cursor_index - 1].isspace():
            cursor_index -= 1

        return cursor_index

    def resolve_line_indent(self, content: str, index: int) -> str:
        line_start_index: int = content.rfind("\n", 0, index) + 1
        cursor_index: int = line_start_index
        indent_characters: list[str] = []

        while cursor_index < len(content) and content[cursor_index] in (" ", "\t"):
            indent_characters.append(content[cursor_index])
            cursor_index += 1

        return "".join(indent_characters)
