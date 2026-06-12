from __future__ import annotations

import tomllib


class TomlSectionMergeService:
    def merge_missing_sections(
        self,
        current_content: str,
        managed_content: str,
    ) -> str:
        self.validate_toml(current_content)
        self.validate_toml(managed_content)

        current_section_names: tuple[str, ...] = self.collect_section_names(
            current_content
        )
        managed_sections: tuple[tuple[str, str], ...] = self.collect_sections(
            managed_content
        )
        missing_section_contents: list[str] = []

        for section_name, section_content in managed_sections:
            if section_name in current_section_names:
                continue

            missing_section_contents.append(section_content.rstrip())

        if not missing_section_contents:
            return self.normalize_trailing_newline(current_content)

        updated_content: str = current_content.rstrip()
        if updated_content:
            updated_content = updated_content + "\n\n"

        return updated_content + "\n\n".join(missing_section_contents) + "\n"

    def collect_missing_section_names(
        self,
        current_content: str,
        managed_content: str,
    ) -> tuple[str, ...]:
        self.validate_toml(current_content)
        self.validate_toml(managed_content)

        current_section_names: tuple[str, ...] = self.collect_section_names(
            current_content
        )
        managed_sections: tuple[tuple[str, str], ...] = self.collect_sections(
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

    def validate_toml(self, content: str) -> None:
        if not content.strip():
            return

        tomllib.loads(content)

    def collect_section_names(self, content: str) -> tuple[str, ...]:
        section_names: list[str] = []

        for raw_line in content.splitlines():
            stripped_line: str = raw_line.strip()

            if not self.is_section_header(stripped_line):
                continue

            section_names.append(self.normalize_section_name(stripped_line))

        return tuple(section_names)

    def collect_sections(self, content: str) -> tuple[tuple[str, str], ...]:
        sections: list[tuple[str, str]] = []
        active_section_name: str | None = None
        active_section_lines: list[str] = []
        preamble_lines: list[str] = []

        for raw_line in content.splitlines():
            stripped_line: str = raw_line.strip()

            if self.is_section_header(stripped_line):
                if active_section_name is not None:
                    sections.append(
                        (
                            active_section_name,
                            "\n".join(active_section_lines),
                        )
                    )

                active_section_name = self.normalize_section_name(stripped_line)
                active_section_lines = []
                active_section_lines.extend(preamble_lines)
                preamble_lines = []
                active_section_lines.append(raw_line)
                continue

            if active_section_name is None:
                if stripped_line:
                    preamble_lines.append(raw_line)
                continue

            active_section_lines.append(raw_line)

        if active_section_name is not None:
            sections.append((active_section_name, "\n".join(active_section_lines)))

        return tuple(sections)

    def is_section_header(self, stripped_line: str) -> bool:
        return stripped_line.startswith("[") and stripped_line.endswith("]")

    def normalize_section_name(self, stripped_line: str) -> str:
        section_name: str = stripped_line.strip("[]").strip()
        return section_name

    def normalize_trailing_newline(self, content: str) -> str:
        if content == "":
            return content

        return content.rstrip("\n") + "\n"
