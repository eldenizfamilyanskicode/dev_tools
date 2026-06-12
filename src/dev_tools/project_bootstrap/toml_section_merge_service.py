from __future__ import annotations

import tomllib
from dataclasses import dataclass

from dev_tools.project_bootstrap.toml_section_parser import (
    TomlKeyBlock,
    TomlSection,
    TomlSectionParser,
)


@dataclass(frozen=True)
class TomlMergeResult:
    content: str
    applied_paths: tuple[str, ...]
    preserved_paths: tuple[str, ...]
    conflict_paths: tuple[str, ...]


class TomlSectionMergeService:
    def __init__(self, toml_section_parser: TomlSectionParser) -> None:
        self.toml_section_parser = toml_section_parser

    def build_merge_result(
        self,
        current_content: str,
        managed_content: str,
    ) -> TomlMergeResult:
        self.validate_toml(current_content)
        self.validate_toml(managed_content)

        current_sections: tuple[TomlSection, ...]
        current_sections = self.toml_section_parser.collect_section_models(
            current_content
        )
        managed_sections: tuple[TomlSection, ...]
        managed_sections = self.toml_section_parser.collect_section_models(
            managed_content
        )
        current_sections_by_name: dict[str, tuple[TomlSection, ...]]
        current_sections_by_name = self.toml_section_parser.group_sections_by_name(
            current_sections
        )
        output_lines: list[str] = list(current_content.splitlines())
        inserted_line_count: int = 0
        appended_section_contents: list[str] = []
        applied_paths: list[str] = []
        preserved_paths: list[str] = []
        conflict_paths: list[str] = []

        for managed_section in managed_sections:
            matching_current_sections: tuple[TomlSection, ...] = (
                current_sections_by_name.get(managed_section.name, ())
            )

            if not matching_current_sections:
                appended_section_contents.append(
                    "\n".join(managed_section.lines).rstrip()
                )
                applied_paths.append(
                    self.toml_section_parser.format_section_path(managed_section)
                )
                continue

            if self.toml_section_parser.has_section_kind_conflict(
                current_sections=matching_current_sections,
                managed_section=managed_section,
            ):
                conflict_paths.append(
                    self.toml_section_parser.format_section_path(managed_section)
                )
                continue

            if managed_section.is_array_table:
                preserved_paths.append(
                    self.toml_section_parser.format_section_path(managed_section)
                )
                continue

            current_section: TomlSection = matching_current_sections[0]
            section_merge_result: tuple[tuple[TomlKeyBlock, ...], tuple[str, ...]]
            section_merge_result = self.toml_section_parser.collect_missing_key_blocks(
                current_section=current_section,
                managed_section=managed_section,
            )
            missing_key_blocks: tuple[TomlKeyBlock, ...]
            preserved_key_paths: tuple[str, ...]
            missing_key_blocks, preserved_key_paths = section_merge_result
            preserved_paths.extend(preserved_key_paths)

            if not missing_key_blocks:
                continue

            for missing_key_block in missing_key_blocks:
                applied_paths.append(
                    self.toml_section_parser.format_key_path(
                        section=managed_section,
                        key=missing_key_block.key,
                    )
                )

            insertion_index: int = self.resolve_section_insertion_index(
                output_lines=output_lines,
                section=current_section,
                inserted_line_count=inserted_line_count,
            )
            insertion_lines: tuple[str, ...] = self.build_insertion_lines(
                missing_key_blocks
            )
            for insertion_line_offset, insertion_line in enumerate(insertion_lines):
                output_lines.insert(
                    insertion_index + insertion_line_offset,
                    insertion_line,
                )

            inserted_line_count = inserted_line_count + len(insertion_lines)

        if appended_section_contents:
            output_lines = self.append_missing_sections(
                output_lines=output_lines,
                section_contents=tuple(appended_section_contents),
            )

        return TomlMergeResult(
            content=self.join_lines(output_lines),
            applied_paths=tuple(applied_paths),
            preserved_paths=tuple(preserved_paths),
            conflict_paths=tuple(conflict_paths),
        )

    def merge_missing_sections(
        self,
        current_content: str,
        managed_content: str,
    ) -> str:
        merge_result: TomlMergeResult = self.build_merge_result(
            current_content=current_content,
            managed_content=managed_content,
        )
        return merge_result.content

    def collect_missing_section_names(
        self,
        current_content: str,
        managed_content: str,
    ) -> tuple[str, ...]:
        self.validate_toml(current_content)
        self.validate_toml(managed_content)

        current_section_names: tuple[str, ...]
        current_section_names = self.toml_section_parser.collect_section_names(
            current_content
        )
        managed_sections: tuple[tuple[str, str], ...]
        managed_sections = self.toml_section_parser.collect_sections(
            managed_content
        )
        missing_section_names: list[str] = []

        for section_name, section_content in managed_sections:
            if section_content == "":
                continue

            if section_name in current_section_names:
                continue

            missing_section_names.append(f"[{section_name}]")

        return tuple(missing_section_names)

    def collect_preserved_section_names(
        self,
        current_content: str,
        managed_content: str,
    ) -> tuple[str, ...]:
        self.validate_toml(current_content)
        self.validate_toml(managed_content)

        current_section_names: tuple[str, ...]
        current_section_names = self.toml_section_parser.collect_section_names(
            current_content
        )
        managed_sections: tuple[tuple[str, str], ...]
        managed_sections = self.toml_section_parser.collect_sections(
            managed_content
        )
        preserved_section_names: list[str] = []

        for section_name, section_content in managed_sections:
            if section_content == "":
                continue

            if section_name not in current_section_names:
                continue

            preserved_section_names.append(f"[{section_name}]")

        return tuple(preserved_section_names)

    def validate_toml(self, content: str) -> None:
        if not content.strip():
            return

        tomllib.loads(content)

    def resolve_section_insertion_index(
        self,
        output_lines: list[str],
        section: TomlSection,
        inserted_line_count: int,
    ) -> int:
        insertion_index: int = section.end_line_index + inserted_line_count
        minimum_insertion_index: int = (
            section.start_line_index + inserted_line_count + 1
        )

        while insertion_index > minimum_insertion_index:
            previous_line: str = output_lines[insertion_index - 1]
            if previous_line.strip() != "":
                break

            insertion_index = insertion_index - 1

        return insertion_index

    def build_insertion_lines(
        self,
        missing_key_blocks: tuple[TomlKeyBlock, ...],
    ) -> tuple[str, ...]:
        insertion_lines: list[str] = []

        for missing_key_block in missing_key_blocks:
            for missing_key_line in missing_key_block.lines:
                insertion_lines.append(missing_key_line)

        return tuple(insertion_lines)

    def append_missing_sections(
        self,
        output_lines: list[str],
        section_contents: tuple[str, ...],
    ) -> list[str]:
        updated_output_lines: list[str] = list(output_lines)

        if updated_output_lines:
            while updated_output_lines and updated_output_lines[-1].strip() == "":
                updated_output_lines.pop()

            updated_output_lines.append("")

        for section_index, section_content in enumerate(section_contents):
            if section_index > 0:
                updated_output_lines.append("")

            for section_line in section_content.splitlines():
                updated_output_lines.append(section_line)

        return updated_output_lines

    def join_lines(self, lines: list[str]) -> str:
        if not lines:
            return ""

        return "\n".join(lines).rstrip("\n") + "\n"
