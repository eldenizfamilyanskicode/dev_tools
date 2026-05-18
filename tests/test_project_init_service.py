from __future__ import annotations

from pathlib import Path
from typing import Any

from dev_tools.project_context.project_root_resolver import ProjectRootResolver
from dev_tools.project_init.application_service import ProjectInitService
from dev_tools.project_init.git_exclude import GitExcludeService
from dev_tools.project_init.template_writer import ProjectContextTemplateWriter
from dev_tools.shared.file_system import FileSystem


class RecordingIncludeFileUpdateService:
    def __init__(self) -> None:
        self.requested_project_root: Path | None = None

    def update_include_file(self, requested_project_root: Path | None) -> Path:
        self.requested_project_root = requested_project_root
        return requested_project_root / ".dev_tools" / "include.toml"  # type: ignore[operator]


class RecordingProjectBootstrapService:
    def __init__(self) -> None:
        self.requests: list[Any] = []

    def bootstrap_project(self, request: Any) -> Any:
        self.requests.append(request)
        return None

    def render_plan(self, plan: Any) -> str:
        return ""


def test_old_dev_tools_init_behavior_still_works(tmp_path: Path) -> None:
    git_info_directory: Path = tmp_path / ".git" / "info"
    git_info_directory.mkdir(parents=True)
    (git_info_directory / "exclude").write_text("", encoding="utf-8")
    file_system: FileSystem = FileSystem()
    include_file_update_service: RecordingIncludeFileUpdateService = (
        RecordingIncludeFileUpdateService()
    )
    project_bootstrap_service: RecordingProjectBootstrapService = (
        RecordingProjectBootstrapService()
    )
    project_init_service: ProjectInitService = ProjectInitService(
        project_root_resolver=ProjectRootResolver(),
        file_system=file_system,
        template_writer=ProjectContextTemplateWriter(file_system),
        git_exclude_service=GitExcludeService(file_system),
        include_file_update_service=include_file_update_service,  # type: ignore[arg-type]
        project_bootstrap_service=project_bootstrap_service,  # type: ignore[arg-type]
    )

    initialized_project_root: Path = project_init_service.initialize_project(
        requested_project_root=tmp_path,
        force=False,
        about_file_path=None,
    )

    assert initialized_project_root == tmp_path
    assert (tmp_path / ".dev_tools" / "context.toml").exists()
    assert (tmp_path / ".dev_tools" / "include.toml").exists()
    assert (tmp_path / ".dev_tools" / "exclude.toml").exists()
    assert (tmp_path / ".dev_tools" / "about_current_project.md").exists()
    assert (tmp_path / ".dev_tools" / "output").is_dir()
    assert include_file_update_service.requested_project_root == tmp_path
    assert len(project_bootstrap_service.requests) == 1
    assert ".dev_tools/" in (git_info_directory / "exclude").read_text(
        encoding="utf-8"
    )
