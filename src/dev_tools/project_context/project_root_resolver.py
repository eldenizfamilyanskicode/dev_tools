from __future__ import annotations

from pathlib import Path


class ProjectRootResolver:
    def resolve_for_init(self, requested_project_root: Path | None = None) -> Path:
        project_root: Path = self.resolve_candidate_project_root(requested_project_root)
        self.ensure_directory_exists(project_root)
        self.ensure_git_directory_exists(project_root)
        return project_root

    def resolve_existing_context(
        self,
        requested_project_root: Path | None = None,
    ) -> Path:
        if requested_project_root is not None:
            project_root: Path = requested_project_root.resolve()
            self.ensure_directory_exists(project_root)
            self.ensure_context_exists(project_root)
            return project_root

        current_directory: Path = Path.cwd().resolve()

        for candidate_directory in self.iterate_current_and_parents(current_directory):
            context_file_path: Path = (
                candidate_directory / ".dev_tools" / "context.toml"
            )
            if context_file_path.exists():
                return candidate_directory

        git_project_root: Path = self.find_nearest_git_root(current_directory)
        self.ensure_context_exists(git_project_root)
        return git_project_root

    def resolve_candidate_project_root(
        self,
        requested_project_root: Path | None,
    ) -> Path:
        if requested_project_root is not None:
            return requested_project_root.resolve()

        return self.find_nearest_git_root(Path.cwd())

    def find_nearest_git_root(self, starting_directory: Path) -> Path:
        resolved_starting_directory: Path = starting_directory.resolve()

        for candidate_directory in self.iterate_current_and_parents(
            resolved_starting_directory
        ):
            git_directory: Path = candidate_directory / ".git"
            if git_directory.exists():
                return candidate_directory

        raise FileNotFoundError(
            f"Unable to find git root from directory: {resolved_starting_directory}"
        )

    def iterate_current_and_parents(self, starting_directory: Path) -> tuple[Path, ...]:
        directories: list[Path] = []
        directories.append(starting_directory)

        for parent_directory in starting_directory.parents:
            directories.append(parent_directory)

        return tuple(directories)

    def ensure_directory_exists(self, project_root: Path) -> None:
        if not project_root.exists():
            raise FileNotFoundError(f"Project root does not exist: {project_root}")

        if not project_root.is_dir():
            raise NotADirectoryError(f"Project root is not a directory: {project_root}")

    def ensure_git_directory_exists(self, project_root: Path) -> None:
        git_directory: Path = project_root / ".git"

        if not git_directory.exists():
            raise FileNotFoundError(
                f"Git directory not found. Run inside a git repo: {project_root}"
            )

    def ensure_context_exists(self, project_root: Path) -> None:
        context_file_path: Path = project_root / ".dev_tools" / "context.toml"

        if not context_file_path.exists():
            raise FileNotFoundError(
                f"Dev tools context not found: {context_file_path}. "
                "Run `dev-tools init` first."
            )
