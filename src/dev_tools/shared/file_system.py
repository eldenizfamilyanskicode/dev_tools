from __future__ import annotations

from pathlib import Path

from dev_tools.typings.strings import GitExcludeLine


class FileSystem:
    def ensure_directory(self, directory_path: Path) -> None:
        directory_path.mkdir(parents=True, exist_ok=True)

    def write_text_if_missing(
        self,
        file_path: Path,
        content: str,
        force: bool,
    ) -> None:
        if file_path.exists() and not force:
            return

        self.write_text(file_path=file_path, content=content)

    def write_text(
        self,
        file_path: Path,
        content: str,
    ) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    def read_text(self, file_path: Path) -> str:
        return file_path.read_text(encoding="utf-8")

    def read_text_with_fallback(self, file_path: Path) -> str:
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return file_path.read_text(encoding="utf-8", errors="replace")

    def append_line_if_missing(
        self,
        file_path: Path,
        line: GitExcludeLine,
    ) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)

        current_content: str = ""
        if file_path.exists():
            current_content = file_path.read_text(encoding="utf-8")

        line_as_string: str = str(line).strip()
        existing_lines: list[str] = current_content.splitlines()

        for existing_line in existing_lines:
            if existing_line.strip() == line_as_string:
                return

        if current_content and not current_content.endswith("\n"):
            current_content = current_content + "\n"

        updated_content: str = current_content + line_as_string + "\n"
        file_path.write_text(updated_content, encoding="utf-8")
