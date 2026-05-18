from __future__ import annotations

from pathlib import Path

from dev_tools.shared.file_system import FileSystem
from dev_tools.typings.strings import GitExcludeLine


class GitExcludeService:
    def __init__(self, file_system: FileSystem) -> None:
        self.file_system = file_system

    def ensure_dev_tools_ignored(self, project_root: Path) -> None:
        self.ensure_project_context_ignored(
            project_root=project_root,
            additional_ignored_paths=(),
        )

    def ensure_project_context_ignored(
        self,
        project_root: Path,
        additional_ignored_paths: tuple[Path, ...],
    ) -> None:
        git_exclude_file_path: Path = project_root / ".git" / "info" / "exclude"

        if not git_exclude_file_path.exists():
            raise FileNotFoundError(
                f"Git exclude file not found: {git_exclude_file_path}"
            )

        self.file_system.append_line_if_missing(
            file_path=git_exclude_file_path,
            line=GitExcludeLine(".dev_tools/"),
        )

        for additional_ignored_path in additional_ignored_paths:
            exclude_line: GitExcludeLine = self.build_git_exclude_line(
                additional_ignored_path
            )
            self.file_system.append_line_if_missing(
                file_path=git_exclude_file_path,
                line=exclude_line,
            )

    def build_git_exclude_line(self, relative_path: Path) -> GitExcludeLine:
        normalized_path: str = relative_path.as_posix().strip("/")

        if normalized_path == "":
            raise ValueError("Cannot ignore empty git exclude path.")

        return GitExcludeLine(normalized_path)
