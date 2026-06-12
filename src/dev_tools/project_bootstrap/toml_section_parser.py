from __future__ import annotations

from base_pydantic_schemas import ImmutableDTO


class TomlSection(ImmutableDTO):
    name: str
    header: str
    is_array_table: bool
    start_line_index: int
    end_line_index: int
    lines: tuple[str, ...]


class TomlKeyBlock(ImmutableDTO):
    key: str
    lines: tuple[str, ...]


class TomlSectionParser:
    def collect_section_names(self, content: str) -> tuple[str, ...]:
        section_names: list[str] = []

        for section in self.collect_section_models(content):
            section_names.append(section.name)

        return tuple(section_names)

    def collect_sections(self, content: str) -> tuple[tuple[str, str], ...]:
        sections: list[tuple[str, str]] = []

        for section in self.collect_section_models(content):
            sections.append((section.name, "\n".join(section.lines)))

        return tuple(sections)

    def collect_section_models(self, content: str) -> tuple[TomlSection, ...]:
        lines: list[str] = content.splitlines()
        sections: list[TomlSection] = []
        active_section_name: str | None = None
        active_section_header: str | None = None
        active_section_is_array_table: bool = False
        active_section_start_line_index: int = 0

        for line_index, raw_line in enumerate(lines):
            stripped_line: str = raw_line.strip()

            if not self.is_section_header(stripped_line):
                continue

            if active_section_name is not None and active_section_header is not None:
                sections.append(
                    TomlSection(
                        name=active_section_name,
                        header=active_section_header,
                        is_array_table=active_section_is_array_table,
                        start_line_index=active_section_start_line_index,
                        end_line_index=line_index,
                        lines=tuple(lines[active_section_start_line_index:line_index]),
                    )
                )

            active_section_name = self.normalize_section_name(stripped_line)
            active_section_header = raw_line
            active_section_is_array_table = self.is_array_table_header(stripped_line)
            active_section_start_line_index = line_index

        if active_section_name is not None and active_section_header is not None:
            sections.append(
                TomlSection(
                    name=active_section_name,
                    header=active_section_header,
                    is_array_table=active_section_is_array_table,
                    start_line_index=active_section_start_line_index,
                    end_line_index=len(lines),
                    lines=tuple(lines[active_section_start_line_index:]),
                )
            )

        return tuple(sections)

    def group_sections_by_name(
        self,
        sections: tuple[TomlSection, ...],
    ) -> dict[str, tuple[TomlSection, ...]]:
        grouped_sections: dict[str, list[TomlSection]] = {}

        for section in sections:
            section_group: list[TomlSection] = grouped_sections.setdefault(
                section.name,
                [],
            )
            section_group.append(section)

        frozen_grouped_sections: dict[str, tuple[TomlSection, ...]] = {}
        for section_name, section_group in grouped_sections.items():
            frozen_grouped_sections[section_name] = tuple(section_group)

        return frozen_grouped_sections

    def has_section_kind_conflict(
        self,
        current_sections: tuple[TomlSection, ...],
        managed_section: TomlSection,
    ) -> bool:
        for current_section in current_sections:
            if current_section.is_array_table != managed_section.is_array_table:
                return True

        return False

    def collect_missing_key_blocks(
        self,
        current_section: TomlSection,
        managed_section: TomlSection,
    ) -> tuple[tuple[TomlKeyBlock, ...], tuple[str, ...]]:
        current_key_names: tuple[str, ...] = self.collect_key_names(current_section)
        managed_key_blocks: tuple[TomlKeyBlock, ...] = self.collect_key_blocks(
            managed_section
        )
        missing_key_blocks: list[TomlKeyBlock] = []
        preserved_key_paths: list[str] = []

        for managed_key_block in managed_key_blocks:
            if managed_key_block.key in current_key_names:
                preserved_key_paths.append(
                    self.format_key_path(
                        section=managed_section,
                        key=managed_key_block.key,
                    )
                )
                continue

            missing_key_blocks.append(managed_key_block)

        return tuple(missing_key_blocks), tuple(preserved_key_paths)

    def collect_key_names(self, section: TomlSection) -> tuple[str, ...]:
        key_names: list[str] = []

        for key_block in self.collect_key_blocks(section):
            key_names.append(key_block.key)

        return tuple(key_names)

    def collect_key_blocks(self, section: TomlSection) -> tuple[TomlKeyBlock, ...]:
        key_blocks: list[TomlKeyBlock] = []
        active_key: str | None = None
        active_lines: list[str] = []

        for raw_line in section.lines[1:]:
            stripped_line: str = raw_line.strip()

            if self.is_key_line(stripped_line):
                if active_key is not None:
                    key_blocks.append(
                        TomlKeyBlock(
                            key=active_key,
                            lines=tuple(active_lines),
                        )
                    )

                active_key = self.extract_key_name(stripped_line)
                active_lines = [raw_line]
                continue

            if active_key is not None:
                active_lines.append(raw_line)

        if active_key is not None:
            key_blocks.append(
                TomlKeyBlock(
                    key=active_key,
                    lines=tuple(active_lines),
                )
            )

        return tuple(key_blocks)

    def is_section_header(self, stripped_line: str) -> bool:
        return stripped_line.startswith("[") and stripped_line.endswith("]")

    def is_array_table_header(self, stripped_line: str) -> bool:
        return stripped_line.startswith("[[") and stripped_line.endswith("]]")

    def normalize_section_name(self, stripped_line: str) -> str:
        section_name: str = stripped_line.strip("[]").strip()
        return section_name

    def is_key_line(self, stripped_line: str) -> bool:
        if stripped_line == "":
            return False

        if stripped_line.startswith("#"):
            return False

        if stripped_line.startswith("["):
            return False

        return "=" in stripped_line

    def extract_key_name(self, stripped_line: str) -> str:
        raw_key: str
        raw_key, _, _ = stripped_line.partition("=")
        return raw_key.strip()

    def format_section_path(self, section: TomlSection) -> str:
        if section.is_array_table:
            return f"[[{section.name}]]"

        return f"[{section.name}]"

    def format_key_path(self, section: TomlSection, key: str) -> str:
        return f"{self.format_section_path(section)}.{key}"
